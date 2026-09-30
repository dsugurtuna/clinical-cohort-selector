"""Tests for the command-line interface, run against examples/."""

from pathlib import Path

import pytest

from cohort_selector.__main__ import main

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"


def test_stratify(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    code = main(
        [
            "stratify",
            str(EXAMPLES / "candidates.csv"),
            "--e4-per-stage",
            "10",
            "--e3e3-per-stage",
            "10",
            "--seed",
            "1",
            "--out",
            str(tmp_path),
        ]
    )
    out = capsys.readouterr().out
    assert code == 0
    assert "Recall summary:" in out
    assert (tmp_path / "male_recall_list.csv").exists()


def test_impact(capsys: pytest.CaptureFixture[str]) -> None:
    main(["impact", str(EXAMPLES / "candidates.csv"), "--pattern", "E2"])
    assert "Excluded by criterion" in capsys.readouterr().out


def test_merge(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    out = tmp_path / "master.csv"
    main(
        [
            "merge",
            str(EXAMPLES / "genotypes.csv"),
            str(EXAMPLES / "phenotypes.txt"),
            str(out),
        ]
    )
    assert "matched 8" in capsys.readouterr().out
    assert out.read_text().startswith("sample_id,participant_id,genotype,age,gender")
