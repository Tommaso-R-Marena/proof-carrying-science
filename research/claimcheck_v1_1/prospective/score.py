"""Scoring for the prospective evaluation (draft 3): per-number records -> per-paper counts by scope
-> clustered proportions -> criteria.

Every rule here is a rule written in PROTOCOL_DRAFT.md and criteria.json; the tests in
``tests/test_score_draft3.py`` check them one by one.

* Scopes (protocol 7, 11): C1 and C3 on original articles; C2 on originals and planted-error
  copies; D1 on planted errors (planted copies), with F numbers of the originals reported apart.
* Labels of a planted-error copy are the original's (protocol 7): a changed number is a planted
  error only where the original number was adjudicated T.
* The primary-analysis set (protocol 2, 3, 10a): three contexts with at least 20 eligible papers
  each (no topping up), the 120-paper design or its fallback, and the 90 % primary-complete rule.
* C2c uses the same clustered (conservative) bound as every other claim-level criterion.
* C4 (replay) and C7 (kernel cost) are judged from replay and kernel-run records.

The same code scores a demonstration on DEVELOPMENT data (``demo``) and, after the owner approves
the protocol, the prospective run.  Nothing here looks at prospective outcomes before that.

    python -m research.claimcheck_v1_1.prospective.score demo --out research/claimcheck_v1_1/prospective/DEMONSTRATION_ON_DEVELOPMENT_DATA.json
"""
from __future__ import annotations

import argparse
import hashlib
import inspect
import json
import math
import statistics
from collections import Counter, defaultdict
from pathlib import Path

from .stats import proportion, upper_bound

CRITERIA = Path(__file__).with_name("criteria.json")

OUTCOMES = ("CONFIRMATION", "DISCREPANCY_FOR_REVIEW", "REQUIRE_HUMAN_REVIEW", "UNKNOWN", "NO_PROPOSAL")
CLASSES = ("T", "F", "N", "A")
TOTAL = {"T": "true_claims_total", "F": "false_claims_total", "N": "not_derivable_total", "A": "ambiguous_total"}
EXPOSED = {"T": "exposed_true", "F": "exposed_false", "N": "exposed_not_derivable", "A": "exposed_ambiguous"}
CONFIRMATIONS = ("correct_confirmation", "unsupported_confirmation", "unlabelled_confirmation")
FLAGS = ("correct_discrepancy", "misleading_refutation", "unlabelled_discrepancy")


def pilot(criteria: dict) -> dict:
    return criteria["levels"]["supervised_external_pilot"]


# ---------------------------------------------------------------- per-number records -> per-paper counts

def copy_class(original_class: str | None, changed: bool) -> tuple[str | None, bool]:
    """Class of a number in the planted-error copy, from the original's adjudication (protocol 7).
    Returns (class, is_planted_error).  A changed number is a planted error (F) only if the original
    number was adjudicated T; otherwise it keeps the original's class (N, A or F) and is not one."""
    if not changed or original_class is None:
        return original_class, False
    if original_class == "T":
        return "F", True
    return original_class, False


def paper_counts(records: list[dict]) -> dict[str, Counter]:
    """Counts for one paper and one arm.  Each record is one printed number in one document:

      variant          "original" or "planted"
      cls              the adjudicated class of the number in the ORIGINAL article (T, F, N, A),
                       or None if the number was not adjudicated
      changed          True if the number was altered in the planted-error copy (planted copy only)
      outcome          one of OUTCOMES (abstentions: REQUIRE_HUMAN_REVIEW, UNKNOWN, NO_PROPOSAL)
      reading_matches  the decided reading is the adjudicated one or an equivalent row selection
    """
    out = {"original": Counter(), "planted": Counter()}
    for r in records:
        variant, outcome = r["variant"], r["outcome"]
        if variant not in out or outcome not in OUTCOMES:
            raise ValueError(f"bad record {r!r}")
        c = out[variant]
        if variant == "original":
            cls, planted_error = r["cls"], False
        else:
            cls, planted_error = copy_class(r["cls"], bool(r.get("changed")))
        if cls is None:
            if outcome == "CONFIRMATION":
                c["unlabelled_confirmation"] += 1
            elif outcome == "DISCREPANCY_FOR_REVIEW":
                c["unlabelled_discrepancy"] += 1
            continue
        if cls not in CLASSES:
            raise ValueError(f"bad class {cls!r}")
        c[TOTAL[cls]] += 1
        if cls == "F":
            c["false_planted_total" if planted_error else "false_natural_total" if variant == "original" else "false_natural_in_copy_total"] += 1
        if outcome != "NO_PROPOSAL":
            c[EXPOSED[cls]] += 1
        match = bool(r.get("reading_matches"))
        if outcome == "CONFIRMATION":
            c["correct_confirmation" if cls == "T" and match else "unsupported_confirmation"] += 1
        elif outcome == "DISCREPANCY_FOR_REVIEW":
            correct = cls == "F" and match
            c["correct_discrepancy" if correct else "misleading_refutation"] += 1
            if correct and planted_error:
                c["correct_discrepancy_planted"] += 1
            elif correct and variant == "original":
                c["correct_discrepancy_natural"] += 1
        else:
            if cls == "T":
                c["abstained_on_true"] += 1
            if outcome == "REQUIRE_HUMAN_REVIEW":
                c["review_requested"] += 1
    return out


