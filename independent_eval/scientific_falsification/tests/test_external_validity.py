"""Task 11 — external-validity protocol templates + scoring (no invented results)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from python_harness.external_validity import score_protocol, score_protocol_file  # noqa: E402
from python_harness.paths import EXTERNAL  # noqa: E402
from python_harness.pcs_cli import load_json  # noqa: E402


def test_templates_exist_without_participant_results():
    templates = list((EXTERNAL / "templates").glob("*.json"))
    assert len(templates) >= 3
    for path in templates:
        obj = load_json(path)
        assert obj.get("participants", {}).get("status") in (None, "NOT_ENROLLED") or obj[
            "participants"
        ] == {"status": "NOT_ENROLLED"}
        results = obj.get("results")
        assert results in (None, {"status": "NOT_COLLECTED"}) or (
            isinstance(results, dict) and results.get("status") == "NOT_COLLECTED"
        )
        # Guard against invented numeric outcomes
        blob = path.read_text(encoding="utf-8").lower()
        assert "p-value" not in blob
        assert "n=" not in blob


def test_score_blank_protocol_completeness():
    score = score_protocol_file(
        EXTERNAL / "templates" / "external_validity_protocol_blank.json",
        EXTERNAL / "rubrics" / "completeness_rubric.json",
    )
    assert score["empirical_adequacy_established"] is False
    assert score["pcs_verification_equivalence"] is False
    assert score["results_status"] in {"NOT_COLLECTED", "NOT_PROVIDED"}
    # Blank population fields reduce completeness below 1.0
    assert 0.0 < score["completeness_score"] < 1.0


def test_score_does_not_invent_results():
    protocol = load_json(
        EXTERNAL / "templates" / "external_validity_protocol_blank.json"
    )
    rubric = load_json(EXTERNAL / "rubrics" / "completeness_rubric.json")
    protocol["population_definition"] = "adults 18-65 with condition X"
    protocol["inclusion_criteria"] = ["age >= 18"]
    protocol["exclusion_criteria"] = ["pregnancy"]
    protocol["endpoints"] = [{"id": "E1", "statement": "pre-specified endpoint"}]
    score = score_protocol(protocol, rubric)
    assert score["empirical_adequacy_established"] is False
    assert "NOT_COLLECTED" in score["results_status"] or score["results_status"] == "NOT_PROVIDED"
