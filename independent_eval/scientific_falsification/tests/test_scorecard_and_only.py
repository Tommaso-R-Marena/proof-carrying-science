from __future__ import annotations

import json

from python_harness.canonical_seal import seal_artifact, verify_artifact_integrity
from python_harness.falsification_scorecard import build_scorecard
from python_harness.run_all import SELECTABLE, main as run_all_main


def test_scorecard_marks_inadequacy_open_and_never_accepts():
    summary = {
        "inadequacy": {
            "example_count": 4,
            "computational_pass_count": 4,
            "empirical_adequacy_established_count": 0,
        },
        "external_validity": {
            "completeness_score": 0.5,
            "empirical_adequacy_established": False,
            "results_status": "NOT_COLLECTED",
        },
        "metamorphic": {
            "case_count": 2,
            "cases_ok": 2,
            "oracles_all_passed_count": 2,
        },
        "casebook_fixtures": {
            "case_count": 2,
            "positives_ok": 2,
            "negatives_rejected": 1,
        },
        "aristotle_candidates": {
            "candidate_count": 4,
            "status": "proposal_candidates_only",
            "empirical_adequacy_established_any": False,
        },
    }
    card = build_scorecard(summary)
    assert card["issues_accept"] is False
    assert card["inspection_is_not_authority"] is True
    assert verify_artifact_integrity(card) is True
    by_id = {r["id"]: r for r in card["rows"]}
    assert by_id["SF-INADEQUACY"]["inspection_class"] == "scientific_adequacy_open"
    assert by_id["SF-ARISTOTLE-CANDIDATES"]["inspection_class"] == "scientific_adequacy_open"
    assert by_id["SF-METAMORPHIC"]["inspection_class"] == "computationally_supported"


def test_seal_detects_tamper():
    sealed = seal_artifact({"format": "x", "n": 1})
    assert verify_artifact_integrity(sealed) is True
    sealed["n"] = 2
    assert verify_artifact_integrity(sealed) is False


def test_run_all_only_aristotle_skips_heavy_surfaces(tmp_path, monkeypatch):
    # Efficient path: aristotle + scorecard only; SKIPPED ≠ PASS.
    rc = run_all_main(["--skip-build", "--only", "aristotle"])
    assert rc == 0
    from python_harness.paths import RESULTS

    summary = json.loads((RESULTS / "SUMMARY.json").read_text(encoding="utf-8"))
    assert summary["issues_accept"] is False
    assert verify_artifact_integrity(summary) is True
    assert summary["aristotle_candidates"]["status"] == "proposal_candidates_only"
    assert summary["metamorphic"]["status"] == "SKIPPED"
    assert summary["casebook_fixtures"]["status"] == "SKIPPED"
    assert set(summary["selected_surfaces"]) == {"aristotle"}
    assert (RESULTS / "falsification_scorecard.json").is_file()
    assert set(SELECTABLE) >= {"aristotle", "metamorphic", "inadequacy"}
