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

from .stats import proportion, upper_bound

CRITERIA = Path(__file__).with_name("criteria.json")


def metrics(per_paper: dict[str, Counter], icc_floor: float = 0.0) -> dict:
    """``per_paper[paper]`` holds class counts for one arm.  One cluster per paper.

    Counter keys (dev.evaluate.classes writes the first three groups; a prospective label set adds the last):
      verdicts   correct_confirmation, unsupported_confirmation, unlabelled_confirmation,
                 correct_discrepancy, misleading_refutation, unlabelled_discrepancy
      totals     true_claims_total, false_claims_total, not_derivable_total
      exposure   exposed_true, exposed_not_derivable        (numbers for which the arm proposed a reading)
      ambiguous  ambiguous_total, exposed_ambiguous         (a decided verdict on an ambiguous number is counted
                                                             as unsupported_confirmation / misleading_refutation)
    """
    def clusters(events, opportunities):
        return [(sum(c.get(k, 0) for k in events), sum(c.get(k, 0) for k in opportunities)) for c in per_paper.values()]

    def prop(events, opportunities):
        return proportion(clusters(events, opportunities), icc_floor=icc_floor)

    confirmations = ("correct_confirmation", "unsupported_confirmation", "unlabelled_confirmation")
    flags = ("correct_discrepancy", "misleading_refutation", "unlabelled_discrepancy")
    non_false = ("true_claims_total", "not_derivable_total", "ambiguous_total")
    exposed = ("exposed_true", "exposed_not_derivable", "exposed_ambiguous")
    has_exposure = any(c.get(k, 0) for c in per_paper.values() for k in exposed)
    ambiguous = sum(c.get("ambiguous_total", 0) for c in per_paper.values())
    labelled = sum(c.get(k, 0) for c in per_paper.values() for k in ("true_claims_total", "false_claims_total", "not_derivable_total", "ambiguous_total"))
    # paper-level view of C1 uses papers that have a confirmation, of C2 all papers
    flag_clusters = [(sum(c.get(k, 0) for k in ("misleading_refutation",)), 1) for c in per_paper.values()]
    out = {
        "unsupported_confirmations_among_confirmations": prop(("unsupported_confirmation",), confirmations),
        "misleading_refutations_among_flags": prop(("misleading_refutation",), flags),
        "misleading_refutations_per_exposed_number": prop(("misleading_refutation",), exposed) if has_exposure else None,
        "misleading_refutations_per_true_or_not_derivable_number": prop(("misleading_refutation",), non_false),
        "papers_with_a_misleading_refutation": {"papers": len(per_paper), "affected": sum(1 for k, _n in flag_clusters if k),
                                                "upper_bound": upper_bound(sum(1 for k, _n in flag_clusters if k), len(per_paper))},
        "coverage_of_true_statements": prop(("correct_confirmation",), ("true_claims_total", "ambiguous_total")),
        "coverage_of_true_statements_ambiguous_removed": prop(("correct_confirmation",), ("true_claims_total",)),
        "discrepancies_detected_among_false_statements": prop(("correct_discrepancy",), ("false_claims_total",)),
        "abstention_on_true_statements": prop(("abstained_on_true",), ("true_claims_total",)),
        "ambiguous": {"numbers": ambiguous, "share_of_labelled_numbers": (ambiguous / labelled) if labelled else None},
        "not_adjudicated": {"confirmations": sum(c.get("unlabelled_confirmation", 0) for c in per_paper.values()),
                            "flags": sum(c.get("unlabelled_discrepancy", 0) for c in per_paper.values())},
        "papers": len(per_paper), "icc_floor_assumed": icc_floor,
    }
    return out


