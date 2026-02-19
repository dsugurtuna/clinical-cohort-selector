"""Tests for the CohortStratifier class."""

import pytest
from cohort_selector.stratifier import CohortStratifier


@pytest.fixture
def candidates_csv(tmp_path):
    p = tmp_path / "females.csv"
    rows = ["participant_id,genotype,gender,age_band"]
    for i, (gt, band) in enumerate([
        ("E3/E3", "35-39"), ("E3/E4", "35-39"), ("E4/E4", "40-44"),
        ("E3/E3", "45-49"), ("E3/E4", "45-49"),
        ("E3/E3", "50-54"), ("E3/E4", "50-54"),
        ("E3/E3", "55-59"), ("E3/E4", "60-64"), ("E4/E4", "65-69"),
        ("E2/E3", "40-44"),  # should be excluded
    ], start=1):
        rows.append(f"F{i:03d},{gt},Female,{band}")
    p.write_text("\n".join(rows))
    return str(p)


@pytest.fixture
def males_csv(tmp_path):
    p = tmp_path / "males.csv"
    rows = ["participant_id,genotype,gender,age_band"]
    for i, gt in enumerate(["E3/E3", "E3/E4", "E4/E4", "E3/E3"], start=1):
        rows.append(f"M{i:03d},{gt},Male,40-44")
    p.write_text("\n".join(rows))
    return str(p)


class TestCohortStratifier:
    def test_load_candidates_excludes_e2(self, candidates_csv):
        s = CohortStratifier(exclude_e2=True)
        cands = s.load_candidates(candidates_csv, gender_filter="Female")
        genotypes = [c["genotype"] for c in cands]
        assert all("E2" not in g for g in genotypes)

    def test_build_recall(self, candidates_csv, males_csv):
        s = CohortStratifier()
        result = s.build_recall(candidates_csv, males_csv, e4_per_stage=2, e3e3_per_stage=2)
        assert result.total_selected > 0
        assert "pre" in result.female_stages
        assert "peri" in result.female_stages

    def test_export_recall(self, candidates_csv, males_csv, tmp_path):
        s = CohortStratifier()
        result = s.build_recall(candidates_csv, males_csv, e4_per_stage=2, e3e3_per_stage=2)
        files = s.export_recall(result, str(tmp_path / "output"))
        assert len(files) >= 1
