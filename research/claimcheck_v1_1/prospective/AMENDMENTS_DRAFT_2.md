# Protocol draft 2: what changed and why

The owner's decision on A1 to A3 was "amend before approval" (2026-11-15), with seven points. Each
row says what was changed, where, and why. **Draft 2 is not approved and nothing has been run.** No
prospective paper has been sampled, retrieved, inspected, labelled or scored.

## 1.1 Sampling consistency

| Change | Where | Reason |
| --- | --- | --- |
| minimum per context 15 → **20** in the criteria, equal to the protocol | `criteria.json` | draft 1 disagreed with itself |
| a context with fewer than 20 eligible papers is **not topped up** from another; C1 to C3 are then not evaluable | protocol 3, `criteria.json` | topping up would change the population after seeing which contexts are hard |
| screening limit 150 → 300 candidates per context | protocol 3 | 20 eligible from 150 was optimistic (v1 needed about 3 candidates per usable paper) |
| new exclusion **E6: one paper per author group** | protocol 4 | every bound treats papers as independent |
| power analysis that accounts for clustering, with tables | protocol 10, `stats.power_table` | the owner asked whether 60 is enough |
| **recommendation: 120 papers (40 per context)**; the sample is not reduced below 60 | protocol 10 | at 60 papers C2 tolerates no misleading flag at all: a system with a true rate of 1 % of papers fails 45 % of the time |

## 1.2 Model calls

| Change | Where | Reason |
| --- | --- | --- |
| 120 → **240 calls** for 60 papers (480 for 120) | protocol 2 and 13 | two documents per paper; draft 1 forgot the planted-error copies |
| retry policy stated as the frozen code implements it | protocol 2 | draft 2's first wording said unparseable answers were repeated; the code does not do that |
| **primary-complete** rule: both models answered for both documents; below 90 % of papers the primary analysis is not evaluable | protocol 2, `criteria.json` | v1's Gemini free tier refused about half of the attempts |
| availability checked, quotas and the Gemini price not verifiable without use, tokens and costs measured | `MODEL_ACCESS.md` | the owner asked not to assume earlier conditions still hold |

## 1.3 Misleading refutations

| Change | Where | Reason |
| --- | --- | --- |
| three denominators, **all three in C2**: per exposed number (C2a), per paper (C2b), among flags (C2c); the denominator of all T, N and A numbers is still reported | protocol 7 and 9, `criteria.json`, `score.py` | each answers a different question; draft 1's single denominator could be inflated by a proposer that proposes little |
| C2c: misleading share of flags, upper bound ≤ 50 %, at least 5 flags or not evaluable | same | the weakest requirement under which a flag is an alert; not fitted to results |
| fixed vocabulary: **mathematical mismatch**, **discrepancy for review**, **scientific error** (never asserted by the system) | protocol 7 | the owner's requirement that no exported word implies a paper is wrong |
| scope rule: a context with any misleading flag is outside a pilot | protocol 9 | a pooled pass must not cover a context where the harm occurred |

## 1.4 Useful discrepancy detection

| Change | Where | Reason |
| --- | --- | --- |
| **D1**: flag recall (planted and natural errors separately) and "mismatch shown" (what a reviewer reading the review list could find), with paper-clustered intervals | protocol 9a, `criteria.json`, `score.py` | development showed detection falling from 13 to 3 and 11 to 2 of 41 |
| **no pass mark**, and the reason stated | protocol 9a | no evidence fixes a level at which recall becomes useful; any number now would be arbitrary or fitted to the 5 to 8 % seen in development |
| a necessary condition (recall on planted errors above the misleading rate) and a **wording rule**: below an owner-set level the pilot is "confirmation only" and the absence of a flag is stated to carry no information | protocol 9a, `criteria.json` field `wording_rule` (empty) | lets the owner decide what may be claimed, before the run |

## 1.5 Ambiguous adjudications

| Change | Where | Reason |
| --- | --- | --- |
| primary analysis is the unfavourable one in each metric: a decided verdict on an A number is an error; A numbers count in C2's denominators; A numbers count **against** coverage (C3 = correct confirmations / (T + A)) | protocol 7, `criteria.json`, `score.py` | excluding hard cases must not raise apparent reliability |
| more than 20 % A numbers: labels cannot carry C1 to C3 (not evaluable) | `criteria.json` C6, `score.py` | |
| sensitivity: A as T, as N, removed; either adjudicator's "error" before resolution | protocol 11 | |
| tests: calling hard numbers ambiguous lowers coverage; 25 % ambiguous makes everything not evaluable | `tests/test_score_draft2.py` | |

