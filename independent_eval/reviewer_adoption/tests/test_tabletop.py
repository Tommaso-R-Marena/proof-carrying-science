from __future__ import annotations

import json
from pathlib import Path

import pytest

from independent_eval.reviewer_adoption.tabletop.simulator import evaluate_after_action

ROOT = Path(__file__).resolve().parents[1]
SCENARIOS = ROOT / "tabletop" / "scenarios"
FIXTURE = ROOT / "tabletop" / "fixtures" / "sample_responses_compromised_key.json"


def test_required_scenario_files_exist():
    needed = {
        "compromised_signing_key.json",
        "stale_verifier.json",
        "corrupted_archive.json",
        "lost_commitment.json",
    }
    present = {p.name for p in SCENARIOS.glob("*.json")}
    assert needed <= present
    assert len(present) >= 5
    for path in SCENARIOS.glob("*.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data.get("offline_only") is True
        assert data.get("live_credential_changes_allowed") is False
        assert data.get("exercises")
        assert data.get("after_action_criteria")


def test_compromised_key_fixture_passes_offline():
    scenario = json.loads((SCENARIOS / "compromised_signing_key.json").read_text(encoding="utf-8"))
    responses = json.loads(FIXTURE.read_text(encoding="utf-8"))
    result = evaluate_after_action(scenario, responses)
    assert result["live_credential_changes_performed"] is False
    assert result["offline_only"] is True
    assert result["passed"] is True


def test_simulator_refuses_live_credential_flag():
    scenario = json.loads((SCENARIOS / "compromised_signing_key.json").read_text(encoding="utf-8"))
    responses = dict(json.loads(FIXTURE.read_text(encoding="utf-8")))
    responses["live_credential_changes_performed"] = True
    with pytest.raises(RuntimeError, match="live credential"):
        evaluate_after_action(scenario, responses)
