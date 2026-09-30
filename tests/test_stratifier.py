"""Tests for the CohortStratifier class."""

import pytest

from cohort_selector.stratifier import CohortStratifier


@pytest.fixture
def candidates_csv(tmp_path):
    p = tmp_path / "females.csv"
    rows = ["participant_id,genotype,gender,age_band"]
    for i, (gt, band) in enumerate(
        [
            ("E3/E3", "35-39"),
            ("E3/E4", "35-39"),
            ("E4/E4", "40-44"),
            ("E3/E3", "45-49"),
            ("E3/E4", "45-49"),
            ("E3/E3", "50-54"),
            ("E3/E4", "50-54"),
            ("E3/E3", "55-59"),
            ("E3/E4", "60-64"),
            ("E4/E4", "65-69"),
            ("E2/E3", "40-44"),  # should be excluded
        ],
        start=1,
    ):
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
        result = s.build_recall(
            candidates_csv, males_csv, e4_per_stage=2, e3e3_per_stage=2
        )
        assert result.total_selected > 0
        assert "pre" in result.female_stages
        assert "peri" in result.female_stages

    def test_export_recall(self, candidates_csv, males_csv, tmp_path):
        s = CohortStratifier()
        result = s.build_recall(
            candidates_csv, males_csv, e4_per_stage=2, e3e3_per_stage=2
        )
        files = s.export_recall(result, str(tmp_path / "output"))
        assert len(files) >= 1


def _write(path, rows):
    path.write_text(
        "participant_id,genotype,gender,age_band\n"
        + "\n".join(",".join(r) for r in rows)
        + "\n"
    )
    return str(path)


def test_normalise_genotype():
    from cohort_selector.stratifier import normalise_genotype

    assert normalise_genotype("e4/e3") == "E3/E4"
    assert normalise_genotype("E3E4") == "E3/E4"
    assert normalise_genotype("3/3") == "E3/E3"
    assert normalise_genotype("NA") == "NA"


def test_exclude_e2_flag_changes_selection(tmp_path):
    csv = _write(
        tmp_path / "c.csv",
        [
            ("F1", "E2/E4", "Female", "40-44"),
            ("F2", "E3/E3", "Female", "40-44"),
            ("F3", "E2/E3", "Female", "40-44"),
        ],
    )
    strict = CohortStratifier(exclude_e2=True).load_candidates(csv, "Female")
    loose = CohortStratifier(exclude_e2=False).load_candidates(csv, "Female")
    assert [r["participant_id"] for r in strict] == ["F2"]
    # e2/e4 is an e4 carrier once e2 is allowed; e2/e3 is never a target.
    assert [r["participant_id"] for r in loose] == ["F1", "F2"]


def test_males_are_age_matched_to_selected_females(tmp_path):
    females = [(f"F{i}", "E3/E4", "Female", "40-44") for i in range(6)]
    females += [(f"G{i}", "E3/E3", "Female", "60-64") for i in range(2)]
    males = [(f"M{i}", "E3/E4", "Male", "40-44") for i in range(5)]
    males += [(f"N{i}", "E3/E3", "Male", "40-44") for i in range(5)]
    males += [(f"P{i}", "E3/E4", "Male", "60-64") for i in range(5)]
    males += [(f"Q{i}", "E3/E3", "Male", "60-64") for i in range(5)]
    s = CohortStratifier()
    result = s.build_recall(
        _write(tmp_path / "f.csv", females),
        _write(tmp_path / "m.csv", males),
        e4_per_stage=6,
        e3e3_per_stage=2,
        male_ratio=1.0,
    )
    # 8 females selected: 6 in 40-44 and 2 in 60-64 -> 8 males (4 e4 carriers,
    # 4 e3/e3), each apportioned 3:1 across the two bands.
    assert result.male_band_targets == {"40-44": (3, 3), "60-64": (1, 1)}
    male = result.male_allocation
    assert male is not None
    bands = sorted(r["age_band"] for r in male.e4_carriers + male.e3e3_controls)
    assert bands == ["40-44"] * 6 + ["60-64"] * 2


def test_shortfall_and_exclusions_are_reported(candidates_csv, males_csv, tmp_path):
    s = CohortStratifier()
    result = s.build_recall(candidates_csv, males_csv, e4_per_stage=5, e3e3_per_stage=5)
    assert result.excluded_count == 1  # the E2/E3 female
    assert result.female_stages["peri"].shortfall == 8  # 1 of 5 e4, 1 of 5 e3/e3
    files = s.export_recall(result, tmp_path / "out")
    summary = (tmp_path / "out" / "recall_summary.txt").read_text()
    assert "shortfall 8" in summary
    assert len(files) == 6


def test_seed_gives_reproducible_order(tmp_path):
    rows = [(f"F{i:02d}", "E3/E4", "Female", "40-44") for i in range(20)]
    csv = _write(tmp_path / "f.csv", rows)
    s = CohortStratifier()

    def pick(seed):
        r = s.build_recall(csv, e4_per_stage=3, e3e3_per_stage=0, seed=seed)
        return [x["participant_id"] for x in r.female_stages["pre"].e4_carriers]

    assert pick(7) == pick(7)
    assert pick(None) == ["F00", "F01", "F02"]


def test_apportion_sums_to_total():
    from cohort_selector.stratifier import apportion

    parts = apportion(10, {"a": 1, "b": 1, "c": 1})
    assert sum(parts.values()) == 10
    assert parts == {"a": 4, "b": 3, "c": 3}
    assert apportion(0, {"a": 1}) == {"a": 0}
