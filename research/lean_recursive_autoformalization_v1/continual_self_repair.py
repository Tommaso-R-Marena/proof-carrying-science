"""PGRA continual self-repair controller — research only.

Breakthrough over one-shot recursive loops: when a proposal is REJECTED by the
dual formalize+prove gate, the controller does **not** stop. It diagnoses the
reject reason, proposes a structured repair, re-gates, and only CAS-promotes
on ACCEPT. Rejected states never become HEAD (PGSI gatedStep semantics).

This demonstrates genuine proof-gated self-improvement that continually runs
and fixes itself inside a finite frozen protocol — not unrestricted AI
self-modification.

Invariants (never weakened):
  * fitting-only dual gate (holdout report-only)
  * monotonic rulebooks (no removals)
  * preserve / expand / strict loss on both formalization and proof sides
  * automatic_deployment=false, pcs_scientific_authority=false
"""
from __future__ import annotations

import argparse
import hashlib
import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Mapping, Sequence

try:
    from .capability import evaluate_corpus
    from .corpus import build_frozen_corpus, corpus_sha256
    from .dual_recursive_v3 import (
        accept_dual,
        fitting_corpus,
        fitting_proof_ids,
        holdout_corpus,
        holdout_proof_ids,
    )
    from .gate import POLICY_HASH
    from .grammar_extensions import RULE_IDS
    from .proof_coupled_v2 import DEFAULT_PROOF_TARGETS, evaluate_proof_corpus
    from .store import FormalizationPromotionStore, ProposalRejected, StaleHead
except ImportError:  # flat sys.path research execution
    from capability import evaluate_corpus
    from corpus import build_frozen_corpus, corpus_sha256
    from dual_recursive_v3 import (
        accept_dual,
        fitting_corpus,
        fitting_proof_ids,
        holdout_corpus,
        holdout_proof_ids,
    )
    from gate import POLICY_HASH
    from grammar_extensions import RULE_IDS
    from proof_coupled_v2 import DEFAULT_PROOF_TARGETS, evaluate_proof_corpus
    from store import FormalizationPromotionStore, ProposalRejected, StaleHead

CONTROLLER_PROTOCOL = {
    "format": "pcs-pgra-continual-self-repair-protocol-v1",
    "frozen": True,
    "gate": "accept_dual on fitting only",
    "repair_strategies": [
        "skip_failed_candidate",
        "combine_with_proof_expander",
        "combine_with_formalization_expander",
        "next_catalog_rule",
        "reject_rule_removal_forever",
    ],
    "max_repairs_per_proposal": 4,
    "holdout_role": "report_only_never_gates",
    "automatic_deployment": False,
    "pcs_scientific_authority": False,
}

# Rules known (from measured campaigns) to unlock kernel proofs on fitting.
PROOF_EXPANDING_RULES: tuple[str, ...] = (
    "rule_unique_exists",
    "rule_plus_times_words",
    "rule_zero_word",
    "rule_is_equal_to",
    "rule_surface_paraphrase",
    "rule_distinct_forall",  # holdout-heavy; may still help dual if fitting items appear
)


@dataclass(frozen=True)
class Diagnosis:
    reason: str
    failing_side: str  # "formalization" | "proof" | "both" | "monotonicity" | "other"
    lost_or_blocked: tuple[str, ...] = ()
    suggested_strategy: str = "next_catalog_rule"
    details: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Proposal:
    rules: frozenset[str]
    kind: str  # "catalog" | "repair" | "adversarial"
    parent_reason: str | None = None
    strategy: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "rules": sorted(self.rules),
            "kind": self.kind,
            "parent_reason": self.parent_reason,
            "strategy": self.strategy,
        }


