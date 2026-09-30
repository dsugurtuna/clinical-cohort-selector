#!/usr/bin/env python3
"""
Cohort Stratification Engine
==============================

Builds balanced clinical recall lists by stratifying participants into
biological stages (e.g. pre/peri/early/late menopausal) and generating
age-matched control groups.

Supports genotype-based filtering (e.g. include only e3/e3, e3/e4, e4/e4;
exclude all e2 carriers).

Author: Ugur Tuna
"""

import csv
import logging
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

# Default biological stages for female participants
DEFAULT_STAGES: dict[str, list[str]] = {
    "pre": ["35-39", "40-44"],
    "peri": ["45-49"],
    "early": ["50-54"],
    "late": ["55-59", "60-64", "65-69"],
}

VALID_GENOTYPES: set[str] = {"E3/E3", "E3/E4", "E4/E4"}


@dataclass
class StageAllocation:
    """Participants allocated to a single biological stage."""

    stage_name: str
    e4_carriers: list[dict] = field(default_factory=list)
    e3e3_controls: list[dict] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.e4_carriers) + len(self.e3e3_controls)


@dataclass
class StratificationResult:
    """Complete output of a cohort stratification run."""

    female_stages: dict[str, StageAllocation] = field(default_factory=dict)
    male_allocation: StageAllocation | None = None
    excluded_count: int = 0
    total_input: int = 0

    @property
    def total_selected(self) -> int:
        n = sum(s.total for s in self.female_stages.values())
        if self.male_allocation:
            n += self.male_allocation.total
        return n


class CohortStratifier:
    """
    Builds stratified recall lists balanced by genotype, gender, and age band.

    Example::

        stratifier = CohortStratifier()
        result = stratifier.build_recall(
            candidates_csv="available_females.csv",
            males_csv="available_males.csv",
            e4_per_stage=80,
            e3e3_per_stage=80,
        )
    """

    def __init__(
        self,
        stages: dict[str, list[str]] | None = None,
        exclude_e2: bool = True,
    ):
        self.stages = stages or DEFAULT_STAGES
        self.exclude_e2 = exclude_e2

    def load_candidates(
        self,
        filepath: str,
        gender_filter: str | None = None,
    ) -> list[dict]:
        """
        Load and filter candidates from a CSV file.

        Expected columns: participant_id, genotype, gender, age_band
        """
        path = Path(filepath)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {filepath}")

        candidates: list[dict] = []
        with open(path) as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                gt = row.get("genotype", "").strip()
                # Exclude e2 carriers
                if self.exclude_e2 and "E2" in gt.upper():
                    continue
                # Keep only target genotypes
                if gt.upper() not in {g.upper() for g in VALID_GENOTYPES}:
                    continue
                # Gender filter
                if (
                    gender_filter
                    and row.get("gender", "").strip().lower() != gender_filter.lower()
                ):
                    continue
                candidates.append(row)
        return candidates

    def build_recall(
        self,
        candidates_csv: str,
        males_csv: str | None = None,
        e4_per_stage: int = 80,
        e3e3_per_stage: int = 80,
        male_ratio: float = 0.22,
    ) -> StratificationResult:
        """
        Build a complete recall list.

        Parameters
        ----------
        candidates_csv : str
            CSV file of female candidates.
        males_csv : str, optional
            CSV file of male candidates. If None, males are drawn from
            the same file.
        e4_per_stage : int
            Target number of e4 carriers per female stage.
        e3e3_per_stage : int
            Target number of e3/e3 controls per female stage.
        male_ratio : float
            Ratio of males to total females selected.

        Returns
        -------
        StratificationResult
        """
        females = self.load_candidates(candidates_csv, gender_filter="Female")
        males_file = males_csv or candidates_csv
        males = self.load_candidates(males_file, gender_filter="Male")

        result = StratificationResult(total_input=len(females) + len(males))

        # Index females by age band
        by_band: dict[str, dict[str, list[dict]]] = {}
        for f in females:
            band = f.get("age_band", "").strip()
            gt = f.get("genotype", "").strip().upper()
            by_band.setdefault(band, {"E4": [], "E3E3": []})
            if gt in ("E3/E4", "E4/E4"):
                by_band[band]["E4"].append(f)
            elif gt == "E3/E3":
                by_band[band]["E3E3"].append(f)

        # Build female stages
        for stage_name, bands in self.stages.items():
            alloc = StageAllocation(stage_name=stage_name)
            e4_pool: list[dict] = []
            e3_pool: list[dict] = []
            for b in bands:
                if b in by_band:
                    e4_pool.extend(by_band[b]["E4"])
                    e3_pool.extend(by_band[b]["E3E3"])
            alloc.e4_carriers = e4_pool[:e4_per_stage]
            alloc.e3e3_controls = e3_pool[:e3e3_per_stage]
            result.female_stages[stage_name] = alloc

        # Build male cohort proportional to females
        total_females = sum(s.total for s in result.female_stages.values())
        male_target = int(total_females * male_ratio)
        male_alloc = StageAllocation(stage_name="male")
        e4_males = [
            m for m in males if m.get("genotype", "").upper() in ("E3/E4", "E4/E4")
        ]
        e3_males = [m for m in males if m.get("genotype", "").upper() == "E3/E3"]
        half = male_target // 2
        male_alloc.e4_carriers = e4_males[:half]
        male_alloc.e3e3_controls = e3_males[: male_target - half]
        result.male_allocation = male_alloc

        return result

    @staticmethod
    def export_recall(result: StratificationResult, output_dir: str) -> list[str]:
        """Write recall lists and summary to CSV files."""
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        files: list[str] = []

        # Female lists per stage
        for stage_name, alloc in result.female_stages.items():
            p = out / f"female_{stage_name}.csv"
            with open(p, "w", newline="") as fh:
                writer = csv.writer(fh)
                writer.writerow(["participant_id", "genotype", "gender", "age_band"])
                for row in alloc.e4_carriers + alloc.e3e3_controls:
                    writer.writerow(
                        [
                            row.get("participant_id"),
                            row.get("genotype"),
                            row.get("gender"),
                            row.get("age_band"),
                        ]
                    )
            files.append(str(p))

        # Male list
        if result.male_allocation:
            p = out / "male_recall_list.csv"
            with open(p, "w", newline="") as fh:
                writer = csv.writer(fh)
                writer.writerow(["participant_id", "genotype", "gender", "age_band"])
                for row in (
                    result.male_allocation.e4_carriers
                    + result.male_allocation.e3e3_controls
                ):
                    writer.writerow(
                        [
                            row.get("participant_id"),
                            row.get("genotype"),
                            row.get("gender"),
                            row.get("age_band"),
                        ]
                    )
            files.append(str(p))

        # Summary
        summary = out / "recall_summary.txt"
        lines = [
            f"Recall Summary — {result.total_selected} selected from {result.total_input}\n"
        ]
        for name, alloc in result.female_stages.items():
            lines.append(
                f"  {name}: {alloc.total} (e4+={len(alloc.e4_carriers)}, e3/e3={len(alloc.e3e3_controls)})"
            )
        if result.male_allocation:
            ma = result.male_allocation
            lines.append(
                f"  male: {ma.total} (e4+={len(ma.e4_carriers)}, e3/e3={len(ma.e3e3_controls)})"
            )
        summary.write_text("\n".join(lines))
        files.append(str(summary))

        return files