# ---------------------------------------------------------------- the primary-analysis set

def select_primary(papers: dict[str, dict], criteria: dict, design: int) -> dict:
    """Protocol 3 (at least 20 eligible papers in each of three contexts, no topping up), 10a (the
    120-paper design and its fallback) and 2 (at least 90 % of the primary papers primary-complete).

    ``papers[id]`` holds "context", "order" (the hash-order key of protocol 3) and "primary_complete"."""
    need = pilot(criteria)["minimum_sample"]
    larger = need["owner_option_larger_sample"]
    if design not in (need["papers"], larger["papers"]):
        raise ValueError("design must be the 60- or the 120-paper design")
    minimum = need["papers_per_context"]
    by_context: dict[str, list[str]] = defaultdict(list)
    for pid, p in papers.items():
        by_context[p["context"]].append(pid)
    for ids in by_context.values():
        ids.sort(key=lambda pid: papers[pid]["order"])
    reasons = []
    if len(by_context) < need["scientific_contexts"]:
        reasons.append(f"{len(by_context)} contexts; {need['scientific_contexts']} are required")
    short = sorted(c for c, ids in by_context.items() if len(ids) < minimum)
    if short:
        reasons.append(f"shortfall: fewer than {minimum} eligible papers in {', '.join(short)}; no topping up")
    used = design
    if design == larger["papers"] and any(len(ids) < larger["papers_per_context"] for ids in by_context.values()):
        used = need["papers"]                                     # fallback, protocol 10a
    per = minimum if used == need["papers"] else larger["papers_per_context"]
    primary = [pid for c in sorted(by_context) for pid in by_context[c][:per]]
    share = (sum(1 for pid in primary if papers[pid]["primary_complete"]) / len(primary)) if primary else 0.0
    if share < need["primary_complete_share"]:
        reasons.append(f"primary-complete share {share:.3f} is below {need['primary_complete_share']}")
    return {"design_requested": design, "design_used": used, "fallback": used != design, "papers_per_context_used": per,
            "eligible_per_context": {c: len(ids) for c, ids in sorted(by_context.items())},
            "primary": primary, "secondary_all_eligible": sorted(papers, key=lambda pid: (papers[pid]["context"], papers[pid]["order"])) if used != design else None,
            "primary_complete_share": share, "evaluable": not reasons, "reasons": reasons}


# ---------------------------------------------------------------- proportions by scope