def diagnose_reject(decision: Mapping[str, Any]) -> Diagnosis:
    """Map dual/formalization/proof reject reasons to a repair diagnosis."""
    reason = str(decision.get("reason") or "REJECT:unknown")
    form = decision.get("formalization") or {}
    proof = decision.get("proof") or {}

    if "rule_removal" in reason or "nonmonotonic" in reason:
        return Diagnosis(
            reason=reason,
            failing_side="monotonicity",
            suggested_strategy="reject_rule_removal_forever",
            details={"form": form.get("reason"), "proof": proof.get("reason")},
        )

    if reason.startswith("REJECT:formalization_gate") or (
        not form.get("accepted") and proof.get("accepted")
    ):
        return Diagnosis(
            reason=reason,
            failing_side="formalization",
            lost_or_blocked=tuple(form.get("gained") or ()),
            suggested_strategy="combine_with_formalization_expander"
            if "no_new" in str(form.get("reason", ""))
            else "next_catalog_rule",
            details={"form": form.get("reason"), "proof": proof.get("reason")},
        )

    if reason.startswith("REJECT:proof_gate") or (
        form.get("accepted") and not proof.get("accepted")
    ):
        # Classic partial success: formalization expanded, proofs did not.
        return Diagnosis(
            reason=reason,
            failing_side="proof",
            lost_or_blocked=tuple(proof.get("gained") or ()),
            suggested_strategy="combine_with_proof_expander",
            details={
                "form": form.get("reason"),
                "proof": proof.get("reason"),
                "form_gained": form.get("gained"),
            },
        )

    if reason.startswith("REJECT:dual_both_failed"):
        return Diagnosis(
            reason=reason,
            failing_side="both",
            suggested_strategy="next_catalog_rule",
            details={"form": form.get("reason"), "proof": proof.get("reason")},
        )

    return Diagnosis(
        reason=reason,
        failing_side="other",
        suggested_strategy="next_catalog_rule",
        details={"form": form.get("reason"), "proof": proof.get("reason")},
    )


def catalog_proposals(active: frozenset[str], tried: set[frozenset[str]]) -> list[Proposal]:
    """Propose enabling each unused catalog rule once."""
    out: list[Proposal] = []
    for rule in RULE_IDS:
        candidate = frozenset(active | {rule})
        if candidate == active or candidate in tried:
            continue
        out.append(Proposal(rules=candidate, kind="catalog", strategy="next_catalog_rule"))
    return out


def repair_proposal(
    active: frozenset[str],
    failed: Proposal,
    diagnosis: Diagnosis,
    tried: set[frozenset[str]],
) -> Proposal | None:
    """Propose a monotonic repair from a structured diagnosis."""
    if diagnosis.suggested_strategy == "reject_rule_removal_forever":
        # Convert illegal removals into a no-op skip (caller advances).
        return None

    if diagnosis.suggested_strategy == "combine_with_proof_expander":
        # Keep the failed candidate's new rules; add a proof-expanding rule.
        for rule in PROOF_EXPANDING_RULES:
            if rule in failed.rules:
                continue
            candidate = frozenset(failed.rules | {rule})
            if candidate in tried or not active <= candidate:
                continue
            return Proposal(
                rules=candidate,
                kind="repair",
                parent_reason=diagnosis.reason,
                strategy="combine_with_proof_expander",
            )

    if diagnosis.suggested_strategy == "combine_with_formalization_expander":
        for rule in RULE_IDS:
            if rule in failed.rules:
                continue
            candidate = frozenset(failed.rules | {rule})
            if candidate in tried or not active <= candidate:
                continue
            return Proposal(
                rules=candidate,
                kind="repair",
                parent_reason=diagnosis.reason,
                strategy="combine_with_formalization_expander",
            )

    # Default: try next unused catalog rule from active (skip failed delta).
    failed_delta = failed.rules - active
    for rule in RULE_IDS:
        if rule in active or rule in failed_delta:
            continue
        candidate = frozenset(active | {rule})
        if candidate in tried:
            continue
        return Proposal(
            rules=candidate,
            kind="repair",
            parent_reason=diagnosis.reason,
            strategy="skip_failed_candidate",
        )
    return None


