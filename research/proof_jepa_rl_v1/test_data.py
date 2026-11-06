"""Partition, provenance and actual-kernel feedback boundary tests."""
from copy import deepcopy
import json
import shutil

import pytest

from pcs.experimental.prover.environment import LeanEnvironment, act, search
from pcs.experimental.prover.induction_ir import binary, declaration, var
from research.proof_jepa_rl_v1.data import (
    tasks, audit_splits, collect, replay_receipt, verifier_identity,
    receipt_claim_graph,
)


def test_frozen_public_partitions_and_training_boundary():
    rows = tasks()
    audit = audit_splits(rows)
    assert audit["unique_alpha_asts"] == len(rows)
    assert all(audit["counts"][s] > 0 for s in ("train", "validation", "test"))
    assert audit["scope"].startswith("authored AST/template")
    assert not any(r["negative_control"] for r in rows if r["split"] != "test")
    assert any(r["distribution"] == "novel_law" for r in rows if r["split"] == "test")
    assert tasks() == rows  # no process/global-RNG dependency


def test_alpha_duplicate_rejected_even_with_different_family():
    rows = tasks()
    duplicate = deepcopy(rows[0])
    duplicate.update(id="renamed_holdout", family="different_claimed_family", split="test")
    duplicate["goal"] = declaration(["X"], binary("implies", var("X"), var("X")))
    with pytest.raises(ValueError, match="alpha-equivalent"):
        audit_splits(rows + [duplicate])


def test_family_leakage_rejected_for_distinct_asts():
    rows = tasks()
    train = next(r for r in rows if r["split"] == "train")
    heldout = next(r for r in rows if r["split"] == "test")
    heldout["family"] = train["family"]
    with pytest.raises(ValueError, match="family"):
        audit_splits(rows)


def test_ill_typed_input_rejected_before_collection():
    rows = tasks()
    rows[0]["goal"]["body"]["left"] = {"op": "number", "value": 0, "type": "Nat"}
    with pytest.raises(ValueError):
        collect(object(), rows[:1])


def test_collector_refuses_all_evaluation_feedback_before_touching_checker():
    for split in ("validation", "test"):
        row = next(r for r in tasks() if r["split"] == split)
        with pytest.raises(ValueError, match="evaluation firewall"):
            collect(object(), [row])


def test_negative_control_cannot_be_relabelled_for_training():
    row = next(r for r in tasks() if r["negative_control"])
    row["split"] = "train"
    with pytest.raises(ValueError, match="negative control"):
        audit_splits([row])


@pytest.fixture(scope="module")
def lean(tmp_path_factory):
    # Required, rather than silently turning a no-checker run green. Caller
    # chooses whether to invoke this explicitly Lean-dependent research suite.
    assert shutil.which("lean"), "Pinned Lean 4.28.0 is required for data tests"
    env = LeanEnvironment(cache=tmp_path_factory.mktemp("proof-jepa-lean"), timeout=30)
    try:
        yield env
    finally:
        env.close()


def test_actual_collection_replay_and_equivalence(lean):
    row = tasks()[0]
    result = collect(lean, [row], budget=24)
    assert result["verified_episodes"] == 1
    receipt = result["episodes"][0]["result"]["receipt"]
    assert replay_receipt(lean, row, receipt) == receipt
    assert set(receipt["kernel"]["axioms"]) <= {"propext", "Classical.choice", "Quot.sound"}
    accepted = [t for t in result["transitions"] if t["kernel_completed"]]
    assert len(accepted) == len(receipt["actions"])
    assert accepted[0]["remaining"] == len(receipt["actions"])
    assert all(t["split"] == "train" for t in result["transitions"])
    assert result["equivalence_evidence"]
    evidence = result["equivalence_evidence"][0]
    renamed = evidence["renamed_receipt"]
    assert renamed["actions"] != receipt["actions"]
    assert renamed["goal_sha256"] == receipt["goal_sha256"]
    assert replay_receipt(lean, row, renamed) == renamed
    assert accepted[0]["equivalent_state"]
    assert result["authority"] == "NONE"
    # The stored corpus survives ordinary JSON serialization without losing
    # the exact action/statement binding needed for independent replay.
    restored = json.loads(json.dumps(result))
    replay_receipt(lean, row, restored["episodes"][0]["result"]["receipt"])


def test_actual_replay_rejects_forged_provenance_and_wrong_theorem(lean):
    row = tasks()[0]
    result = search(lean, row["goal"], budget=24)
    receipt = result["receipt"]
    forged = deepcopy(receipt)
    forged["adapter_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="provenance"):
        replay_receipt(lean, row, forged)
    other = next(r for r in tasks() if r["id"] == "false_missing_assumption")
    with pytest.raises(ValueError, match="bound"):
        replay_receipt(lean, other, receipt)
    expected = verifier_identity(lean)
    expected["lean_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="provenance"):
        replay_receipt(lean, row, receipt, expected)


def test_actual_false_control_never_gets_receipt(lean):
    row = next(r for r in tasks() if r["id"] == "false_missing_assumption")
    result = search(lean, row["goal"], budget=24, beam=3)
    assert result["status"] == "unknown" and result["receipt"] is None
    # Claimed positive metadata cannot turn a partial proof into acceptance.
    forged = {"format": "pcs-prover-proof-v1", "goal_sha256": "unbound", "actions": [],
              "kernel": {"axioms": []}, "status": "verified"}
    with pytest.raises(ValueError):
        replay_receipt(lean, row, forged)
    with pytest.raises(RuntimeError):
        lean.verify(row["goal"], [act("intro", "h0"), act("intro", "h1"), act("intro", "h2")])


def test_claim_graph_keeps_scientific_acceptance_obligations():
    result = receipt_claim_graph(tasks()[0])
    assert result["pcs_authority"] is False
    raw = json.dumps(result)
    assert "REGISTERED_SCIENTIFIC_AUTHORITY" in raw
    assert "ENGLISH_INTENT_GROUNDING" in raw
