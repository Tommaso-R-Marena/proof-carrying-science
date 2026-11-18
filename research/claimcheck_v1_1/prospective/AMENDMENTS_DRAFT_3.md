# Protocol draft 3: the nineteen inconsistencies of draft 2, resolved

**Draft 3 is UNAPPROVED.** Nothing has been sampled, retrieved, screened, labelled, scored or run
for the prospective evaluation. There have been no model calls and no recruitment. Nothing under
`research/claimcheck_v1/` was changed, and no frozen digest was changed.

Each row below has four parts:

* the inconsistency found in draft 2 ([`DECISION_PACKAGE.md`](DECISION_PACKAGE.md), section 12);
* what draft 3 does about it;
* where the change is;
* the test that checks it.

Tests are in `research/claimcheck_v1_1/tests/`. Where a fix would have needed frozen v1 behaviour
to change, the row says whether the protocol now describes the frozen code or a v1.1 wrapper was
added.

| # | Draft 2 | Draft 3 | Files | Test |
| --- | --- | --- | --- | --- |
| 1 | Protocol 5 said `mutate.py` uses the seed `prospective-2026` and changes up to four numbers. The frozen code takes no seed (SHA-256 of `claimcheck-mutation-v1:` + slug) and changes each true derivable number with probability ½. In v1 held-out that was 1 to 9 per paper. | **The protocol now describes the frozen code; no wrapper was added.** A wrapper would be new mutation code with no measured behaviour. The slug-derived seed is fixed before any system run. The D1 tables use the observed distribution (weighted cluster size 6.3). | `PROTOCOL_DRAFT.md` 5.4 | `test_score_draft3`: `test_planted_errors_are_described_as_the_frozen_code_makes_them` |
| 2 | The scorer pooled planted and natural F numbers for the D1 necessary condition and the wording rule. Protocol 9a kept them apart. | The scorer counts planted errors (planted copies) and natural F numbers (originals) separately. The necessary condition and the wording rule use planted errors only. Natural F numbers are reported. | `score.py` (`paper_counts`, `scoped_metrics`, `judge`), `criteria.json` D1, protocol 9a | `test_d1_uses_planted_errors_only` |
| 3 | C1 and C3 are defined on originals, but the scorer's driver merged each original with its copy. | Counts are kept per document variant. C1 and C3 use originals, C2 uses both copies, D1 uses planted errors (`score.scoped_metrics`). The development demonstration was regenerated this way. | `score.py`, `criteria.json` `scopes`, protocol 7, `DEMONSTRATION_ON_DEVELOPMENT_DATA.json` | `test_scopes_c1_on_originals_c2_on_both_copies` |
| 4 | C2c used the exact bound that ignores clustering. | C2c uses the conservative (design-effect, ICC floor) bound, like every other claim-level criterion (`score.c2c_met`). | `score.py`, `criteria.json` C2c, protocol 9 | `test_c2c_uses_the_clustered_bound` (5 flags in one paper: 45 % unclustered, fails clustered; 5 in 5 papers pass) |
| 5 | The criteria said too few flags give a confirmation-only pilot; protocol 9 said every criterion is required. | One rule, in the criteria (`pilot_scope_rule`), the protocol and the scorer's output `pilot_scope_if_C4_to_C10_are_met`. If C2a, C2b and C2c are all met, flags are shown to pilot users. If C2a and C2b are met and C2c is not, the pilot is confirmation only and flags reach only the supervising PCS reviewer. If C2a or C2b fails, there is no pilot. D1's wording rule now governs wording only. | `criteria.json`, protocol 9 and 9a, `score.judge` | `test_c2c_not_evaluable_gives_a_confirmation_only_pilot`, `test_scopes_...` (no pilot) |
| 6 | Protocol 10a's tolerance rows did not match the scorer. `design_120.py` divided only the opportunities by the design effect and left out C1's estimate and paper-level conditions. | **The scorer's rule (the standard effective sample size) is kept, and the tables now follow it.** `design_120.py` computes C1 jointly, C2a alone, and C2a and C2b jointly (spread, and all in one paper). Protocol 10 and 10a print these rows. The scorer itself is unchanged in this respect. | `design_120.py`, `DESIGN_120.json`, protocol 10 and 10a, `criteria.json` (larger-sample `why`) | `test_design_120`: `test_c1_rows_...`, `test_c2_rows_...` (each row at its boundary, against `stats.proportion` with its bootstrap), `test_the_protocol_table_prints_these_rows` |
| 7 | The judge checked only the paper count. It did not check the 90 % primary-complete rule, the 20-per-context minimum or the fallback. | `score.select_primary` implements protocol 2, 3 and 10a: three contexts, at least 20 eligible papers each, no topping up, hash order, the 120-paper design or its fallback, then the 90 % rule on the primary set. `score.evaluate` applies it before any criterion. | `score.py`, `criteria.json` `minimum_sample`, protocol 2 and 11 | `test_per_context_minimum_without_topping_up`, `test_the_120_paper_design_and_its_fallback`, `test_the_90_percent_primary_complete_rule`, `test_too_few_confirmations` |
| 8 | C7's "supported size" was undefined. | Provisional supported sizes per statistic are taken from `perf/results.json`: count 51,209 B; mean, sd and Pearson 33,760 B; min, median and anything not measured 8,219 B. A capacity run before approval replaces them. Larger tables are still run, and their UNKNOWN counts as an abstention in C1 to C3. They fall outside C7 and are reported with their completed share. "Completed" means the kernel accepted. | `criteria.json` C7, protocol 9 and 13, `score.judge_c7` | `test_c7_within_the_supported_size_of_each_statistic` |
| 9 | There was no memory limit per process with two workers. | **A v1.1 wrapper.** `lean_guard.py` writes an executable named in `PCS_CLAIMCHECK_LEAN`, which the frozen kernel call already honours. It runs the real Lean, stops it at 7 GB of resident memory (two workers, under 16 GB) and logs time and peak memory per run for C7. A stopped run exits non-zero, which the frozen call treats as not accepted (UNKNOWN). Lean is tied to the guard (parent-death signal), so the frozen call's timeout, which stops only the guard, stops Lean too; a start record without a finish record marks such a run. | `lean_guard.py`, protocol 6 step 4, `criteria.json` C7 `kernel_configuration` | `test_lean_guard` (synthetic Lean, through the frozen `check_source`: accepted within the limit; stopped and failing closed above it; after a timeout no Lean process is left running) |
| 10 | C7 is per claim, but step 4 put two claims in a file (and the v1.1 default is four). | **One claim per proof file** (`batch_size` 1). The kernel record's `batch_seconds` is then the claim's time. The batch-rejection re-runs of the frozen `check_items` cannot occur. perf measured this configuration. | protocol 6 step 4, `criteria.json` C7 | `test_kernel_configuration` |
| 11 | Adjudication upper figures of 55, 110 and 220 h did not follow from 57.5 minutes per paper. | Corrected to 57.5, 115 and 230. `design_120.py` now derives minutes from the plan's rates. | adjudication plan section 4, `design_120.py`, `DESIGN_120.json`, protocol 10a and 13 | `test_adjudication_hours_follow_the_plans_rates` |
| 12 | `MODEL_ACCESS.md` divided Gemini's tokens by all attempts. | Now per successful call: 5,160 / 563 and 2,846 / 643. The ranges are 2,088–5,160 prompt and 134–3,032 output tokens. Token totals were recomputed. | `MODEL_ACCESS.md`, `design_120.py`, `DESIGN_120.json`, protocol 10a and 13 | `test_token_figures_are_the_v1_ledgers_per_successful_call` (reads the ledgers) |
| 13 | Protocol 13 and `MODEL_ACCESS.md` contradicted each other on who enforces the cap, and the frozen code has no cost accounting. | Three layers, stated the same way in both. (1) `budget.py` refuses before sending any request whose worst case (the bytes of the whole request body and the maximum output, at frozen prices) could pass a sub-cap or the total cap, and stops for good if a response costs more than its worst case. It refuses a provider without a frozen price and refuses without a recorded owner authorisation. It write-ahead logs every request to a synced spend log, resumes from it, charges a sent request with no result at its worst case, and refuses to start if cached answers exist without a log. (2) The frozen ledger's attempt budget is set to four per call. (3) Provider-side hard limits are set by the owner. | `budget.py`, `model_config.json`, protocol 2 and 13, `MODEL_ACCESS.md` | `test_budget.Guard` (11 tests, synthetic transport) |
| 14 | Protocol 2 named `…:free`, while configuration P uses the paid route. | Identifiers per configuration are in `model_config.json` and protocol 2. The guard refuses any other identifier. | `model_config.json`, protocol 2, `MODEL_ACCESS.md` | `test_model_identifiers_by_configuration`, `test_unpriced_provider_and_unfrozen_model_are_refused` |
| 15 | v1's harness also makes critic calls. | `budget.fetch_proposals` calls only `propose_with_model`, once per model per document; the protocol says so. | `budget.py`, protocol 2 and 6 | `test_one_call_per_model_per_document_and_no_critic_call` |
| 16 | The 20 % ambiguity rule had two denominators. | One denominator: T + F + A numbers of the originals (N excluded, the stricter choice), in the scorer and the text. | `criteria.json` C6, protocol 7 and 9, `score.scoped_metrics` | `test_ambiguous_share_counts_t_f_and_a_numbers_of_the_originals` (3 / 14 = 21 % fails; draft 2's 3 / 20 passed) |
| 17 | There was no rule for a planted number whose original is adjudicated N or A. | The copy carries over the original's labels and is not adjudicated separately. A changed number is a planted error only if the original is T; otherwise it keeps N, A or F, and a flag on N or A is misleading (`score.copy_class`). | `score.py`, `criteria.json` `labels_of_the_planted_error_copy`, protocol 7, adjudication plan section 4 | `test_labels_of_the_planted_copy_come_from_the_original` |
| 18 | There was no pacing rule and no rule on re-sending failed calls. | A daily request limit (configuration F: 20 Gemini requests per UTC day). A call over the limit is deferred, not failed. A call whose attempts all failed with retryable errors may be re-sent in at most three sessions, at least 24 h apart, before step 4. Deterministic failures, unparseable answers and cap refusals are final. | `budget.py` (`call_state`, `fetch_proposals`), `model_config.json` `reissue`, protocol 2, `MODEL_ACCESS.md` | `test_daily_request_limit`, `test_reissue_only_retryable_...`, `test_a_deterministic_failure_is_final`, `test_a_cached_answer_is_never_requested_again` |
| 19 | There was no rule for replay jobs lost to infrastructure. | 12 jobs (6 at 60 papers) from `score.replay_shards`, each ≤ 5.5 h, on runners with at least the kernel's memory limit. A job that does not finish is re-run and recorded. A replay with a different result fails C4 (`score.judge_c4`). | `score.py`, `criteria.json` C4, protocol 6 step 6 | `test_c4_replay_rule_and_shards` |

## Also changed

* **Status:** the protocol and criteria are labelled draft 3, unapproved. `model_config.json` is
  added to the freeze table.
* **Sensitivity analyses:** the ICC floor at 0.5 was added. A criterion met at 0.25 but not at 0.5
  is stated as not robust.
* **The scorer's API** is now `evaluate(papers, criteria, design=...)`. It takes per-number records
  through `paper_counts`. The draft-2 `metrics`/`judge` pair, which accepted merged counts and
  skipped the sample rules, is gone. `tests/test_score_draft2.py` is replaced by
  `tests/test_score_draft3.py`.
* **The development demonstration** goes through the same path. The six papers are one context, so
  it reports "not evaluable" for the sample. It uses cached kernel receipts only, so it passes no
  development switch for receipts: every decided verdict in it needs a kernel-established status
  under the outward-verdict guard (`policy.established_status`).
* **`DECISION_SUPPORT.json` and `DECISION_PACKAGE.md`** were updated where these changes alter
  figures.

## Changes made on review, before integration (2026-11-18)

The draft was reviewed independently before it was integrated. These changes were made; each has a
test that fails on the reviewed draft and passes now.

* **Lean outlived its guard after a timeout.** The frozen kernel call's timeout kills only the
  process it started, which is the guard. The real Lean then kept running, with no memory limit,
  and its run was never logged. Lean is now started with the parent-death signal set to SIGKILL, and
  every run is logged when it starts (`lean_guard.stopped_from_outside` lists runs ended from
  outside). Test: `test_a_timeout_of_the_frozen_call_stops_lean_with_its_guard`. Without the
  parent-death signal it fails ("Lean outlived its guard").
* **The prompt bound counted text parts only.** Any other input field (a tool definition, a schema,
  a non-text part) would have counted as zero bytes. The bound is now the UTF-8 bytes of the whole
  request body. Test: `test_the_prompt_bound_counts_every_byte_of_the_request_body`.
* **A timeout (HTTP 408) was charged nothing**, against the package's own rule that a timeout is
  charged its worst case. Only an explicit set of refusals (400, 401, 402, 403, 404, 413, 422 and
  429) is now charged nothing. Test: `test_failed_attempts_without_usage_are_charged_conservatively`.
* **Nothing detected a wrong cost model.** For example, a provider might bill reasoning tokens
  beyond the requested maximum. A response that costs more than its worst case now halts the guard,
  and a resumed guard refuses to start. Test:
  `test_a_response_that_costs_more_than_its_worst_case_stops_the_guard`.
* **The demonstration's conditional development switch** (it passed `oracle_receipts=True` only if
  the parameter existed) is removed. The demonstration uses kernel receipts only. Regenerated at the
  integrated head, `DEMONSTRATION_ON_DEVELOPMENT_DATA.json`, `DESIGN_120.json` and
  `DECISION_SUPPORT.json` are byte-identical to the committed files.

## Not resolved here, and why

* **Supported sizes and the kernel-time estimate** stay provisional until the capacity run
  (`DECISION_PACKAGE.md` 13.7, 14). It needs Lean 4.28.0 on the reference machine, which this
  environment does not have.
* **The owner's choices stay open:**
  * the ICC floor;
  * 60 or 120 papers;
  * the wording threshold (the field stays empty; 0.20 is proposed);
  * the C2c threshold;
  * the screening cap;
  * configuration F or P;
  * the Gemini price (`model_config.json` has `null`, so the guard refuses paid Gemini requests).

  Draft 3 fixes the rules, not these choices.
* **Not among the nineteen, unchanged:**
  * C2a counting each exposed number in both copies (package section 15, row 9);
  * C6's zero tolerance across all arms.
* **The guard samples memory every 0.05 s.** A spike shorter than that can exceed the limit before
  the process is stopped. The measured peak is logged either way.
