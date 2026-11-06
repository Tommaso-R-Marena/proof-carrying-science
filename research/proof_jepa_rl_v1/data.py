"""Authored, typed corpus and Lean-controlled transition intake.

Partitions are frozen by theorem template before any training. Alpha-equivalent
ASTs and declared template families cannot cross partitions. This is a public,
small structural holdout, not a secret external benchmark: distinct tautologies
can be logically equivalent, and primitive tactics necessarily recur.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
from pathlib import Path
import re
import time

from pcs.experimental.prover.data import (
    structural_fingerprint,
    replay_receipt as pcs_replay_receipt,
    claim_graph,
)
from pcs.experimental.prover.environment import search, SOURCE, WORKER
from pcs.experimental.prover.induction_ir import binary, declaration, digest, theorem, var


CORPUS_VERSION = "pcs-proof-jepa-authored-templates-v1"
SPLITS = ("train", "validation", "test")


def tasks():
    """Deterministic typed tasks; no solution trajectories attached to evaluation."""
    p, q, r, s = (var(n) for n in "PQRS")
    n, m, k = (var(v) for v in ("n", "m", "k"))
    b = binary
    neg = lambda a: {"op": "not", "arg": a}
    truth, false = {"op": "true"}, {"op": "false"}
    z, one = ({"op": "number", "value": i, "type": "Nat"} for i in (0, 1))
    rows = []

    def add(split, identity, family, names, body, domain="Prop", distribution="familiar_composition", control=False):
        goal = declaration(names, body, domain)
        rows.append({"id": identity, "family": family, "split": split,
                     "goal": goal, "source": "PCS authored public mathematical templates",
                     "license": "Apache-2.0", "corpus_version": CORPUS_VERSION,
                     "distribution": distribution, "negative_control": control})

    add("train", "identity", "implication_identity", ["P"], b("implies", p, p))
    add("train", "project_left", "binary_projection", ["P", "Q"], b("implies", b("and", p, q), p))
    add("train", "project_right", "binary_projection", ["P", "Q"], b("implies", b("and", p, q), q))
    add("train", "swap", "binary_swap", ["P", "Q"], b("implies", b("and", p, q), b("and", q, p)))
    add("train", "pair", "curried_pairing", ["P", "Q"], b("implies", p, b("implies", q, b("and", p, q))))
    add("train", "or_left", "binary_or_introduction", ["P", "Q"], b("implies", p, b("or", p, q)))
    add("train", "or_right", "binary_or_introduction", ["P", "Q"], b("implies", q, b("or", p, q)))
    add("train", "duplicate", "binary_duplicate", ["P"], b("implies", p, b("and", p, p)))
    add("train", "modus_ponens", "curried_application", ["P", "Q"], b("implies", b("implies", p, q), b("implies", p, q)))
    add("train", "projected_application", "projected_application", ["P", "Q"], b("implies", b("and", b("implies", p, q), p), q))
    add("train", "associate_forward", "conjunction_association", ["P", "Q", "R"], b("implies", b("and", b("and", p, q), r), b("and", p, b("and", q, r))))
    add("train", "associate_backward", "conjunction_association", ["P", "Q", "R"], b("implies", b("and", p, b("and", q, r)), b("and", b("and", p, q), r)))
    add("train", "or_swap", "disjunction_swap", ["P", "Q"], b("implies", b("or", p, q), b("or", q, p)))
    add("train", "iff_reflexive", "iff_reflexivity", ["P"], b("iff", p, p))
    add("train", "false_elimination", "false_elimination", ["P"], b("implies", false, p))
    add("train", "double_negation_intro", "double_negation_intro", ["P"], b("implies", p, neg(neg(p))))
    add("train", "truth_pair", "truth_adjoining", ["P"], b("implies", p, b("and", p, truth)))
    add("train", "nat_add_zero", "nat_add_identity", ["n"], b("eq", b("add", n, z), n), "Nat")
    add("train", "nat_zero_add", "nat_add_identity", ["n"], b("eq", b("add", z, n), n), "Nat")
    add("train", "nat_mul_one", "nat_mul_identity", ["n"], b("eq", b("mul", n, one), n), "Nat")
    add("train", "nat_mul_zero", "nat_mul_annihilation", ["n"], b("eq", b("mul", n, z), z), "Nat")
    add("train", "nat_add_comm", "nat_commutativity", ["n", "m"], b("eq", b("add", n, m), b("add", m, n)), "Nat")
    add("train", "nat_mul_comm", "nat_commutativity", ["n", "m"], b("eq", b("mul", n, m), b("mul", m, n)), "Nat")
    add("train", "nat_le_reflexive", "nat_order_reflexivity", ["n"], b("le", n, n), "Nat")

    add("validation", "chain_three", "three_step_chain", ["P", "Q", "R"], b("implies", b("implies", p, q), b("implies", b("implies", q, r), b("implies", p, r))))
    add("validation", "triple_reverse", "triple_reorder", ["P", "Q", "R"], b("implies", b("and", p, b("and", q, r)), b("and", r, b("and", q, p))))
    add("validation", "nested_identity", "nested_nat_identity", ["n"], b("eq", b("add", b("mul", n, one), z), n), "Nat")
    add("validation", "or_duplicate_elimination", "or_duplicate_elimination", ["P"], b("implies", b("or", p, p), p))
    add("validation", "iff_symmetry", "iff_symmetry", ["P", "Q"], b("implies", b("iff", p, q), b("iff", q, p)))
    add("validation", "order_antisymmetry", "order_antisymmetry", ["n", "m"], b("implies", b("le", n, m), b("implies", b("le", m, n), b("eq", n, m))), "Nat")

    add("test", "four_reorder", "four_reorder", ["P", "Q", "R", "S"], b("implies", b("and", p, b("and", q, b("and", r, s))), b("and", s, b("and", q, b("and", p, r)))))
    add("test", "four_chain", "four_chain", ["P", "Q", "R", "S"], b("implies", b("and", b("implies", p, q), b("and", b("implies", q, r), b("implies", r, s))), b("implies", p, s)))
    add("test", "and_or_distribution", "and_or_distribution", ["P", "Q", "R"], b("implies", b("and", p, b("or", q, r)), b("or", b("and", p, q), b("and", p, r))))
    add("test", "or_and_distribution", "or_and_distribution", ["P", "Q", "R"], b("implies", b("or", b("and", p, q), b("and", p, r)), b("and", p, b("or", q, r))))
    add("test", "contrapositive", "contrapositive", ["P", "Q"], b("implies", b("implies", p, q), b("implies", neg(q), neg(p))))
    add("test", "or_absorption", "or_absorption", ["P", "Q"], b("implies", b("or", p, b("and", p, q)), p))
    add("test", "nat_mixed_identity", "mixed_nat_identity", ["n", "m"], b("eq", b("add", b("mul", n, one), b("add", z, m)), b("add", n, m)), "Nat")
    add("test", "nat_comm_under_add", "contextual_commutativity", ["n", "m", "k"], b("eq", b("add", b("mul", n, m), k), b("add", b("mul", m, n), k)), "Nat")
    add("test", "existential_reflexivity", "existential_reflexivity", ["n"], {"op": "exists", "name": "w", "type": "Nat", "body": b("eq", n, var("w"))}, "Nat", "novel_quantifier")
    add("test", "unseen_distributivity", "nat_distributivity", ["n", "m", "k"], b("eq", b("mul", n, b("add", m, k)), b("add", b("mul", n, m), b("mul", n, k))), "Nat", "novel_law")
    add("test", "false_missing_assumption", "false_missing_assumption", ["P", "Q"], b("implies", p, q), control=True)
    add("test", "false_zero_identity", "false_zero_identity", ["n"], b("eq", n, z), "Nat", control=True)
    audit_splits(rows)
    return rows


def audit_splits(records):
    """Fail closed on duplicate IDs/alpha-ASTs and cross-partition families."""
    if not isinstance(records, list) or not records:
        raise ValueError("nonempty corpus required")
    identities, fingerprints, families = set(), {}, {}
    counts = {split: 0 for split in SPLITS}
    for row in records:
        if row["split"] not in SPLITS or not row["id"] or not row["family"]:
            raise ValueError("invalid task partition")
        theorem(row["goal"])
        if row["id"] in identities:
            raise ValueError("duplicate task ID")
        identities.add(row["id"])
        fp = structural_fingerprint(row["goal"])
        if fp in fingerprints:
            raise ValueError("alpha-equivalent theorem duplicate")
        fingerprints[fp] = row["split"]
        if row["family"] in families and families[row["family"]] != row["split"]:
            raise ValueError("template family crosses partitions")
        families[row["family"]] = row["split"]
        counts[row["split"]] += 1
        if row.get("negative_control") and row["split"] == "train":
            raise ValueError("test negative control entered training")
    return {"format": "pcs-proof-jepa-split-audit-v1", "counts": counts,
            "unique_alpha_asts": len(fingerprints), "families": len(families),
            "corpus_sha256": digest(records), "alpha_duplicates": 0,
            "scope": "authored AST/template separation; not exclusion of logical equivalence or primitive-lemma overlap"}


def _file_sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(65536), b""):
            h.update(block)
    return h.hexdigest()


def verifier_identity(env):
    """Observed host/binary provenance, not an immutable security-root assertion."""
    if digest(SOURCE.read_text()) != env.source_sha:
        raise ValueError("checker source changed after initialization")
    return {"lean_version": env.version,
            "lean_sha256": _file_sha256(env.lean),
            "probe_source_sha256": env.source_sha,
            "probe_olean_sha256": _file_sha256(env.cache / "PCSProofProbe.olean"),
            "worker_source_sha256": _file_sha256(WORKER),
            "scientific_authority": False}


def replay_receipt(env, record, receipt, expected_verifier=None):
    """Ignore claimed success; independently kernel-check the original theorem."""
    theorem(record["goal"])
    before = verifier_identity(env)
    if expected_verifier is not None and before != expected_verifier:
        raise ValueError("verifier provenance changed")
    fresh = pcs_replay_receipt(env, record["goal"], receipt)
    if verifier_identity(env) != before:
        raise ValueError("verifier changed during replay")
    return fresh


def collect(env, records, budget=48, depth=16, beam=4):
    """Collect only training feedback; search/checker controls every label.

    Final theorem verification is repeated independently of search's first
    verdict. Failed attempts and open states are observations, never proof
    receipts. No held-out task is searched or contributes a target here.
    """
    audit_splits(records)
    if any(row["split"] != "train" for row in records):
        raise ValueError("evaluation firewall: collector accepts train records only")
    started = time.monotonic()
    identity = verifier_identity(env)
    episodes, transitions, equivalence_evidence = [], [], []
    calls = env.invocations
    for record in records:
        result = search(env, record["goal"], budget=budget, depth=depth, beam=beam)
        if result["status"] == "verified":
            result["receipt"] = replay_receipt(env, record, result["receipt"], identity)
        episodes.append({**deepcopy(record), "result": result})
        successes = {}
        if result["status"] == "verified":
            path = result["receipt"]["actions"]
            states = result["states"]
            for step, action in enumerate(path):
                successes[digest([path[:step], action])] = {
                    "state": deepcopy(states[step]), "action": deepcopy(action),
                    "next_state": deepcopy(states[step + 1]), "valid": True,
                    "remaining": len(path) - step,
                    "future": [{"action": deepcopy(path[j]), "next_state": deepcopy(states[j + 1])}
                               for j in range(step + 1, min(step + 3, len(path)))],
                    "step": step, "trajectory_id": record["id"], "split": "train",
                    "kernel_completed": True, "receipt_sha256": digest(result["receipt"])}
        # A separately kernel-checked alpha-renaming gives a structure-preserving
        # pair at each corresponding step. Both whole proofs establish the same
        # original typed theorem; this is not a theorem that neural embeddings
        # preserve semantics. Bound extra checker work to four trajectories.
        if successes and len(equivalence_evidence) < 4:
            names = sorted({m.group(0) for action in path
                            for m in re.finditer(r"\bh[0-9]{1,2}\b", str(action["argument"]))})
            if names and len(names) <= 40:
                renaming = {name: f"h{50 + i}" for i, name in enumerate(names)}
                renamed = [{"kind": a["kind"], "argument":
                            re.sub(r"\bh[0-9]{1,2}\b", lambda m: renaming[m.group(0)], a["argument"])
                            if isinstance(a["argument"], str) else a["argument"]}
                           for a in path]
                alternate = env.observe(record["goal"], renamed)
                if alternate["status"] != "closed" or len(alternate["states"]) != len(states):
                    raise RuntimeError("renamed proof did not preserve the full trajectory")
                alternate_receipt = replay_receipt(env, record, env.verify(record["goal"], renamed), identity)
                evidence = {"goal_sha256": digest(record["goal"]),
                            "original_receipt_sha256": digest(result["receipt"]),
                            "renamed_receipt": alternate_receipt,
                            "renaming": renaming, "relation": "Lean-checked same theorem with fresh local binder names"}
                equivalence_evidence.append(evidence)
                for transition in successes.values():
                    transition["equivalent_state"] = deepcopy(alternate["states"][transition["step"] + 1])
                    transition["equivalence_receipt_sha256"] = digest(alternate_receipt)
        emitted = set()
        for attempt in result["attempts"]:
            if "state" not in attempt:
                continue
            key = digest([attempt["path"], attempt["action"]])
            if key in emitted:
                continue
            emitted.add(key)
            if key in successes:
                transitions.append(successes[key])
                continue
            valid = attempt["status"] in {"open", "closed"}
            after = env.observe(record["goal"], attempt["path"] + [attempt["action"]])["states"][-1] if valid else attempt["state"]
            transitions.append({"state": deepcopy(attempt["state"]), "action": deepcopy(attempt["action"]),
                                "next_state": deepcopy(after), "valid": valid, "remaining": None,
                                "future": [], "step": len(attempt["path"]),
                                "trajectory_id": record["id"], "split": "train",
                                "kernel_completed": False, "receipt_sha256": None})
        # Search's successful trajectory is normally a subset of attempts. Keep
        # a defensive completion path instead of silently losing accepted data.
        for key, transition in successes.items():
            if key not in emitted:
                transitions.append(transition)
    if verifier_identity(env) != identity:
        raise ValueError("verifier changed during collection")
    return {"format": "pcs-proof-jepa-transition-corpus-v1", "episodes": episodes,
            "transitions": transitions, "equivalence_evidence": equivalence_evidence, "verifier": identity,
            "training_ids": [row["id"] for row in records],
            "training_goal_sha256": [digest(row["goal"]) for row in records],
            "verified_episodes": sum(e["result"]["status"] == "verified" for e in episodes),
            "invalid_transitions": sum(not t["valid"] for t in transitions),
            "lean_invocations": env.invocations - calls,
            "wall_seconds": time.monotonic() - started,
            "data_sha256": digest(transitions), "authority": "NONE"}


def receipt_claim_graph(record, receipt=None):
    """Use existing PCS Canonical Claim IR/obligation graph without registration."""
    return claim_graph(record.get("original_statement", theorem(record["goal"])), record["goal"], receipt)
