"""PGRA v2 — proof-coupled recursive autoformalization.

v1 gates formalization/abstention capability. v2 additionally requires that
newly unlocked English statements are *kernel-proved* by the existing PCS
symbolic LeanEnvironment under a frozen budget, while previously proved items
are preserved.

This is research-only: pcs_scientific_authority=false, automatic_deployment=false.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

try:
    from .capability import evaluate_case, formalize_with_rules
    from .corpus import build_frozen_corpus, corpus_sha256
    from .gate import POLICY_HASH, digest
    from .grammar_extensions import RULE_IDS
except ImportError:  # flat sys.path research execution
    from capability import evaluate_case, formalize_with_rules
    from corpus import build_frozen_corpus, corpus_sha256
    from gate import POLICY_HASH, digest
    from grammar_extensions import RULE_IDS

# Frozen proof-search protocol — declared before any search.
PROOF_PROTOCOL = {
    "format": "pcs-pgra-proof-coupled-protocol-v2",
    "frozen": True,
    "budget": 96,
    "beam": 4,
    "depth": 18,
    "policy": "symbolic",
    "minimum_additional_proofs": 1,
    "automatic_deployment": False,
    "pcs_scientific_authority": False,
}

# Items expected to be kernel-provable after their required rules unlock.
# Chosen from the v1 e2e campaign (base / plus / distinct verified).
DEFAULT_PROOF_TARGETS = (
    "base_nat_eq",
    "base_nat_add",
    "dup_base_nat_eq",
    "ext_plus_times",
    "dup_ext_plus",
    "ext_distinct_forall",
)


def _search(ir: Mapping[str, Any], *, budget: int, beam: int) -> dict[str, Any]:
    from pcs.experimental.prover.environment import LeanEnvironment, search

    env = LeanEnvironment(timeout=90)
    try:
        return search(env, ir, budget=budget, beam=beam)
    finally:
        env.close()


def evaluate_proof_case(
    rules: frozenset[str],
    item: Mapping[str, Any],
    *,
    budget: int = 96,
    beam: int = 4,
    require_proof: bool = True,
) -> dict[str, Any]:
    """Formalize then optionally kernel-prove one corpus item."""
    case = evaluate_case(rules, item)
    row: dict[str, Any] = {
        "id": item["id"],
        "formalization_outcome": case.outcome,
        "lean": case.lean,
        "ir_digest": case.ir_digest,
        "proof_status": None,
        "action_count": None,
        "proved": False,
        "pcs_scientific_authority": False,
    }
    if case.outcome != "certified_supported":
        return row
    if not require_proof:
        return row
    result = formalize_with_rules(str(item["english"]), rules)
    ir = result["candidates"][0]["ir"]
    proved = _search(ir, budget=budget, beam=beam)
    row["proof_status"] = proved.get("status")
    if proved.get("status") == "verified" and proved.get("receipt"):
        row["proved"] = True
        row["action_count"] = len(proved["receipt"]["actions"])
        row["receipt_goal_sha256"] = proved["receipt"].get("goal_sha256")
    return row


def evaluate_proof_corpus(
    rules: frozenset[str],
    corpus: Sequence[Mapping[str, Any]],
    proof_ids: Sequence[str],
    *,
    budget: int = 96,
    beam: int = 4,
) -> dict[str, Any]:
    targets = [item for item in corpus if item["id"] in set(proof_ids)]
    rows = [
        evaluate_proof_case(rules, item, budget=budget, beam=beam, require_proof=True)
        for item in targets
    ]
    proved = frozenset(r["id"] for r in rows if r["proved"])
    formalized = frozenset(
        r["id"] for r in rows if r["formalization_outcome"] == "certified_supported"
    )
    # Exact loss: unproved proof-targets.
    loss = len(targets) - len(proved)
    return {
        "format": "pcs-pgra-proof-coupled-eval-v2",
        "rules": sorted(rules),
        "proof_ids": list(proof_ids),
        "rows": rows,
        "proved": sorted(proved),
        "formalized": sorted(formalized),
        "loss": loss,
        "proved_count": len(proved),
        "budget": budget,
        "beam": beam,
        "pcs_scientific_authority": False,
        "automatic_deployment": False,
    }


def accept_proof_coupled(
    old_rules: frozenset[str],
    new_rules: frozenset[str],
    corpus: Sequence[Mapping[str, Any]],
    proof_ids: Sequence[str],
    *,
    budget: int = 96,
    beam: int = 4,
    minimum_additional_proofs: int = 1,
) -> dict[str, Any]:
    """Gate: monotonic rules, preserve proved set, expand ≥1 new proof, loss↓."""
    if not old_rules <= new_rules:
        return {
            "accepted": False,
            "reason": "REJECT:rule_removal_or_nonmonotonic",
            "automatic_deployment": False,
            "pcs_scientific_authority": False,
        }
    old_eval = evaluate_proof_corpus(old_rules, corpus, proof_ids, budget=budget, beam=beam)
    new_eval = evaluate_proof_corpus(new_rules, corpus, proof_ids, budget=budget, beam=beam)
    old_proved = frozenset(old_eval["proved"])
    new_proved = frozenset(new_eval["proved"])
    preserved = old_proved <= new_proved
    gained = tuple(sorted(new_proved - old_proved))
    expanded = len(gained) >= minimum_additional_proofs
    loss_down = new_eval["loss"] < old_eval["loss"]
    if not preserved:
        reason = "REJECT:proved_capability_regression"
    elif not expanded:
        reason = "REJECT:no_new_kernel_proof"
    elif not loss_down:
        reason = "REJECT:proof_loss_not_strictly_lower"
    else:
        reason = "ACCEPT:reference_only_proof_coupled"
    return {
        "accepted": reason.startswith("ACCEPT"),
        "reason": reason,
        "old_proved": sorted(old_proved),
        "new_proved": sorted(new_proved),
        "gained": list(gained),
        "old_loss": old_eval["loss"],
        "new_loss": new_eval["loss"],
        "old_eval": old_eval,
        "new_eval": new_eval,
        "automatic_deployment": False,
        "pcs_scientific_authority": False,
    }


def recursive_proof_coupled(
    *,
    output: Path,
    proof_ids: Sequence[str] | None = None,
    max_generations: int = 6,
    budget: int = 96,
    beam: int = 4,
) -> dict[str, Any]:
    """Enable rules one-by-one when the proof-coupled gate accepts."""
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    corpus = build_frozen_corpus()
    targets = list(proof_ids or DEFAULT_PROOF_TARGETS)
    active: set[str] = set()
    generations: list[dict[str, Any]] = []
    baseline = evaluate_proof_corpus(frozenset(), corpus, targets, budget=budget, beam=beam)
    generations.append(
        {
            "generation": 0,
            "rules": [],
            "proved_count": baseline["proved_count"],
            "loss": baseline["loss"],
            "proved": baseline["proved"],
        }
    )
    for gen in range(1, max_generations + 1):
        selected = None
        attempts = []
        for rule in RULE_IDS:
            if rule in active:
                continue
            candidate = frozenset(active | {rule})
            decision = accept_proof_coupled(
                frozenset(active),
                candidate,
                corpus,
                targets,
                budget=budget,
                beam=beam,
            )
            attempts.append(
                {
                    "rule": rule,
                    "accepted": decision["accepted"],
                    "reason": decision["reason"],
                    "gained": decision.get("gained"),
                }
            )
            if decision["accepted"]:
                selected = (candidate, decision)
                break
        if selected is None:
            break
        active_fs, decision = selected
        active = set(active_fs)
        generations.append(
            {
                "generation": gen,
                "rules": sorted(active),
                "proved_count": len(decision["new_proved"]),
                "loss": decision["new_loss"],
                "proved": decision["new_proved"],
                "gained": decision["gained"],
                "reason": decision["reason"],
                "attempts": attempts,
            }
        )
        (output / f"proof-generation-{gen}.json").write_text(
            json.dumps(decision, indent=2, sort_keys=True) + "\n"
        )

    summary = {
        "format": "pcs-pgra-proof-coupled-summary-v2",
        "protocol": PROOF_PROTOCOL,
        "policy_hash": POLICY_HASH,
        "corpus_sha256": corpus_sha256(corpus),
        "proof_ids": targets,
        "accepted_generations": max(0, len(generations) - 1),
        "generations": generations,
        "proved_counts": [g["proved_count"] for g in generations],
        "rising_proved": all(
            generations[i]["proved_count"] < generations[i + 1]["proved_count"]
            for i in range(len(generations) - 1)
        )
        if len(generations) > 1
        else False,
        "final_rules": sorted(active),
        "automatic_deployment": False,
        "pcs_scientific_authority": False,
        "self_improvement_scope": (
            "Finite proof-coupled formalization rulebooks: kernel-proved count on a "
            "frozen authored proof-target set under preserve/expand/loss. Not general "
            "AI self-improvement or unrestricted English."
        ),
    }
    (output / "proof_coupled_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n"
    )
    sha = {
        p.name: hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(output.glob("*"))
        if p.is_file()
    }
    (output / "SHA256.json").write_text(json.dumps(sha, indent=2, sort_keys=True) + "\n")
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--max-generations", type=int, default=6)
    parser.add_argument("--budget", type=int, default=96)
    args = parser.parse_args(argv)
    summary = recursive_proof_coupled(
        output=args.output,
        max_generations=args.max_generations,
        budget=args.budget,
    )
    print(
        json.dumps(
            {
                "accepted_generations": summary["accepted_generations"],
                "proved_counts": summary["proved_counts"],
                "rising_proved": summary["rising_proved"],
                "final_rules": summary["final_rules"],
                "automatic_deployment": False,
                "pcs_scientific_authority": False,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
