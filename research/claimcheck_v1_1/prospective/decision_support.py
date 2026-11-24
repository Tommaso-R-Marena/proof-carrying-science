"""Operating characteristics behind the owner's decision package (DECISION_PACKAGE.md).

    python -m research.claimcheck_v1_1.prospective.decision_support [--out DECISION_SUPPORT.json]

Synthetic computation only.  Statistical figures use ``stats.py``, the module the scorer uses, and,
where the scorer's own rule matters, the formulas ``score.judge`` applies (design-effect bounds
``upper_bound(ceil(k / deff), n / deff)`` and ``lower_bound(floor(k / deff), n / deff)``; C2c with the
exact bound that ignores clustering).  Tolerances at the proposed ICC floor are checked against the
full ``stats.proportion`` (bootstrap included).

Files read, all existing results (nothing prospective, no network): ``criteria.json`` (thresholds),
``DESIGN_120.json`` (runner-hours), ``DEMONSTRATION_ON_DEVELOPMENT_DATA.json`` (development ICC
estimates and counts), ``../perf/results.json`` (kernel runs on synthetic tables) and the v1 prefetch
ledgers ``claimcheck_v1/benchmark/results/heldout/prefetch_ledger*.json`` (calls, failures, tokens,
seconds).  Every other input is a named assumption in ``ASSUMPTIONS``.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from . import stats as S

HERE = Path(__file__).resolve().parent
V11 = HERE.parent
CRITERIA = HERE / "criteria.json"
DESIGN = HERE / "DESIGN_120.json"
DEMO = HERE / "DEMONSTRATION_ON_DEVELOPMENT_DATA.json"
PERF = V11 / "perf" / "results.json"
LEDGERS = V11.parent / "claimcheck_v1" / "benchmark" / "results" / "heldout"

DESIGNS = (60, 120)
ICC_GRID = (0.0, 0.1, 0.25, 0.5)
MODELS, DOCUMENTS = 2, 2
ATTEMPTS = 4                                   # one call and at most three repeats (protocol 2)
SLEEPS = {"server_or_transport": [15, 30, 45], "quota_429": [40, 80, 120]}   # providers.py: min(120, (40|15) * (attempt + 1))
TIMEOUT_S = 300                                # providers.complete default
MAX_OUTPUT_TOKENS = 16384                      # protocol 2 / MODEL_ACCESS.md
NEMOTRON_USD_PER_TOKEN = (0.60e-6, 2.40e-6)    # paid route, listed 2026-11-15 (MODEL_ACCESS.md)
CAP_USD = {60: 15, 120: 30}                    # proposed hard caps (protocol 13)
V1_PLANTED_PER_PAPER = (7, 1, 4, 4, 9, 1)      # claimcheck_v1/benchmark/heldout/*/gold.mutated.json: items marked "planted"

ASSUMPTIONS = {
    "nemotron_sub_cap_usd": {"60": 5, "120": 10},
    "gemini_free_tier_successful_calls_per_day": 20,
    "adjudication": {"minutes_reading_per_paper": [10, 20], "numbers_per_paper": 25, "minutes_per_number": [1, 1.5],
                     "disagreement_share": [0.15, 0.25], "resolver_minutes_per_disagreement": 3,
                     "source": "adjudication/RECRUITMENT_AND_ADJUDICATION_PLAN.md section 4 (assumptions, not measurements)"},
    "adjudicator_hours_per_week": [4, 8],
    "screening_minutes_per_candidate": [10, 20],
    "screening_yields": [0.05, 0.067, 0.08, 0.1, 0.15, 0.25, 0.44],
    "decided_verdicts_per_paper_any_arm": [5, 10],
    "chance_a_decided_verdict_falls_on_an_ambiguous_number": [0.0005, 0.001, 0.005],
    "per_paper_rate_of_a_misleading_flag": [0.005, 0.01, 0.02],
    "replay_underestimate_factors": [1, 1.5, 2, 3],
    "replay_setup_hours_per_job": 0.5,
    "recall_values": [0.05, 0.1, 0.115, 0.15, 0.2, 0.25, 0.3, 0.4],
    "feasibility_minutes_per_paper": [30, 45, 57.5, 60, 75, 90],
    "feasibility_screening_candidates_per_context": [90, 300, 600],
    "per_call_success_grid": [0.9, 0.95, 0.97, 0.98, 0.99, 0.995],
}


def _r(x, d=4):
    return None if x is None else round(x, d)


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sizes_from(pattern, papers):
    return [pattern[i % len(pattern)] for i in range(papers)]


def one_per_paper(sizes, events):
    """``events`` events, at most one in each paper (the spread that keeps the ICC estimate at 0)."""
    assert events <= len(sizes)
    return [(1 if i < events else 0, n) for i, n in enumerate(sizes)]


def scorer_bounds(clusters, floor):
    """Design-effect bounds exactly as stats.proportion computes them, without its bootstrap."""
    clusters = [(k, n) for k, n in clusters if n > 0]
    k, n = sum(c[0] for c in clusters), sum(c[1] for c in clusters)
    deff = S.design_effect(clusters, floor)
    n_eff = n / deff
    return {"events": k, "opportunities": n, "design_effect": deff, "effective": n_eff,
            "upper": S.upper_bound(math.ceil(k / deff), n_eff), "lower": S.lower_bound(max(0, math.floor(k / deff)), n_eff)}


def closed_deff(sizes, icc):
    """1 + (weighted cluster size - 1) * icc: stats.design_effect when the data's ICC estimate is below ``icc``."""
    return 1 + (sum(n * n for n in sizes) / sum(sizes) - 1) * icc


