"""Tests for the PhenotypeIntegrator."""

import pytest

from cohort_selector.integrator import PhenotypeIntegrator


@pytest.fixture
def geno_csv(tmp_path):
    p = tmp_path / "genotypes.csv"
    p.write_text("SAMP001,P001,E3/E3\nSAMP002,P002,E3/E4\nSAMP003,P003,E4/E4\n")
    return str(p)


@pytest.fixture
def pheno_file(tmp_path):
    p = tmp_path / "phenotypes.txt"
    p.write_text("SAMP001 42 Female\nSAMP002 55 Male\n")
    return str(p)


class TestPhenotypeIntegrator:
    def test_merge(self, geno_csv, pheno_file, tmp_path):
        integrator = PhenotypeIntegrator()
        output = str(tmp_path / "master.csv")
        report = integrator.merge(geno_csv, pheno_file, output)
        assert report.genotype_records == 3
        assert report.phenotype_records == 2
        assert report.matched_records == 2
        assert report.unmatched_genotype == 1

    def test_missing_file_raises(self):
        integrator = PhenotypeIntegrator()
        with pytest.raises(FileNotFoundError):
            integrator.load_genotypes("/nonexistent.csv")
