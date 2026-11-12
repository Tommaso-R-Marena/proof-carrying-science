"""Scoring for the prospective evaluation: per-paper counts -> clustered proportions -> criteria.

The same code scores a demonstration on DEVELOPMENT data (to show that it works and what the
intervals look like at small sample sizes) and, after the owner approves the protocol, the
prospective run.  Nothing here looks at prospective outcomes before that.

    python -m research.claimcheck_v1_1.prospective.score demo --out research/claimcheck_v1_1/prospective/DEMONSTRATION_ON_DEVELOPMENT_DATA.json
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

from .stats import lower_bound, proportion

CRITERIA = Path(__file__).with_name("criteria.json")


def metrics(per_paper: dict[str, Counter]) -> dict:
    """``per_paper[paper]`` holds class counts for one arm (see dev.evaluate.classes).  One cluster per paper."""
    def clusters(events, opportunities):
        return [(sum(c.get(k, 0) for k in events), sum(c.get(k, 0) for k in opportunities)) for c in per_paper.values()]

    confirmations = ("correct_confirmation", "unsupported_confirmation", "unlabelled_confirmation")
    flags = ("correct_discrepancy", "misleading_refutation", "unlabelled_discrepancy")
    true_claims = ("correct_confirmation", "abstained_on_true", "true_claim_misjudged")
    false_claims = ("correct_discrepancy", "abstained_on_false", "false_claim_misjudged")
    non_false = ("true_claims_total", "not_derivable_total")
    out = {
        "unsupported_confirmations_among_confirmations": proportion(clusters(("unsupported_confirmation",), confirmations)),
        "misleading_refutations_among_flags": proportion(clusters(("misleading_refutation",), flags)),
        "misleading_refutations_per_true_or_not_derivable_number": proportion(clusters(("misleading_refutation",), non_false)),
        "coverage_of_true_statements": proportion(clusters(("correct_confirmation",), ("true_claims_total",))),
        "discrepancies_detected_among_false_statements": proportion(clusters(("correct_discrepancy",), ("false_claims_total",))),
        "abstention_on_true_statements": proportion(clusters(("abstained_on_true",), ("true_claims_total",))),
        "not_adjudicated": {"confirmations": sum(c.get("unlabelled_confirmation", 0) for c in per_paper.values()),
                            "flags": sum(c.get("unlabelled_discrepancy", 0) for c in per_paper.values())},
        "papers": len(per_paper),
    }
    cov = out["coverage_of_true_statements"]
    cov["lower_bound_ignoring_clustering"] = lower_bound(cov["events"], cov["opportunities"])
    del true_claims, false_claims
    return out


def judge(m: dict, criteria: dict) -> dict:
    """Apply C1 to C3 of the pilot criteria.  A criterion that cannot be evaluated is NOT met."""
    pilot = criteria["levels"]["supervised_external_pilot"]
    need = pilot["minimum_sample"]
    c = pilot["criteria"]
    out = {}
    u = m["unsupported_confirmations_among_confirmations"]
    enough = m["papers"] >= need["papers"] and u["opportunities"] >= need["confirmations_by_primary_arm"] and not m["not_adjudicated"]["confirmations"]
    out["C1_unsupported_confirmations"] = {
        "met": bool(enough and u["estimate"] is not None and u["estimate"] <= c["C1_unsupported_confirmations"]["max_estimate"]
                    and u["conservative_upper_bound"] <= c["C1_unsupported_confirmations"]["max_conservative_upper_bound"]
                    and u["paper_level_upper_bound"] <= c["C1_unsupported_confirmations"]["max_paper_level_upper_bound"]),
        "evaluable": bool(enough), "estimate": u["estimate"], "conservative_upper_bound": u["conservative_upper_bound"],
        "paper_level_upper_bound": u["paper_level_upper_bound"], "confirmations": u["opportunities"], "papers": m["papers"]}
    r = m["misleading_refutations_per_true_or_not_derivable_number"]
    enough = m["papers"] >= need["papers"] and not m["not_adjudicated"]["flags"]
    out["C2_misleading_refutations"] = {
        "met": bool(enough and r["estimate"] is not None and r["estimate"] <= c["C2_misleading_refutations"]["max_estimate"]
                    and r["conservative_upper_bound"] <= c["C2_misleading_refutations"]["max_conservative_upper_bound"]
                    and r["paper_level_upper_bound"] <= c["C2_misleading_refutations"]["max_paper_level_upper_bound"]),
        "evaluable": bool(enough), "estimate": r["estimate"], "conservative_upper_bound": r["conservative_upper_bound"],
        "paper_level_upper_bound": r["paper_level_upper_bound"], "papers": m["papers"]}
    v = m["coverage_of_true_statements"]
    enough = m["papers"] >= need["papers"]
    out["C3_useful_coverage"] = {
        "met": bool(enough and v["estimate"] is not None and v["estimate"] >= c["C3_useful_coverage"]["min_estimate"]
                    and v["lower_bound_design_effect_adjusted"] >= c["C3_useful_coverage"]["min_lower_bound"]),
        "evaluable": bool(enough), "estimate": v["estimate"], "lower_bound": v["lower_bound_design_effect_adjusted"]}
    return out


def demo() -> dict:
    """The harness on DEVELOPMENT data (v1 documents).  Shows the machinery; proves nothing about v1.1."""
    from ...claimcheck_v1.tools.analyze import _CacheOnly, arm_proposals
    from ..dev.common import SPLITS, context, documents
    from ..dev.evaluate import classes, token_outcomes_v11
    from ..policy import assess_document
    results = SPLITS["heldout"]
    verifier = _CacheOnly(results / "receipts")
    per_arm: dict[str, dict[str, Counter]] = defaultdict(lambda: defaultdict(Counter))
    for doc in documents("heldout"):
        if doc.variant == "injected":
            continue
        ctx = context(doc)
        arms = arm_proposals(doc, results)
        for arm in ("gemini", "openrouter", "union"):
            if arm not in arms:
                continue
            receipts = verifier.verify(doc, arms[arm], arm)
            c = classes(doc, token_outcomes_v11(doc, receipts, assess_document(ctx, receipts, oracle_siblings=True)))
            c["true_claims_total"] = sum(1 for g in doc.gold if g["kind"] == "derivable" and g.get("truth") == "consistent")
            c["false_claims_total"] = sum(1 for g in doc.gold if g["kind"] == "derivable" and g.get("truth") == "inconsistent")
            c["not_derivable_total"] = sum(1 for g in doc.gold if g["kind"] != "derivable")
            per_arm[arm][doc.slug].update(c)          # original and planted-error copy of a paper are one cluster
    criteria = json.loads(CRITERIA.read_text(encoding="utf-8"))
    out = {"WARNING": "DEVELOPMENT DATA. Six papers that were used to design v1.1, AI-assisted labels, oracle-predicted sibling corroboration. "
                      "This demonstrates the scoring machinery. It is not an evaluation of v1.1 and no criterion can be met by it.",
           "arms": {}}
    for arm, papers in per_arm.items():
        m = metrics(papers)
        out["arms"][arm] = {"metrics": m, "criteria_C1_to_C3": judge(m, criteria)}
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("demo")
    d.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    out = demo()
    Path(args.out).write_text(json.dumps(out, indent=1), encoding="utf-8")
    for arm, body in out["arms"].items():
        m = body["metrics"]
        print(arm, {k: (round(v["estimate"], 3) if v["estimate"] is not None else None, v["events"], v["opportunities"],
                        "upper", round(v["conservative_upper_bound"], 3), "paper-level upper", round(v["paper_level_upper_bound"], 3))
                    for k, v in m.items() if isinstance(v, dict) and "estimate" in v})
        print("   ", {k: (v["met"], "evaluable" if v["evaluable"] else "NOT evaluable") for k, v in body["criteria_C1_to_C3"].items()})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
