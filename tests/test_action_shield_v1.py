from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

import pytest

from pcs.action_shield_v1 import (
    ActionShieldError, MODEL_FORMAT, SHIELD_FORMAT, admit_action, evaluate, kernel_replay,
    load_model, proof_source, propose,
)
from pcs.canonical_json import canonicalize_jcs_bytes


def model() -> dict:
    return {"format": MODEL_FORMAT, "states": [0, 1, 2, 3, 4, 5], "actions": [0, 1, 2, 3, 4, 5],
        "initial": [0], "safe": [0, 1, 2, 3, 4], "forbidden": [5],
        "transitions": [{"source": s, "action": a, "target": t} for s, a, t in [
            (0, 0, 0), (0, 0, 1), (0, 1, 5), (0, 5, 0), (1, 1, 2), (1, 5, 5),
            (2, 2, 3), (2, 3, 4), (2, 3, 5), (2, 5, 5), (3, 3, 4), (3, 5, 5),
            (4, 4, 4), (4, 5, 5), (5, 4, 5)]],
        "assumptions": [
            {"id": "model_completeness", "statement": "All possible tool outcomes are included in this finite transition relation.", "status": "OPEN"},
            {"id": "shield_enforcement", "statement": "Every executed action passes this exact shield; no alternate tool entry bypasses it.", "status": "OPEN"},
            {"id": "state_observation", "statement": "The observed state/action IDs correspond to actual authorization and information-flow state.", "status": "OPEN"}]}


def data() -> tuple[bytes, bytes]:
    raw = canonicalize_jcs_bytes(model())
    return raw, canonicalize_jcs_bytes(propose(raw))


def altered_shield(raw: bytes, shield_raw: bytes, pair: list[int]) -> bytes:
    shield = json.loads(shield_raw)
    shield["allowed"] = sorted([*shield["allowed"], pair])
    return canonicalize_jcs_bytes(shield)


def test_all_nondeterministic_outcomes_and_two_safety_obligations():
    raw, shield = data()
    report = evaluate(raw, shield)
    assert report["outcome"] == "PASS"
    assert report["allowed_pairs"] == [[0, 0], [1, 1], [2, 2], [3, 3], [4, 4]]
    assert [2, 3] in report["restricted_pairs"]
    assert report["reachable_states"] == [0, 1, 2, 3, 4]
    assert report["reachable_deadlocks"] == []
    assert report["formal_model_support"] == "REQUIRES_FRESH_KERNEL_REPLAY"
    assert report["deployment_safety"] == report["liveness"] == "OPEN"
    assert all(x["status"] == "OPEN" for x in report["assumptions"])


def test_safe_observed_branch_does_not_certify_unsafe_unobserved_successor():
    raw, shield = data()
    report = evaluate(raw, altered_shield(raw, shield, [2, 3]))
    assert report["outcome"] == "FAIL"
    assert report["violations"] == [{"kind": "unsafe_successor", "transition": {"source": 2, "action": 3, "target": 5}}]
    assert 5 in report["reachable_states"]


def test_runtime_untrusted_action_proposals_and_deadlocks_fail_closed():
    raw, shield = data()
    assert admit_action(raw, shield, 0, 0) is True
    assert admit_action(raw, shield, 0, 1) is False
    assert admit_action(raw, shield, 2, 3) is False
    assert admit_action(raw, shield, 3, 3) is True
    assert admit_action(raw, shield, 5, 4) is False
    assert admit_action(raw, shield, 99, 0) is False
    assert admit_action(raw, altered_shield(raw, shield, [2, 3]), 0, 0) is False
    with pytest.raises(ActionShieldError):
        admit_action(raw, shield, True, 0)


def test_forbidden_action_even_when_target_is_safe():
    raw, shield = data()
    report = evaluate(raw, altered_shield(raw, shield, [0, 5]))
    assert report["checks"]["all_nondeterministic_successors_safe"] is True
    assert report["checks"]["forbidden_actions_excluded"] is False
    assert report["outcome"] == "FAIL"


def test_nonmaximal_or_all_deny_shield_never_claims_liveness():
    raw, shield_raw = data()
    shield = json.loads(shield_raw)
    for allowed, deadlocks in [([[0, 0]], [1]), ([], [0])]:
        shield["allowed"] = allowed
        report = evaluate(raw, canonicalize_jcs_bytes(shield))
        assert report["outcome"] == "PASS"
        assert report["reachable_deadlocks"] == deadlocks
        assert report["liveness"] == "OPEN" and report["maximality_authority"] is False