def scoped_metrics(counts: dict[str, dict[str, Counter]], icc_floor: float) -> dict:
    """``counts[paper] = {"original": Counter, "planted": Counter}`` (from ``paper_counts``)."""
    orig = {p: c["original"] for p, c in counts.items()}
    both = {p: c["original"] + c["planted"] for p, c in counts.items()}
    plant = {p: c["planted"] for p, c in counts.items()}

    def total(scope, keys):
        return sum(c.get(k, 0) for c in scope.values() for k in keys)

    def prop(scope, events, opportunities):
        return proportion([(sum(c.get(k, 0) for k in events), sum(c.get(k, 0) for k in opportunities)) for c in scope.values()],
                          icc_floor=icc_floor)

    exposed = (EXPOSED["T"], EXPOSED["N"], EXPOSED["A"])
    t, f, a = (total(orig, (TOTAL[k],)) for k in "TFA")
    affected = sum(1 for c in both.values() if c.get("misleading_refutation", 0))
    return {
        "C1_unsupported_among_confirmations": prop(orig, ("unsupported_confirmation",), CONFIRMATIONS),
        "C2a_misleading_per_exposed_number": prop(both, ("misleading_refutation",), exposed) if total(both, exposed) else None,
        "C2b_papers_with_a_misleading_flag": {"papers": len(both), "affected": affected, "upper_bound": upper_bound(affected, len(both))},
        "C2c_misleading_among_flags": prop(both, ("misleading_refutation",), FLAGS),
        "C2c_misleading_among_flags_originals_only": prop(orig, ("misleading_refutation",), FLAGS),
        "misleading_per_true_not_derivable_or_ambiguous_number": prop(both, ("misleading_refutation",), (TOTAL["T"], TOTAL["N"], TOTAL["A"])),
        "C3_coverage": prop(orig, ("correct_confirmation",), (TOTAL["T"], TOTAL["A"])),
        "C3_coverage_ambiguous_removed": prop(orig, ("correct_confirmation",), (TOTAL["T"],)),
        "D1_flag_recall_planted": prop(plant, ("correct_discrepancy_planted",), ("false_planted_total",)),
        "D1_flag_recall_natural": prop(orig, ("correct_discrepancy_natural",), ("false_natural_total",)),
        "abstention_on_true": prop(orig, ("abstained_on_true",), (TOTAL["T"],)),
        "ambiguous": {"numbers": a, "statistic_like_numbers": t + f + a, "share_of_statistic_like_numbers": (a / (t + f + a)) if t + f + a else None},
        "not_adjudicated": {"confirmations_in_originals": total(orig, ("unlabelled_confirmation",)), "flags_in_both": total(both, ("unlabelled_discrepancy",))},
        "papers": len(counts), "icc_floor_assumed": icc_floor,
    }


# ---------------------------------------------------------------- the rules of C1 to C3 and D1

def c1_met(u: dict, k1: dict) -> bool:
    return bool(u["estimate"] is not None and u["estimate"] <= k1["max_estimate"]
                and u["conservative_upper_bound"] <= k1["max_conservative_upper_bound"]
                and u["paper_level_upper_bound"] <= k1["max_paper_level_upper_bound"])


def c2a_met(r: dict | None, k2a: dict) -> bool:
    return bool(r is not None and r["estimate"] is not None and r["estimate"] <= k2a["max_estimate"]
                and r["conservative_upper_bound"] <= k2a["max_conservative_upper_bound"])


def c2b_met(pp: dict, k2b: dict) -> bool:
    return pp["upper_bound"] <= k2b["max_paper_level_upper_bound"]


def c2c_evaluable(fl: dict, k2c: dict) -> bool:
    return fl["opportunities"] >= k2c["min_flags_for_evaluation"]


def c2c_met(fl: dict, k2c: dict) -> bool:
    return bool(c2c_evaluable(fl, k2c) and fl["conservative_upper_bound"] <= k2c["max_upper_bound"])


def c3_met(v: dict, k3: dict) -> bool:
    return bool(v["estimate"] is not None and v["estimate"] >= k3["min_estimate"] and v["lower_bound_design_effect_adjusted"] >= k3["min_lower_bound"])