# ---------------------------------------------------------------- C1 and C2a: tolerance by ICC floor

def _tolerance(check, limit):
    if not check(0)[0]:
        return -1, check(0)[1]
    k = 0
    while k + 1 <= limit:
        ok, why = check(k + 1)
        if not ok:
            return k, why
        k += 1
    return k, "limit"


def claim_level(crit) -> dict:
    pilot = crit["levels"]["supervised_external_pilot"]["criteria"]
    c1, c2a = pilot["C1_unsupported_confirmations"], pilot["C2_misleading_refutations"]["a_per_exposed_claim"]
    out = {"note": "events placed at most one per paper (ICC estimate 0, so the floor governs); the scorer divides events "
                   "and opportunities by the design effect; 'draft_2_table_rule' divides only opportunities, as draft 2's design_120.py did",
           "C1": [], "C2a": []}
    specs = {"C1": [("2.5 (2 and 3 alternating)", (2, 3)), ("4", (4,)), ("5", (5,))],
             "C2a": [("4", (4,)), ("5", (5,)), ("8", (8,)), ("10", (10,))]}
    for name, rows in specs.items():
        for label, pattern in rows:
            for papers in DESIGNS:
                sizes = sizes_from(pattern, papers)
                total = sum(sizes)
                row = {"per_paper": label, "papers": papers, "opportunities": total, "by_icc": {}}
                for icc in ICC_GRID:
                    def check(k, sizes=sizes, icc=icc, total=total, papers=papers, name=name):
                        b = scorer_bounds(one_per_paper(sizes, k), icc)
                        if name == "C1":
                            if k / total > c1["max_estimate"]:
                                return False, "estimate"
                            if b["upper"] > c1["max_conservative_upper_bound"]:
                                return False, "claim-level bound"
                            if S.upper_bound(k, papers) > c1["max_paper_level_upper_bound"]:
                                return False, "paper-level bound"
                            return True, ""
                        if k / total > c2a["max_estimate"]:
                            return False, "estimate"
                        if b["upper"] > c2a["max_conservative_upper_bound"]:
                            return False, "claim-level bound"
                        return True, ""
                    allowed, binding = _tolerance(check, papers)
                    deff = S.design_effect(one_per_paper(sizes, 0), icc)
                    bound_cap = c1["max_conservative_upper_bound"] if name == "C1" else c2a["max_conservative_upper_bound"]
                    cell = {"design_effect": _r(deff, 3), "effective": _r(total / deff, 1),
                            "upper_bound_with_events": {str(k): _r(scorer_bounds(one_per_paper(sizes, k), icc)["upper"]) for k in (0, 1, 2)},
                            "events_allowed_by_scorer": allowed, "binding_condition_at_one_more": binding,
                            "draft_2_table_rule_events_allowed": S.max_events_for_bound(int(total / deff), bound_cap)}
                    if icc == 0.25:
                        # the scorer itself, bootstrap included, at the boundary
                        def full(k):
                            p = S.proportion(one_per_paper(sizes, k), icc_floor=icc)
                            if name == "C1":
                                return (p["estimate"] <= c1["max_estimate"] and p["conservative_upper_bound"] <= c1["max_conservative_upper_bound"]
                                        and p["paper_level_upper_bound"] <= c1["max_paper_level_upper_bound"])
                            return p["estimate"] <= c2a["max_estimate"] and p["conservative_upper_bound"] <= c2a["max_conservative_upper_bound"]
                        cell["verified_by_stats_proportion"] = bool((allowed < 0 or full(allowed)) and not full(allowed + 1))
                    row["by_icc"][str(icc)] = cell
                if name == "C2a":
                    row["lowest_possible_bound_no_flag_by_icc"] = {str(i): _r(S.upper_bound(0, papers / i)) for i in ICC_GRID if i > 0}
                out[name].append(row)
    return out


