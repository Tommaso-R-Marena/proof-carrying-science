"""
Adversarial attack suite.

Each attack returns AttackResult with success/failure.
success=True means the *attack* succeeded (verifier incorrectly accepted
forged/stale state) — that is a security failure we must fix.
Attack failure (success=False) is the desired outcome for a sound verifier.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from fractions import Fraction
from typing import Any, Callable, Dict, List, Optional

from cache.store import Cache, CacheEntry, reuse_permitted
from model.graph import (
    Certificate,
    Graph,
    Node,
    ObligationKey,
    canonicalize_value,
    obligation_of,
    reject_duplicate_keys,
)
from model.ops import (
    DEFAULT_POLICY,
    OP_INT_ADD,
    OP_INT_CONST,
    OP_INT_MUL,
    OpRegistry,
    default_registry,
)
from reference.fresh import fresh_verify
from verifier.incremental import IncrementalVerifier


@dataclass
class AttackResult:
    name: str
    attack_succeeded: bool  # True = verifier was fooled (bad)
    detail: str
    counterexample: Optional[Dict[str, Any]] = None

    @property
    def verifier_resisted(self) -> bool:
        return not self.attack_succeeded

    def to_json(self) -> dict:
        return {
            "name": self.name,
            "attack_succeeded": self.attack_succeeded,
            "verifier_resisted": self.verifier_resisted,
            "detail": self.detail,
            "counterexample": self.counterexample,
        }


def _tiny_graph(registry: Optional[OpRegistry] = None) -> Graph:
    # a=2, b=3, c=a+b=5, d=c*b=15
    return Graph(
        nodes=[
            Node(id=0, op=OP_INT_CONST, deps=(), policy=DEFAULT_POLICY, version=1, evidence=2),
            Node(id=1, op=OP_INT_CONST, deps=(), policy=DEFAULT_POLICY, version=1, evidence=3),
            Node(id=2, op=OP_INT_ADD, deps=(0, 1), policy=DEFAULT_POLICY, version=1, evidence=0),
            Node(id=3, op=OP_INT_MUL, deps=(2, 1), policy=DEFAULT_POLICY, version=1, evidence=0),
        ]
    )


def _setup() -> IncrementalVerifier:
    v = IncrementalVerifier(default_registry(version=1))
    r = v.initial_verify(_tiny_graph())
    assert r.accepted, r.error
    return v


# --------------------------------------------------------------------------- attacks


def attack_input_substitution() -> AttackResult:
    """Change evidence/input but try to reuse old certificate."""
    v = _setup()
    # Change node 0 evidence 2 -> 9, but sneak old certs for unaffected path
    new_nodes = [
        Node(id=0, op=OP_INT_CONST, deps=(), policy=DEFAULT_POLICY, version=1, evidence=9),
    ]
    # Provide forged cert claiming output still 2
    forged = {
        0: Certificate(payload=("ok", OP_INT_CONST, ("int", 2)), output=2),
    }
    new_g = v.graph.replace_nodes(new_nodes)
    report = v.revalidate(new_g, changes=[0], provided_certs=forged, compare_fresh=True)
    # Attack succeeds if verifier accepts wrong output for node 0
    fooled = report.accepted and report.outputs.get(0) == 2
    return AttackResult(
        name="input_substitution",
        attack_succeeded=fooled,
        detail=(
            "accepted forged const after evidence change"
            if fooled
            else f"resisted: accepted={report.accepted}, out0={report.outputs.get(0)}, err={report.error}"
        ),
        counterexample={"report": report.to_json()} if fooled else None,
    )


def attack_dependency_manipulation() -> AttackResult:
    """Rewire deps so node 2 uses different inputs; attempt stale reuse."""
    v = _setup()
    # Swap: node 2 = add(1,1) instead of add(0,1) — topology change at 2
    repl = [Node(id=2, op=OP_INT_ADD, deps=(1, 1), policy=DEFAULT_POLICY, version=1, evidence=0)]
    new_g = v.graph.replace_nodes(repl)
    # Forge cert claiming still 5
    forged = {2: Certificate(payload=("ok", OP_INT_ADD, ("int", 5)), output=5)}
    report = v.revalidate(new_g, changes=[2], provided_certs=forged, compare_fresh=True)
    fooled = report.accepted and report.outputs.get(2) == 5
    return AttackResult(
        name="dependency_manipulation",
        attack_succeeded=fooled,
        detail=(
            "accepted stale dep wiring"
            if fooled
            else f"resisted: accepted={report.accepted}, out2={report.outputs.get(2)}"
        ),
        counterexample={"report": report.to_json()} if fooled else None,
    )


def attack_op_substitution() -> AttackResult:
    """Replace add with mul; try to keep old output cert."""
    v = _setup()
    repl = [Node(id=2, op=OP_INT_MUL, deps=(0, 1), policy=DEFAULT_POLICY, version=1, evidence=0)]
    forged = {2: Certificate(payload=("ok", OP_INT_ADD, ("int", 5)), output=5)}
    new_g = v.graph.replace_nodes(repl)
    report = v.revalidate(new_g, changes=[2], provided_certs=forged, compare_fresh=True)
    # Correct mul would be 6; attack succeeds if accepts 5 with mul node
    fooled = report.accepted and report.outputs.get(2) == 5
    return AttackResult(
        name="op_substitution",
        attack_succeeded=fooled,
        detail=(
            "accepted old add cert under mul op"
            if fooled
            else f"resisted: accepted={report.accepted}, out2={report.outputs.get(2)}"
        ),
        counterexample={"report": report.to_json()} if fooled else None,
    )


def attack_policy_substitution() -> AttackResult:
    """Change policy id; cache entry with old policy must not reuse under new policy."""
    v = _setup()
    # First, change registry to allow policy 2, then change node policy
    v.registry.allowed_policies.add(2)
    # Change policy on leaf-ish node 3 without changing computation
    repl = [Node(id=3, op=OP_INT_MUL, deps=(2, 1), policy=2, version=1, evidence=0)]
    new_g = v.graph.replace_nodes(repl)
    # Attempt: put a cache entry that matches new key but prior_accepted=False,
    # AND also leave old key. Reuse should fail for new policy (different key).
    report = v.revalidate(new_g, changes=[3], compare_fresh=True)
    # Attack: if somehow reused without recheck under new policy with forged authority
    # Stronger: inject forged authoritative-looking entry without going through verify
    v2 = _setup()
    v2.registry.allowed_policies.add(2)
    # Manually forge cache entry for NEW obligation with prior_accepted=False claiming 15
    # After change, obligation key differs in policy; lookup miss → recheck.
    # Also try putting entry with prior_accepted=False for the new key
    fresh = fresh_verify(v2.graph, v2.registry)
    # Build new key for policy=2
    dep_outs = [fresh.outputs[2], fresh.outputs[1]]
    new_node = Node(id=3, op=OP_INT_MUL, deps=(2, 1), policy=2, version=1, evidence=0)
    new_key = obligation_of(new_node, dep_outs)
    forged_cert = Certificate(payload=("ok", OP_INT_MUL, ("int", 999)), output=999)
    v2.cache.put_untrusted(new_key, forged_cert)
    new_g = v2.graph.replace_nodes([new_node])
    report = v2.revalidate(new_g, changes=[3], compare_fresh=True)
    fooled = report.accepted and report.outputs.get(3) == 999
    return AttackResult(
        name="policy_substitution",
        attack_succeeded=fooled,
        detail=(
            "reused untrusted/forged policy entry"
            if fooled
            else f"resisted: accepted={report.accepted}, out3={report.outputs.get(3)}, reused={report.reused}"
        ),
        counterexample={"report": report.to_json()} if fooled else None,
    )


def attack_version_mismatch() -> AttackResult:
    """Node version ≠ registry version must fail."""
    v = _setup()
    repl = [Node(id=2, op=OP_INT_ADD, deps=(0, 1), policy=DEFAULT_POLICY, version=99, evidence=0)]
    new_g = v.graph.replace_nodes(repl)
    report = v.revalidate(new_g, changes=[2], compare_fresh=True)
    fooled = report.accepted  # should reject
    return AttackResult(
        name="version_mismatch",
        attack_succeeded=fooled,
        detail=(
            "accepted mismatched version"
            if fooled
            else f"resisted: accepted={report.accepted}, err={report.error}"
        ),
        counterexample={"report": report.to_json()} if fooled else None,
    )


def attack_cache_forgery() -> AttackResult:
    """Inject wrong cert: (A) prior_accepted=False; (B) forged prior_accepted=True."""
    # (A) no authority → must recheck, not accept output 0
    v = _setup()
    assert v.valid_state is not None
    real_entries = [e for e in v.cache.entries if e.key.id == 3]
    assert real_entries
    real = real_entries[0]
    v.cache.put(
        CacheEntry(
            key=real.key,
            cert=Certificate(payload=("ok", OP_INT_MUL, ("int", 0)), output=0),
            prior_accepted=False,
        )
    )
    report_a = v.revalidate(v.graph.copy(), changes=[], compare_fresh=True)
    fooled_a = report_a.accepted and report_a.outputs.get(3) == 0

    # (B) forged authority flag + wrong math → local check on reuse must fail-closed
    v2 = _setup()
    real2 = [e for e in v2.cache.entries if e.key.id == 3][0]
    v2.cache.put(
        CacheEntry(
            key=real2.key,
            cert=Certificate(payload=("ok", OP_INT_MUL, ("int", 0)), output=0),
            prior_accepted=True,
        )
    )
    report_b = v2.revalidate(v2.graph.copy(), changes=[], compare_fresh=True)
    fooled_b = report_b.accepted and report_b.outputs.get(3) == 0

    fooled = fooled_a or fooled_b
    return AttackResult(
        name="cache_forgery",
        attack_succeeded=fooled,
        detail=(
            "accepted forged cache payload"
            if fooled
            else (
                f"resisted: A out3={report_a.outputs.get(3)} rechecked={report_a.rechecked}; "
                f"B accepted={report_b.accepted} out3={report_b.outputs.get(3)}"
            )
        ),
        counterexample=(
            {"a": report_a.to_json(), "b": report_b.to_json()} if fooled else None
        ),
    )


def attack_serialization_duplicate_keys() -> AttackResult:
    """Duplicate JSON keys must be rejected by loader."""
    payload = '{"nodes":[{"id":0,"op":1,"deps":[],"policy":1,"version":1,"evidence":1,"evidence":99}]}'
    try:
        data = json.loads(payload, object_pairs_hook=reject_duplicate_keys)
        # if we got here without error, attack succeeded (duplicate accepted)
        fooled = True
        detail = f"duplicate key accepted: {data}"
        cex = {"data": data}
    except ValueError as exc:
        fooled = False
        detail = f"resisted: {exc}"
        cex = None
    return AttackResult(
        name="serialization_duplicate_keys",
        attack_succeeded=fooled,
        detail=detail,
        counterexample=cex,
    )


def attack_rollback() -> AttackResult:
    """
    Rollback: after accepting a change, try to re-insert an old cache entry
    for a superseded obligation and reuse it after another change that should
    not revive the old value.
    """
    v = _setup()
    # Change evidence of node 0: 2 -> 4; c becomes 7, d becomes 21
    r1 = v.apply_node_changes(
        [Node(id=0, op=OP_INT_CONST, deps=(), policy=DEFAULT_POLICY, version=1, evidence=4)]
    )
    assert r1.accepted and r1.outputs[3] == 21
    # Snapshot old (stale) certificate for original obligation of node 0
    stale_key = ObligationKey(
        id=0, op=OP_INT_CONST, policy=DEFAULT_POLICY, version=1, evidence=2, dep_outputs=()
    )
    stale_cert = Certificate(payload=("ok", OP_INT_CONST, ("int", 2)), output=2)
    # Inject stale authoritative-looking entry (attacker sets prior_accepted True)
    # Trust model: only verifier may set prior_accepted; but we simulate forgery of the flag
    v.cache.put(CacheEntry(key=stale_key, cert=stale_cert, prior_accepted=True))
    # Now change node 0 again to evidence=2 (rollback of definition)
    # Correct output is 2; that's fine. Attack is: change to evidence=5 but reuse stale 2
    # via somehow matching keys — classic rollback is accepting old state without recheck.
    # Variant: change to evidence=5; inject stale key for evidence=5 wrongly.
    wrong = CacheEntry(
        key=ObligationKey(
            id=0, op=OP_INT_CONST, policy=DEFAULT_POLICY, version=1, evidence=5, dep_outputs=()
        ),
        cert=Certificate(payload=("ok", OP_INT_CONST, ("int", 2)), output=2),
        prior_accepted=True,  # forged authority
    )
    v.cache.put(wrong)
    new_g = v.graph.replace_nodes(
        [Node(id=0, op=OP_INT_CONST, deps=(), policy=DEFAULT_POLICY, version=1, evidence=5)]
    )
    report = v.revalidate(new_g, changes=[0], compare_fresh=True)
    # Node 0 is affected → must recheck, ignoring forged cache for that key
    # If implementation wrongly reuses affected nodes from cache, attack succeeds
    fooled = report.accepted and report.outputs.get(0) == 2 and 0 in report.reused
    return AttackResult(
        name="rollback",
        attack_succeeded=fooled,
        detail=(
            "reused stale rolled-back value on affected node"
            if fooled
            else f"resisted: out0={report.outputs.get(0)}, reused={report.reused}, rechecked={report.rechecked}"
        ),
        counterexample={"report": report.to_json()} if fooled else None,
    )


def attack_proof_context_misuse() -> AttackResult:
    """
    Use a certificate that checks under a different proof context (wrong op in payload)
    or attach a valid cert from another node.
    """
    v = _setup()
    # Take node 3's valid cert and try to use it for node 2 after a change
    cert3 = v.valid_state.certs[3]
    repl = [Node(id=2, op=OP_INT_ADD, deps=(0, 1), policy=DEFAULT_POLICY, version=1, evidence=0)]
    # Force recheck of 2 with wrong cert (from node 3)
    new_g = v.graph.replace_nodes(repl)
    # Mark 2 changed (even if definition same) to force recheck path with provided cert
    report = v.revalidate(new_g, changes=[2], provided_certs={2: cert3}, compare_fresh=True)
    fooled = report.accepted and canonicalize_value(report.outputs.get(2, -1)) == canonicalize_value(
        cert3.output
    )
    # Actually if cert3.output is 15 and node 2 should be 5, accepting 15 is the attack
    # local_check should fail because payload/op/output don't match add(2,3)=5
    return AttackResult(
        name="proof_context_misuse",
        attack_succeeded=fooled,
        detail=(
            "accepted foreign node certificate"
            if fooled
            else f"resisted: accepted={report.accepted}, out2={report.outputs.get(2)}, err={report.error}"
        ),
        counterexample={"report": report.to_json()} if fooled else None,
    )


ALL_ATTACKS: List[Callable[[], AttackResult]] = [
    attack_input_substitution,
    attack_dependency_manipulation,
    attack_op_substitution,
    attack_policy_substitution,
    attack_version_mismatch,
    attack_cache_forgery,
    attack_serialization_duplicate_keys,
    attack_rollback,
    attack_proof_context_misuse,
]


def run_all_attacks() -> List[AttackResult]:
    results: List[AttackResult] = []
    for fn in ALL_ATTACKS:
        try:
            results.append(fn())
        except Exception as exc:
            results.append(
                AttackResult(
                    name=getattr(fn, "__name__", "unknown"),
                    attack_succeeded=True,  # unexpected crash treated as failure to resist cleanly
                    detail=f"exception during attack: {exc}",
                    counterexample={"exception": str(exc)},
                )
            )
    return results
