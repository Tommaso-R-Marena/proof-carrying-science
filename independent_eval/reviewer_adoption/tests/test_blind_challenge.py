"""Task 16 — blind challenge scorer tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from independent_eval.reviewer_adoption.blind_challenge.blind import (
    build_blind_packet,
    load_cases,
    write_packet,
)
from independent_eval.reviewer_adoption.blind_challenge.score import score_responses

ROOT = Path(__file__).resolve().parents[1]


def test_cases_cover_required_categories():
    cases = load_cases(ROOT / "blind_challenge" / "cases")
    labels = {c["ground_truth_label"] for c in cases}
    assert "valid" in labels
    assert "invalid" in labels
    assert "computationally_valid_scientifically_unsupported" in labels
    assert len(cases) >= 3


def test_blind_packet_omits_ground_truth(tmp_path):
    cases = load_cases(ROOT / "blind_challenge" / "cases")
    packet = build_blind_packet(cases, seed=1)
    path = write_packet(packet, tmp_path / "packet")
    reviewer = json.loads(path.read_text(encoding="utf-8"))
    assert "facilitator_map" not in reviewer
    for case in reviewer["cases"]:
        assert "ground_truth_label" not in case
        assert "ground_truth" not in case
        assert "expected_judgment" not in case
    assert reviewer["blinding"]["human_results_included"] is False


def test_scorer_on_synthetic_fixture_not_human_claim():
    gt = json.loads(
        (ROOT / "blind_challenge" / "keys" / "ground_truth.json").read_text(encoding="utf-8")
    )
    resp = json.loads(
        (ROOT / "blind_challenge" / "fixtures" / "sample_responses.json").read_text(
            encoding="utf-8"
        )
    )
    assert resp.get("synthetic") is True
    assert resp.get("human_study") is False
    result = score_responses(gt, resp)
    assert result["human_study"] is False
    assert result["synthetic"] is True
    assert result["n_scored"] >= 3
    assert 0.0 <= result["accuracy"] <= 1.0
    assert any(row["correct"] is False for row in result["per_case"])


def test_scorer_refuses_unattested_human_study():
    gt = json.loads(
        (ROOT / "blind_challenge" / "keys" / "ground_truth.json").read_text(encoding="utf-8")
    )
    resp = {
        "synthetic": False,
        "human_study": True,
        "responses": [
            {
                "opaque_id": "CASE-01",
                "raw_case_id": "RAW-VALID-001",
                "judgment": "accept_as_valid",
            }
        ],
    }
    with pytest.raises(ValueError):
        score_responses(gt, resp)