def test_initial_condition_cannot_be_omitted():
    value = model()
    value["initial"] = [5]
    raw = canonicalize_jcs_bytes(value)
    report = evaluate(raw, canonicalize_jcs_bytes(propose(raw)))
    assert report["outcome"] == "FAIL"
    assert report["violations"] == [{"kind": "unsafe_initial", "state": 5}]


def test_omitted_successor_is_a_different_model_not_external_completeness():
    raw, shield_raw = data()
    omitted = model()
    omitted["transitions"] = [e for e in omitted["transitions"] if e != {"source": 2, "action": 3, "target": 5}]
    omitted_raw = canonicalize_jcs_bytes(omitted)
    stale = altered_shield(raw, shield_raw, [2, 3])
    with pytest.raises(ActionShieldError, match="exact model"):
        evaluate(omitted_raw, stale)
    new_shield = canonicalize_jcs_bytes(propose(omitted_raw))
    assert [2, 3] in json.loads(new_shield)["allowed"]
    report = evaluate(omitted_raw, new_shield)
    assert report["outcome"] == "PASS" and report["deployment_safety"] == "OPEN"
    assert report["model_sha256"] != evaluate(raw, shield_raw)["model_sha256"]


@pytest.mark.parametrize("mutate", [
    lambda m: m.update(states=[False, 1]),
    lambda m: m.update(initial=[]),
    lambda m: m.update(safe=[]),
    lambda m: m.update(actions=list(range(17))),
    lambda m: m.update(states=list(range(33))),
    lambda m: m.update(transitions=[]),
    lambda m: m["transitions"].append(m["transitions"][0]),
    lambda m: m["transitions"][0].update(target=99),
    lambda m: m["transitions"][0].update(action=0.0),
    lambda m: m["assumptions"][0].update(status="VERIFIED"),
    lambda m: m["assumptions"][0].update(id=[]),
    lambda m: m.update(assumptions=[]),
    lambda m: m.update(extra="ignored"),
])
def test_malformed_model_is_rejected(mutate):
    value = model()
    mutate(value)
    with pytest.raises(ActionShieldError):
        load_model(json.dumps(value).encode())


@pytest.mark.parametrize("raw", [b'{"format":"x","format":"y"}', b'{"x":NaN}', b'\xff', b'[' * 1000])
def test_strict_json_errors(raw):
    with pytest.raises(ActionShieldError):
        load_model(raw)


@pytest.mark.parametrize("allowed", [[[0, True]], [[0, 0], [0, 0]], [[5, 0]], [[0, 0.0]], [[0, 0, 1]]])
def test_malformed_shields_fail_closed(allowed):
    raw, shield_raw = data()
    shield = json.loads(shield_raw)
    shield["allowed"] = allowed
    with pytest.raises(ActionShieldError):
        evaluate(raw, json.dumps(shield).encode())


def test_only_integer_literals_enter_generated_lean_source():
    value = model()
    value["assumptions"][0]["statement"] = '"\naxiom bad : False\n--'
    raw = canonicalize_jcs_bytes(value)
    proof = proof_source(raw, canonicalize_jcs_bytes(propose(raw)))
    assert b"axiom bad" not in proof
    assert b"native_decide" not in proof
    assert b"all_finite_histories_safe" in proof


def test_actual_fresh_kernel_positive_and_negative_replay():
    raw, shield = data()
    good = kernel_replay(raw, shield)
    assert good["kernel_checked"] is True, good
    assert good["status"] == "KERNEL_CHECKED"
    assert set(good["kernel_axioms"]).issubset({"propext", "Classical.choice", "Quot.sound"})
    bad = kernel_replay(raw, altered_shield(raw, shield, [2, 3]))
    assert bad["kernel_checked"] is False and bad["status"] == "CERTIFICATE_REJECTED"


def test_kernel_exhaustion_does_not_grant_support(monkeypatch):
    import subprocess
    import pcs.action_shield_v1 as module
    raw, shield = data()
    def exhausted(*args, **kwargs):
        raise subprocess.TimeoutExpired("lean", 1)
    monkeypatch.setattr(module.subprocess, "run", exhausted)
    result = kernel_replay(raw, shield)
    assert result["kernel_checked"] is False and result["status"] == "UNAVAILABLE_OR_EXHAUSTED"


def test_unsupported_compiler_does_not_grant_support(monkeypatch):
    import subprocess
    import pcs.action_shield_v1 as module
    raw, shield = data()
    monkeypatch.setattr(module.subprocess, "run", lambda *a, **kw:
        subprocess.CompletedProcess(a, 0, "Lean version 4.27.0", ""))
    assert kernel_replay(raw, shield)["status"] == "UNSUPPORTED_LEAN_VERSION"
