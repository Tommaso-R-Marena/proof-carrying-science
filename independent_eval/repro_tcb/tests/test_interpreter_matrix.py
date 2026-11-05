"""Interpreter matrix: agreement among present Pythons; absences not passes."""

from __future__ import annotations

from pathlib import Path

from python_harness.interpreter_matrix import run_interpreter_matrix


def test_interpreter_matrix_agrees_and_records_absences(tmp_path: Path) -> None:
    report = run_interpreter_matrix(output=tmp_path / "matrix.json")
    assert report["format"] == "pcs-independent-eval-interpreter-matrix-v1"
    assert report["interpreters_ok"] >= 1
    assert report["interpreters_disagree"] == 0
    assert report["pass"] is True
    assert isinstance(report["absences"], list)
    # At least the expected digest is 64 hex chars.
    assert len(report["expected_archive_sha256"]) == 64
    for row in report["rows"]:
        if row["probe_ok"]:
            assert row["matches_expected"] is True
            assert row["archive_sha256"] == report["expected_archive_sha256"]
    # Absences must never be labeled PASS.
    for absence in report["absences"]:
        assert absence["status"] in {"ABSENT", "PRESENT_BUT_NOT_PROBED"}
        assert "PASS" not in absence["status"]
    assert (tmp_path / "matrix.json").is_file()
