import copy
import os
import pytest

from pcs.experimental.prover.promotion import evaluate_promotion
from pcs.experimental.prover.state_graph import encode_state, decode_state
from pcs.experimental.prover.mathlib_retrieval import MathlibRetriever


def test_promotion_rejects_training_leak_and_inferior_checkpoint():
    sha = "a" * 64
    protocol = {"format": "pcs-promotion-protocol-v1", "frozen": True, "protocol_sha256": sha,
                "dataset_sha256": sha, "heldout_ids": ["unseen"], "budget": 48,
                "checker_sha256": sha, "max_calls_per_task": 100, "minimum_additional_solves": 1}
    row = {"id": "unseen", "budget": 48, "checker_sha256": sha, "physical_lean_calls": 10,
           "status": "verified", "independent_kernel_replay": True, "receipt_sha256": sha}
    candidate = {binding: sha for binding in ("source_sha256", "dataset_sha256", "checkpoint_sha256", "optimizer_sha256", "protocol_sha256", "architecture_sha256", "hyperparameters_sha256")}
    candidate.update(outcomes=[row], training_ids=["unseen"])
    decision = evaluate_promotion(candidate, {"outcomes": [row]}, protocol)
    assert not decision["eligible_for_review"]
    assert "holdout_leakage_training_ids" in decision["reasons"]
    assert "no_predeclared_heldout_improvement" in decision["reasons"]
    assert decision["automatic_deployment"] is False


def test_promotion_never_auto_deploys_verified_improvement():
    sha = "a" * 64
    protocol = {"format": "pcs-promotion-protocol-v1", "frozen": True, "protocol_sha256": sha,
                "dataset_sha256": sha, "heldout_ids": ["x"], "budget": 48,
                "checker_sha256": sha, "max_calls_per_task": 100, "minimum_additional_solves": 1}
    row = {"id": "x", "budget": 48, "checker_sha256": sha, "physical_lean_calls": 10,
           "status": "verified", "independent_kernel_replay": True, "receipt_sha256": sha}
    candidate = {binding: sha for binding in ("source_sha256", "dataset_sha256", "checkpoint_sha256", "optimizer_sha256", "protocol_sha256", "architecture_sha256", "hyperparameters_sha256")}
    candidate["outcomes"] = [row]
    result = evaluate_promotion(candidate, {"outcomes": [{**row, "status": "unknown"}]}, protocol)
    assert result["eligible_for_review"] and not result["automatic_deployment"]
    corrupted = copy.deepcopy(candidate)
    corrupted["outcomes"][0]["independent_kernel_replay"] = False
    assert not evaluate_promotion(corrupted, {"outcomes": [{**row, "status": "unknown"}]}, protocol)["eligible_for_review"]


def test_lossless_sharing_and_scope_edges():
    bound = {"kind": "bound", "value": "0", "children": []}
    domain = {"kind": "constant", "value": "Nat:[]", "children": []}
    expr = {"kind": "forall", "value": "n", "children": [domain, {"kind": "application", "value": "", "children": [bound, bound]}]}
    state = {"goals": [{"target": "test", "expression": expr, "locals": []}]}
    graph = encode_state(state)
    assert decode_state(graph) == state
    assert graph["unique_nodes"] < graph["occurrences"]
    assert len(graph["bindings"]) == 2
    assert graph["bindings"][0]["binder_path"] == [0, -1]
    damaged = copy.deepcopy(graph)
    damaged["nodes"][0]["children"] = [0]
    with pytest.raises(ValueError):
        decode_state(damaged)


@pytest.mark.parametrize("source", ["True := by sorry", "True\naxiom bad : False", "True; exact bad", "True /- hi -/", "by exact True"])
def test_external_statement_rejects_code(source):
    with pytest.raises(ValueError):
        MathlibRetriever._statement(source)


@pytest.mark.skipif(os.environ.get("PCS_REQUIRE_PROVER") != "1", reason="requires pinned real Lean environment")
def test_actual_std_hybrid_receipt_and_goal_tampering(tmp_path):
    from pcs.experimental.prover.hybrid import std_search, replay_std_receipt
    from pcs.experimental.prover.memory_cost import MeasuredInductionEnvironment
    from pcs.experimental.prover.induction_language import formalize
    goal = formalize("For all natural numbers n, (n + 0) equals n.")["candidates"][0]["ir"]
    env = MeasuredInductionEnvironment(cache=tmp_path, timeout=30)
    try:
        result = std_search(env, goal)
        assert result["status"] == "verified"
    finally:
        env.close()
    assert replay_std_receipt(goal, result["receipt"], cache=tmp_path)["status"] == "verified"
    forged = copy.deepcopy(result["receipt"])
    forged["goal_sha256"] = "f" * 64
    with pytest.raises(ValueError):
        replay_std_receipt(goal, forged, cache=tmp_path)