def c2_joint(crit) -> dict:
    """C2a and C2b together.  Misleading flags in different papers each count against C2b; flags
    concentrated in one paper raise the estimated ICC of C2a.  Full stats.proportion (bootstrap included)."""
    k2 = crit["levels"]["supervised_external_pilot"]["criteria"]["C2_misleading_refutations"]
    a, b = k2["a_per_exposed_claim"], k2["b_per_paper"]["max_paper_level_upper_bound"]
    floor = crit["assumptions"]["icc_floor"]
    def spread(papers, m):
        sizes = [m] * papers
        k = -1
        while k + 1 <= papers:
            bb = scorer_bounds(one_per_paper(sizes, k + 1), floor)
            if (k + 1) / (m * papers) > a["max_estimate"] or bb["upper"] > a["max_conservative_upper_bound"]:
                break
            k += 1
        return k

    rows = []
    for papers in DESIGNS:
        affected = S.max_events_for_bound(papers, b)
        for m in (5, 10):
            j = 0
            while True:
                p = S.proportion([(j + 1 if i == 0 else 0, m) for i in range(papers)], icc_floor=floor)
                if affected < 1 or not (p["estimate"] <= a["max_estimate"] and p["conservative_upper_bound"] <= a["max_conservative_upper_bound"]):
                    break
                j += 1
            rows.append({"papers": papers, "exposed_per_paper": m, "c2b_affected_papers_allowed": affected,
                         "misleading_flags_allowed_all_in_one_paper": j if affected >= 1 else 0,
                         "misleading_flags_allowed_spread_one_per_paper": max(0, min(affected, spread(papers, m)))})
    return {"rows": rows}


def duplicate_copies() -> dict:
    """C2a counts each exposed number in the original and again in the planted-error copy."""
    rows = []
    for papers in DESIGNS:
        for m in (4, 5, 8):
            orig = papers * m / closed_deff([m] * papers, 0.25)
            both = papers * 2 * m / closed_deff([2 * m] * papers, 0.25)
            rows.append({"papers": papers, "exposed_per_document": m,
                         "bound_no_flag_originals_only": _r(S.upper_bound(0, orig)), "bound_no_flag_both_copies": _r(S.upper_bound(0, both)),
                         "bound_one_flag_originals_only": _r(S.upper_bound(1, orig)), "bound_one_flag_both_copies": _r(S.upper_bound(1, both))})
    return {"note": "ICC floor 0.25, equal sizes; most exposed numbers of the copy repeat the original's, which a 0.25 floor treats as nearly independent",
            "rows": rows}


# ---------------------------------------------------------------- C2c

