"""Tests for the branch non-overlap auditor."""

from __future__ import annotations

from pathlib import Path

from python_harness.nonoverlap_auditor import (
    audit_branch_nonoverlap,
    write_nonoverlap_report,
)


def test_pairwise_overlap_detected(tmp_path: Path) -> None:
    diffs = {
        "feature/a": [
            "independent_eval/protocol_adversarial/README.md",
            "independent_eval/README.md",
        ],
        "feature/b": [
            "independent_eval/scientific_falsification/README.md",
            "independent_eval/README.md",
        ],
        "feature/c": [
            "independent_eval/repro_tcb/README.md",
        ],
    }

    def runner(branch: str, repo: Path) -> list[str]:
        assert repo == tmp_path
        return list(diffs[branch])

    report = audit_branch_nonoverlap(
        ["feature/a", "feature/b", "feature/c"],
        repo=tmp_path,
        diff_runner=runner,
        existence_check=lambda _b, _r: True,
    )
    assert not report.missing_branches
    assert report.has_overlaps
    # Exactly one overlapping pair: a∩b on independent_eval/README.md
    overlapping = [p for p in report.pair_overlaps if p.overlap]
    assert len(overlapping) == 1
    assert overlapping[0].branch_a == "feature/a"
    assert overlapping[0].branch_b == "feature/b"
    assert overlapping[0].overlap == ("independent_eval/README.md",)
    # a∩c and b∩c empty
    empty = [p for p in report.pair_overlaps if not p.overlap]
    assert len(empty) == 2


def test_no_overlap_when_disjoint(tmp_path: Path) -> None:
    diffs = {
        "feature/a": ["independent_eval/protocol_adversarial/x.py"],
        "feature/b": ["independent_eval/scientific_falsification/y.py"],
    }

    report = audit_branch_nonoverlap(
        list(diffs),
        repo=tmp_path,
        diff_runner=lambda b, _r: diffs[b],
        existence_check=lambda _b, _r: True,
    )
    assert not report.has_overlaps
    assert all(p.overlap == () for p in report.pair_overlaps)


def test_missing_branch_recorded(tmp_path: Path) -> None:
    report = audit_branch_nonoverlap(
        ["feature/present", "feature/absent"],
        repo=tmp_path,
        diff_runner=lambda b, _r: ["only/present.txt"] if b == "feature/present" else [],
        existence_check=lambda b, _r: b == "feature/present",
    )
    # When existence_check fails, branch is missing and runner is not called.
    assert report.missing_branches == ("feature/absent",)
    assert "feature/present" in report.changed_files
    assert "feature/absent" not in report.changed_files
    assert report.pair_overlaps == ()


def test_diff_error_recorded(tmp_path: Path) -> None:
    def runner(branch: str, repo: Path) -> list[str]:
        if branch == "feature/bad":
            raise RuntimeError("git diff failed for feature/bad")
        return ["ok.txt"]

    report = audit_branch_nonoverlap(
        ["feature/ok", "feature/bad"],
        repo=tmp_path,
        diff_runner=runner,
        existence_check=lambda _b, _r: True,
    )
    assert "feature/bad" in report.missing_branches
    assert "feature/bad" in report.errors
    assert "git diff failed" in report.errors["feature/bad"]


def test_write_nonoverlap_report(tmp_path: Path) -> None:
    report = audit_branch_nonoverlap(
        ["feature/a"],
        repo=tmp_path,
        diff_runner=lambda _b, _r: ["x.md"],
        existence_check=lambda _b, _r: True,
    )
    out = tmp_path / "nonoverlap.json"
    write_nonoverlap_report(report, out)
    text = out.read_text(encoding="utf-8")
    assert "pcs-independent-branch-nonoverlap-audit-v1" in text
    assert "feature/a" in text