def adversarial_removal_probe(active: frozenset[str]) -> Proposal | None:
    """Deliberately illegal proposal used to prove self-repair rejects removals."""
    if not active:
        return None
    victim = sorted(active)[0]
    return Proposal(
        rules=frozenset(active - {victim}),
        kind="adversarial",
        strategy="adversarial_rule_removal",
    )


def _snapshot_metrics(
    rules: frozenset[str],
    corpus: Sequence[Mapping[str, Any]],
    proof_ids: Sequence[str],
    *,
    budget: int,
    beam: int,
) -> dict[str, Any]:
    fit = fitting_corpus(corpus)
    hold = holdout_corpus(corpus)
    fit_proofs = fitting_proof_ids(corpus, proof_ids)
    hold_proofs = holdout_proof_ids(corpus, proof_ids)
    form = evaluate_corpus(rules, fit)
    proof = evaluate_proof_corpus(rules, fit, fit_proofs, budget=budget, beam=beam)
    hold_form = evaluate_corpus(rules, hold)
    hold_proof = evaluate_proof_corpus(rules, hold, hold_proofs, budget=budget, beam=beam)
    return {
        "rules": sorted(rules),
        "fitting_certified": len(form.certified),
        "fitting_form_loss": form.loss,
        "fitting_proved": proof["proved_count"],
        "fitting_proof_loss": proof["loss"],
        "holdout_certified": len(hold_form.certified),
        "holdout_proved": hold_proof["proved_count"],
        "holdout_role": "report_only",
    }


