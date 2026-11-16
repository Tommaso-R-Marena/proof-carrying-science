"""The 60- and 120-paper designs side by side: what each can show, and what each costs (protocol 10a, 13).

    python -m research.claimcheck_v1_1.prospective.design_120 [--out DESIGN_120.json]

Every statistical figure comes from ``stats.py``, the module the scorer uses.  Cost figures are
arithmetic on the per-call and per-paper figures stated in protocol 13 and in the adjudication plan;
they are assumptions and v1 measurements, not measurements of this evaluation.  Nothing here reads
or samples a prospective paper.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from . import stats as S

ICC_FLOOR = 0.25
CONTEXTS = 3
MODELS = 2
DOCUMENTS_PER_PAPER = 2            # the original and the planted-error copy
ATTEMPTS_PER_CALL = 4              # one call and up to three retries after a 429 (40, 80 and 120 s)
PROMPT_TOKENS = (2600, 4400)       # per call, measured in v1
OUTPUT_TOKENS = (300, 3000)
NEMOTRON_USD_PER_120_CALLS = (1.2, 5.0)   # protocol 13: estimate, and every call repeated three times
KERNEL_HOURS_PER_60_PAPERS = 10
ADJUDICATOR_HOURS_PER_PAPER = (35 / 60, 55 / 60)      # adjudication plan, section 4 (assumptions)
RESOLVER_HOURS_PER_PAPER = (11 / 60, 19 / 60)
V1_SCREENING_YIELD = (8, 18)       # v1 held-out funnel: 8 eligible of 18 screened (one context)


def neff(papers: int, per_paper: float, icc: float = ICC_FLOOR) -> float:
    """Effective sample with equal cluster sizes.  Unequal sizes raise the design effect: the
    weighted cluster size is mean + variance / mean."""
    return papers * per_paper / (1 + (per_paper - 1) * icc)


def design(papers: int, screening_cap: int) -> dict:
    per_context = papers // CONTEXTS
    c2b_allowed = S.max_events_for_bound(papers, 0.05)
    c1p_allowed = S.max_events_for_bound(papers, 0.10)
    calls = papers * MODELS * DOCUMENTS_PER_PAPER
    return {
        "papers": papers, "papers_per_context": per_context, "screening_cap_per_context": screening_cap,
        "lowest_screening_yield_that_fills_a_context": round(per_context / screening_cap, 3),
        "screened_per_context_at_the_v1_yield": round(per_context * V1_SCREENING_YIELD[1] / V1_SCREENING_YIELD[0]),
        "statistics": {
            "C2b_affected_papers_allowed": c2b_allowed,
            "C2b_chance_of_passing_by_true_paper_rate": {str(r): round(S.acceptance_probability(papers, c2b_allowed, r), 3)
                                                         for r in (0.005, 0.01, 0.02, 0.05)},
            "C1_paper_level_affected_papers_allowed": c1p_allowed,
            "C2a_upper_bound_by_exposed_numbers_per_paper": {
                str(m): {"no_flag": round(S.upper_bound(0, neff(papers, m)), 4), "one_flag": round(S.upper_bound(1, neff(papers, m)), 4),
                         "flags_allowed": S.max_events_for_bound(int(neff(papers, m)), 0.02)} for m in (4, 5, 8, 10)},
            "C2a_lowest_possible_bound_no_flag": round(S.upper_bound(0, papers / ICC_FLOOR), 4),
            "C1_unsupported_confirmations_allowed_by_confirmations_per_paper": {
                str(c): S.max_events_for_bound(int(neff(papers, c)), 0.05) for c in (2.5, 3, 4, 5)},
            "C3_lower_bound_at_estimate_25_percent_by_numbers_per_paper": {
                str(m): round(S.lower_bound(round(0.25 * neff(papers, m)), neff(papers, m)), 4) for m in (5, 8, 10)},
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
            "adjudication_hours_per_adjudicator_covering_all_papers": [round(h * papers) for h in ADJUDICATOR_HOURS_PER_PAPER],
            "adjudication_person_hours_two_labels_per_number": [round(2 * h * papers) for h in ADJUDICATOR_HOURS_PER_PAPER],
            "resolver_hours": [round(h * papers) for h in RESOLVER_HOURS_PER_PAPER],
        },
    }


def tables() -> dict:
    return {"status": "computed for the owner's choice between designs; nothing sampled, nothing run",
            "icc_floor": ICC_FLOOR, "assumptions": {
                "equal_cluster_sizes": True, "attempts_per_call": ATTEMPTS_PER_CALL, "prompt_tokens_per_call": PROMPT_TOKENS,
                "output_tokens_per_call": OUTPUT_TOKENS, "kernel_hours_per_60_papers": KERNEL_HOURS_PER_60_PAPERS,
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
