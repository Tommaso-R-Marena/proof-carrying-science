"""End-to-end PGRA demo: recursive rulebook improvement + formalize + optional search.

Steps:
  1. Run recursive rulebook improvement (≥2 accepted generations)
  2. Formalize a newly unlocked English statement under the final rulebook
  3. Optionally run ``pcs.experimental.prover.environment.search`` with the
     symbolic policy if a Lean 4.28 worker is available; else record skip
  4. Write results JSON with ``pcs_authority`` / ``pcs_scientific_authority`` false

Does not modify the SVB repository. Does not auto-deploy. Research only.

Sibling note: capability/gate/store/corpus/recursive_loop may use either
package-relative imports (``.capability``) or flat imports (``capability``)
while other agents edit them. This demo bootstraps both and falls back to
self-contained helpers if imports fail.
"""
from __future__ import annotations

import argparse
import json
import os
import secrets
import shutil
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

_PKG = Path(__file__).resolve().parent
_REPO = _PKG.parents[1]
# Allow sibling modules that temporarily use flat imports (``from capability``).
if str(_PKG) not in sys.path:
    sys.path.insert(0, str(_PKG))
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from pcs.experimental.prover.ir import digest as ir_digest
from pcs.experimental.prover.language import formalize as base_formalize

# ---------------------------------------------------------------------------
# Import sibling PGRA APIs with fallbacks
# ---------------------------------------------------------------------------

_IMPORT_NOTES: list[str] = []


def _try_import(name: str):
    try:
        return __import__(
            f"research.lean_recursive_autoformalization_v1.{name}",
            fromlist=["*"],
        )
    except Exception as ex:  # pragma: no cover
        _IMPORT_NOTES.append(f"package import {name}: {type(ex).__name__}: {ex}")
    try:
        return __import__(name, fromlist=["*"])
    except Exception as ex:  # pragma: no cover
        _IMPORT_NOTES.append(f"flat import {name}: {type(ex).__name__}: {ex}")
        return None


_grammar = _try_import("grammar_extensions")
_capability = _try_import("capability")
_gate = _try_import("gate")
_corpus = _try_import("corpus")
_loop = _try_import("recursive_loop")
_svb = _try_import("svb_bridge")

RULE_IDS: tuple[str, ...] = tuple(getattr(_grammar, "RULE_IDS", ()) or ())
if not RULE_IDS and _grammar is not None and hasattr(_grammar, "RULE_CATALOG"):
    catalog = _grammar.RULE_CATALOG
    if isinstance(catalog, dict):
        RULE_IDS = tuple(catalog.keys())
    else:
        RULE_IDS = tuple(r for r, *_ in catalog)


def _formalize_with_rules(source: str, rules: frozenset[str]) -> dict[str, Any]:
    if _capability is not None and hasattr(_capability, "formalize_with_rules"):
        return _capability.formalize_with_rules(source, rules)
    apply_extensions = getattr(_grammar, "apply_extensions", None)
    if apply_extensions is not None and rules:
        extended = apply_extensions(source, frozenset(rules))
        if extended is not None:
            return extended
    formalize_with_rules = getattr(_grammar, "formalize_with_rules", None)
    if formalize_with_rules is not None:
        return formalize_with_rules(source, frozenset(rules))
    return base_formalize(source)


def _evaluate_corpus(rules: frozenset[str], corpus: Sequence[Mapping[str, Any]]) -> Any:
    if _capability is not None and hasattr(_capability, "evaluate_corpus"):
        return _capability.evaluate_corpus(frozenset(rules), corpus)
    outcomes: dict[str, str] = {}
    for item in corpus:
        item_id = str(item["id"])
        target = item["target"]
        required = frozenset(item.get("required_rules") or ())
        result = _formalize_with_rules(str(item["english"]), frozenset(rules))
        status = result.get("status")
        if target == "abstain":
            outcomes[item_id] = (
                "certified_abstain"
                if status == "unsupported" and not result.get("candidates")
                else "wrong_ir"
            )
        elif required and not required <= frozenset(rules):
            outcomes[item_id] = "unsupported_fail"
        elif status in {"supported", "ambiguous"} and result.get("candidates"):
            outcomes[item_id] = "certified_supported"
        else:
            outcomes[item_id] = "unsupported_fail"
    certified_supported = frozenset(
        i for i, o in outcomes.items() if o == "certified_supported"
    )
    certified_abstain = frozenset(
        i for i, o in outcomes.items() if o == "certified_abstain"
    )
    failed_supported = frozenset(
        str(it["id"])
        for it in corpus
        if it["target"] == "supported"
        and outcomes[str(it["id"])] != "certified_supported"
    )
    failed_abstain = frozenset(
        str(it["id"])
        for it in corpus
        if it["target"] == "abstain" and outcomes[str(it["id"])] != "certified_abstain"
    )
    wrong = frozenset(i for i, o in outcomes.items() if o in {"wrong_ir", "roundtrip_fail"})

    @dataclass(frozen=True)
    class Report:
        outcomes: dict
        certified_supported: frozenset
        certified_abstain: frozenset
        certified: frozenset
        loss: int
        rules: frozenset

    return Report(
        outcomes=outcomes,
        certified_supported=certified_supported,
        certified_abstain=certified_abstain,
        certified=certified_supported | certified_abstain,
        loss=len(failed_supported) + len(failed_abstain) + len(wrong),
        rules=frozenset(rules),
    )


