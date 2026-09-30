"""Tests for the ExclusionImpactAnalyser."""

import pytest

from cohort_selector.impact import ExclusionImpactAnalyser


@pytest.fixture
def master_csv(tmp_path):
    p = tmp_path / "master.csv"
    p.write_text(
        "participant_id,genotype,gender,age_band\n"
        "P001,E3/E3,Female,40-44\n"
        "P002,E2/E3,Male,50-54\n"
        "P003,E4/E4,Female,60-64\n"
        "P004,E2/E4,Female,45-49\n"
        "P005,E3/E4,Male,55-59\n"
    )
    return str(p)


class TestExclusionImpactAnalyser:
    def test_analyse_e2(self, master_csv):
        analyser = ExclusionImpactAnalyser()
        report = analyser.analyse(master_csv, exclusion_pattern="E2")
        assert report.total_before == 5
        assert report.excluded_count == 2  # P002 and P004
        assert report.remaining_count == 3

    def test_format_report(self, master_csv):
        analyser = ExclusionImpactAnalyser()
        report = analyser.analyse(master_csv, exclusion_pattern="E2")
        text = analyser.format_report(report)
        assert "Excluded by criterion" in text
        assert "2" in text
