"""Stratified recall-list builder.

Selects female participants by life stage (approximated by age band) with a
fixed number of APOE e4 carriers and e3/e3 controls per stage, then selects
male participants age-matched to the female selection: each age band gets a
share of the male target proportional to its share of selected females.

Selection is deterministic. By default candidates are taken in file order;
pass ``seed`` to draw them in a reproducible random order instead.
"""

from __future__ import annotations

import csv
import random
import re
from dataclasses import dataclass, field
from pathlib import Path

Row = dict[str, str]

# Female life stages by five-year age band. Age is a proxy for menopausal
# stage here; the input carries no hormonal or clinical staging.
DEFAULT_STAGES: dict[str, list[str]] = {
    "pre": ["35-39", "40-44"],
    "peri": ["45-49"],
    "early": ["50-54"],
    "late": ["55-59", "60-64", "65-69"],
}

E4_CARRIERS = frozenset({"E3/E4", "E4/E4"})
CONTROLS = frozenset({"E3/E3"})


def normalise_genotype(genotype: str) -> str:
    """Return an APOE genotype as ``E<a>/E<b>`` with a <= b.

    Accepts forms such as ``e4/e3``, ``E3E4`` or ``3/4``. Anything that does
    not contain exactly two alleles from 2, 3 and 4 is returned upper-cased
    and unchanged, so it will not match a target genotype.
    """
    alleles = re.findall(r"[234]", genotype)
    if len(alleles) != 2:
        return genotype.strip().upper()
    a, b = sorted(alleles)
    return f"E{a}/E{b}"


def apportion(total: int, weights: dict[str, int]) -> dict[str, int]:
    """Split ``total`` across keys in proportion to ``weights``.

    Uses the largest-remainder method so the parts always sum to ``total``.
    Ties go to the key that sorts first, which keeps the result stable.
    """
    weight_sum = sum(weights.values())
    if total <= 0 or weight_sum == 0:
        return {k: 0 for k in weights}
    quotas = {k: total * w / weight_sum for k, w in weights.items()}
    parts = {k: int(q) for k, q in quotas.items()}
    leftover = total - sum(parts.values())
    by_remainder = sorted(quotas, key=lambda k: (-(quotas[k] - parts[k]), k))
    for k in by_remainder[:leftover]:
        parts[k] += 1
    return parts


@dataclass
class StageAllocation:
    """Participants selected for one stage (or the male arm)."""

    stage_name: str
    e4_carriers: list[Row] = field(default_factory=list)
    e3e3_controls: list[Row] = field(default_factory=list)
    e4_target: int = 0
    e3e3_target: int = 0

    @property
    def total(self) -> int:
        return len(self.e4_carriers) + len(self.e3e3_controls)

    @property
    def shortfall(self) -> int:
        """How many selections are missing because the pool ran out."""
        return (self.e4_target - len(self.e4_carriers)) + (
            self.e3e3_target - len(self.e3e3_controls)
        )


@dataclass
class StratificationResult:
    """Complete output of a stratification run."""

    female_stages: dict[str, StageAllocation] = field(default_factory=dict)
    male_allocation: StageAllocation | None = None
    male_band_targets: dict[str, tuple[int, int]] = field(default_factory=dict)
    excluded_count: int = 0
    total_input: int = 0

    @property
    def total_selected(self) -> int:
        n = sum(s.total for s in self.female_stages.values())
        if self.male_allocation:
            n += self.male_allocation.total
        return n