def judge(m: dict, criteria: dict, sample: dict) -> dict:
    """C1 to C3, D1 and the pilot scope they allow.  A criterion that cannot be evaluated is NOT met."""
    p = pilot(criteria)
    need, c = p["minimum_sample"], p["criteria"]
    share = m["ambiguous"]["share_of_statistic_like_numbers"]
    too_ambiguous = share is not None and share > c["C6_abstention"]["max_share_ambiguous"]
    sample_ok = bool(sample["evaluable"]) and not too_ambiguous
    out = {"sample_evaluable": sample_ok, "reasons_not_evaluable": list(sample["reasons"]) + (
        [f"ambiguous share {share:.3f} above {c['C6_abstention']['max_share_ambiguous']}"] if too_ambiguous else [])}
    u, k1 = m["C1_unsupported_among_confirmations"], c["C1_unsupported_confirmations"]
    c1_eval = sample_ok and u["opportunities"] >= need["confirmations_by_primary_arm"] and not m["not_adjudicated"]["confirmations_in_originals"]
    out["C1_unsupported_confirmations"] = {
        "met": bool(c1_eval and c1_met(u, k1)), "evaluable": bool(c1_eval), "estimate": u["estimate"],
        "conservative_upper_bound": u["conservative_upper_bound"], "paper_level_upper_bound": u["paper_level_upper_bound"],
        "confirmations": u["opportunities"], "upper_bound_by_assumed_icc": u["upper_bound_by_assumed_icc"]}
    k2 = c["C2_misleading_refutations"]
    r, pp, fl = m["C2a_misleading_per_exposed_number"], m["C2b_papers_with_a_misleading_flag"], m["C2c_misleading_among_flags"]
    ab_eval = sample_ok and not m["not_adjudicated"]["flags_in_both"] and r is not None
    a_ok, b_ok = c2a_met(r, k2["a_per_exposed_claim"]), c2b_met(pp, k2["b_per_paper"])
    c_eval, c_ok = c2c_evaluable(fl, k2["c_among_flags"]), c2c_met(fl, k2["c_among_flags"])
    fo = m["C2c_misleading_among_flags_originals_only"]
    out["C2_misleading_refutations"] = {
        "met": bool(ab_eval and a_ok and b_ok and c_ok), "evaluable": bool(ab_eval and c_eval),
        "met_for_a_confirmation_only_pilot": bool(ab_eval and a_ok and b_ok),
        "a_per_exposed_claim": {"met": a_ok, "estimate": r["estimate"] if r else None, "conservative_upper_bound": r["conservative_upper_bound"] if r else None},
        "b_per_paper": {"met": bool(b_ok), "affected_papers": pp["affected"], "papers": pp["papers"], "upper_bound": pp["upper_bound"]},
        "c_among_flags": {"met": c_ok, "evaluable": c_eval, "misleading": fl["events"], "flags": fl["opportunities"],
                          "conservative_upper_bound": fl["conservative_upper_bound"] if fl["opportunities"] else None,
                          "bound_ignoring_clustering": upper_bound(fl["events"], fl["opportunities"]) if fl["opportunities"] else None},
        "c_among_flags_originals_only_reported": {"misleading": fo["events"], "flags": fo["opportunities"],
                                                  "conservative_upper_bound": fo["conservative_upper_bound"] if fo["opportunities"] else None}}
    v, k3 = m["C3_coverage"], c["C3_useful_coverage"]
    out["C3_useful_coverage"] = {
        "met": bool(sample_ok and c3_met(v, k3)), "evaluable": sample_ok, "estimate": v["estimate"],
        "lower_bound": v["lower_bound_design_effect_adjusted"], "estimate_with_ambiguous_numbers_removed": m["C3_coverage_ambiguous_removed"]["estimate"]}
    det, nat, rule = m["D1_flag_recall_planted"], m["D1_flag_recall_natural"], c["D1_discrepancy_detection"]["wording_rule"]
    needed = rule["flag_recall_lower_bound_needed_to_describe_the_tool_as_finding_errors"]
    lower = det["lower_bound_design_effect_adjusted"] if det["opportunities"] else None
    necessary = bool(lower is not None and r is not None and lower > r["conservative_upper_bound"])
    wording = bool(sample_ok and needed is not None and lower is not None and necessary and lower >= needed)
    out["D1_discrepancy_detection"] = {
        "flag_recall_planted": det["estimate"], "lower_bound_planted": lower, "planted_errors": det["opportunities"],
        "flag_recall_natural_reported": nat["estimate"], "natural_false_numbers": nat["opportunities"],
        "necessary_condition_met": necessary, "may_be_described_as_finding_errors": wording,
        "note": "No pass/fail minimum. If the wording threshold is unset or not reached, nothing may describe the tool as finding errors."}
    ready = out["C1_unsupported_confirmations"]["met"] and out["C3_useful_coverage"]["met"] and out["C2_misleading_refutations"]["met_for_a_confirmation_only_pilot"]
    out["pilot_scope_if_C4_to_C10_are_met"] = {
        "pilot": bool(ready),
        "discrepancy_flags_shown_to": (None if not ready else "pilot users, as discrepancies for review" if out["C2_misleading_refutations"]["met"]
                                       else "the supervising PCS reviewer only"),
        "may_be_described_as_finding_errors": bool(ready and wording),
        "every_screen_must_say_that_no_flag_carries_no_information": not (ready and wording)}
    return out