def c2c(crit, demo) -> dict:
    k2 = crit["levels"]["supervised_external_pilot"]["criteria"]["C2_misleading_refutations"]["c_among_flags"]
    t, minf = k2["max_upper_bound"], k2["min_flags_for_evaluation"]

    def min_flags(threshold, step=1, deff=1.0):
        f = step
        while S.upper_bound(0, f / deff) > threshold:
            f += step
        return f

    scorer = [{"flags": f, "evaluable": f >= minf, "bound_0": _r(S.upper_bound(0, f)), "bound_1": _r(S.upper_bound(1, f)),
               "bound_2": _r(S.upper_bound(2, f)), "misleading_allowed": S.max_events_for_bound(f, t) if f >= minf else None}
              for f in (4, 5, 6, 8, 10, 15, 20, 25, 30, 40, 60)]
    thresholds = {}
    for th in (0.5, 1 / 3, 0.2):
        thresholds[str(_r(th))] = {"min_flags_none_misleading": min_flags(th),
                                   "misleading_allowed_at": {str(f): S.max_events_for_bound(f, th) for f in (10, 20, 40)}}
    clustered = []
    for per in (1, 2, 4):
        deff = 1 + (per - 1) * 0.25
        allowed = {}
        for f in (20, 40):
            sizes = [per] * (f // per)
            def ok(m, sizes=sizes):
                b = scorer_bounds(one_per_paper(sizes, m), 0.25)
                return b["upper"] <= t
            k = -1
            while k + 1 <= len(sizes) and ok(k + 1):
                k += 1
            allowed[str(f)] = k
        clustered.append({"flags_per_flagged_paper": per, "design_effect": deff, "min_flags_none_misleading": min_flags(t, per, deff),
                          "misleading_allowed_at": allowed})
    u = demo["arms"]["union"]
    fl = u["metrics"]["C2c_misleading_among_flags"]
    dev = {"flags": fl["opportunities"], "misleading": fl["events"], "papers": fl["papers"],
           "bound_ignoring_clustering": _r(S.upper_bound(fl["events"], fl["opportunities"])),
           "conservative_bound_with_floor": _r(fl["conservative_upper_bound"]),
           "flags_on_original_articles": u["metrics"]["C2c_misleading_among_flags_originals_only"]["opportunities"]}
    # what C2c measures: planted errors raise the share of real discrepancies far above a natural document
    det = u["metrics"]["D1_flag_recall_planted"]
    exposed = u["metrics"]["C2a_misleading_per_exposed_number"]["opportunities"]
    papers = u["metrics"]["papers"]
    planted = det["opportunities"]
    natural = u["metrics"]["D1_flag_recall_natural"]["opportunities"] / papers
    exp_doc = exposed / (2 * papers)
    recall = det["estimate"]                           # assumed to apply to natural errors too
    ppv = []
    for mu in (0.005, 0.02):
        corr_o, mis_o = recall * natural, mu * exp_doc
        corr_p, mis_p = recall * (2 * natural + planted / papers), mu * 2 * exp_doc
        ppv.append({"misleading_per_exposed_number": mu, "real_share_of_flags_originals_only": _r(corr_o / (corr_o + mis_o), 3),
                    "real_share_of_flags_originals_and_copies": _r(corr_p / (corr_p + mis_p), 3)})
    expected = {}
    for label, per in (("4 per paper (protocol 5 text)", 4.0), ("4.33 per paper (frozen mutate.py, v1 held-out)", planted / len(V1_PLANTED_PER_PAPER))):
        expected[label] = {str(p): {str(r): _r(r * per * p, 1) for r in (0.05, 0.115, 0.2)} for p in DESIGNS}
    return {"threshold": t, "min_flags": minf, "scorer_rule_ignoring_clustering": scorer, "alternative_thresholds": thresholds,
            "with_design_effect_floor_0_25": clustered, "development_union_arm": dev,
            "expected_correct_flags_on_planted_errors": expected,
            "illustration_real_share_of_flags": {"assumptions": {"natural_F_per_paper": _r(natural, 2), "planted_per_paper": _r(planted / papers, 2),
                                                                 "exposed_non_F_numbers_per_document": _r(exp_doc, 2), "flag_recall": _r(recall, 3),
                                                                 "source": "DEMONSTRATION_ON_DEVELOPMENT_DATA.json union arm: 26 planted errors (3 flagged), 6 natural F numbers, 93 exposed numbers, 6 papers; natural errors assumed detected as often as planted ones"},
                                                 "rows": ppv}}


# ---------------------------------------------------------------- D1 flag recall and the wording rule

def flag_recall(c2a_rows, demo) -> dict:
    dev_icc = demo["arms"]["union"]["metrics"]["D1_flag_recall_planted"]["icc_estimate"]
    structures = {"4 per paper (protocol 5 text)": (4,), "as frozen mutate.py did in v1 held-out (7,1,4,4,9,1)": V1_PLANTED_PER_PAPER}

    def lb(k, total, deff):
        return S.lower_bound(max(0, math.floor(k / deff)), total / deff)

    def min_k(total, deff, target, strict=False):
        lo, hi = 0, total
        ok = (lambda k: lb(k, total, deff) > target) if strict else (lambda k: lb(k, total, deff) >= target)
        if not ok(hi):
            return None
        while lo < hi:
            mid = (lo + hi) // 2
            if ok(mid):
                hi = mid
            else:
                lo = mid + 1
        return lo

    out = {"development_icc_estimate_union": dev_icc, "rows": []}
    for papers in DESIGNS:
        c2a_bound = next(r for r in c2a_rows if r["papers"] == papers and r["per_paper"] == "10")["by_icc"]["0.25"]["upper_bound_with_events"]["0"]
        for label, pattern in structures.items():
            sizes = sizes_from(pattern, papers)
            total = sum(sizes)
            row = {"papers": papers, "planted": label, "planted_errors": total,
                   "weighted_cluster_size": _r(sum(n * n for n in sizes) / total, 2), "lower_bound_at_observed_recall": {}}
            for icc in (0.25, round(dev_icc, 2)):
                deff = closed_deff(sizes, icc)
                row["lower_bound_at_observed_recall"][str(icc)] = {str(r): _r(lb(round(r * total), total, deff)) for r in ASSUMPTIONS["recall_values"]}
            deff = closed_deff(sizes, 0.25)
            need = {}
            for target in (0.1, 0.15, 0.2, 0.3):
                k = min_k(total, deff, target)
                need[str(target)] = {"detections": k, "observed_recall": _r(k / total, 3),
                                     "chance_if_true_recall": {str(r): _r(1 - S.acceptance_probability(total, k - 1, r), 3)
                                                               for r in (0.115, 0.15, 0.2, 0.25, 0.3, 0.4)}}
            k = min_k(total, deff, c2a_bound, strict=True)
            row["observed_recall_needed_for_lower_bound"] = need
            row["necessary_condition"] = {"c2a_bound_no_flag_10_exposed": c2a_bound, "detections": k, "observed_recall": _r(k / total, 3)}
            out["rows"].append(row)
    out["note"] = ("ICC floor 0.25 unless stated; detections spread evenly so the floor governs; 'chance_if_true_recall' treats "
                   "detections as independent (binomial), which understates the spread when detections cluster by paper")
    return out


# ---------------------------------------------------------------- model calls, retries, cost

def model_calls() -> dict:
    led = {}
    for name in ("prefetch_ledger.day1.json", "prefetch_ledger.gemini_day2.json", "prefetch_ledger.json"):
        d = _load(LEDGERS / name)
        for p in ("gemini", "openrouter"):
            a, f = d["network_calls"][p], d["failures"][p]
            if a:
                ok = a - f
                led.setdefault(p, []).append({"ledger": name, "attempts": a, "failed_attempts": f, "successful": ok,
                                              "prompt_tokens_per_successful_call": _r(d["prompt_tokens"][p] / ok, 0) if ok else None,
                                              "output_tokens_per_successful_call": _r(d["output_tokens"][p] / ok, 0) if ok else None,
                                              "prompt_tokens_per_attempt": _r(d["prompt_tokens"][p] / a, 0),
                                              "seconds_per_attempt": _r(d["seconds"][p] / a, 1)})
    fail = {p: sum(x["failed_attempts"] for x in v) / sum(x["attempts"] for x in v) for p, v in led.items()}
    nem = led["openrouter"][0]                         # day 1: 14 calls, no failure: per call = per attempt
    nem_call = nem["prompt_tokens_per_successful_call"] * NEMOTRON_USD_PER_TOKEN[0] + nem["output_tokens_per_successful_call"] * NEMOTRON_USD_PER_TOKEN[1]
    nem_worst = nem["prompt_tokens_per_successful_call"] * NEMOTRON_USD_PER_TOKEN[0] + MAX_OUTPUT_TOKENS * NEMOTRON_USD_PER_TOKEN[1]
    gem_tokens = max(x["prompt_tokens_per_successful_call"] + x["output_tokens_per_successful_call"] for x in led["gemini"])
    nem_s = nem["seconds_per_attempt"]                 # free tier, 3,000 output tokens per call
    gem_s = max(x["seconds_per_attempt"] for x in led["gemini"])
    sleeps = {k: sum(v) for k, v in SLEEPS.items()}
    designs = []
    for papers in DESIGNS:
        per_provider = papers * DOCUMENTS
        calls = per_provider * MODELS
        sub = ASSUMPTIONS["nemotron_sub_cap_usd"][str(papers)]
        gem_cap = CAP_USD[papers] - sub
        pc = {}
        for q in ASSUMPTIONS["per_call_success_grid"]:
            need = math.ceil(0.9 * papers)
            pc[str(q)] = _r(1 - S.acceptance_probability(papers, need - 1, q ** 4), 3)
        qg, qn = 1 - fail["gemini"] ** ATTEMPTS, 1 - fail["openrouter"] ** ATTEMPTS
        designs.append({
            "papers": papers, "calls": calls, "calls_per_provider": per_provider, "attempts_worst_case": calls * ATTEMPTS,
            "ledger_attempt_budget_needed_per_provider": per_provider * ATTEMPTS, "ledger_default_budget": {"gemini": 60, "openrouter": 40},
            "worst_case_wall_hours_per_provider_one_at_a_time": _r(per_provider * (ATTEMPTS * TIMEOUT_S + sleeps["quota_429"]) / 3600, 1),
            "free_tier_days_for_gemini_calls_at_20_a_day": math.ceil(per_provider / ASSUMPTIONS["gemini_free_tier_successful_calls_per_day"]),
            "nemotron_usd": {"measured_sizes": _r(per_provider * nem_call, 2), "measured_sizes_every_call_four_attempts": _r(per_provider * ATTEMPTS * nem_call, 2),
                             "every_attempt_full_16384_output_tokens": _r(per_provider * ATTEMPTS * nem_worst, 2)},
            "cap_usd": CAP_USD[papers], "nemotron_sub_cap_usd": sub, "gemini_sub_cap_usd": gem_cap,
            "gemini_highest_average_usd_per_million_tokens_within_sub_cap": {
                "every_call_once": _r(gem_cap / (per_provider * gem_tokens / 1e6), 2),
                "every_call_four_attempts": _r(gem_cap / (per_provider * ATTEMPTS * gem_tokens / 1e6), 2)},
            "chance_primary_complete_share_at_least_90_percent_by_per_call_success": pc,
            "v1_failure_rates_if_independent": {"per_call_success_gemini": _r(qg, 4), "per_call_success_nemotron": _r(qn, 6),
                                                "per_paper_complete": _r(qg ** 2 * qn ** 2, 4),
                                                "chance_share_at_least_90_percent": _r(1 - S.acceptance_probability(papers, math.ceil(0.9 * papers) - 1, qg ** 2 * qn ** 2), 3)},
            "if_gemini_answers_only_20_calls_a_day_and_calls_are_not_paced": {"successful_gemini_calls_first_day": 20,
                                                                             "primary_complete_share_at_most": _r(min(1, 20 / per_provider), 3)},
            "sequential_hours_at_v1_latency": {"nemotron": _r(per_provider * nem_s / 3600, 1), "gemini": _r(per_provider * gem_s / 3600, 1)},
        })
    return {"v1_ledgers": led, "v1_failed_attempt_share": {p: _r(v, 3) for p, v in fail.items()},
            "backoff_seconds_per_call_worst_case": sleeps, "timeout_seconds_per_attempt": TIMEOUT_S,
            "nemotron_usd_per_call": {"measured_sizes": _r(nem_call, 5), "full_output": _r(nem_worst, 5)},
            "gemini_tokens_per_successful_call_highest_ledger_mean": gem_tokens, "designs": designs}


# ---------------------------------------------------------------- kernel, replay

def kernel(design) -> dict:
    perf = _load(PERF)
    runs = perf["runs"]
    by_stat = {}
    for r in runs:
        by_stat.setdefault(r["statistic"], []).append(r)
    stats = {}
    for s, rs in by_stat.items():
        rs.sort(key=lambda r: r["rows"])
        first_fail = next((r for r in rs if not r["kernel_accepted"]), None)
        passed = [r for r in rs if r["kernel_accepted"] and (first_fail is None or r["rows"] < first_fail["rows"])]
        last = passed[-1] if passed else None
        why = None
        if first_fail:
            w = first_fail["why_not"]
            why = "recursion depth" if "recursion depth" in w else "out of memory" if ("bad_alloc" in w or "out of memory" in w) else w[:40]
        stats[s] = {"largest_rows_accepted": last["rows"] if last else None, "bytes": last["bytes"] if last else None,
                    "seconds": last["seconds"] if last else None, "peak_gb": _r(last["peak_rss_mb"] / 1024, 2) if last else None,
                    "first_failure_rows": first_fail["rows"] if first_fail else None,
                    "first_failure_peak_gb": _r(first_fail["peak_rss_mb"] / 1024, 2) if first_fail else None, "first_failure": why}
    accepted = [r for r in runs if r["kernel_accepted"]]
    all_ok = min(v["bytes"] for v in stats.values() if v["bytes"] is not None)
    worst_ok = max(r["peak_rss_mb"] for r in accepted) / 1024
    worst_any = max(r["peak_rss_mb"] for r in runs) / 1024
    replay = []
    for d in design["designs"]:
        h = d["costs"]["replay_runner_hours_C4"]
        shards = {}
        for n in (4, 6, 8, 12):
            shards[str(n)] = {str(f): _r(h * f / n + ASSUMPTIONS["replay_setup_hours_per_job"], 2) for f in ASSUMPTIONS["replay_underestimate_factors"]}
        replay.append({"papers": d["papers"], "runner_hours": h, "fewest_jobs_under_6_h": math.ceil(h / 6),
                       "fewest_jobs_under_6_h_if_twice_the_estimate": math.ceil(2 * h / 6), "hours_per_job_by_jobs_and_underestimate": shards})
    return {"measured": {"cpus": perf["cpus"], "memory_limit_gb_per_process": perf["memory_limit_gb_per_lean_process"],
                         "time_limit_seconds": perf["time_limit_seconds"], "note": perf["note"]},
            "by_statistic": stats, "largest_bytes_at_which_every_statistic_was_accepted": all_ok,
            "highest_peak_gb_among_accepted_runs": _r(worst_ok, 2), "highest_peak_gb_any_run": _r(worst_any, 2),
            "two_workers_two_highest_accepted_peaks_gb": _r(2 * worst_ok, 2), "two_workers_two_failing_median_runs_gb": _r(2 * worst_any, 2),
            "reference_machine_gb": 16, "c7_peak_limit_gb": 8, "replay": replay}


# ---------------------------------------------------------------- people

def adjudication() -> dict:
    a = ASSUMPTIONS["adjudication"]
    per_paper = [a["minutes_reading_per_paper"][i] + a["numbers_per_paper"] * a["minutes_per_number"][i] for i in (0, 1)]
    out = {"minutes_per_paper_per_adjudicator": per_paper, "designs": []}
    for papers in DESIGNS:
        each = [papers * m / 60 for m in per_paper]
        resolver = [papers * a["numbers_per_paper"] * s * a["resolver_minutes_per_disagreement"] / 60 for s in a["disagreement_share"]]
        six = [e / 3 for e in each]
        out["designs"].append({"papers": papers, "hours_each_two_adjudicators_covering_all": [_r(x, 1) for x in each],
                               "person_hours_two_labels_per_number": [_r(2 * x, 1) for x in each], "resolver_hours": [_r(x, 1) for x in resolver],
                               "hours_each_six_adjudicators_two_per_context": [_r(x, 1) for x in six],
                               "weeks_two_adjudicators_by_hours_per_week": {str(w): [_r(x / w, 1) for x in each] for w in ASSUMPTIONS["adjudicator_hours_per_week"]},
                               "weeks_six_adjudicators_by_hours_per_week": {str(w): [_r(x / w, 1) for x in six] for w in ASSUMPTIONS["adjudicator_hours_per_week"]}})
    prelim_numbers, prelim_papers = 30, 3
    out["preliminary_round_hours_each_by_these_rates"] = [_r((prelim_papers * a["minutes_reading_per_paper"][i] + prelim_numbers * a["minutes_per_number"][i]) / 60, 2) for i in (0, 1)]
    return out


def usability() -> dict:
    rows = []
    for n in (5, 8, 10):
        need = math.ceil(0.8 * n)
        one = {str(p): _r(1 - S.acceptance_probability(n, need - 1, p), 3) for p in (0.7, 0.8, 0.9, 0.95)}
        rows.append({"participants": n, "correct_needed": need, "chance_one_question_passes": one,
                     "chance_all_four_questions_pass_if_independent": {k: _r(v ** 4, 3) for k, v in one.items()},
                     "lower_bound_at_threshold": _r(S.lower_bound(need, n), 3), "lower_bound_all_correct": _r(S.lower_bound(n, n), 3)})
    return {"rows": rows}


def screening() -> dict:
    rows = []
    for y in ASSUMPTIONS["screening_yields"]:
        rows.append({"yield": y,
                     "chance_20_within_300": _r(1 - S.acceptance_probability(300, 19, y), 3),
                     "chance_40_within_600": _r(1 - S.acceptance_probability(600, 39, y), 3),
                     "chance_40_within_300": _r(1 - S.acceptance_probability(300, 39, y), 3),
                     "chance_at_least_20_within_600": _r(1 - S.acceptance_probability(600, 19, y), 3),
                     "expected_screened_for_40": _r(40 / y, 0)})
    effort = {str(m): {"cap_300_all_contexts_hours": _r(3 * 300 * m / 60, 0), "cap_600_all_contexts_hours": _r(3 * 600 * m / 60, 0)}
              for m in ASSUMPTIONS["screening_minutes_per_candidate"]}
    sizes = {}
    for n in (60, 75, 90, 105, 120):
        allowed = S.max_events_for_bound(n, 0.05)
        sizes[str(n)] = {"c2b_affected_allowed": allowed,
                         "chance_of_passing_at_1_percent": _r(S.acceptance_probability(n, allowed, 0.01), 3)}
    return {"rows": rows, "worst_case_screening_hours": effort, "intermediate_sizes": sizes}


def zero_event_rules() -> dict:
    c6 = []
    for papers in DESIGNS:
        for v in ASSUMPTIONS["decided_verdicts_per_paper_any_arm"]:
            c6.append({"papers": papers, "decided_verdicts_per_paper": v,
                       "chance_no_event": {str(a): _r((1 - a) ** (v * papers), 3) for a in ASSUMPTIONS["chance_a_decided_verdict_falls_on_an_ambiguous_number"]}})
    scope = []
    for papers in DESIGNS:
        for pi in ASSUMPTIONS["per_paper_rate_of_a_misleading_flag"]:
            s = (1 - pi) ** (papers // 3)
            allowed = S.max_events_for_bound(papers, 0.05)
            scope.append({"papers": papers, "per_paper_rate": pi, "c2b_chance_of_passing": _r(S.acceptance_probability(papers, allowed, pi), 3),
                          "chance_all_three_contexts_in_scope": _r(s ** 3, 3), "chance_at_least_two_in_scope": _r(s ** 3 + 3 * s * s * (1 - s), 3),
                          "expected_contexts_in_scope": _r(3 * s, 2)})
    c1_context = {str(n): math.floor(0.02 * n + 1e-9) for n in (25, 40, 50, 75, 100, 150, 200)}
    return {"C6_no_decided_verdict_on_an_ambiguous_number": c6, "scope_rule_any_misleading_flag_excludes_its_context": scope,
            "scope_rule_C1_unsupported_confirmations_allowed_per_context_by_its_confirmations": c1_context}


def icc_evidence(demo) -> dict:
    out = {}
    for arm, body in demo["arms"].items():
        m = body["metrics"]
        out[arm] = {k: {"events": m[k]["events"], "opportunities": m[k]["opportunities"], "icc_estimate": m[k]["icc_estimate"]}
                    for k in ("C3_coverage", "D1_flag_recall_planted", "C1_unsupported_among_confirmations", "C2a_misleading_per_exposed_number")}
    return out


def feasibility(mc: dict) -> dict:
    """What the preliminary study would cost, and what its measurements would imply at 120 papers
    (DECISION_PACKAGE.md 14).  The pilot package: the prepared v1_discrepancies package (2 to 3 h each,
    adjudication plan section 9) and the six held-out v1 papers at the plan's rates; the smoke run: the
    eight development papers that have a planted-error copy, two documents each, one call per model."""
    a = ASSUMPTIONS["adjudication"]
    per_paper_h = [(a["minutes_reading_per_paper"][i] + a["numbers_per_paper"] * a["minutes_per_number"][i]) / 60 for i in (0, 1)]
    each = [(2, 3)[i] + 6 * per_paper_h[i] for i in (0, 1)]
    resolver = [6 * a["numbers_per_paper"] * sh * a["resolver_minutes_per_disagreement"] / 60 for sh in a["disagreement_share"]]
    pilot = {"hours_each_adjudicator": [_r(x, 2) for x in each], "resolver_hours": [_r(x, 2) for x in resolver],
             "person_hours_two_adjudicators_and_resolver": [_r(2 * each[i] + resolver[i], 1) for i in (0, 1)]}
    smoke = {"papers": 8, "documents": 16, "calls": 32, "nemotron_calls": 16,
             "nemotron_usd_at_measured_sizes": _r(16 * mc["nemotron_usd_per_call"]["measured_sizes"], 2)}
    adj = {str(m): {"hours_each_two_adjudicators": _r(120 * m / 60, 1), "person_hours": _r(2 * 120 * m / 60, 1),
                    "hours_each_six_adjudicators": _r(120 * m / 60 / 3, 1)} for m in ASSUMPTIONS["feasibility_minutes_per_paper"]}
    scr = {str(n): {str(mi): _r(3 * n * mi / 60, 0) for mi in ASSUMPTIONS["screening_minutes_per_candidate"]}
           for n in ASSUMPTIONS["feasibility_screening_candidates_per_context"]}
    return {"pilot_adjudication": pilot, "smoke_run_configuration_P": smoke,
            "adjudication_at_120_papers_by_measured_minutes_per_paper": adj,
            "screening_hours_three_contexts_by_candidates_per_context_and_minutes_each": scr,
            "plan_rates_minutes_per_paper": [a["minutes_reading_per_paper"][i] + a["numbers_per_paper"] * a["minutes_per_number"][i] for i in (0, 1)]}


def tables() -> dict:
    crit, design, demo = _load(CRITERIA), _load(DESIGN), _load(DEMO)
    cl = claim_level(crit)
    return {"status": "synthetic operating characteristics for the owner's decisions; nothing sampled, nothing run, no network",
            "icc_floor_proposed": crit["assumptions"]["icc_floor"], "assumptions": ASSUMPTIONS,
            "claim_level_tolerance": cl, "C2_a_and_b_together": c2_joint(crit), "C2a_original_and_copy_counted_twice": duplicate_copies(),
            "C2c": c2c(crit, demo), "D1_flag_recall": flag_recall(cl["C2a"], demo), "model_calls": (mc := model_calls()),
            "kernel_and_replay": kernel(design), "adjudication": adjudication(), "usability": usability(),
            "screening": screening(), "zero_event_rules": zero_event_rules(), "development_icc_estimates": icc_evidence(demo),
            "feasibility_study": feasibility(mc)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out")
    args = ap.parse_args(argv)
    text = json.dumps(tables(), indent=1)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
