from __future__ import annotations

import json
from pathlib import Path

from python_harness.card import build_assurance_card
from python_harness.program_context import attach_program_context


def test_attach_absent_is_not_pass(tmp_path: Path):
    missing = tmp_path / "nope"
    ctx = attach_program_context([missing])
    assert ctx["is_authority"] is False
    assert ctx["issues_accept"] is False
    assert ctx["summary"]["absent"] == 1
    assert ctx["summary"]["present"] == 0
    assert ctx["entries"][0]["status"] == "ABSENT"


def test_attach_results_dir_digests_summary(tmp_path: Path, fixture_bundle: Path):
    results = tmp_path / "results"
    results.mkdir()
    summary = results / "SUMMARY.json"
    summary.write_text(
        json.dumps({"format": "pcs-test-summary-v1", "ok": True}, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    card = build_assurance_card(
        fixture_bundle,
        skip_verify=True,
        attach_results=[results],
        generated_at_utc="2026-10-17T21:00:00Z",
    )
    ctx = card["program_context"]
    assert ctx["summary"]["present"] == 1
    assert ctx["entries"][0]["status"] == "PRESENT"
    assert ctx["entries"][0]["files"][0]["name"] == "SUMMARY.json"
    assert len(ctx["entries"][0]["files"][0]["sha256"]) == 64
    assert card["card_issues_accept"] is False
    assert ctx["is_authority"] is False


def test_empty_attach_list_is_zero_requested(fixture_bundle: Path):
    card = build_assurance_card(fixture_bundle, skip_verify=True)
    assert card["program_context"]["summary"]["requested"] == 0