def evaluate(papers: dict[str, dict], criteria: dict, *, design: int) -> dict:
    """``papers[id]`` holds "context", "order", "primary_complete" and "counts" (from ``paper_counts``)."""
    sample = select_primary(papers, criteria, design)
    m = scoped_metrics({pid: papers[pid]["counts"] for pid in sample["primary"]}, criteria["assumptions"]["icc_floor"])
    return {"sample": sample, "metrics": m, "criteria": judge(m, criteria, sample)}


# ---------------------------------------------------------------- C4 replay and C7 kernel cost

def replay_shards(paper_ids: list[str], jobs: int) -> list[list[str]]:
    """Protocol 6 step 6: papers to replay jobs, by a fixed hash order, round robin."""
    order = sorted(paper_ids, key=lambda p: hashlib.sha256(f"claimcheck-v1.1-replay|{p}".encode()).hexdigest())
    return [order[i::jobs] for i in range(jobs)]


def judge_c4(bundles: dict[str, str], criteria: dict) -> dict:
    """``bundles[id]`` is "replayed", "mismatch" or "infrastructure_failure" (the job did not finish).
    Infrastructure failures are re-run before C4 is judged; a mismatch fails C4."""
    rule = pilot(criteria)["criteria"]["C4_independent_replay"]
    bad = sorted(b for b, s in bundles.items() if s not in ("replayed", "mismatch", "infrastructure_failure"))
    if bad:
        raise ValueError(f"unknown replay status for {bad}")
    rerun = sorted(b for b, s in bundles.items() if s == "infrastructure_failure")
    failed = sorted(b for b, s in bundles.items() if s == "mismatch")
    share = sum(1 for s in bundles.values() if s == "replayed") / len(bundles) if bundles else 0.0
    return {"met": bool(bundles) and not rerun and share >= rule["required"], "evaluable": bool(bundles) and not rerun,
            "rerun_required": rerun, "failed": failed, "replayed_share": share}


def supported_size(statistic: str, criteria: dict) -> int:
    sizes = pilot(criteria)["criteria"]["C7_computation"]["supported_size_bytes"]
    return sizes.get(statistic, sizes["any_other_statistic"])


def judge_c7(runs: list[dict], criteria: dict) -> dict:
    """``runs``: one record per kernel run (one claim per proof file): statistic, table_bytes, seconds,
    peak_gb (from the kernel guard log) and kernel_accepted.  Within the supported size of its
    statistic a run counts for C7; outside it, it is reported and its UNKNOWN counts as an abstention
    in C1 to C3 like any other."""
    k7 = pilot(criteria)["criteria"]["C7_computation"]
    within = [r for r in runs if r["table_bytes"] <= supported_size(r["statistic"], criteria)]
    outside = len(runs) - len(within)
    if not within:
        return {"met": False, "evaluable": False, "runs_within_supported_size": 0, "runs_outside_supported_size": outside}
    secs = sorted(r["seconds"] for r in within)
    p95 = secs[max(0, math.ceil(0.95 * len(secs)) - 1)]
    peak = max(r["peak_gb"] for r in within)
    done = sum(1 for r in within if r["kernel_accepted"]) / len(within)
    med = statistics.median(secs)
    met = (med <= k7["max_median_seconds_per_claim"] and p95 <= k7["max_p95_seconds_per_claim"]
           and peak <= k7["max_peak_memory_gb"] and done >= k7["min_completed_share"])
    return {"met": bool(met), "evaluable": True, "median_seconds": med, "p95_seconds": p95, "peak_gb": peak,
            "completed_share": done, "runs_within_supported_size": len(within), "runs_outside_supported_size": outside,
            "completed_share_all_runs_reported": sum(1 for r in runs if r["kernel_accepted"]) / len(runs)}


# ---------------------------------------------------------------- development demonstration

