"""Task 17 — tabletop simulator tests."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent))

from independent_eval.reviewer_adoption.tabletop.simulator import evaluate_after_action


def test_compromised_key_scenario_scores_fixture():
    scenario = json.loads(
        (ROOT / "tabletop" / "scenarios" / "compromised_signing_key.json").read_text(
            encoding="utf-8"
        )
    )
    responses = json.loads(
        (
            ROOT / "tabletop" / "fixtures" / "sample_responses_compromised_key.json"
        ).read_text(encoding="utf-8")
    )
    result = evaluate_after_action(scenario, responses)
    assert result["live_credential_changes_performed"] is False
    assert result["offline_only"] is True
    assert result["passed"] is True


def test_live_credential_flag_rejected():
    scenario = json.loads(
        (ROOT / "tabletop" / "scenarios" / "compromised_signing_key.json").read_text(
            encoding="utf-8"
        )
    )
    responses = {
        "scenario_id": scenario["scenario_id"],
        "live_credential_changes_performed": True,
        "answers": {},
        "after_action_notes": [],
    }
    try:
        evaluate_after_action(scenario, responses)
        raised = False
    except RuntimeError:
        raised = True
    assert raised


def test_scenario_catalog_size():
    scenarios = list((ROOT / "tabletop" / "scenarios").glob("*.json"))
    assert len(scenarios) >= 5
