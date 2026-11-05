import json
from pathlib import Path

from pcs.impact import impact_from_artifacts

CORPUS = Path(__file__).resolve().parents[1] / "commons" / "claim-invalidation-v1" / "seed-corpus.json"


def test_public_invalidation_seed_corpus_matches_reference():
    corpus = json.loads(CORPUS.read_text(encoding="utf-8"))
    assert corpus["format"] == "pcs-claim-invalidation-corpus-v1"
    for case in corpus["cases"]:
        actual = impact_from_artifacts(case["certificate"], set(case["changed_artifacts"]))
        assert actual == case["expected_impact"], case["id"]


def test_hidden_dependency_negative_control_does_not_overclaim_nonimpact():
    corpus = json.loads(CORPUS.read_text(encoding="utf-8"))
    cases = {case["id"]: case for case in corpus["cases"]}
    case = cases["seed_hidden_dependency_negative_control"]
    assert case["dependency_complete"] is False
    assert "hidden_dependency" in case
    assert "c_other" not in case["expected_impact"]["affected_claims"]
    assert "c_other" in case["hidden_dependency"]["real_world_consequence"]
