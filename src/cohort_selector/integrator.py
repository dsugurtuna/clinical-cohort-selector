#!/usr/bin/env python3
"""
Phenotype Integrator
=====================

Merges genotype data (APOE status from CSV) with clinical phenotype data
(age, gender from space-delimited files) into a single master record.

Author: Ugur Tuna
"""

import csv
import logging
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class IntegrationReport:
    """Summary of a phenotype integration run."""

    genotype_records: int = 0
    phenotype_records: int = 0
    matched_records: int = 0
    unmatched_genotype: int = 0
    unmatched_phenotype: int = 0


class PhenotypeIntegrator:
    """
    Joins genotype and phenotype data sources on a shared sample identifier.

    Example::

        integrator = PhenotypeIntegrator()
        report = integrator.merge(
            genotype_csv="v3_to_apoe.csv",
            phenotype_file="phenotype_sampleid_age_gender.txt",
            output_csv="master_participant_data.csv",
        )
    """

    def load_genotypes(
        self,
        filepath: str,
        sample_col: int = 0,
        participant_col: int = 1,
        genotype_col: int = 2,
        delimiter: str = ",",
        has_header: bool = False,
    ) -> dict[str, tuple[str, str]]:
        """
        Load genotype file and return mapping of sample_id to (participant_id, genotype).
        """
        path = Path(filepath)
        if not path.exists():
            raise FileNotFoundError(f"Genotype file not found: {filepath}")

        mapping: dict[str, tuple[str, str]] = {}
        with open(path) as fh:
            reader = csv.reader(fh, delimiter=delimiter)
            if has_header:
                next(reader, None)
            for row in reader:
                if len(row) > max(sample_col, participant_col, genotype_col):
                    sid = row[sample_col].strip()
                    pid = row[participant_col].strip()
                    gt = row[genotype_col].strip()
                    mapping[sid] = (pid, gt)
        return mapping

    def load_phenotypes(
        self,
        filepath: str,
        delimiter: str | None = None,
    ) -> dict[str, tuple[str, str]]:
        """
        Load phenotype file and return mapping of sample_id to (age, gender).

        Expects columns: sample_id, age, gender (space or tab delimited).
        """
        path = Path(filepath)
        if not path.exists():
            raise FileNotFoundError(f"Phenotype file not found: {filepath}")

        mapping: dict[str, tuple[str, str]] = {}
        with open(path) as fh:
            for line in fh:
                parts = (
                    line.strip().split(delimiter) if delimiter else line.strip().split()
                )
                if len(parts) >= 3:
                    mapping[parts[0]] = (parts[1], parts[2])
        return mapping

    def merge(
        self,
        genotype_csv: str,
        phenotype_file: str,
        output_csv: str,
        genotype_delimiter: str = ",",
        genotype_has_header: bool = False,
    ) -> IntegrationReport:
        """
        Merge genotype and phenotype data into a master CSV.

        Parameters
        ----------
        genotype_csv : str
            Path to genotype CSV (sample_id, participant_id, genotype).
        phenotype_file : str
            Path to phenotype file (sample_id, age, gender).
        output_csv : str
            Output CSV path.

        Returns
        -------
        IntegrationReport
        """
        geno = self.load_genotypes(
            genotype_csv, delimiter=genotype_delimiter, has_header=genotype_has_header
        )
        pheno = self.load_phenotypes(phenotype_file)

        report = IntegrationReport(
            genotype_records=len(geno),
            phenotype_records=len(pheno),
        )

        out = Path(output_csv)
        out.parent.mkdir(parents=True, exist_ok=True)

        matched: list[dict] = []
        for sid, (pid, gt) in geno.items():
            if sid in pheno:
                age, gender = pheno[sid]
                matched.append(
                    {
                        "sample_id": sid,
                        "participant_id": pid,
                        "genotype": gt,
                        "age": age,
                        "gender": gender,
                    }
                )

        report.matched_records = len(matched)
        report.unmatched_genotype = len(geno) - len(matched)
        report.unmatched_phenotype = len(pheno) - len(matched)

        with open(out, "w", newline="") as fh:
            writer = csv.DictWriter(
                fh,
                fieldnames=["sample_id", "participant_id", "genotype", "age", "gender"],
            )
            writer.writeheader()
            writer.writerows(matched)

        logger.info("Wrote %d matched records to %s", len(matched), output_csv)
        return report
