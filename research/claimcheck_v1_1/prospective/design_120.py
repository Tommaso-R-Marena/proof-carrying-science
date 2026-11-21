"""The 60- and 120-paper designs side by side: what each can show, and what each costs (protocol 10a, 13).

    python -m research.claimcheck_v1_1.prospective.design_120 [--out DESIGN_120.json]

Draft 3: every tolerance is the scorer's own rule (``score.judge``): bounds on the effective sample,
events and opportunities both divided by the design effect, C1's three conditions jointly, C2a and
C2b jointly.  ``tests/test_design_120.py`` checks each row at its boundary against
``stats.proportion`` (bootstrap included) and the scorer's rule functions.  Cost figures are
arithmetic on v1 measurements and on the adjudication plan's rates; they are assumptions, not
measurements of this evaluation.  Nothing here reads or samples a prospective paper.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from . import stats as S

CRITERIA = Path(__file__).with_name("criteria.json")
ICC_FLOOR = 0.25
CONTEXTS = 3
MODELS = 2
DOCUMENTS_PER_PAPER = 2            # the original and the planted-error copy
ATTEMPTS_PER_CALL = 4              # one call and up to three repeats (protocol 2)
# per SUCCESSFUL call, lowest and highest ledger means in v1 (claimcheck_v1/benchmark/results/heldout/prefetch_ledger*.json;
# checked against the ledgers by tests/test_design_120.py)
PROMPT_TOKENS = (2088, 5160)
OUTPUT_TOKENS = (134, 3032)
NEMOTRON_USD_PER_120_CALLS = (1.2, 5.0)   # protocol 13: estimate, and every call repeated three times
KERNEL_HOURS_PER_60_PAPERS = 10
# adjudication plan, section 4 (assumptions): 10 to 20 min reading + 25 numbers at 1 to 1.5 min
ADJUDICATOR_MINUTES_PER_PAPER = (10 + 25 * 1, 20 + 25 * 1.5)
RESOLVER_HOURS_PER_PAPER = (25 * 0.15 * 3 / 60, 25 * 0.25 * 3 / 60)
V1_SCREENING_YIELD = (8, 18)       # v1 held-out funnel: 8 eligible of 18 screened (one context)


def _criteria() -> dict:
    return json.loads(CRITERIA.read_text(encoding="utf-8"))["levels"]["supervised_external_pilot"]["criteria"]


def _bounds(clusters, floor=ICC_FLOOR):
    """The scorer's design-effect bound without its bootstrap (the bootstrap is checked by the tests)."""
    k, n = sum(c[0] for c in clusters), sum(c[1] for c in clusters)
    deff = S.design_effect(clusters, floor)
    return S.upper_bound(math.ceil(k / deff), n / deff), deff


def _sizes(pattern, papers):
    return [pattern[i % len(pattern)] for i in range(papers)]


def spread(sizes, k):
    return [(1 if i < k else 0, n) for i, n in enumerate(sizes)]


def c1_allowed(papers: int, pattern) -> dict:
    """Unsupported confirmations, at most one per paper, accepted by C1's three conditions jointly."""
    k1 = _criteria()["C1_unsupported_confirmations"]
    sizes = _sizes(pattern, papers)

    def why_not(k):
        if k / sum(sizes) > k1["max_estimate"]:
            return "estimate"
        if _bounds(spread(sizes, k))[0] > k1["max_conservative_upper_bound"]:
            return "claim-level bound"
        if S.upper_bound(k, papers) > k1["max_paper_level_upper_bound"]:
            return "paper-level bound"
        return None
    k = -1
    while k + 1 <= papers and why_not(k + 1) is None:
        k += 1
    return {"allowed": k, "binding_at_one_more": why_not(k + 1) if k + 1 <= papers else None}


def c2a_allowed(papers: int, per_paper: int) -> int:
    """Misleading flags, at most one per paper, accepted by C2a alone (-1: not even none)."""
    k2a = _criteria()["C2_misleading_refutations"]["a_per_exposed_claim"]
    sizes = [per_paper] * papers
    k = -1
    while k + 1 <= papers and (k + 1) / sum(sizes) <= k2a["max_estimate"] and _bounds(spread(sizes, k + 1))[0] <= k2a["max_conservative_upper_bound"]:
        k += 1
    return k


def c2_joint(papers: int, per_paper: int) -> dict:
    """C2a and C2b together: flags in different papers each count against C2b; flags in one paper
    raise C2a's estimated ICC."""
    k2 = _criteria()["C2_misleading_refutations"]
    affected = S.max_events_for_bound(papers, k2["b_per_paper"]["max_paper_level_upper_bound"])
    one = 0
    if affected >= 1:
        while True:
            cl = [(one + 1 if i == 0 else 0, per_paper) for i in range(papers)]
            if (one + 1) / (papers * per_paper) > k2["a_per_exposed_claim"]["max_estimate"] or \
                    _bounds(cl)[0] > k2["a_per_exposed_claim"]["max_conservative_upper_bound"]:
                break
            one += 1
    alone = c2a_allowed(papers, per_paper)
    return {"affected_papers_allowed": affected, "flags_allowed_spread": max(0, min(affected, alone)) if alone >= 0 else -1,
            "flags_allowed_all_in_one_paper": one if alone >= 0 else -1}