def _local_corpus() -> list[dict[str, Any]]:
    """Tiny authored corpus used only when sibling corpus.py cannot import."""
    items = [
        {
            "id": "demo_base_eq",
            "english": "For all natural numbers n, n equals n.",
            "target": "supported",
            "required_rules": [],
        },
        {
            "id": "demo_base_add",
            "english": "For all natural numbers n, n + 0 equals n.",
            "target": "supported",
            "required_rules": [],
        },
        {
            "id": "demo_abstain",
            "english": "Prove everything.",
            "target": "abstain",
            "required_rules": [],
        },
        {
            "id": "demo_exactly_when",
            "english": "For all propositions A and B, A exactly when B.",
            "target": "supported",
            "required_rules": ["rule_exactly_when"],
        },
        {
            "id": "demo_whenever",
            "english": "For all propositions A and B, whenever A, B.",
            "target": "supported",
            "required_rules": ["rule_whenever"],
        },
        {
            "id": "demo_neither",
            "english": "For all propositions A and B, neither A nor B.",
            "target": "supported",
            "required_rules": ["rule_neither_nor"],
        },
        {
            "id": "demo_plus",
            "english": "For all natural numbers n, n plus 0 equals n.",
            "target": "supported",
            "required_rules": ["rule_plus_times_words"],
        },
        {
            "id": "demo_unique",
            "english": "There exists a unique natural number n such that n equals n.",
            "target": "supported",
            "required_rules": ["rule_unique_exists"],
        },
    ]
    return items


def _gate_accept(
    old_rules: frozenset[str], new_rules: frozenset[str], corpus: Sequence[Mapping[str, Any]]
) -> Any:
    if _gate is not None and hasattr(_gate, "accept"):
        return _gate.accept(old_rules, new_rules, corpus)
    old_report = _evaluate_corpus(old_rules, corpus)
    new_report = _evaluate_corpus(new_rules, corpus)
    old_cert = {
        i: o
        for i, o in old_report.outcomes.items()
        if o in {"certified_supported", "certified_abstain"}
    }
    new_cert = {
        i: o
        for i, o in new_report.outcomes.items()
        if o in {"certified_supported", "certified_abstain"}
    }
    if not old_rules <= new_rules:
        reason = "REJECT:rule_removal_forbidden"
    elif any(new_cert.get(i) != outcome for i, outcome in old_cert.items()):
        reason = "REJECT:certified_capability_regression"
    elif not (set(new_cert) - set(old_cert)):
        reason = "REJECT:no_new_certified_capability"
    elif not new_report.loss < old_report.loss:
        reason = "REJECT:loss_not_strictly_lower"
    else:
        reason = "ACCEPT:reference_only"

    @dataclass(frozen=True)
    class Decision:
        accepted: bool
        reason: str
        old_loss: int
        new_loss: int
        gained: tuple
        old_rules: tuple
        new_rules: tuple
        pcs_scientific_authority: bool = False
        automatic_deployment: bool = False

    return Decision(
        accepted=reason.startswith("ACCEPT"),
        reason=reason,
        old_loss=old_report.loss,
        new_loss=new_report.loss,
        gained=tuple(sorted(set(new_cert) - set(old_cert))),
        old_rules=tuple(sorted(old_rules)),
        new_rules=tuple(sorted(new_rules)),
    )


