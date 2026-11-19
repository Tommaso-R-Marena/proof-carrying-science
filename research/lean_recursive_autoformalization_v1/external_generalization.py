"""External generalization harness for PGRA — research only.

Axes (none confer PCS authority):
  1. Sealed lean-learning-v2 formalization-evaluation (English→IR exact)
  2. OOD surface paraphrases (must formalize under full rulebook)
  3. OOD abstention (must remain unsupported)
  4. Real SVB evaluation claims (must fail-closed abstain; false-accept=0)
  5. Sealed lean-learning-v2 final IR kernel prove rate

This is the strongest offline multi-axis suite available in-workspace without
vendoring miniF2F/FormL4. Mathlib-v4 is optional if Mathlib is installed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from pcs.experimental.prover.ir import digest

try:
    from .capability import formalize_with_rules
    from .grammar_extensions import RULE_IDS
except ImportError:
    from capability import formalize_with_rules
    from grammar_extensions import RULE_IDS

REPO = Path(__file__).resolve().parents[2]
LEAN_LEARNING_V2 = REPO / "research" / "lean-learning-v2"
SVB_ROOT = REPO.parent / "scientific-verification-benchmark-svb-"

OOD_SUPPORTED: tuple[tuple[str, str], ...] = (
    ("ood_every_eq", "For every natural number n, n equals n."),
    ("ood_any_eq", "For any natural number k, k equals k."),
    ("ood_itself", "Every natural number equals itself."),
    ("ood_zero_eq_zero", "Zero is equal to zero."),
    ("ood_plus_trailing", "n plus zero equals n for every natural number n."),
    ("ood_sum_of", "The sum of n and 0 equals n for all natural numbers n."),
    ("ood_unique_paraphrase", "There is a unique natural number equal to zero."),
    ("ood_distinct_paraphrase", "Any two distinct naturals a and b satisfy a equals a."),
    ("ood_whenever_trailing", "Whenever A holds, B holds, for all propositions A and B."),
    ("ood_exactly_trailing", "A is true exactly when B is true for propositions A and B."),
    ("ood_neither_trailing", "Neither P nor Q holds for all propositions P and Q."),
    ("ood_zero_word", "For all natural numbers n, zero + n equals n."),
    ("ood_is_equal", "For all natural numbers n, n is equal to n."),
    ("ood_plus_words", "For all natural numbers n, n plus 0 equals n."),
    ("ood_zero_plus_words", "For all natural numbers n, zero plus n equals n."),
)

OOD_ABSTAIN: tuple[tuple[str, str], ...] = (
    ("ood_reals", "For all real numbers x, x equals x."),
    ("ood_graph", "Every connected graph has a spanning tree."),
    ("ood_poetry", "Beauty is truth, truth beauty."),
    ("ood_physics", "Energy is always conserved somehow."),
    ("ood_prove_all", "Prove everything."),
    ("ood_clinical", "Mean clinical assay response was nanomolar."),
)


def _score_lean_learning_formalization(rules: frozenset[str]) -> dict[str, Any]:
    data = json.loads((LEAN_LEARNING_V2 / "formalization-evaluation.json").read_text())
    supported_hits = 0
    supported_rows = []
    for i, item in enumerate(data["supported"]):
        result = formalize_with_rules(item["text"], rules)
        ok = False
        if result.get("status") in {"supported", "ambiguous"} and result.get("candidates"):
            ok = digest(result["candidates"][0]["ir"]) == digest(item["expected_ir"])
        supported_hits += int(ok)
        supported_rows.append(
            {"i": i, "text": item["text"], "status": result.get("status"), "ir_match": ok}
        )
    neg_hits = 0
    neg_rows = []
    for i, item in enumerate(data["negative_controls"]):
        result = formalize_with_rules(item["text"], rules)
        expected = item.get("expected")
        ok = result.get("status") == expected
        neg_hits += int(ok)
        neg_rows.append(
            {
                "i": i,
                "text": item["text"],
                "expected": expected,
                "status": result.get("status"),
                "match": ok,
            }
        )
    return {
        "format": "pcs-pgra-ext-lean-learning-v2-formalization",
        "supported_exact_ir": supported_hits,
        "supported_total": len(data["supported"]),
        "supported_rate": supported_hits / max(1, len(data["supported"])),
        "negative_status_match": neg_hits,
        "negative_total": len(data["negative_controls"]),
        "negative_rate": neg_hits / max(1, len(data["negative_controls"])),
        "rows_supported": supported_rows,
        "rows_negative": neg_rows,
        "source": str(LEAN_LEARNING_V2 / "formalization-evaluation.json"),
        "pcs_scientific_authority": False,
    }


def _score_ood(rules: frozenset[str]) -> dict[str, Any]:
    supported_ok = 0
    supported_rows = []
    for iid, text in OOD_SUPPORTED:
        result = formalize_with_rules(text, rules)
        ok = result.get("status") in {"supported", "ambiguous"} and bool(result.get("candidates"))
        supported_ok += int(ok)
        supported_rows.append({"id": iid, "text": text, "status": result.get("status"), "ok": ok})
    abstain_ok = 0
    abstain_rows = []
    false_accepts = 0
    for iid, text in OOD_ABSTAIN:
        result = formalize_with_rules(text, rules)
        status = result.get("status")
        ok = status == "unsupported" and not result.get("candidates")
        false_accepts += int(status in {"supported", "ambiguous"} and bool(result.get("candidates")))
        abstain_ok += int(ok)
        abstain_rows.append({"id": iid, "text": text, "status": status, "ok": ok})
    return {
        "format": "pcs-pgra-ext-ood-paraphrase",
        "supported_ok": supported_ok,
        "supported_total": len(OOD_SUPPORTED),
        "supported_rate": supported_ok / max(1, len(OOD_SUPPORTED)),
        "abstain_ok": abstain_ok,
        "abstain_total": len(OOD_ABSTAIN),
        "abstain_rate": abstain_ok / max(1, len(OOD_ABSTAIN)),
        "false_accepts": false_accepts,
        "rows_supported": supported_rows,
        "rows_abstain": abstain_rows,
        "pcs_scientific_authority": False,
    }


def _score_svb_abstention(rules: frozenset[str]) -> dict[str, Any]:
    """Real SVB evaluation claims must not be falsely autoformalized as supported."""
    if not SVB_ROOT.is_dir():
        return {
            "format": "pcs-pgra-ext-svb-abstention",
            "available": False,
            "reason": "SVB repository not found beside proof-carrying-science",
            "pcs_scientific_authority": False,
        }
    import sys

    sys.path.insert(0, str(SVB_ROOT / "src"))
    from svb.core import load_dataset  # type: ignore

    items = load_dataset(SVB_ROOT)
    if not isinstance(items, list):
        items = list(items)
    evaluation = [t for t in items if t.get("split") == "evaluation" and t.get("scored", True)]
    false_accept = 0
    abstain = 0
    rows = []
    for task in evaluation:
        claim = str(task.get("claim") or "")
        result = formalize_with_rules(claim, rules)
        status = result.get("status")
        accepted = status in {"supported", "ambiguous"} and bool(result.get("candidates"))
        false_accept += int(accepted)
        abstain += int(not accepted)
        rows.append(
            {
                "id": task.get("id"),
                "status": status,
                "false_accept": accepted,
                "claim": claim[:160],
            }
        )
    return {
        "format": "pcs-pgra-ext-svb-abstention",
        "available": True,
        "evaluation_scored": len(evaluation),
        "correct_abstain": abstain,
        "false_accept": false_accept,
        "false_accept_rate": false_accept / max(1, len(evaluation)),
        "abstain_rate": abstain / max(1, len(evaluation)),
        "rows": rows,
        "source": str(SVB_ROOT / "data" / "tasks.json"),
        "pcs_scientific_authority": False,
        "note": (
            "SVB is a scientific evidence-scope benchmark; success here means "
            "fail-closed abstention on out-of-grammar scientific claims, not SVB label accuracy."
        ),
    }


def _score_lean_learning_final_proofs(*, budget: int = 128, beam: int = 6) -> dict[str, Any]:
    from pcs.experimental.prover.environment import LeanEnvironment, search

    tasks = json.loads((LEAN_LEARNING_V2 / "tasks.json").read_text())
    final = [t for t in tasks if t.get("split") == "final"]
    rows = []
    env = LeanEnvironment(timeout=90)
    try:
        for task in final:
            proved = search(env, task["goal"], budget=budget, beam=beam)
            status = proved.get("status") if proved else None
            rows.append(
                {
                    "id": task.get("id"),
                    "family": task.get("family"),
                    "status": status,
                    "expansions": proved.get("expansions") if proved else None,
                    "verified": status == "verified",
                }
            )
    finally:
        env.close()
    verified = sum(1 for r in rows if r["verified"])
    return {
        "format": "pcs-pgra-ext-lean-learning-v2-final-prove",
        "verified": verified,
        "total": len(final),
        "rate": verified / max(1, len(final)),
        "budget": budget,
        "beam": beam,
        "rows": rows,
        "source": str(LEAN_LEARNING_V2 / "tasks.json"),
        "pcs_scientific_authority": False,
    }


def run_external_suite(
    *,
    output: Path,
    rules: frozenset[str] | None = None,
    skip_proofs: bool = False,
    budget: int = 128,
) -> dict[str, Any]:
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    active = frozenset(rules if rules is not None else RULE_IDS)
    formalization = _score_lean_learning_formalization(active)
    ood = _score_ood(active)
    svb = _score_svb_abstention(active)
    proofs = (
        {"format": "pcs-pgra-ext-lean-learning-v2-final-prove", "skipped": True}
        if skip_proofs
        else _score_lean_learning_final_proofs(budget=budget)
    )
    # Pass criteria for research generalization report (honest, not authority).
    gates = {
        "lean_learning_supported_exact": formalization["supported_rate"] == 1.0,
        "lean_learning_negatives": formalization["negative_rate"] == 1.0,
        "ood_supported_all": ood["supported_rate"] == 1.0,
        "ood_abstain_all": ood["false_accepts"] == 0,
        "svb_zero_false_accept": (not svb.get("available")) or svb.get("false_accept") == 0,
        "lean_learning_final_prove_ge_5_of_6": (
            proofs.get("skipped") or proofs.get("verified", 0) >= 5
        ),
    }
    summary = {
        "format": "pcs-pgra-external-generalization-summary-v1",
        "rules": sorted(active),
        "axes": {
            "lean_learning_v2_formalization": formalization,
            "ood_paraphrase": ood,
            "svb_abstention": svb,
            "lean_learning_v2_final_prove": proofs,
        },
        "gates": gates,
        "all_gates_passed": all(gates.values()),
        "automatic_deployment": False,
        "pcs_scientific_authority": False,
        "limitations": [
            "Not miniF2F/FormL4 (absent from workspace)",
            "Not unrestricted English equivalence",
            "SVB axis measures fail-closed abstention, not SVB label accuracy",
            "lean-learning-v2 is sealed PCS-authored elementary math, not novel mathematics",
        ],
    }
    (output / "external_generalization_summary.json").write_text(
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
    parser.add_argument("--skip-proofs", action="store_true")
    parser.add_argument("--budget", type=int, default=128)
    args = parser.parse_args(argv)
    summary = run_external_suite(
        output=args.output, skip_proofs=args.skip_proofs, budget=args.budget
    )
    print(
        json.dumps(
            {
                "all_gates_passed": summary["all_gates_passed"],
                "gates": summary["gates"],
                "lean_learning_supported": summary["axes"]["lean_learning_v2_formalization"][
                    "supported_rate"
                ],
                "ood_supported_rate": summary["axes"]["ood_paraphrase"]["supported_rate"],
                "ood_false_accepts": summary["axes"]["ood_paraphrase"]["false_accepts"],
                "svb_false_accept": summary["axes"]["svb_abstention"].get("false_accept"),
                "final_prove": summary["axes"]["lean_learning_v2_final_prove"].get("rate"),
                "automatic_deployment": False,
                "pcs_scientific_authority": False,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if summary["all_gates_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