class CohortStratifier:
    """Build stratified recall lists balanced by genotype, sex and age band.

    Parameters
    ----------
    stages : dict, optional
        Stage name -> list of age bands. Defaults to :data:`DEFAULT_STAGES`.
    exclude_e2 : bool
        If True (default), e2/e4 participants are excluded. If False they join
        the e4-carrier pool. e2/e2 and e2/e3 are never selected because they
        are neither e4 carriers nor e3/e3 controls.
    """

    def __init__(
        self,
        stages: dict[str, list[str]] | None = None,
        exclude_e2: bool = True,
    ) -> None:
        self.stages = stages or DEFAULT_STAGES
        self.exclude_e2 = exclude_e2
        self.carriers = E4_CARRIERS if exclude_e2 else E4_CARRIERS | {"E2/E4"}

    @staticmethod
    def read_rows(filepath: str | Path) -> list[Row]:
        """Read a CSV with columns participant_id, genotype, gender, age_band."""
        path = Path(filepath)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {filepath}")
        with open(path, newline="") as fh:
            return list(csv.DictReader(fh))

    def filter_rows(
        self, rows: list[Row], gender_filter: str | None = None
    ) -> tuple[list[Row], int]:
        """Keep target genotypes (and one gender, if given).

        Returns ``(kept, excluded)`` where ``excluded`` counts rows of the
        requested gender dropped for their genotype.
        """
        kept: list[Row] = []
        excluded = 0
        for row in rows:
            gender = (row.get("gender") or "").strip().lower()
            if gender_filter and gender != gender_filter.lower():
                continue
            genotype = normalise_genotype(row.get("genotype") or "")
            if genotype in self.carriers or genotype in CONTROLS:
                kept.append({**row, "genotype": genotype})
            else:
                excluded += 1
        return kept, excluded

    def load_candidates(
        self, filepath: str | Path, gender_filter: str | None = None
    ) -> list[Row]:
        """Load and filter candidates from a CSV file."""
        kept, _ = self.filter_rows(self.read_rows(filepath), gender_filter)
        return kept

    def _pools_by_band(self, rows: list[Row]) -> dict[str, dict[str, list[Row]]]:
        pools: dict[str, dict[str, list[Row]]] = {}
        for row in rows:
            band = (row.get("age_band") or "").strip()
            pool = pools.setdefault(band, {"e4": [], "e3e3": []})
            key = "e4" if row["genotype"] in self.carriers else "e3e3"
            pool[key].append(row)
        return pools

    def build_recall(
        self,
        candidates_csv: str | Path,
        males_csv: str | Path | None = None,
        e4_per_stage: int = 80,
        e3e3_per_stage: int = 80,
        male_ratio: float = 0.22,
        seed: int | None = None,
    ) -> StratificationResult:
        """Build the female stage lists and an age-matched male list.

        Parameters
        ----------
        candidates_csv : path
            Candidates (females are taken from this file).
        males_csv : path, optional
            Male candidates. If None, males are taken from ``candidates_csv``.
        e4_per_stage, e3e3_per_stage : int
            Targets per female stage.
        male_ratio : float
            Male target as a fraction of the number of females selected. It
            is split evenly between e4 carriers and e3/e3 controls.
        seed : int, optional
            Shuffle each pool with this seed before selecting. Without it,
            candidates are taken in file order.
        """
        female_rows, female_excluded = self.filter_rows(
            self.read_rows(candidates_csv), "Female"
        )
        male_rows, male_excluded = self.filter_rows(
            self.read_rows(males_csv or candidates_csv), "Male"
        )
        if seed is not None:
            rng = random.Random(seed)
            female_rows = rng.sample(female_rows, len(female_rows))
            male_rows = rng.sample(male_rows, len(male_rows))

        result = StratificationResult(
            total_input=len(female_rows) + len(male_rows),
            excluded_count=female_excluded + male_excluded,
        )

        female_pools = self._pools_by_band(female_rows)
        for stage_name, bands in self.stages.items():
            e4_pool = [r for b in bands for r in female_pools.get(b, {}).get("e4", [])]
            e3_pool = [
                r for b in bands for r in female_pools.get(b, {}).get("e3e3", [])
            ]
            result.female_stages[stage_name] = StageAllocation(
                stage_name=stage_name,
                e4_carriers=e4_pool[:e4_per_stage],
                e3e3_controls=e3_pool[:e3e3_per_stage],
                e4_target=e4_per_stage,
                e3e3_target=e3e3_per_stage,
            )

        # Age-match males to the females actually selected.
        band_counts: dict[str, int] = {}
        for alloc in result.female_stages.values():
            for row in alloc.e4_carriers + alloc.e3e3_controls:
                band = (row.get("age_band") or "").strip()
                band_counts[band] = band_counts.get(band, 0) + 1
        total_females = sum(band_counts.values())
        male_target = round(total_females * male_ratio)
        e4_target = male_target // 2
        e3_target = male_target - e4_target
        e4_by_band = apportion(e4_target, band_counts)
        e3_by_band = apportion(e3_target, band_counts)

        male_pools = self._pools_by_band(male_rows)
        male_alloc = StageAllocation(
            stage_name="male", e4_target=e4_target, e3e3_target=e3_target
        )
        for band in sorted(band_counts):
            pool = male_pools.get(band, {"e4": [], "e3e3": []})
            male_alloc.e4_carriers.extend(pool["e4"][: e4_by_band[band]])
            male_alloc.e3e3_controls.extend(pool["e3e3"][: e3_by_band[band]])
            result.male_band_targets[band] = (e4_by_band[band], e3_by_band[band])
        result.male_allocation = male_alloc
        return result

    @staticmethod
    def export_recall(
        result: StratificationResult, output_dir: str | Path
    ) -> list[str]:
        """Write per-stage female lists, the male list and a summary."""
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        header = ["participant_id", "genotype", "gender", "age_band"]
        files: list[str] = []

        def write(path: Path, rows: list[Row]) -> None:
            with open(path, "w", newline="") as fh:
                writer = csv.writer(fh)
                writer.writerow(header)
                for row in rows:
                    writer.writerow([row.get(col, "") for col in header])
            files.append(str(path))

        for stage_name, alloc in result.female_stages.items():
            write(
                out / f"female_{stage_name}.csv",
                alloc.e4_carriers + alloc.e3e3_controls,
            )
        if result.male_allocation:
            ma = result.male_allocation
            write(out / "male_recall_list.csv", ma.e4_carriers + ma.e3e3_controls)

        lines = [
            f"Recall summary: {result.total_selected} selected from "
            f"{result.total_input} eligible ({result.excluded_count} excluded "
            "by genotype)",
            "",
        ]
        allocations = list(result.female_stages.values())
        if result.male_allocation:
            allocations.append(result.male_allocation)
        for alloc in allocations:
            lines.append(
                f"  {alloc.stage_name}: {alloc.total} "
                f"(e4 carriers {len(alloc.e4_carriers)}/{alloc.e4_target}, "
                f"e3/e3 {len(alloc.e3e3_controls)}/{alloc.e3e3_target}, "
                f"shortfall {alloc.shortfall})"
            )
        summary = out / "recall_summary.txt"
        summary.write_text("\n".join(lines) + "\n")
        files.append(str(summary))
        return files
