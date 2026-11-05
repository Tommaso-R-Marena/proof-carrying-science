from pcs_epistemic.invalidate import compute_impact, nonimpact


GRAPH = {
    "workflow": [
        {"id": "prepare", "inputs": ["raw"], "outputs": ["processed"]},
        {"id": "analyze", "inputs": ["processed"], "outputs": ["result"]},
    ],
    "evidence": [
        {"id": "e_result", "artifact_ids": ["result"], "claim_ids": ["c_result"]},
    ],
    "claims": [
        {"id": "c_result", "required_evidence": ["e_result"]},
        {"id": "c_unrelated", "required_evidence": ["e_other"]},
    ],
}


def test_transitive_invalidation():
    report = compute_impact(GRAPH, ["raw"])
    assert "result" in report["affected_artifacts"]
    assert "e_result" in report["affected_evidence"]
    assert "c_result" in report["affected_claims"]


def test_nonimpact_requires_completeness():
    incomplete = nonimpact(GRAPH, ["raw"], "c_unrelated", dependency_complete=False)
    assert incomplete["declared_nonimpact"] is True
    assert incomplete["world_nonimpact_endorsed"] is False

    complete = nonimpact(GRAPH, ["raw"], "c_unrelated", dependency_complete=True)
    assert complete["world_nonimpact_endorsed"] is True


def test_hidden_dependency_negative_control():
    # Declared graph says unrelated, but without completeness we refuse endorsement.
    result = nonimpact(GRAPH, ["raw"], "c_hidden_world_effect", dependency_complete=False)
    assert result["declared_nonimpact"] is True
    assert result["world_nonimpact_endorsed"] is False
