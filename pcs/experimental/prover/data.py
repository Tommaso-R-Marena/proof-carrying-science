"""Checked trajectory intake, alpha-duplicate firewall and existing PCS graphs."""
from __future__ import annotations

from copy import deepcopy
import hashlib

from pcs.proof_translation_v06 import _claim_ir_v06, _obligation, _proof_obligation_graph
from .ir import digest, theorem


def structural_fingerprint(ir):
    theorem(ir)
    variables = {}
    def normalize(e):
        if e["op"] == "var": return {"op": "var", "name": variables[e["name"]]}
        if e["op"] in {"forall", "exists"}:
            name = f"v{len(variables)}"
            variables[e["name"]] = name
            return {"op": e["op"], "name": name, "type": e["type"], "body": normalize(e["body"])}
        return {k: normalize(v) if type(v) is dict else v for k, v in e.items()}
    binders = []
    for b in ir["binders"]:
        name = f"v{len(variables)}"; variables[b["name"]] = name
        binders.append({"name": name, "type": b["type"]})
    return digest({"binders": binders, "body": normalize(ir["body"])})


def replay_receipt(env, goal, receipt):
    if type(receipt) is not dict or receipt.get("format") != "pcs-prover-proof-v1" or receipt.get("goal_sha256") != digest(goal) or receipt.get("statement") != theorem(goal):
        raise ValueError("receipt not bound to requested theorem")
    # Ignore producer success, reward, kernel and authority assertions.
    fresh = env.verify(goal, receipt["actions"])
    if fresh["proof"] != receipt.get("proof") or fresh["adapter_sha256"] != receipt.get("adapter_sha256") or fresh["lean"] != receipt.get("lean"):
        raise ValueError("receipt provenance or source mismatch")
    return fresh


def intake_feedback(env, feedback, heldout, *, license, source_revision):
    if license not in {"Apache-2.0", "MIT", "BSD-3-Clause", "CC0-1.0"} or not source_revision:
        raise ValueError("explicit cleared provenance required")
    goal = feedback["goal"]
    fingerprint = structural_fingerprint(goal)
    if fingerprint in {structural_fingerprint(t["goal"]) for t in heldout}:
        raise ValueError("evaluation firewall: held-out theorem or alpha duplicate")
    checked = replay_receipt(env, goal, feedback["receipt"])
    observed = env.observe(goal, checked["actions"])
    if observed["status"] != "closed":
        raise ValueError("trajectory does not close original theorem")
    return {"format": "pcs-intelligence-data-v1", "id": fingerprint, "family": fingerprint,
            "goal": deepcopy(goal), "original_statement": feedback["original_statement"],
            "split": "train", "license": license, "source_revision": source_revision,
            "source": "explicitly authorized local intake", "hint_exposure": feedback["hint_exposure"],
            "result": {"status": "verified", "receipt": checked, "states": observed["states"]},
            "checker_revision": checked["adapter_sha256"]}


def claim_graph(source, ir, receipt=None):
    raw = source.encode()
    source_sha = hashlib.sha256(raw).hexdigest()
    identifier = "lean-" + digest(ir)[:16]
    candidate = {"id": identifier, "source": {"name": "English statement", "source_sha256": source_sha},
        "artifact_ids": ["statement"], "selected": False, "formalizable": False,
        "status": "EXPERIMENTAL_LEAN_CHECKED" if receipt else "EXPERIMENTAL_LEAN_PROPOSAL",
        "typed_claim": {"id": identifier, "kind": "formal", "statement": source,
            "predicate": {"format": "pcs-math-ir-v1", "interpretation": ir,
                          "kernel_receipt_sha256": digest(receipt) if receipt else None}},
        "obligations": [_obligation(identifier, "ENGLISH_INTENT_GROUNDING",
            "The controlled grammar and kernel do not certify the researcher's intended English meaning.", blocking=True),
            _obligation(identifier, "REGISTERED_SCIENTIFIC_AUTHORITY",
            "Experimental Lean mathematics is not a registered PCS scientific acceptance adapter.", blocking=True)]}
    inventory = {"statement": {"id": "statement", "path": "statement.txt", "sha256": source_sha, "size": len(raw)}}
    claims = _claim_ir_v06([candidate])
    graph = _proof_obligation_graph([candidate], inventory=inventory, claim_ir=claims)
    return {"claim_ir": claims, "obligation_graph": graph, "pcs_authority": False}