def judge(m: dict, criteria: dict) -> dict:
    """Apply C1 to C3 and D1 of the pilot criteria.  A criterion that cannot be evaluated is NOT met."""
    pilot = criteria["levels"]["supervised_external_pilot"]
    need = pilot["minimum_sample"]
    c = pilot["criteria"]
    too_ambiguous = (m["ambiguous"]["share_of_labelled_numbers"] or 0) > c["C6_abstention"].get("max_share_ambiguous", 1)
    papers_ok = m["papers"] >= need["papers"] and not too_ambiguous
    out = {}
    u, k1 = m["unsupported_confirmations_among_confirmations"], c["C1_unsupported_confirmations"]
    enough = papers_ok and u["opportunities"] >= need["confirmations_by_primary_arm"] and not m["not_adjudicated"]["confirmations"]
    out["C1_unsupported_confirmations"] = {
        "met": bool(enough and u["estimate"] is not None and u["estimate"] <= k1["max_estimate"]
                    and u["conservative_upper_bound"] <= k1["max_conservative_upper_bound"]
                    and u["paper_level_upper_bound"] <= k1["max_paper_level_upper_bound"]),
        "evaluable": bool(enough), "estimate": u["estimate"], "conservative_upper_bound": u["conservative_upper_bound"],
        "paper_level_upper_bound": u["paper_level_upper_bound"], "confirmations": u["opportunities"], "papers": m["papers"],
        "upper_bound_by_assumed_icc": u["upper_bound_by_assumed_icc"]}
    k2 = c["C2_misleading_refutations"]
    r, fl, pp = m["misleading_refutations_per_exposed_number"], m["misleading_refutations_among_flags"], m["papers_with_a_misleading_refutation"]
    enough = papers_ok and not m["not_adjudicated"]["flags"] and r is not None
    a_ok = bool(r and r["estimate"] is not None and r["estimate"] <= k2["a_per_exposed_claim"]["max_estimate"]
                and r["conservative_upper_bound"] <= k2["a_per_exposed_claim"]["max_conservative_upper_bound"])
    b_ok = pp["upper_bound"] <= k2["b_per_paper"]["max_paper_level_upper_bound"]
    c_evaluable = fl["opportunities"] >= k2["c_among_flags"]["min_flags_for_evaluation"]
    c_ok = bool(c_evaluable and upper_bound(fl["events"], fl["opportunities"]) <= k2["c_among_flags"]["max_upper_bound"])
    out["C2_misleading_refutations"] = {
        "met": bool(enough and a_ok and b_ok and c_ok), "evaluable": bool(enough and c_evaluable),
        "a_per_exposed_claim": {"met": a_ok, "estimate": r["estimate"] if r else None, "conservative_upper_bound": r["conservative_upper_bound"] if r else None},
        "b_per_paper": {"met": bool(b_ok), "affected_papers": pp["affected"], "papers": pp["papers"], "upper_bound": pp["upper_bound"]},
        "c_among_flags": {"met": c_ok, "evaluable": c_evaluable, "misleading": fl["events"], "flags": fl["opportunities"],
                          "upper_bound": upper_bound(fl["events"], fl["opportunities"]) if fl["opportunities"] else None}}
    v, k3 = m["coverage_of_true_statements"], c["C3_useful_coverage"]
    out["C3_useful_coverage"] = {
        "met": bool(papers_ok and v["estimate"] is not None and v["estimate"] >= k3["min_estimate"]
                    and v["lower_bound_design_effect_adjusted"] >= k3["min_lower_bound"]),
        "evaluable": bool(papers_ok), "estimate": v["estimate"], "lower_bound": v["lower_bound_design_effect_adjusted"],
        "estimate_with_ambiguous_numbers_removed": m["coverage_of_true_statements_ambiguous_removed"]["estimate"]}
    det, rule = m["discrepancies_detected_among_false_statements"], c["D1_discrepancy_detection"]["wording_rule"]
    needed = rule["flag_recall_lower_bound_needed_to_describe_the_tool_as_finding_errors"]
    lower = det["lower_bound_design_effect_adjusted"] if det["opportunities"] else None
    out["D1_discrepancy_detection"] = {
        "flag_recall": det["estimate"], "lower_bound": lower, "false_statements": det["opportunities"],
        "necessary_condition_met": bool(lower is not None and r is not None and lower > r["conservative_upper_bound"]),
        "may_be_described_as_finding_errors": bool(needed is not None and lower is not None and lower >= needed),
        "note": "No pass/fail minimum. If the wording threshold is unset or not reached, a pilot is confirmation only."}
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
        m = metrics(papers, icc_floor=criteria["assumptions"]["icc_floor"])
        out["arms"][arm] = {"metrics": m, "criteria": judge(m, criteria)}
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
        print(arm, {k: (v["met"] if "met" in v else v.get("may_be_described_as_finding_errors"), "evaluable" if v.get("evaluable", True) else "NOT evaluable")
                    for k, v in body["criteria"].items()})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