RESULT_TO_OUTCOME = {"PROVED": "CONFIRMATION", "REFUTED": "DISCREPANCY_FOR_REVIEW", "REQUIRE_HUMAN_REVIEW": "REQUIRE_HUMAN_REVIEW",
                     "NO_PROPOSAL": "NO_PROPOSAL"}


def _dev_class(item: dict) -> str:
    if item["kind"] != "derivable":
        return "N"
    return {"consistent": "T", "inconsistent": "F"}.get(item.get("truth"), "A")   # a conditional label counts as ambiguous


def dev_records(doc, outcomes: dict) -> list[dict]:
    """Development documents only: AI-assisted v1 labels stand in for adjudicated classes.  In the
    planted copy a planted item's original class is T (mutate.py plants only on true numbers)."""
    from ...claimcheck_v1.benchmark.harness import spec_signature
    variant = "original" if doc.variant == "original" else "planted"
    recs, labelled = [], set()
    for item in doc.gold:
        labelled.add(item["start"])
        o = outcomes.get(item["start"], {"result": "NO_PROPOSAL", "specs": []})
        sigs = {spec_signature(doc, g) for g in item.get("gold", [])}
        changed = variant == "planted" and bool(item.get("planted"))
        recs.append({"variant": variant, "cls": "T" if changed else _dev_class(item), "changed": changed,
                     "outcome": RESULT_TO_OUTCOME.get(o["result"], "UNKNOWN"),
                     "reading_matches": any(spec_signature(doc, s) in sigs for s in o["specs"])})
    for start, o in outcomes.items():
        if start not in labelled and o["result"] in ("PROVED", "REFUTED"):
            recs.append({"variant": variant, "cls": None, "outcome": RESULT_TO_OUTCOME[o["result"]], "reading_matches": False})
    return recs


def demo() -> dict:
    """The scorer on DEVELOPMENT data (v1 documents).  Shows the machinery; proves nothing about v1.1."""
    from ...claimcheck_v1.tools.analyze import _CacheOnly, arm_proposals
    from ..dev.common import SPLITS, context, documents
    from ..dev.evaluate import token_outcomes_v11
    from ..policy import assess_document
    # development use: receipts whose verdict an oracle predicted are marked as such (policy flag, where it exists)
    extra = {"oracle_receipts": True} if "oracle_receipts" in inspect.signature(assess_document).parameters else {}
    results = SPLITS["heldout"]
    verifier = _CacheOnly(results / "receipts")
    records: dict[str, dict[str, list]] = defaultdict(lambda: defaultdict(list))
    for doc in documents("heldout"):
        if doc.variant == "injected":
            continue
        ctx = context(doc)
        arms = arm_proposals(doc, results)
        for arm in ("gemini", "openrouter", "union"):
            if arm not in arms:
                continue
            receipts = verifier.verify(doc, arms[arm], arm)
            outcomes = token_outcomes_v11(doc, receipts, assess_document(ctx, receipts, oracle_siblings=True, **extra))
            records[arm][doc.slug].extend(dev_records(doc, outcomes))
    criteria = json.loads(CRITERIA.read_text(encoding="utf-8"))
    out = {"WARNING": "DEVELOPMENT DATA. Six papers that were used to design v1.1, one context, AI-assisted labels, oracle-predicted "
                      "sibling corroboration. This demonstrates the scoring machinery. It is not an evaluation of v1.1 and no "
                      "criterion can be met by it.",
           "policy_flags": {"oracle_siblings": True, **extra}, "arms": {}}
    for arm, per_paper in records.items():
        papers = {slug: {"context": "ecology and organismal biology (v1)", "order": slug, "primary_complete": True,
                         "counts": paper_counts(recs)} for slug, recs in per_paper.items()}
        out["arms"][arm] = evaluate(papers, criteria, design=60)
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("demo")
    d.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    out = demo()
    Path(args.out).write_text(json.dumps(out, indent=1, sort_keys=False), encoding="utf-8")
    for arm, body in out["arms"].items():
        print(arm, {k: (v.get("met"), "evaluable" if v.get("evaluable", True) else "NOT evaluable")
                    for k, v in body["criteria"].items() if isinstance(v, dict) and "met" in v})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