def design(papers: int, screening_cap: int) -> dict:
    per_context = papers // CONTEXTS
    c2b_allowed = S.max_events_for_bound(papers, 0.05)
    c1p_allowed = S.max_events_for_bound(papers, 0.10)
    calls = papers * MODELS * DOCUMENTS_PER_PAPER

    def neff(per):
        return papers * per / (1 + (per - 1) * ICC_FLOOR)
    return {
        "papers": papers, "papers_per_context": per_context, "screening_cap_per_context": screening_cap,
        "lowest_screening_yield_that_fills_a_context": round(per_context / screening_cap, 3),
        "screened_per_context_at_the_v1_yield": round(per_context * V1_SCREENING_YIELD[1] / V1_SCREENING_YIELD[0]),
        "statistics": {
            "C2b_affected_papers_allowed": c2b_allowed,
            "C2b_chance_of_passing_by_true_paper_rate": {str(r): round(S.acceptance_probability(papers, c2b_allowed, r), 3)
                                                         for r in (0.005, 0.01, 0.02, 0.05)},
            "C1_paper_level_affected_papers_allowed": c1p_allowed,
            "C2a_by_exposed_numbers_per_paper": {
                str(m): {"bound_no_flag": round(_bounds(spread([m] * papers, 0))[0], 4), "bound_one_flag": round(_bounds(spread([m] * papers, 1))[0], 4),
                         "flags_allowed_alone": c2a_allowed(papers, m), **c2_joint(papers, m)} for m in (4, 5, 8, 10)},
            "C2a_lowest_possible_bound_no_flag": round(S.upper_bound(0, papers / ICC_FLOOR), 4),
            "C1_unsupported_confirmations_allowed_by_confirmations_per_paper": {
                "2.5": c1_allowed(papers, (2, 3)), "4": c1_allowed(papers, (4,)), "5": c1_allowed(papers, (5,))},
            "C3_lower_bound_at_estimate_25_percent_by_numbers_per_paper": {
                str(m): round(S.lower_bound(round(0.25 * neff(m)), neff(m)), 4) for m in (5, 8, 10)},
            "per_context_paper_level_bound_with_no_event": round(S.upper_bound(0, per_context), 4),
        },
        "costs": {
            "model_calls": calls,
            "http_requests_worst_case": calls * ATTEMPTS_PER_CALL,
            "prompt_tokens_million": [round(calls * t / 1e6, 2) for t in PROMPT_TOKENS],
            "output_tokens_million": [round(calls * t / 1e6, 2) for t in OUTPUT_TOKENS],
            "nemotron_usd": [round(u * (calls / MODELS) / 120, 1) for u in NEMOTRON_USD_PER_120_CALLS],
            "gemini_usd": "unknown: the price could not be read from the provider's listing (MODEL_ACCESS.md)",
            "kernel_hours_reference_machine": KERNEL_HOURS_PER_60_PAPERS * papers / 60,
            "replay_runner_hours_C4": KERNEL_HOURS_PER_60_PAPERS * papers / 60,
            "replay_jobs": 6 if papers == 60 else 12,
            "adjudication_hours_per_adjudicator_covering_all_papers": [round(m * papers / 60, 1) for m in ADJUDICATOR_MINUTES_PER_PAPER],
            "adjudication_person_hours_two_labels_per_number": [round(2 * m * papers / 60, 1) for m in ADJUDICATOR_MINUTES_PER_PAPER],
            "resolver_hours": [round(h * papers, 1) for h in RESOLVER_HOURS_PER_PAPER],
        },
    }


def tables() -> dict:
    return {"status": "draft 3: computed for the owner's choice between designs with the scorer's own rule; nothing sampled, nothing run",
            "icc_floor": ICC_FLOOR, "assumptions": {
                "equal_cluster_sizes": "except C1 at 2.5 per paper (2 and 3 alternating)", "events": "at most one per paper unless stated",
                "attempts_per_call": ATTEMPTS_PER_CALL, "prompt_tokens_per_successful_call": PROMPT_TOKENS,
                "output_tokens_per_successful_call": OUTPUT_TOKENS, "kernel_hours_per_60_papers": KERNEL_HOURS_PER_60_PAPERS,
                "adjudicator_minutes_per_paper": ADJUDICATOR_MINUTES_PER_PAPER,
                "adjudication_figures": "assumptions from the adjudication plan, not measurements"},
            "designs": [design(60, 300), design(120, 600)]}


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