def _recursive_improvement(max_generations: int = 4) -> dict[str, Any]:
    """Prefer sibling ``automatic_search``; else a local ≥2-generation loop."""
    if _loop is not None and hasattr(_loop, "automatic_search"):
        corpus = None
        if _corpus is not None and hasattr(_corpus, "build_frozen_corpus"):
            corpus = _corpus.build_frozen_corpus()
        # Store initialize() requires a non-existent path (it mkdir's itself).
        store_root = Path(tempfile.gettempdir()) / f"pgra-e2e-store-{tempfile.gettempprefix()}-{os.getpid()}-{secrets.token_hex(4)}"
        summary = _loop.automatic_search(
            corpus=corpus,
            store_root=store_root,
            max_generations=max_generations,
        )
        summary = dict(summary)
        summary["engine"] = "sibling_recursive_loop.automatic_search"
        summary["store_root"] = str(store_root)
        return summary

    corpus = _local_corpus()
    active: frozenset[str] = frozenset()
    baseline = _evaluate_corpus(active, corpus)
    generations = [
        {
            "generation": 0,
            "rules": [],
            "certified_count": len(baseline.certified),
            "loss": baseline.loss,
            "accepted": None,
        }
    ]
    trace: list[dict[str, Any]] = []
    order = list(RULE_IDS) or [
        "rule_unique_exists",
        "rule_neither_nor",
        "rule_exactly_when",
        "rule_whenever",
        "rule_plus_times_words",
        "rule_distinct_forall",
    ]
    for gen in range(1, max_generations + 1):
        selected = None
        attempts = []
        for rule_id in order:
            if rule_id in active:
                continue
            candidate = active | {rule_id}
            decision = _gate_accept(active, candidate, corpus)
            attempts.append(
                {
                    "candidate_rules": sorted(candidate),
                    "accepted": decision.accepted,
                    "reason": decision.reason,
                    "gained": list(decision.gained),
                }
            )
            if decision.accepted:
                selected = (candidate, decision)
                break
        if selected is None:
            break
        active, decision = selected
        report = _evaluate_corpus(active, corpus)
        event = {
            "generation": gen,
            "rules": sorted(active),
            "certified_count": len(report.certified),
            "loss": report.loss,
            "accepted": True,
            "reason": decision.reason,
            "gained": list(decision.gained),
            "attempts": attempts,
        }
        trace.append(event)
        generations.append(
            {
                "generation": gen,
                "rules": sorted(active),
                "certified_count": len(report.certified),
                "loss": report.loss,
                "accepted": True,
            }
        )
    final = _evaluate_corpus(active, corpus)
    return {
        "format": "pcs-pgra-recursive-summary-v1",
        "engine": "end_to_end_demo.local_recursive_improvement",
        "accepted_generations": len(trace),
        "generations": generations,
        "trace": trace,
        "final_rules": sorted(active),
        "final_certified_count": len(final.certified),
        "final_loss": final.loss,
        "certified_counts": [g["certified_count"] for g in generations],
        "automatic_deployment": False,
        "pcs_scientific_authority": False,
        "pcs_authority": False,
        "import_notes": list(_IMPORT_NOTES),
    }


def _newly_unlocked_statement(summary: dict[str, Any]) -> dict[str, Any]:
    """Pick an English statement unlocked by an accepted generation."""
    candidates = [
        ("rule_exactly_when", "For all propositions A and B, A exactly when B."),
        ("rule_whenever", "For all propositions A and B, whenever A, B."),
        ("rule_neither_nor", "For all propositions A and B, neither A nor B."),
        ("rule_plus_times_words", "For all natural numbers n, n plus 0 equals n."),
        ("rule_unique_exists", "There exists a unique natural number n such that n equals n."),
        ("rule_distinct_forall", "For all distinct natural numbers a and b, a equals a."),
    ]
    final_rules = set(summary.get("final_rules") or [])
    start = set(summary.get("start_rules") or [])
    unlocked = final_rules - start
    for rule_id, english in candidates:
        if rule_id in unlocked or (not unlocked and rule_id in final_rules):
            formal = _formalize_with_rules(english, frozenset(final_rules))
            return {
                "rule_id": rule_id,
                "english": english,
                "formalization": formal,
                "status": formal.get("status"),
                "lean": (formal.get("candidates") or [{}])[0].get("lean"),
                "ir_digest": ir_digest((formal.get("candidates") or [{}])[0]["ir"])
                if formal.get("candidates")
                else None,
            }
    # Fallback: base statement always available.
    english = "For all natural numbers n, n equals n."
    formal = _formalize_with_rules(english, frozenset(final_rules))
    return {
        "rule_id": None,
        "english": english,
        "formalization": formal,
        "status": formal.get("status"),
        "lean": (formal.get("candidates") or [{}])[0].get("lean"),
        "note": "no extension unlock detected; used base identity",
    }


def _lean_available() -> tuple[bool, str]:
    lean = shutil.which("lean")
    if not lean:
        return False, "lean binary not found on PATH"
    try:
        import subprocess

        version = subprocess.check_output([lean, "--version"], text=True, timeout=10).strip()
    except Exception as ex:  # pragma: no cover
        return False, f"lean --version failed: {ex}"
    if "version 4.28.0," not in version:
        return False, f"exact Lean 4.28.0 required; found: {version}"
    worker = _REPO / "formal" / "PCSProofWorker.lean"
    if not worker.exists():
        return False, f"missing worker source: {worker}"
    return True, version


