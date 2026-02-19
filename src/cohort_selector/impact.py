#!/usr/bin/env python3
"""
Exclusion Impact Analyser
==========================

Quantifies the effect of introducing new exclusion criteria on the
available participant pool before committing to a study design.

Author: Ugur Tuna
"""

import csv
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set

logger = logging.getLogger(__name__)


@dataclass
class ImpactReport:
    """Quantified impact of exclusion criteria."""

    criterion_label: str
    total_before: int = 0
    excluded_count: int = 0
    remaining_count: int = 0
    females_remaining: int = 0
    males_remaining: int = 0
    breakdown_by_genotype: Dict[str, int] = field(default_factory=dict)

    @property
    def exclusion_rate(self) -> float:
        if self.total_before == 0:
            return 0.0
        return self.excluded_count / self.total_before


class ExclusionImpactAnalyser:
    """
    Diagnoses how an exclusion criterion affects the participant pool.

    Example::

        analyser = ExclusionImpactAnalyser()
        report = analyser.analyse(
            master_csv="master_participant_data.csv",
            exclusion_pattern="E2",
        )
        print(f"Would lose {report.excluded_count} participants")
    """

    def analyse(
        self,
        master_csv: str,
        exclusion_pattern: str = "E2",
        criterion_label: Optional[str] = None,
    ) -> ImpactReport:
        """
        Analyse the impact of excluding participants whose genotype
        matches a pattern.

        Parameters
        ----------
        master_csv : str
            Path to master participant CSV with columns:
            participant_id, genotype, gender, age_band  (or similar).
        exclusion_pattern : str
            Substring to match in the genotype column.
        criterion_label : str, optional
            Human-readable label for the exclusion.

        Returns
        -------
        ImpactReport
        """
        label = criterion_label or f"Exclude genotypes containing '{exclusion_pattern}'"
        report = ImpactReport(criterion_label=label)

        path = Path(master_csv)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {master_csv}")

        with open(path) as fh:
            reader = csv.DictReader(fh)
            rows = list(reader)

        report.total_before = len(rows)

        remaining: List[dict] = []
        for row in rows:
            gt = row.get("genotype", row.get("apoe", ""))
            if exclusion_pattern.upper() in gt.upper():
                report.excluded_count += 1
            else:
                remaining.append(row)

        report.remaining_count = len(remaining)
        report.females_remaining = sum(
            1 for r in remaining if r.get("gender", "").strip().lower() in ("female", "f")
        )
        report.males_remaining = sum(
            1 for r in remaining if r.get("gender", "").strip().lower() in ("male", "m")
        )

        for r in remaining:
            gt = r.get("genotype", r.get("apoe", "Unknown"))
            report.breakdown_by_genotype[gt] = report.breakdown_by_genotype.get(gt, 0) + 1

        return report

    @staticmethod
    def format_report(report: ImpactReport) -> str:
        """Format an impact report as human-readable text."""
        lines = [
            f"Exclusion Impact Analysis: {report.criterion_label}",
            "=" * 60,
            f"Total participants before    : {report.total_before:,}",
            f"Excluded by criterion        : {report.excluded_count:,} ({report.exclusion_rate:.1%})",
            f"Remaining in pool            : {report.remaining_count:,}",
            f"  Females remaining          : {report.females_remaining:,}",
            f"  Males remaining            : {report.males_remaining:,}",
            "",
            "Remaining genotype breakdown:",
        ]
        for gt, count in sorted(report.breakdown_by_genotype.items(), key=lambda x: -x[1]):
            lines.append(f"  {gt:15s}  {count:>6,}")
        return "\n".join(lines)