def continual_self_repair(
    *,
    output: Path,
    proof_ids: Sequence[str] | None = None,
    max_episodes: int = 24,
    max_repairs_per_proposal: int = 4,
    budget: int = 96,
    beam: int = 4,
    inject_adversarial_removal: bool = True,
    use_store: bool = True,
) -> dict[str, Any]:
    """Run the continual propose→gate→diagnose→repair→promote controller."""
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    wall_started = time.monotonic()
    corpus = build_frozen_corpus()
    targets = list(proof_ids or DEFAULT_PROOF_TARGETS)
    fit = fitting_corpus(corpus)

    store: FormalizationPromotionStore | None = None
    if use_store:
        store_root = output / "store"
        if store_root.exists():
            raise SystemExit(f"store path already exists: {store_root}")
        store = FormalizationPromotionStore.initialize(store_root, frozenset())

    active: frozenset[str] = frozenset()
    tried: set[frozenset[str]] = set()
    journal: list[dict[str, Any]] = []
    episodes: list[dict[str, Any]] = []
    repairs_succeeded = 0
    rejects_seen = 0
    accepts = 0
    adversarial_rejected = 0

    baseline = _snapshot_metrics(active, corpus, targets, budget=budget, beam=beam)
    episodes.append({"episode": 0, "event": "baseline", **baseline})

    if inject_adversarial_removal:
        # Seed one catalog accept first so removal probe is meaningful later.
        pass

    episode = 0
    pending_adversarial = inject_adversarial_removal
    while episode < max_episodes:
        episode += 1
        # After ≥1 successful accept, inject one adversarial removal to prove repair.
        if pending_adversarial and accepts >= 1 and active:
            probe = adversarial_removal_probe(active)
            pending_adversarial = False
            if probe is not None:
                decision = accept_dual(
                    active, probe.rules, corpus, targets, budget=budget, beam=beam
                )
                rejects_seen += 1
                diagnosis = diagnose_reject(decision)
                journal.append(
                    {
                        "episode": episode,
                        "phase": "adversarial_probe",
                        "proposal": probe.as_dict(),
                        "decision_accepted": decision["accepted"],
                        "decision_reason": decision["reason"],
                        "diagnosis": diagnosis.as_dict(),
                        "head_unchanged": True,
                        "automatic_deployment": False,
                        "pcs_scientific_authority": False,
                    }
                )
                if not decision["accepted"] and diagnosis.failing_side == "monotonicity":
                    adversarial_rejected += 1
                    episodes.append(
                        {
                            "episode": episode,
                            "event": "adversarial_rejected_and_ignored",
                            "diagnosis": diagnosis.as_dict(),
                            **_snapshot_metrics(
                                active, corpus, targets, budget=budget, beam=beam
                            ),
                        }
                    )
                    continue

        # Primary proposal stream: catalog then repairs.
        proposals = catalog_proposals(active, tried)
        if not proposals:
            break

        selected = proposals[0]
        tried.add(selected.rules)
        decision = accept_dual(
            active, selected.rules, corpus, targets, budget=budget, beam=beam
        )

        if decision["accepted"]:
            if store is not None:
                head, _ = store.read_active()
                try:
                    store.promote(selected.rules, head, fit)
                except (ProposalRejected, StaleHead) as ex:
                    raise RuntimeError(f"FAIL CLOSED: store rejected promotion: {ex}") from ex
            active = selected.rules
            accepts += 1
            metrics = _snapshot_metrics(active, corpus, targets, budget=budget, beam=beam)
            journal.append(
                {
                    "episode": episode,
                    "phase": "accept",
                    "proposal": selected.as_dict(),
                    "decision_reason": decision["reason"],
                    "metrics": metrics,
                    "automatic_deployment": False,
                    "pcs_scientific_authority": False,
                }
            )
            episodes.append({"episode": episode, "event": "accept", **metrics})
            (output / f"episode-{episode:02d}-accept.json").write_text(
                json.dumps(
                    {"proposal": selected.as_dict(), "decision": decision, "metrics": metrics},
                    indent=2,
                    sort_keys=True,
                )
                + "\n"
            )
            continue

        # REJECT → diagnose → repair loop (self-fix).
        rejects_seen += 1
        diagnosis = diagnose_reject(decision)
        repair_trace: list[dict[str, Any]] = []
        repaired = False
        current_failed = selected

        for repair_i in range(1, max_repairs_per_proposal + 1):
            repair = repair_proposal(active, current_failed, diagnosis, tried)
            if repair is None:
                repair_trace.append(
                    {
                        "repair_index": repair_i,
                        "status": "no_repair_available",
                        "diagnosis": diagnosis.as_dict(),
                    }
                )
                break
            tried.add(repair.rules)
            re_decision = accept_dual(
                active, repair.rules, corpus, targets, budget=budget, beam=beam
            )
            entry = {
                "repair_index": repair_i,
                "proposal": repair.as_dict(),
                "accepted": re_decision["accepted"],
                "reason": re_decision["reason"],
                "diagnosis_used": diagnosis.as_dict(),
            }
            repair_trace.append(entry)
            if re_decision["accepted"]:
                if store is not None:
                    head, _ = store.read_active()
                    try:
                        store.promote(repair.rules, head, fit)
                    except (ProposalRejected, StaleHead) as ex:
                        raise RuntimeError(
                            f"FAIL CLOSED: store rejected repair promotion: {ex}"
                        ) from ex
                active = repair.rules
                accepts += 1
                repairs_succeeded += 1
                repaired = True
                metrics = _snapshot_metrics(
                    active, corpus, targets, budget=budget, beam=beam
                )
                journal.append(
                    {
                        "episode": episode,
                        "phase": "repair_accept",
                        "original_proposal": selected.as_dict(),
                        "original_reject": decision["reason"],
                        "repair_trace": repair_trace,
                        "metrics": metrics,
                        "automatic_deployment": False,
                        "pcs_scientific_authority": False,
                    }
                )
                episodes.append(
                    {
                        "episode": episode,
                        "event": "repair_accept",
                        "repairs_used": repair_i,
                        "strategy": repair.strategy,
                        **metrics,
                    }
                )
                (output / f"episode-{episode:02d}-repair-accept.json").write_text(
                    json.dumps(
                        {
                            "original": selected.as_dict(),
                            "original_decision": decision,
                            "repair_trace": repair_trace,
                            "metrics": metrics,
                        },
                        indent=2,
                        sort_keys=True,
                    )
                    + "\n"
                )
                break

            # Repair also rejected → re-diagnose and continue.
            rejects_seen += 1
            diagnosis = diagnose_reject(re_decision)
            current_failed = repair

        if not repaired:
            journal.append(
                {
                    "episode": episode,
                    "phase": "reject_exhausted",
                    "original_proposal": selected.as_dict(),
                    "original_reject": decision["reason"],
                    "repair_trace": repair_trace,
                    "head_unchanged": True,
                    "automatic_deployment": False,
                    "pcs_scientific_authority": False,
                }
            )
            episodes.append(
                {
                    "episode": episode,
                    "event": "reject_exhausted",
                    "original_reason": decision["reason"],
                    **_snapshot_metrics(active, corpus, targets, budget=budget, beam=beam),
                }
            )

    final = _snapshot_metrics(active, corpus, targets, budget=budget, beam=beam)
    proved_series = [e.get("fitting_proved", 0) for e in episodes if "fitting_proved" in e]
    certified_series = [
        e.get("fitting_certified", 0) for e in episodes if "fitting_certified" in e
    ]
    accept_events = [e for e in episodes if e.get("event") in {"accept", "repair_accept"}]
    rising_proved = all(
        accept_events[i]["fitting_proved"] < accept_events[i + 1]["fitting_proved"]
        for i in range(len(accept_events) - 1)
    ) if len(accept_events) > 1 else False

    summary = {
        "format": "pcs-pgra-continual-self-repair-summary-v1",
        "protocol": CONTROLLER_PROTOCOL,
        "policy_hash": POLICY_HASH,
        "corpus_sha256": corpus_sha256(list(corpus)),
        "proof_ids": targets,
        "episodes": episodes,
        "journal_len": len(journal),
        "accepts": accepts,
        "rejects_seen": rejects_seen,
        "repairs_succeeded": repairs_succeeded,
        "adversarial_rejected": adversarial_rejected,
        "self_repair_rate": (
            repairs_succeeded / rejects_seen if rejects_seen else None
        ),
        "fitting_proved_series": proved_series,
        "fitting_certified_series": certified_series,
        "rising_fitting_proved_on_accepts": rising_proved,
        "final": final,
        "final_rules": sorted(active),
        "store_root": str(output / "store") if use_store else None,
        "automatic_deployment": False,
        "pcs_scientific_authority": False,
        "self_improvement_scope": (
            "Finite continual dual-gated rulebook search with REJECT→diagnose→repair→"
            "re-gate and CAS promotion only on ACCEPT. Demonstrates self-repair under "
            "frozen protocols. Not general AI self-modification or automatic deployment."
        ),
        "wall_seconds": round(time.monotonic() - wall_started, 3),
    }

    (output / "journal.json").write_text(
        json.dumps(
            {
                "format": "pcs-pgra-continual-journal-v1",
                "entries": journal,
                "automatic_deployment": False,
                "pcs_scientific_authority": False,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )
    (output / "continual_self_repair_summary.json").write_text(
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
    parser.add_argument("--max-episodes", type=int, default=24)
    parser.add_argument("--max-repairs", type=int, default=4)
    parser.add_argument("--budget", type=int, default=96)
    parser.add_argument("--no-adversarial", action="store_true")
    parser.add_argument("--no-store", action="store_true")
    args = parser.parse_args(argv)
    summary = continual_self_repair(
        output=args.output,
        max_episodes=args.max_episodes,
        max_repairs_per_proposal=args.max_repairs,
        budget=args.budget,
        inject_adversarial_removal=not args.no_adversarial,
        use_store=not args.no_store,
    )
    print(
        json.dumps(
            {
                "accepts": summary["accepts"],
                "rejects_seen": summary["rejects_seen"],
                "repairs_succeeded": summary["repairs_succeeded"],
                "adversarial_rejected": summary["adversarial_rejected"],
                "self_repair_rate": summary["self_repair_rate"],
                "rising_fitting_proved_on_accepts": summary[
                    "rising_fitting_proved_on_accepts"
                ],
                "final_rules": summary["final_rules"],
                "fitting_proved_series": summary["fitting_proved_series"],
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
