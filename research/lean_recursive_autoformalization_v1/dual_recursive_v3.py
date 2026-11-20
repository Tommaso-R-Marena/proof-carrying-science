"""PGRA v3 — dual formalize+prove recursive autoformalization with holdout blind.

v1 gates formalization capability. v2 gates kernel proofs. v3 requires *both*
to improve on the fitting split (seed ∪ validation) while the holdout split is
never consulted by the acceptance gate — only reported after each accepted
generation.

Additionally, each accepted generation may harvest verified receipts into a
checked lemma library and measure whether re-proving previously solved targets
costs fewer Lean expansions (efficiency non-regression).

Research-only: pcs_scientific_authority=false, automatic_deployment=false.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

try:
    from .capability import evaluate_corpus
    from .corpus import build_frozen_corpus, corpus_sha256, split_corpus
    from .gate import POLICY_HASH, accept as accept_formalization
    from .grammar_extensions import RULE_IDS
    from .proof_coupled_v2 import (
        DEFAULT_PROOF_TARGETS,
        PROOF_PROTOCOL,
        accept_proof_coupled,
        evaluate_proof_corpus,
    )
except ImportError:  # flat sys.path research execution
    from capability import evaluate_corpus
    from corpus import build_frozen_corpus, corpus_sha256, split_corpus
    from gate import POLICY_HASH, accept as accept_formalization
    from grammar_extensions import RULE_IDS
    from proof_coupled_v2 import (
        DEFAULT_PROOF_TARGETS,
        PROOF_PROTOCOL,
        accept_proof_coupled,
        evaluate_proof_corpus,
    )

DUAL_PROTOCOL = {
    "format": "pcs-pgra-dual-recursive-protocol-v3",
    "frozen": True,
    "fitting_splits": ["seed", "validation"],
    "holdout_split": "holdout",
    "gate": "formalization_accept AND proof_coupled_accept on fitting only",
    "holdout_role": "report_only_never_gates",
    "lemma_harvest": "optional_efficiency_metric_after_accept",
    "automatic_deployment": False,
    "pcs_scientific_authority": False,
}


def fitting_corpus(corpus: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [dict(item) for item in corpus if item.get("split") in {"seed", "validation"}]


def holdout_corpus(corpus: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [dict(item) for item in split_corpus(list(corpus), "holdout")]


def fitting_proof_ids(
    corpus: Sequence[Mapping[str, Any]],
    proof_ids: Sequence[str],
) -> list[str]:
    fitting_ids = {item["id"] for item in fitting_corpus(corpus)}
    return [pid for pid in proof_ids if pid in fitting_ids]


def holdout_proof_ids(
    corpus: Sequence[Mapping[str, Any]],
    proof_ids: Sequence[str],
) -> list[str]:
    holdout_ids = {item["id"] for item in holdout_corpus(corpus)}
    return [pid for pid in proof_ids if pid in holdout_ids]


def accept_dual(
    old_rules: frozenset[str],
    new_rules: frozenset[str],
    corpus: Sequence[Mapping[str, Any]],
    proof_ids: Sequence[str],
    *,
    budget: int = 96,
    beam: int = 4,
) -> dict[str, Any]:
    """Accept only when both formalization and proof gates accept on fitting."""
    fit = fitting_corpus(corpus)
    fit_proofs = fitting_proof_ids(corpus, proof_ids)
    if not fit_proofs:
        return {
            "accepted": False,
            "reason": "REJECT:no_fitting_proof_targets",
            "automatic_deployment": False,
            "pcs_scientific_authority": False,
        }
    form = accept_formalization(old_rules, new_rules, fit)
    proof = accept_proof_coupled(
        old_rules,
        new_rules,
        fit,
        fit_proofs,
        budget=budget,
        beam=beam,
    )
    accepted = bool(form.accepted and proof["accepted"])
    if not form.accepted and not proof["accepted"]:
        reason = f"REJECT:dual_both_failed form={form.reason};proof={proof['reason']}"
    elif not form.accepted:
        reason = f"REJECT:formalization_gate form={form.reason}"
    elif not proof["accepted"]:
        reason = f"REJECT:proof_gate proof={proof['reason']}"
    else:
        reason = "ACCEPT:reference_only_dual_v3"
    return {
        "accepted": accepted,
        "reason": reason,
        "formalization": {
            "accepted": form.accepted,
            "reason": form.reason,
            "old_loss": form.old_loss,
            "new_loss": form.new_loss,
            "gained": list(form.gained),
        },
        "proof": {
            "accepted": proof["accepted"],
            "reason": proof["reason"],
            "old_loss": proof.get("old_loss"),
            "new_loss": proof.get("new_loss"),
            "gained": proof.get("gained"),
            "old_proved": proof.get("old_proved"),
            "new_proved": proof.get("new_proved"),
        },
        "fitting_proof_ids": fit_proofs,
        "automatic_deployment": False,
        "pcs_scientific_authority": False,
    }


def _harvest_library(
    rules: frozenset[str],
    corpus: Sequence[Mapping[str, Any]],
    proof_ids: Sequence[str],
    *,
    budget: int,
    beam: int,
) -> dict[str, Any]:
    """Harvest verified fitting proofs into a checked lemma library envelope."""
    from pcs.experimental.prover.environment import LeanEnvironment, search
    from pcs.experimental.prover.library import validate_library

    try:
        from .capability import formalize_with_rules
    except ImportError:
        from capability import formalize_with_rules

    from pcs.experimental.prover.data import structural_fingerprint

    targets = {item["id"]: item for item in corpus if item["id"] in set(proof_ids)}
    entries: list[dict[str, Any]] = []
    records: list[dict[str, Any]] = []
    seen_fps: set[str] = set()
    env = LeanEnvironment(timeout=90)
    try:
        for item_id in sorted(targets):
            item = targets[item_id]
            result = formalize_with_rules(str(item["english"]), rules)
            if result.get("status") not in {"supported", "ambiguous"} or not result.get(
                "candidates"
            ):
                records.append({"id": item_id, "status": "not_formalized"})
                continue
            ir = result["candidates"][0]["ir"]
            proved = search(env, ir, budget=budget, beam=beam)
            if proved is None or proved.get("status") != "verified" or not proved.get("receipt"):
                records.append({"id": item_id, "status": proved.get("status") if proved else None})
                continue
            checked = env.verify(ir, proved["receipt"]["actions"])
            fp = structural_fingerprint(ir)
            if fp in seen_fps:
                records.append(
                    {
                        "id": item_id,
                        "status": "verified_alpha_duplicate",
                        "expansions": proved.get("expansions"),
                        "actions": len(checked["actions"]),
                    }
                )
                continue
            seen_fps.add(fp)
            entries.append(
                {
                    "goal": ir,
                    "actions": checked["actions"],
                    "license": "CC0-1.0",
                    "source_revision": "pgra-dual-v3",
                }
            )
            records.append(
                {
                    "id": item_id,
                    "status": "verified",
                    "expansions": proved.get("expansions"),
                    "actions": len(checked["actions"]),
                }
            )
    finally:
        env.close()

    # Cap to library capacity (16); prefer shorter proofs.
    entries.sort(key=lambda e: len(e["actions"]))
    entries = entries[:16]
    library = {"format": "pcs-checked-lemma-library-v1", "entries": entries}
    if entries:
        validate_library(library)
    return {
        "library": library,
        "entry_count": len(entries),
        "records": records,
        "pcs_scientific_authority": False,
    }


def _measure_expansions(
    rules: frozenset[str],
    corpus: Sequence[Mapping[str, Any]],
    proof_ids: Sequence[str],
    *,
    budget: int,
    beam: int,
    library: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    from pcs.experimental.prover.environment import LeanEnvironment, search
    from pcs.experimental.prover.library import LibraryEnvironment, reuse_priority

    try:
        from .capability import formalize_with_rules
    except ImportError:
        from capability import formalize_with_rules

    targets = [item for item in corpus if item["id"] in set(proof_ids)]
    rows: list[dict[str, Any]] = []
    use_lib = bool(library and library.get("entries"))
    env: Any
    rank = reuse_priority if use_lib else None
    if use_lib:
        env = LibraryEnvironment(library, timeout=90)
    else:
        env = LeanEnvironment(timeout=90)
    try:
        for item in targets:
            result = formalize_with_rules(str(item["english"]), rules)
            if result.get("status") not in {"supported", "ambiguous"} or not result.get(
                "candidates"
            ):
                rows.append({"id": item["id"], "proved": False, "expansions": None})
                continue
            ir = result["candidates"][0]["ir"]
            proved = search(env, ir, rank, budget=budget, beam=beam)
            ok = bool(proved and proved.get("status") == "verified")
            rows.append(
                {
                    "id": item["id"],
                    "proved": ok,
                    "expansions": proved.get("expansions") if proved else None,
                }
            )
    finally:
        env.close()
    proved_rows = [r for r in rows if r["proved"] and r["expansions"] is not None]
    total_exp = sum(int(r["expansions"]) for r in proved_rows)
    return {
        "rows": rows,
        "proved_count": sum(1 for r in rows if r["proved"]),
        "total_expansions": total_exp,
        "mean_expansions": (total_exp / len(proved_rows)) if proved_rows else None,
        "used_library": use_lib,
        "ranker": "reuse_priority" if use_lib else "symbolic_default",
    }


def recursive_dual(
    *,
    output: Path,
    proof_ids: Sequence[str] | None = None,
    max_generations: int = 8,
    budget: int = 96,
    beam: int = 4,
    harvest_lemmas: bool = True,
) -> dict[str, Any]:
    """Enable rules one-by-one when the dual fitting gate accepts."""
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    corpus = build_frozen_corpus()
    targets = list(proof_ids or DEFAULT_PROOF_TARGETS)
    fit = fitting_corpus(corpus)
    hold = holdout_corpus(corpus)
    fit_proofs = fitting_proof_ids(corpus, targets)
    hold_proofs = holdout_proof_ids(corpus, targets)

    active: set[str] = set()
    generations: list[dict[str, Any]] = []

    baseline_form = evaluate_corpus(frozenset(), fit)
    baseline_proof = evaluate_proof_corpus(frozenset(), fit, fit_proofs, budget=budget, beam=beam)
    baseline_hold_form = evaluate_corpus(frozenset(), hold)
    baseline_hold_proof = evaluate_proof_corpus(
        frozenset(), hold, hold_proofs, budget=budget, beam=beam
    )
    generations.append(
        {
            "generation": 0,
            "rules": [],
            "fitting_certified": len(baseline_form.certified),
            "fitting_form_loss": baseline_form.loss,
            "fitting_proved": baseline_proof["proved_count"],
            "fitting_proof_loss": baseline_proof["loss"],
            "holdout_certified": len(baseline_hold_form.certified),
            "holdout_proved": baseline_hold_proof["proved_count"],
            "holdout_role": "report_only",
        }
    )

    last_library: dict[str, Any] | None = None
    for gen in range(1, max_generations + 1):
        selected = None
        attempts: list[dict[str, Any]] = []
        for rule in RULE_IDS:
            if rule in active:
                continue
            candidate = frozenset(active | {rule})
            decision = accept_dual(
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
                    "formalization_gained": decision["formalization"].get("gained"),
                    "proof_gained": decision["proof"].get("gained"),
                }
            )
            if decision["accepted"]:
                selected = (candidate, decision)
                break
        if selected is None:
            break
        active_fs, decision = selected
        active = set(active_fs)

        hold_form = evaluate_corpus(active_fs, hold)
        hold_proof = evaluate_proof_corpus(
            active_fs, hold, hold_proofs, budget=budget, beam=beam
        )

        harvest = None
        efficiency = None
        if harvest_lemmas:
            harvest = _harvest_library(
                active_fs, fit, fit_proofs, budget=budget, beam=beam
            )
            last_library = harvest["library"]
            (output / f"library-generation-{gen}.json").write_text(
                json.dumps(harvest, indent=2, sort_keys=True) + "\n"
            )
            bare = _measure_expansions(
                active_fs, fit, fit_proofs, budget=budget, beam=beam, library=None
            )
            with_lib = _measure_expansions(
                active_fs,
                fit,
                fit_proofs,
                budget=budget,
                beam=beam,
                library=last_library,
            )
            efficiency = {
                "bare_total_expansions": bare["total_expansions"],
                "library_total_expansions": with_lib["total_expansions"],
                "expansions_non_increasing": with_lib["total_expansions"]
                <= bare["total_expansions"],
                "library_entry_count": harvest["entry_count"],
            }

        event = {
            "generation": gen,
            "rules": sorted(active),
            "fitting_certified": len(
                evaluate_corpus(active_fs, fit).certified
            ),
            "fitting_form_loss": decision["formalization"]["new_loss"],
            "fitting_proved": len(decision["proof"].get("new_proved") or []),
            "fitting_proof_loss": decision["proof"]["new_loss"],
            "holdout_certified": len(hold_form.certified),
            "holdout_proved": hold_proof["proved_count"],
            "holdout_role": "report_only",
            "gained_formalization": decision["formalization"].get("gained"),
            "gained_proofs": decision["proof"].get("gained"),
            "reason": decision["reason"],
            "attempts": attempts,
            "efficiency": efficiency,
            "automatic_deployment": False,
            "pcs_scientific_authority": False,
        }
        generations.append(event)
        (output / f"dual-generation-{gen}.json").write_text(
            json.dumps({"decision": decision, "event": event}, indent=2, sort_keys=True)
            + "\n"
        )

    rising_fit_proved = all(
        generations[i]["fitting_proved"] < generations[i + 1]["fitting_proved"]
        for i in range(len(generations) - 1)
    ) if len(generations) > 1 else False
    rising_fit_certified = all(
        generations[i]["fitting_certified"] < generations[i + 1]["fitting_certified"]
        for i in range(len(generations) - 1)
    ) if len(generations) > 1 else False
    holdout_proved_nondecreasing = all(
        generations[i]["holdout_proved"] <= generations[i + 1]["holdout_proved"]
        for i in range(len(generations) - 1)
    ) if len(generations) > 1 else True

    summary = {
        "format": "pcs-pgra-dual-recursive-summary-v3",
        "protocol": DUAL_PROTOCOL,
        "proof_protocol": PROOF_PROTOCOL,
        "policy_hash": POLICY_HASH,
        "corpus_sha256": corpus_sha256(corpus),
        "proof_ids": targets,
        "fitting_proof_ids": fit_proofs,
        "holdout_proof_ids": hold_proofs,
        "accepted_generations": max(0, len(generations) - 1),
        "generations": generations,
        "fitting_proved_counts": [g["fitting_proved"] for g in generations],
        "fitting_certified_counts": [g["fitting_certified"] for g in generations],
        "holdout_proved_counts": [g["holdout_proved"] for g in generations],
        "rising_fitting_proved": rising_fit_proved,
        "rising_fitting_certified": rising_fit_certified,
        "holdout_proved_nondecreasing": holdout_proved_nondecreasing,
        "final_rules": sorted(active),
        "automatic_deployment": False,
        "pcs_scientific_authority": False,
        "self_improvement_scope": (
            "Finite dual formalize+prove rulebooks on fitting splits with holdout "
            "report-only; optional lemma-harvest efficiency. Not general AI "
            "self-improvement or unrestricted English."
        ),
    }
    (output / "dual_recursive_summary.json").write_text(
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
    parser.add_argument("--max-generations", type=int, default=8)
    parser.add_argument("--budget", type=int, default=96)
    parser.add_argument("--no-harvest", action="store_true")
    args = parser.parse_args(argv)
    summary = recursive_dual(
        output=args.output,
        max_generations=args.max_generations,
        budget=args.budget,
        harvest_lemmas=not args.no_harvest,
    )
    print(
        json.dumps(
            {
                "accepted_generations": summary["accepted_generations"],
                "fitting_proved_counts": summary["fitting_proved_counts"],
                "fitting_certified_counts": summary["fitting_certified_counts"],
                "holdout_proved_counts": summary["holdout_proved_counts"],
                "rising_fitting_proved": summary["rising_fitting_proved"],
                "rising_fitting_certified": summary["rising_fitting_certified"],
                "holdout_proved_nondecreasing": summary["holdout_proved_nondecreasing"],
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