def _optional_symbolic_search(formalization: dict[str, Any]) -> dict[str, Any]:
    ok, reason = _lean_available()
    if not ok:
        return {
            "status": "skipped",
            "reason": reason,
            "policy": "symbolic",
            "pcs_authority": False,
        }
    if formalization.get("status") not in {"supported", "ambiguous"} or not formalization.get(
        "candidates"
    ):
        return {
            "status": "skipped",
            "reason": "formalization not supported; nothing to search",
            "policy": "symbolic",
            "pcs_authority": False,
        }
    try:
        from pcs.experimental.prover.environment import LeanEnvironment, search
    except Exception as ex:  # pragma: no cover
        return {
            "status": "skipped",
            "reason": f"could not import prover.environment: {ex}",
            "policy": "symbolic",
            "pcs_authority": False,
        }
    goal = formalization["candidates"][0]["ir"]
    env = None
    try:
        env = LeanEnvironment(cache=tempfile.mkdtemp(prefix="pgra-lean-cache-"), timeout=20)
        # Symbolic policy: default_rank / _symbolic_priority inside search(rank=None).
        result = search(env, goal, rank=None, budget=32, depth=12, beam=4)
        return {
            "status": result.get("status"),
            "policy": "symbolic",
            "expansions": result.get("expansions"),
            "lean_invocations": result.get("lean_invocations"),
            "wall_seconds": result.get("wall_seconds"),
            "receipt_present": result.get("receipt") is not None,
            "pcs_authority": False,
            "lean_version": reason,
        }
    except Exception as ex:
        return {
            "status": "skipped",
            "reason": f"Lean worker/search failed: {type(ex).__name__}: {ex}",
            "policy": "symbolic",
            "pcs_authority": False,
        }
    finally:
        if env is not None:
            try:
                env.close()
            except Exception:
                pass


def run_demo(*, output: Path, max_generations: int = 4) -> dict[str, Any]:
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)

    recursive = _recursive_improvement(max_generations=max_generations)
    unlocked = _newly_unlocked_statement(recursive)
    search_result = _optional_symbolic_search(unlocked.get("formalization") or {})

    svb_score = None
    if _svb is not None and hasattr(_svb, "score_fixture"):
        try:
            svb_score = _svb.score_fixture(rules=frozenset(recursive.get("final_rules") or ()))
        except Exception as ex:  # pragma: no cover
            svb_score = {"status": "error", "reason": str(ex), "pcs_authority": False}

    payload = {
        "format": "pcs-pgra-end-to-end-demo-v1",
        "pcs_authority": False,
        "pcs_scientific_authority": False,
        "automatic_deployment": False,
        "svb_superiority_claim": False,
        "steps": {
            "1_recursive_rulebook_improvement": {
                "accepted_generations": recursive.get("accepted_generations"),
                "certified_counts": recursive.get("certified_counts"),
                "final_rules": recursive.get("final_rules"),
                "final_loss": recursive.get("final_loss"),
                "engine": recursive.get("engine"),
                "meets_min_two_generations": int(recursive.get("accepted_generations") or 0) >= 2,
            },
            "2_formalize_newly_unlocked": unlocked,
            "3_optional_symbolic_search": search_result,
            "4_svb_like_bridge_score": svb_score,
        },
        "import_notes": list(_IMPORT_NOTES),
        "scope": (
            "Research demonstration of proof-gated recursive autoformalization plus an "
            "optional SVB-like claim→obligation bridge. Not production PCS authority, "
            "not an SVB leaderboard, not unrestricted English equivalence."
        ),
    }
    # Keep a compact recursive summary alongside the full demo payload.
    (output / "recursive_summary.json").write_text(
        json.dumps(recursive, indent=2, sort_keys=True, default=str) + "\n"
    )
    (output / "end_to_end_demo.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n"
    )
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=_PKG / "results" / "end_to_end_demo",
    )
    parser.add_argument("--max-generations", type=int, default=4)
    args = parser.parse_args(argv)
    # Fail closed on non-empty prior demo dir to avoid silent reuse.
    if args.output.exists() and any(args.output.iterdir()):
        raise SystemExit(f"output directory must be empty: {args.output}")
    payload = run_demo(output=args.output, max_generations=args.max_generations)
    print(
        json.dumps(
            {
                "output": str(args.output),
                "accepted_generations": payload["steps"]["1_recursive_rulebook_improvement"][
                    "accepted_generations"
                ],
                "meets_min_two_generations": payload["steps"]["1_recursive_rulebook_improvement"][
                    "meets_min_two_generations"
                ],
                "formalization_status": payload["steps"]["2_formalize_newly_unlocked"].get(
                    "status"
                ),
                "search_status": payload["steps"]["3_optional_symbolic_search"].get("status"),
                "pcs_authority": False,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