## 1.6 Contexts and generalisation

| Change | Where | Reason |
| --- | --- | --- |
| what may generalise across contexts (properties proved for every input: a decided verdict implies the kernel result, fail-closed behaviour, replay) and what may not (coverage, wording rules, units, row semantics, hence C1 to C3) | protocol 11 | |
| arms never pooled: model proposals, data-aware search, adversary | protocol 11 | |
| primary arm, secondary comparisons, ICC floor, wording level, sensitivity list fixed before the run | protocol 11 | |

## 1.7 Statistical integrity

| Found in draft 1 | Change | Evidence |
| --- | --- | --- |
| with no event the ICC estimate is 0, so the "conservative" bound equalled the bound that ignores clustering, exactly when it matters | design effect uses max(ICC, **0.25**), an assumption for the owner to confirm; bounds for ICC 0, 0.1, 0.25, 0.5, 1 always reported | `stats.py`, test `test_zero_events_are_not_read_as_no_clustering_when_a_floor_is_assumed` |
| `lower_bound` rounded a fractional sample size down, the anti-conservative direction for a lower bound | rounds up | test `test_lower_bound_is_the_mirror_image_and_rounds_conservatively` |
| the bootstrap's "upper limit" is the 97.5 % point of a two-sided interval; degenerate without events; too short with one or two events | stated; criteria rest on the exact bounds | protocol 10 |
| the evaluator had never been checked against anything | independent oracle: exact rational binomial CDF, ICC from raw 0/1 data by ANOVA, closed forms, adversarial cluster shapes, orderings that must hold; evaluator tested on synthetic fixtures | `tests/test_stats_oracle.py` (9 tests), `tests/test_score_draft2.py` (11 tests) |
| the tolerance of C1 for one unsupported confirmation depends on how confirmations cluster (passes at 3 per paper, fails at 4) | stated | protocol 10, test `test_one_unsupported_confirmation_and_cluster_size` |
| results could be looked at as adjudication forms arrive | no result is inspected before every form is returned and sealed | protocol 11 |

## Also changed

* The decoy limit's "2 %" is a local density, not a bound on coincidental confirmation by a chooser who
  has seen the data. The proved bound is 2/51 ≈ 3.9 % (protocol 2; owner decision A6).

## Additions and corrections of 2026-11-16 (still draft 2, still for review)

| What | Change | Where |
| --- | --- | --- |
| the 120-paper design and its costs (owner: continue preparing) | new section: 40 per context, screening cap 600 per context, a fallback to the 60-paper design fixed in advance, what each criterion gains, calls, tokens, money, kernel and replay time, adjudication hours | protocol 10a; `design_120.py`, `DESIGN_120.json`, test `tests/test_design_120.py`; `criteria.json` (larger-sample option) |
| C2a figures at 60 papers | draft 2 printed 2.2 / 2.0 / 1.9 % for 5 / 8 / 10 exposed numbers per paper; `stats.py` gives 2.0 / 1.7 / 1.6 % (and 2.2 % for 4); conclusion unchanged: borderline at 60, met only with no misleading flag and about five or more exposed numbers per paper | protocol 10 |
| decoy rule (owner decision A6: retain, correct the wording) | the description now states the proved bound's model, its assumptions and the effect of several supporting reading sets (`max(1, s) × 2` per 51); the rule itself is unchanged; alternatives only as exploratory comparisons on development data | protocol 2, 11 |
| cost cap | 30 USD proposed for 120 papers; to be enforced by the calling code | protocol 13 |
* `DEMONSTRATION_ON_DEVELOPMENT_DATA.json` regenerated with the draft-2 scorer. Still development data
  only; every criterion "not evaluable". Not an evaluation of v1.1.
* `dev/evaluate.py` records which labelled numbers received at least one proposal ("exposed"), needed
  for C2a. It does not change any count that was reported before.

## Decisions draft 2 leaves to the owner

1. ICC floor 0.25 (or another value).
2. 60 or 120 papers.
3. Flag-recall level for the wording rule (empty; 20 % suggested as a judgement).
4. C2c threshold 50 %.
5. Screening limit 300 per context (600 if 120 papers), and the fallback of protocol 10a.
6. ~~Decoy rule (A6)~~: decided 2026-11-16, the rule is retained with corrected wording.
7. Model configuration F or P, and the identifiers (`MODEL_ACCESS.md`).
