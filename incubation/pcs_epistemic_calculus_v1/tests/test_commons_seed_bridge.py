"""Read-only bridge to the public commons claim-invalidation seed corpus.

Does not modify commons/. Confirms this incubation's impact semantics agree on
positive seed cases and refuse world non-impact without completeness.
"""

from __future__ import annotations

import json
from pathlib import Path

from pcs_epistemic.invalidate import compute_impact, nonimpact

COMMONS = (
    Path(__file__).resolve().parents[3]
    / "commons"
    / "claim-invalidation-v1"
    / "seed-corpus.json"
)


def test_commons_seed_corpus_present():
    assert COMMONS.is_file()


def test_impact_matches_complete_seed_cases():
    corpus = json.loads(COMMONS.read_text(encoding="utf-8"))
    assert corpus["format"] == "pcs-claim-invalidation-corpus-v1"
    checked = 0
    for case in corpus["cases"]:
        impact = compute_impact(case["certificate"], case["changed_artifacts"])
        expected = case["expected_impact"]
        assert set(impact["affected_claims"]) == set(expected["affected_claims"]), case["id"]
        assert set(impact["affected_evidence"]) == set(expected["affected_evidence"]), case["id"]
        if not case.get("dependency_complete", True):
            # Negative control: c_other is declared non-impacted but completeness is false.
            result = nonimpact(
                case["certificate"],
                case["changed_artifacts"],
                "c_other",
                dependency_complete=False,
            )
            assert result["declared_nonimpact"] is True
            assert result["world_nonimpact_endorsed"] is False
        checked += 1
    assert checked >= 3


def test_incomplete_seed_never_endorses():
    corpus = json.loads(COMMONS.read_text(encoding="utf-8"))
    incompletes = [c for c in corpus["cases"] if not c.get("dependency_complete", True)]
    assert incompletes, "corpus should retain a hidden-dependency negative control"
    for case in incompletes:
        result = nonimpact(
            case["certificate"],
            case["changed_artifacts"],
            "c_other",
            dependency_complete=False,
        )
        assert result["world_nonimpact_endorsed"] is False
