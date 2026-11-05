"""Tests for residual-trust rollup."""

from __future__ import annotations

from pathlib import Path

from python_harness.residual_trust import extract_assumption_ids, rollup_residual_trust


def test_extract_assumption_ids_from_table() -> None:
    text = """
| ID | Meaning |
| --- | --- |
| `Sha256Collision` | Collision resistance |
| `NoForgery` | Ed25519 unforgeability |
"""
    ids = extract_assumption_ids(text)
    assert "Sha256Collision" in ids
    assert "NoForgery" in ids
    assert "ID" not in ids


def test_rollup_reads_working_tree(tmp_path: Path, monkeypatch) -> None:
    from python_harness import residual_trust as rt

    trust = tmp_path / "independent_eval" / "repro_tcb"
    trust.mkdir(parents=True)
    (trust / "OPEN_TRUST_ASSUMPTIONS.md").write_text(
        "| `ZipDecoderFaithful` | extractor fidelity |\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(rt, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(
        rt,
        "TRUST_SOURCES",
        (
            {
                "path": "independent_eval/repro_tcb/OPEN_TRUST_ASSUMPTIONS.md",
                "branch": "feature/independent-eval-repro-tcb-c8bb",
                "workstream": "repro_tcb",
            },
        ),
    )
    report = rollup_residual_trust(repo=tmp_path)
    assert report["tcb_closed"] is False
    assert report["sources_present"] == 1
    assert "ZipDecoderFaithful" in report["assumption_ids"]
