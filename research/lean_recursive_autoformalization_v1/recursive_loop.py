"""Automatic search over formalization rule proposers (PGRA v1).

Starts from empty (or base-only) rules. Each generation tries enabling one
unused catalog rule, evaluates the PGSI-style gate on the generation slice
(with full-corpus preserve semantics via the gate's full evaluate), and on
accept CAS-promotes in the content-addressed store.

This never deploys rulebooks. ``automatic_deployment`` is always false.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Callable, Sequence

try:
    from .capability import evaluate_corpus
except ImportError:  # flat sys.path research execution
    from capability import evaluate_corpus
try:
    from .corpus import (
    build_frozen_corpus,
    corpus_sha256,
    slice_for_generation,
    write_protocol,
)
except ImportError:  # flat sys.path research execution
    from corpus import (
    build_frozen_corpus,
    corpus_sha256,
    slice_for_generation,
    write_protocol,
)
try:
    from .gate import POLICY_HASH, accept, digest
except ImportError:  # flat sys.path research execution
    from gate import POLICY_HASH, accept, digest
try:
    from .grammar_extensions import RULE_IDS
except ImportError:  # flat sys.path research execution
    from grammar_extensions import RULE_IDS
try:
    from .store import FormalizationPromotionStore, ProposalRejected, StaleHead
except ImportError:  # flat sys.path research execution
    from store import FormalizationPromotionStore, ProposalRejected, StaleHead

Proposer = Callable[[frozenset[str]], Sequence[frozenset[str]]]


def catalog_single_rule_proposer(active: frozenset[str]) -> list[frozenset[str]]:
    """Try enabling each unused catalog rule, one at a time, in catalog order."""
    proposals: list[frozenset[str]] = []
    for rule_id in RULE_IDS:
        if rule_id not in active:
            proposals.append(active | {rule_id})
    return proposals


def adversarial_drop_proposer(active: frozenset[str]) -> list[frozenset[str]]:
    """Adversarial: propose removing one enabled rule (must be rejected)."""
    return [active - {rule_id} for rule_id in sorted(active)]


def adversarial_noop_proposer(active: frozenset[str]) -> list[frozenset[str]]:
    """Adversarial: propose the same rule set (no expansion)."""
    return [frozenset(active)]


def gate_corpus_for_generation(
    corpus: list[dict[str, Any]], generation: int
) -> list[dict[str, Any]]:
    """Generation slice unioned with the full corpus for preserve coverage.

    Expand/loss are dominated by newly unlocked extension items in the slice;
    preserve is checked on every previously certified id because the gate
    evaluates the full passed corpus. We therefore pass the full corpus always,
    while recording which slice was "generation-appropriate".
    """
    _ = slice_for_generation(corpus, generation)  # documented slice
    return list(corpus)


def automatic_search(
    *,
    corpus: list[dict[str, Any]] | None = None,
    start_rules: frozenset[str] | None = None,
    store_root: Path | None = None,
    max_generations: int = 8,
    proposer: Proposer | None = None,
) -> dict[str, Any]:
    """Run the recursive formalization rule search.

    Returns a summary with per-generation certified counts. Demonstrates ≥2
    accepted generations when the frozen corpus is well-designed.
    """
    items = corpus if corpus is not None else build_frozen_corpus()
    active = frozenset(start_rules or ())
    propose = proposer or catalog_single_rule_proposer

    store: FormalizationPromotionStore | None = None
    if store_root is not None:
        store = FormalizationPromotionStore.initialize(Path(store_root), active)

    baseline = evaluate_corpus(active, items)
    trace: list[dict[str, Any]] = []
    generations: list[dict[str, Any]] = [
        {
            "generation": 0,
            "rules": sorted(active),
            "certified_count": len(baseline.certified),
            "certified_supported": len(baseline.certified_supported),
            "certified_abstain": len(baseline.certified_abstain),
            "loss": baseline.loss,
            "accepted": None,
        }
    ]

    for gen in range(1, max_generations + 1):
        gate_corpus = gate_corpus_for_generation(items, gen)
        selected = None
        attempts: list[dict[str, Any]] = []
        for candidate in propose(active):
            decision = accept(active, frozenset(candidate), gate_corpus)
            attempts.append(
                {
                    "candidate_rules": sorted(candidate),
                    "accepted": decision.accepted,
                    "reason": decision.reason,
                    "old_loss": decision.old_loss,
                    "new_loss": decision.new_loss,
                    "gained": list(decision.gained),
                }
            )
            if decision.accepted:
                selected = (frozenset(candidate), decision)
                break
        if selected is None:
            break
        candidate_rules, decision = selected
        if store is not None:
            head, _ = store.read_active()
            try:
                store.promote(candidate_rules, head, gate_corpus)
            except (ProposalRejected, StaleHead) as ex:
                raise RuntimeError(f"FAIL CLOSED: store rejected promotion: {ex}") from ex

        active = candidate_rules
        report = evaluate_corpus(active, items)
        event = {
            "generation": gen,
            "rules": sorted(active),
            "certified_count": len(report.certified),
            "certified_supported": len(report.certified_supported),
            "certified_abstain": len(report.certified_abstain),
            "loss": report.loss,
            "accepted": True,
            "reason": decision.reason,
            "gained": list(decision.gained),
            "attempts": attempts,
            "automatic_deployment": False,
            "pcs_scientific_authority": False,
        }
        trace.append(event)
        generations.append(
            {
                "generation": gen,
                "rules": sorted(active),
                "certified_count": len(report.certified),
                "certified_supported": len(report.certified_supported),
                "certified_abstain": len(report.certified_abstain),
                "loss": report.loss,
                "accepted": True,
            }
        )

    final = evaluate_corpus(active, items)
    summary = {
        "format": "pcs-pgra-recursive-summary-v1",
        "policy_hash": POLICY_HASH,
        "corpus_sha256": corpus_sha256(items),
        "start_rules": sorted(start_rules or ()),
        "final_rules": sorted(active),
        "accepted_generations": len(trace),
        "generations": generations,
        "trace": trace,
        "final_certified_count": len(final.certified),
        "final_loss": final.loss,
        "certified_counts": [g["certified_count"] for g in generations],
        "rising_certified": all(
            generations[i]["certified_count"] < generations[i + 1]["certified_count"]
            for i in range(len(generations) - 1)
            if generations[i + 1].get("accepted")
        )
        if len(trace) >= 1
        else False,
        "automatic_deployment": False,
        "pcs_scientific_authority": False,
        "pcs_authority": False,
        "reference_only": True,
        "store_root": str(store_root) if store_root else None,
    }
    return summary


def write_results(output_dir: Path, summary: dict[str, Any], corpus: list[dict[str, Any]]) -> dict[str, str]:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    protocol = write_protocol(output_dir, corpus)
    (output_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n"
    )
    (output_dir / "generations.json").write_text(
        json.dumps(
            {
                "format": "pcs-pgra-generations-v1",
                "generations": summary["generations"],
                "certified_counts": summary["certified_counts"],
                "automatic_deployment": False,
                "pcs_scientific_authority": False,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )
    sha_map = {}
    for name in ("tasks.json", "protocol.json", "summary.json", "generations.json"):
        path = output_dir / name
        if path.exists():
            sha_map[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    sha_map["corpus_sha256"] = corpus_sha256(corpus)
    sha_map["policy_hash"] = POLICY_HASH
    sha_map["automatic_deployment"] = False
    sha_map["pcs_scientific_authority"] = False
    # digest helper for nested binding
    sha_payload = {
        k: v for k, v in sha_map.items() if isinstance(v, str)
    }
    sha_map["artifact_digest"] = digest(sha_payload)
    (output_dir / "SHA256.json").write_text(
        json.dumps(sha_map, indent=2, sort_keys=True) + "\n"
    )
    return {k: str(v) for k, v in sha_map.items()}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        required=True,
        help="Directory for tasks/protocol/summary/generations/SHA256 artifacts",
    )
    parser.add_argument("--max-generations", type=int, default=8)
    parser.add_argument(
        "--store",
        default=None,
        help="Optional path for content-addressed promotion store",
    )
    args = parser.parse_args(argv)
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    corpus = build_frozen_corpus()
    store_root = Path(args.store) if args.store else (output / "store")
    if store_root.exists():
        # Fail closed: do not reuse a prior store silently.
        raise SystemExit(f"store path already exists: {store_root}")
    summary = automatic_search(
        corpus=corpus,
        store_root=store_root,
        max_generations=args.max_generations,
    )
    write_results(output, summary, corpus)
    print(json.dumps({
        "accepted_generations": summary["accepted_generations"],
        "certified_counts": summary["certified_counts"],
        "final_rules": summary["final_rules"],
        "output": str(output),
        "automatic_deployment": False,
        "pcs_scientific_authority": False,
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
