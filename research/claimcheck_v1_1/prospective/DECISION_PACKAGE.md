# ClaimCheck v1.1 prospective evaluation: decision package for the owner

**Status (2026-11-18): for the owner's decision. The protocol is now draft 3, still UNAPPROVED.**
Nothing has been sampled, retrieved, screened, labelled, scored or run for the prospective
evaluation. No model call has been made and nobody has been recruited. The package was written
against draft 2. Draft 3 resolves the nineteen inconsistencies of section 12; every change, its
files and its test are in [`AMENDMENTS_DRAFT_3.md`](AMENDMENTS_DRAFT_3.md). Figures below that the
fixes changed were updated. Section 14 assesses the feasibility study proposed before committing to
the 120-paper design.

## How the figures were obtained

Every number below comes from an existing file or from one synthetic computation:

* `DS` = [`DECISION_SUPPORT.json`](DECISION_SUPPORT.json), written by
  [`decision_support.py`](decision_support.py):
  `python -m research.claimcheck_v1_1.prospective.decision_support --out research/claimcheck_v1_1/prospective/DECISION_SUPPORT.json`.
  It uses `stats.py` (the scorer's own module) and the formulas `score.judge` applies. It reads only
  existing results: `criteria.json`, `DESIGN_120.json`, `DEMONSTRATION_ON_DEVELOPMENT_DATA.json`,
  `../perf/results.json` and the v1 prefetch ledgers
  (`claimcheck_v1/benchmark/results/heldout/prefetch_ledger*.json`). It has no network code
  (a test checks its imports). DS keys are given in backticks, for example
  `DS model_calls.designs`.
* The test [`../tests/test_decision_support.py`](../tests/test_decision_support.py) recomputes DS
  and requires it to match the committed file. It also checks that the tolerances at the proposed
  ICC floor agree with the full `stats.proportion`, bootstrap included.
* Other files are cited by path. Inputs that nobody has measured are labelled **Assumption**. They
  are also listed in `DS assumptions`.

Abbreviations: T, F, N, A are the adjudicated classes (true, false, not derivable, ambiguous). ICC is
the intraclass correlation. "Bound" means the one-sided exact 95 % bound the criterion uses.

## 1. Recommendations in brief

| Decision | Recommendation |
| --- | --- |
| ICC floor | Keep **0.25**. Always report the grid. A criterion that is met at 0.25 but not at 0.5 is reported as "not robust". |
| Sample size | **120 papers (40 per context)**, on two conditions: the preliminary adjudication round confirms about an hour or less per paper, and adjudicators are recruited for that load. Otherwise 60, with its zero-tolerance caveat stated in advance. |
| Wording threshold (D1) | Set it at **0.20** for the lower bound of flag recall **on planted errors**, primary arm, all contexts pooled, clustered as the other bounds are. The owner should accept in advance that "confirmation only" is the expected outcome. |
| C2c | Keep **50 % with at least 5 flags**. The bound is now clustered like the other bounds, the meaning is reworded, and the "confirmation only" conflict is resolved (all in draft 3; section 12, items 4 and 5). |
| Screening cap and fallback | **600 per context** for 120 papers (300 for 60), with the fallback of protocol 10a as drafted. |
| Model configuration | **P (capped paid route)**: 30 USD for 120 papers (15 for 60), split into sub-caps per provider. The cap is enforced in code by a budget check run before each request. Provider-side hard limits are added where offered. Re-list the models before approval and again just before the calls; record exact identifiers and parameters; keep every response. |

Reasons and the consequences of each alternative are in section 13. The decisions are summarised in
the table of section 15.

## 2. Model calls: initial calls, retries, failures, withdrawal

**Volume** (`DS model_calls.designs`). Each paper has two documents (the original and the
planted-error copy), and each document gets one call per model:

| | 60 papers | 120 papers |
| --- | ---: | ---: |
| calls in total | 240 | 480 |
| calls per provider | 120 | 240 |
| HTTP attempts, worst case (each call + 3 repeats) | 960 | 1,920 |
| attempt budget the ledger needs per provider (4 × calls) | 480 | 960 |

The frozen `Ledger` (`claimcheck_v1/providers.py`) counts **attempts**, not calls, and its default
budget is 60 (Gemini) and 40 (OpenRouter). A prospective harness that kept the defaults would stop
early. It must set the budget explicitly.

**Retries as implemented** (`providers.complete`). Transport failures, HTTP 429 responses and server
errors are repeated up to three times. Deterministic failures (HTTP 200 without text, 400, 401, 403,
404) are not repeated, and neither is text that does not parse. In the worst case one call waits
90 s in back-off (15 + 30 + 45), or 240 s after HTTP 429s (40 + 80 + 120). Each attempt may take up
to the 300 s timeout. One call can therefore take 24 minutes at most. If calls run strictly one at a
time, that bounds a provider at 48 h (60 papers) or 96 h (120 papers): a ceiling, not a forecast.

**What v1 measured** (`DS model_calls.v1_ledgers`):

* Nemotron, free tier: 14 attempts, 0 failed, 66.9 s per call, 4,404 prompt and 3,032 output tokens
  per call. A later run had 3 attempts, of which 1 failed.
* Gemini, free tier: 7 of 14 attempts failed on day 2, and 5 of 15 later, so 41 % of attempts failed
  (12 of 29). Each attempt took 3.8 to 4.5 s.
* At v1 latency, calls made one at a time take 2.2 h (60 papers) or 4.5 h (120 papers) for
  Nemotron, and 0.1 h or 0.3 h for Gemini (`sequential_hours_at_v1_latency`).

**Primary-complete rule.** A paper counts only if both models answered for both documents (four
calls). The primary analysis needs at least 90 % of papers. If each call succeeds with probability
q, independently, the chance of reaching 90 % is
(`chance_primary_complete_share_at_least_90_percent_by_per_call_success`):

| per-call success q | 0.95 | 0.97 | 0.98 | 0.99 |
| --- | ---: | ---: | ---: | ---: |
| 60 papers | 0.055 | 0.459 | 0.818 | 0.991 |
| 120 papers | 0.008 | 0.371 | 0.860 | 0.999 |

So each call must succeed about 98 to 99 % of the time.

Two cases bracket configuration F:

* **Failures independent.** If v1's failure rates applied to independent attempts, retries would
  rescue most calls: per-call success would be 0.9707 for Gemini and about 1 for Nemotron. The
  chance of reaching 90 % would be 0.943 (60 papers) or 0.978 (120 papers)
  (`v1_failure_rates_if_independent`).
* **A daily quota.** A daily quota is not an independent failure: once the day's allowance is used,
  every repeat within the four-minute schedule fails too. **Assumption:** about 20 successful Gemini
  calls a day, as observed in v1 (`MODEL_ACCESS.md`). An unpaced run then completes at most 16.7 %
  (60 papers) or 8.3 % (120 papers) of papers. The primary analysis would not be evaluable. A paced
  run needs at least 6 days (60 papers) or 12 days (120 papers) of Gemini calls
  (`free_tier_days_for_gemini_calls_at_20_a_day`).

Draft 2 had no pacing rule and no rule on sending a failed call again later (section 12, item 18).
Draft 3 has both, implemented in `budget.py`.

**A model withdrawn or changed mid-study.** That arm becomes "not run" for the remaining papers, and
no substitute is allowed (protocol 2). The primary-complete share is then at most the share of papers
finished before the change. Unless the change comes after 90 % of papers, the primary analysis is
not evaluable. The exposure window is what differs between the configurations:

* configuration F: at least 6 days (60 papers) or 12 days (120 papers);
* configuration P: hours, at v1 latency.

Mitigations:

* re-list both models immediately before step 3;
* make all calls in one short window;
* record the model version each response reports (section 10).

**Critic calls.** v1's `benchmark/run.py` also makes two "critic" calls per original document. The
counts of 240 and 480 include proposal calls only. Draft 3 names the harness (`budget.fetch_proposals`,
which makes proposal calls only) and states that no critic calls are made (section 12, item 15).

## 3. Cost, and how the cap is enforced

**Nemotron, paid route** (0.60 and 2.40 USD per million prompt and output tokens, `MODEL_ACCESS.md`;
`DS model_calls`):

* one call at the measured sizes costs 0.00992 USD;
* one call that uses the full 16,384 output tokens costs 0.04196 USD.

| Nemotron, USD | 60 papers | 120 papers |
| --- | ---: | ---: |
| measured sizes, one attempt per call | 1.19 | 2.38 |
| measured sizes, four billed attempts per call | 4.76 | 9.52 |
| every attempt using all 16,384 output tokens | 20.14 | 40.29 |

The last row exceeds the proposed 30 USD cap for 120 papers. A cap therefore has to be enforced on
every request; estimates alone do not bound the cost.

**Gemini.** The price is not in the provider's listing, so it is unknown. The highest ledger mean is
5,723 tokens per successful call. Under a Gemini sub-cap of 20 USD (120 papers) or 10 USD
(60 papers), the run fits if the average price per million tokens (prompt and output alike) is at
most:

* 14.56 USD, with one attempt per call;
* 3.64 USD, if every call were billed four times.

(`gemini_highest_average_usd_per_million_tokens_within_sub_cap`; **Assumption:** sub-caps of
Nemotron 10 and Gemini 20 USD at 120 papers, 5 and 10 USD at 60.) The owner compares these figures
with Google's price page before authorising. The cap holds whatever the price; a high price only
means the cap stops the run earlier, and the calls it stops are recorded as "not run".

**How the cap is enforced in code** (implemented in draft 3 as `budget.py`, tested with a synthetic transport only; no request has been sent):

1. **A budgeted transport.** `providers.complete` accepts a `transport` argument, but `propose.py`
   does not pass one. A v1.1 harness can route every request through a budgeted transport without
   changing a byte of v1. It substitutes `claimcheck_v1.propose.complete` with
   `functools.partial(providers.complete, transport=budgeted)` for the duration of the run. A test
   must show that no request reaches `_post` except through the budget.
2. **Before each request.** Compute the worst-case cost: the bytes of the whole request body as an
   upper bound on prompt tokens, plus the request's maximum output tokens (16,384), at that
   provider's frozen prices. If the money already committed plus this worst case would exceed the provider's sub-cap
   or the total cap, raise `BudgetExceeded` and send nothing. `BudgetExceeded` is a subclass of
   `ProviderError`, so `propose_with_model` records it as a failure of that arm for that document.
3. **After each response.** Charge the usage the provider reports: Gemini's `promptTokenCount`,
   `candidatesTokenCount` and `thoughtsTokenCount`; OpenRouter's `prompt_tokens` and
   `completion_tokens`. If usage is missing after a timeout (including HTTP 408), a server error or
   a transport failure, charge the worst case. **Assumption, to be checked against the providers'
   statements:** HTTP 400, 401, 402, 403, 404, 413, 422 and 429 are not billed (the request was
   refused before any generation); any other answer without usage is charged its worst case.
   **Tripwire:** the worst case assumes that every billed output token, including hidden reasoning
   tokens, counts against the request's maximum. If a response's reported usage ever costs more
   than its worst case, that assumption is wrong for that provider: the guard sends nothing more,
   and a guard resumed from that log refuses to start. With one request in flight, a wrong
   assumption can overshoot a cap by at most that one request.
4. **A persistent spend log.** Append one line per attempt (time, provider, model, status, usage,
   amount charged, running total) and sync it to disk. A resumed run starts from the logged total. It
   refuses to start if cached responses exist but the log does not.
5. **Prices.** They are entered by the owner from the providers' price pages, with the date, and
   frozen with the software. With no price, the transport refuses to send.
6. **The attempt budget** (`Ledger.max_calls`) is set to 4 × calls per provider and stays as an
   independent second limit.
7. **Provider-side limits** are added by the owner where a provider offers a hard limit, for example
   a credit limit on an API key or a daily request quota for the project. A budget *alert* that only
   notifies is not a limit.
8. **After the run.** The provider's billing statement is compared with the spend log, and both are
   reported.

## 4. Kernel runtime and resources; hosted replay

**Measured** (`DS kernel_and_replay`, from `../perf/results.json`). The measurements used 4 CPUs,
an 11 GB limit per Lean process, 600 s, one claim per proof file and synthetic two-decimal data. GB
here means MB / 1024.

| Statistic | Largest table accepted (rows, bytes) | Time, peak memory there | First failure |
| --- | --- | --- | --- |
| count | 2,400 rows, 51,209 B | 35.2 s, 4.24 GB | none measured |
| mean, sd | 1,600 rows, 33,760 B | 32.3 to 35.7 s, 4.1 to 4.4 GB | 2,400 rows: recursion depth |
| pearson | 1,600 rows, 33,760 B | 54.2 s, 6.19 GB | 2,400 rows: recursion depth |
| min | 400 rows, 8,219 B | 9.8 s, 1.40 GB | 800 rows: recursion depth |
| median | 400 rows, 8,219 B | 34.6 s, 4.05 GB | 800 rows: out of memory at 10.2 GB |

* **Every statistic was accepted only up to 8,219 bytes.** The sampling frame admits CSV files up to
  64,000 bytes. Six of the eight development tables are larger than 8,219 bytes. Their sizes in
  bytes are 24,312, 28,005, 33,339, 3,186, 7,909, 26,444, 9,792 and 24,478
  (`claimcheck_v1/benchmark/{dev,heldout}/*/*.csv`). In development, the kernel runs for the
  minimum and the maximum of a 617-row column did not complete within their limits. That was 2 of 33
  adversarial readings checked on originals, or 6 % (`../REPORT.md`, section 2). C7 allows at most
  5 % of runs to be incomplete.
* **Draft 2's C7 said "tables within the supported size" but never defined the size** (section 12,
  item 8). Draft 3 gives provisional sizes per statistic, from this table, until the capacity run.
* **Two workers and memory.** The highest peak among accepted runs was 6.19 GB, so two such runs
  together take 12.4 GB of the reference machine's 16 GB. Two median runs on tables of 800 rows or
  more would each try to reach 10.2 to 10.3 GB, or 20.6 GB together. Draft 2's step 4 set no limit
  per process (section 12, item 9). Draft 3 sets 7 GB per Lean process (`lean_guard.py`) and one claim
  per proof file (item 10).
* **Time per claim versus time per file.** C7 is stated per claim. Step 4 puts up to two claims in a
  proof file with a 900 s limit per file. The measurements used one claim per file and 600 s (item
  10).
* **Kernel time** is given as about 10 h per 60 papers on the reference machine (protocol 13), with
  no documented basis. It should be re-estimated from a capacity run made before approval
  (section 13.7).

**Hosted replay (C4).** The estimate is about 20 runner-hours at 120 papers and 10 at 60
(`DESIGN_120.json`), and a hosted job may run at most 6 h. At face value 120 papers need at least
4 jobs, and at least 7 if the estimate is half the truth. Hours per job, including an assumed
0.5 h of set-up per job (`hours_per_job_by_jobs_and_underestimate`):

| 120 papers, jobs | estimate × 1 | × 1.5 | × 2 | × 3 |
| --- | ---: | ---: | ---: | ---: |
| 4 | 5.5 | 8.0 | 10.5 | 15.5 |
| 8 | 3.0 | 4.25 | 5.5 | 8.0 |
| 12 | 2.17 | 3.0 | 3.83 | 5.5 |

Twelve jobs (six at 60 papers) withstand an estimate that is three times too low. The total
runner-hours are the same apart from set-up. Requirements for the replay:

* the runners need at least as much memory as the kernel's per-process limit;
* C4 requires 100 % of bundles, so a job lost to a timeout or a runner fault must be allowed to run
  again (replay is deterministic). Draft 2 did not say so (item 19); draft 3 does (step 6).

## 5. Adjudication: 140 to 230 adjudicator-hours plus a resolver

**Rates.** The adjudication plan, section 4 (assumptions, not measurements), gives per paper 10 to
20 minutes of reading plus about 25 numbers at 1 to 1.5 minutes each. That is 35 to 57.5 minutes per
paper (`DS adjudication`). The resolver handles 15 to 25 % disagreement at 3 minutes each.

| | 60 papers | 120 papers |
| --- | ---: | ---: |
| each of two adjudicators covering all papers, hours | 35–57.5 | 70–115 |
| person-hours (two labels per number) | 70–115 | **140–230** |
| resolver, hours | 11.2–18.8 | 22.5–37.5 |
| each of six adjudicators (two per context), hours | 11.7–19.2 | 23.3–38.3 |
| weeks, two adjudicators at 4 h/week (**assumption**) | 8.8–14.4 | 17.5–28.8 |
| weeks, two adjudicators at 8 h/week | 4.4–7.2 | 8.8–14.4 |
| weeks, six adjudicators at 4 h/week | 2.9–4.8 | 5.8–9.6 |

The plan, protocol 10a and `DESIGN_120.json` print 55, 110 and 220 h at the upper end. That
corresponds to 55 minutes per paper, while the plan's own per-paper figure is 57 minutes (item 11).

**Preliminary round** (3 papers, 30 numbers). At these rates it takes 1.0 to 1.75 h per adjudicator.
The plan estimates 2 to 3 h including the instructions. It is the only way to measure the rates
before choosing 60 or 120 papers.

**Planted-error copies.** The protocol does not say whether they are adjudicated separately.
Proposed rule, which adds no work:

* classes carry over from the original;
* a planted number is F, under the adjudicated reading, only where the original number was
  adjudicated T;
* otherwise the planted number leaves the planted-error recall, and a flag on it is misleading, as
  for any N or A number.

## 6. Clustering and uncertainty; how sensitive the results are to the ICC floor

**What the data say about the ICC.** In development, an ICC could be estimated only for outcomes
that occur often (`DS development_icc_estimates`; six papers, so very imprecise):

* coverage on original articles: 0.53 (Gemini), 0.32 (Nemotron), 0.49 (union);
* detection of planted errors: 0.00 (2 detections), 0.32 and 0.32.

(Draft 2's demonstration merged each original with its copy and gave 0.35, 0.26, 0.35 and 0.06,
0.41, 0.41.)

For unsupported confirmations and misleading flags, there were too few events to estimate anything
(the estimate is 0). The floor is the assumption that replaces such estimates. The scorer uses the
estimate when it is larger.

**C2a tolerance by assumed ICC.** The table gives the misleading flags `score.judge` accepts, with
flags in different papers (`DS claim_level_tolerance.C2a`). "−1" means the bound fails even with no
flag.

| exposed numbers per paper | ICC 0 | 0.1 | **0.25** | 0.5 |
| --- | --- | --- | --- | --- |
| 60 papers: 4 / 5 / 8 / 10 | 1 / 1 / 2 / 3 | 0 / 0 / 1 / 3 | **−1 / 0 / 0 / 0** | −1 / −1 / −1 / −1 |
| 120 papers: 4 / 5 / 8 / 10 | 2 / 3 / 4 / 6 | 2 / 3 / 4 / 6 | **1 / 2 / 4 / 6** | 0 / 0 / 0 / 0 |

* At ICC 0.5, **C2a can never be met at 60 papers**. However many numbers a paper has, the lowest
  possible bound is 2.47 % (`lowest_possible_bound_no_flag_by_icc`), against a threshold of 2 %.
* At 0.25 and 60 papers, C2a needs zero misleading flags and at least 5 exposed numbers per paper
  (with 4 the bound is 2.16 %).

**C1 tolerance** (`DS claim_level_tolerance.C1`). The table gives the unsupported confirmations
accepted, one per paper. All three C1 conditions apply jointly (estimate ≤ 2 %, claim-level bound
≤ 5 %, paper-level bound ≤ 10 %).

| confirmations per paper | ICC 0 | 0.1 | **0.25** | 0.5 |
| --- | --- | --- | --- | --- |
| 60 papers: 2.5 / 4 / 5 | 1 / 1 / 1 | 1 / 1 / 1 | **1 / 1 / 1** | 0 / 1 / 1 |
| 120 papers: 2.5 / 4 / 5 | 6 / 6 / 6 | 6 / 6 / 6 | **6 / 6 / 6** | 5 / 6 / 6 |

At 120 papers the paper-level bound of C1 decides in most cells, not the ICC.

**The scorer accepted more than draft 2's protocol 10a said.** The scorer uses `stats.proportion`,
which divides both the events and the opportunities by the design effect:
`upper_bound(ceil(k / deff), n / deff)`. Draft 2's `design_120.py` divided only the opportunities,
and its C1 row ignored the estimate and paper-level conditions. Every figure at the 0.25 floor
agrees with the full `stats.proportion` (`verified_by_stats_proportion`). The 120-paper figures are
confirmed end to end through `score.paper_counts` and `score.evaluate` (test
`test_the_scorer_end_to_end_accepts_six_and_rejects_seven_at_120_papers`):

* C2a, 120 papers with 10 exposed numbers per paper: 6 misleading flags pass and 7 fail, where
  draft 2's 10a said 2. The binding condition is the estimate (≤ 0.5 %).
* C1 jointly: 60 papers allow 1 and 1 (2.5 and 5 per paper), where draft 2 said 1 and 2. At 120
  papers 6 and 6, where draft 2 said 5 and 8.

Draft 3 keeps the scorer's rule (the standard effective sample size) and prints these figures in
protocol 10a (item 6).

C2b changes the practical picture, because flags in different papers each count against it
(`DS C2_a_and_b_together`):

* **at 60 papers C2 tolerates no misleading flag;**
* **at 120 papers it tolerates misleading flags in one paper only.** That is 1 flag if spread, or up
  to 2 (5 exposed numbers per paper) or 5 (10 exposed numbers per paper) if all are in that one
  paper.

(Section 12, item 6.)

**C2a counts both copies of a number.** C2a's denominator counts every exposed number in the original
and again in the planted copy, and most of them are repeats. The 0.25 floor treats the two copies as
almost independent, which lowers the bound (`DS C2a_original_and_copy_counted_twice`). Examples with
no misleading flag:

* 60 papers, 4 exposed numbers per document: 2.16 % counting originals only (fails), 1.71 % counting
  both copies (passes);
* 60 papers, 5 per document: 1.98 % against 1.61 %.

Proposal (owner's choice):

* count each printed number once per paper (exposed in either copy);
* count a misleading flag in either copy as an event for that number.

## 7. False confirmations (C1) and misleading refutations (C2a, C2b, C2c)

**C1.** C1 tolerates one unsupported confirmation at 60 papers and six at 120, when they are spread
one per paper (section 6). The per-context scope rule ("C1 estimate above 2 % excludes the context")
gives (`DS zero_event_rules.scope_rule_C1_...`):

* a context with fewer than 50 confirmations tolerates **no** unsupported confirmation;
* 50 to 99 confirmations tolerate one, 100 to 149 two.

The minimum of 150 confirmations, spread evenly, is exactly 50 per context.

**C2b** (`DESIGN_120.json`):

* At 60 papers it allows no affected paper. The chance of passing is 74 / 55 / 30 / 4.6 % if
  0.5 / 1 / 2 / 5 % of papers are affected.
* At 120 papers it allows one. The chance of passing is 88 / 66 / 31 / 1.6 %.
* Intermediate sizes (`DS screening.intermediate_sizes`): 75 and 90 papers still allow none. **105
  is the smallest size that allows one** (71.7 % chance at 1 %).

**The scope rule for misleading flags tightens as the sample grows.** Any misleading flag excludes
its context. With a true rate of 1 % of papers (`DS zero_event_rules.scope_rule_any_...`):

* all three contexts stay in scope with chance 0.547 at 60 papers and 0.299 at 120;
* at least two stay in scope with chance 0.913 at 60 and 0.744 at 120;
* the expected number of contexts in scope is 2.45 at 60 and 2.01 at 120.

The 120-paper design lets the pooled C2b tolerate one affected paper, but that paper's context still
leaves the pilot.

**C2c as `score.judge` computes it** (`DS C2c`). The exact bound ignores clustering.

| flags | 4 | 5 | 10 | 20 | 40 |
| --- | ---: | ---: | ---: | ---: | ---: |
| bound with no misleading flag | 52.7 % | 45.1 % | 25.9 % | 13.9 % | 7.2 % |
| misleading flags allowed (threshold 50 %) | not evaluable | 0 | 1 | 5 | 14 |

* **Five flags is exactly the smallest number at which C2c can pass.** With 4 flags and none
  misleading the bound is 52.7 %. The "at least 5 flags" rule therefore adds nothing beyond the
  bound itself.
* **With the design effect** that every other claim-level bound uses (floor 0.25), at least 8 flags
  are needed when flags come two per flagged paper, and 12 when they come four per paper. On the
  development data, 0 misleading of 3 flags in 2 papers gave draft 2's scorer a bound of 63.2 %. The
  clustered bound, which draft 3 uses, is 77.6 % (`DS C2c.development_union_arm`). All 3 flags were
  on planted-error copies, none on an original.
* **Expected flags.** At the development recall on planted errors (11.5 %), about 28 to 30 correct
  flags are expected at 60 papers, and 55 to 60 at 120. C2c should therefore be evaluable unless
  recall falls.
* **What C2c actually measures.** Flags on planted-error copies are included, and planting raises
  the share of real discrepancies far above a natural document. An illustration using development
  rates (`DS C2c.illustration_real_share_of_flags`; assumptions: 1.0 natural F number and 4.33
  planted per paper, 7.75 exposed non-F numbers per document, recall 11.5 % for natural and planted
  errors alike): the share of flags that are real is
  * 90 % pooled but 75 % on originals alone, if 0.5 % of exposed numbers draw a misleading flag;
  * 70 % pooled but 43 % on originals alone at 2 %, the C2a bound.

  A supervised pilot still has a PCS reviewer check every outward verdict. Even so, the meaning
  given in the criteria ("a flag is more often a real discrepancy than not") overstates what is
  measured.

## 8. Discrepancy detection: minimum useful performance and the wording rule

Assumptions: planted errors as protocol 5 describes them (4 per paper), or as the frozen
`mutate.py` actually produced them in v1 held-out (7, 1, 4, 4, 9 and 1, a weighted cluster size of
6.3); ICC floor 0.25 (`DS D1_flag_recall`).

| Observed recall needed for the lower bound to reach… | 60 papers, 4 per paper | 60, mutate-like | 120, 4 per paper | 120, mutate-like |
| --- | ---: | ---: | ---: | ---: |
| above the C2a bound (the necessary condition) | 4.6 % | 4.6 % | 2.3 % | 2.3 % |
| 0.10 | 15.4 % | 16.2 % | 13.5 % | 14.0 % |
| **0.20** | **26.3 %** | **28.1 %** | **24.6 %** | **25.2 %** |
| 0.30 | 37.5 % | 38.8 % | 35.0 % | 36.0 % |

Chance of reaching 0.20 if the true recall is 11.5 % / 20 % / 25 % / 30 % (binomial, so optimistic
when detections cluster):

* 60 papers: 0 / 0.011 / 0.351 / 0.911 (4 per paper), and 0 / 0.001 / 0.142 / 0.770 (mutate-like);
* 120 papers: 0 / 0.008 / 0.601 / 0.996, and 0 / 0.002 / 0.476 / 0.993.

What this means:

* **Development recall on planted errors was 11.5 % (3 of 26; lower bound 0.5 %), and 0 of 6 on
  natural F numbers.** Draft 2 pooled them as 3 of 38 (7.9 %), counting each natural number in both
  copies. If the prospective recall is similar, the lower bound is 6 to 8 %
  (`lower_bound_at_observed_recall`). That meets the necessary condition and is far from any wording
  threshold. **The expected outcome is that nothing may describe the tool as finding errors.**
* **At 0.20, only a system whose true recall is about 0.3 or more is likely to be described as
  finding errors.** A threshold of 0.10 would allow that description for a tool that misses nearly
  nine in ten planted errors.
* **Draft 2's scorer pooled planted and natural F numbers**, whereas protocol 9a kept them apart.
  Draft 3 uses planted errors only (item 2). **Draft 2's planted count ("up to four") did not match
  `mutate.py`**, which changes each true derivable number with probability ½ and takes no seed;
  draft 3's protocol describes the frozen code (item 1). The thresholds above change little between
  the two structures.

## 9. Ambiguous adjudications

As drafted (protocol 7, criteria C6), A numbers are handled against the system in every metric: a
decided verdict on an A number is an error; A numbers stay in C2's denominators and count against
coverage. Sensitivity analyses treat A as T, as N, and removed. If more than 20 % of numbers are A,
C1 to C3 are not evaluable. That is sound. Open points:

* **The denominator of the 20 % rule.** C6 speaks of "statistic-like numbers". `score.metrics`
  divides by all labelled numbers (T + F + N + A), including N numbers, which makes the rule easier
  to pass (item 16).
* **A planted number whose original is adjudicated N or A** (planted because the provisional label
  said T): see the rule proposed in section 5 (item 17).
* **C6 tolerates no decided verdict on an A number from any arm, adversary included, at any sample
  size.** The chance of zero such events is (`DS zero_event_rules.C6_...`; **assumptions**: decided
  verdicts per paper; the chance that one falls on an A number; independence):

  | | a = 0.05 % | 0.1 % | 0.5 % |
  | --- | ---: | ---: | ---: |
  | 60 papers, 5 verdicts per paper | 0.861 | 0.741 | 0.222 |
  | 60 papers, 10 per paper | 0.741 | 0.549 | 0.049 |
  | 120 papers, 5 per paper | 0.741 | 0.549 | 0.049 |
  | 120 papers, 10 per paper | 0.549 | 0.301 | 0.002 |

  In development, the adversary obtained 53 verdicts in 16 documents (`../REPORT.md`, section 2).
  The union arm obtained 26 in 6 papers: 23 confirmations and 3 flags (`DS
  development_icc_estimates`, `DS C2c.development_union_arm`). More papers make a zero-event rule
  harder to meet. If the owner wants consistency with C2b, C6 could become a paper-level bound
  (≤ 5 %) instead of zero events. That is an option, not a recommendation.
* **Independent adjudication itself is not affected.** Agreement and κ are computed before
  resolution, and an unresolved disagreement stays A (adjudication plan, section 7).

## 10. Model availability and reproducibility

* **Availability was last listed on 2026-11-15 at about 16:40 UTC** (`MODEL_ACCESS.md`), by reading
  metadata only. It **must be re-listed before approval**, and again immediately before step 3.
  Free-tier quotas cannot be verified without spending them.
* **Identifiers.** Protocol 2 names `gemini-3.6-flash` and `nvidia/nemotron-3-ultra-550b-a55b:free`.
  Under configuration P the Nemotron identifier is the paid route,
  `nvidia/nemotron-3-ultra-550b-a55b` (item 14). Newer Gemini versions are listed. Keeping 3.6
  preserves comparability with v1; changing it makes the comparison with v1 exploratory.
* **Record, for every attempt:**
  * the identifier sent, and the version the response reports (Gemini `modelVersion`; OpenRouter
    `model` and the serving provider);
  * the time, HTTP status, latency and reported usage;
  * the request digest.
* **Record once and freeze:**
  * the sampling parameters (temperature 0; at most 16,384 output tokens; Gemini thinking level
    "low" and a JSON response type; OpenRouter reasoning off);
  * the prompt version and SHA-256;
  * the digests of `providers.py` and `propose.py`.

  Re-checked on 2026-11-17: `0c56ec87…a6ecca` and `a666f065…38edb`, equal to `MODEL_ACCESS.md`.
* **Cache every response; it is the reproducible record.** Calling a model again is not
  reproducible, even at temperature 0. The frozen cache key is SHA-256 of (provider, model, system,
  prompt). The sampling parameters are not in the key, and the cached record holds neither the served
  version nor a time. The budgeted transport of section 3 can write these to a side log without
  changing v1. The whole cache, the spend log and the ledger become part of the frozen evidence,
  with digests.

## 11. Ethics and logistics: independent adjudication and the usability study

**Adjudication** (adjudication plan). Nobody has been contacted. Before anything is sent:

* written confirmation of independence and conflicts of interest (section 3);
* consent before anyone is named (section 8);
* the owner decides whether to offer an honorarium; any payment must not depend on results;
* a package keeper who holds the key and seals the forms, and who may be the owner;
* `check_blinding.py` passes on every package;
* instruction items 4 and 5 are added before the first prospective package (section 6 of the plan).

Adjudicators act as research personnel, not as participants. Their timing and agreement data are
kept (section 8). Whether an institution regards this as human-participant research should be asked
in the same submission as the usability study. This package does not decide that.

**Usability study** (`../usability/ETHICS_DETERMINATION.md`, `../usability/STUDY_PROTOCOL.md`).
Nothing may happen before the owner has settled four points:

1. the institution and its review body;
2. a submission for review or for an exemption decision (the institution decides, not the
   investigator);
3. data protection: lawful basis, information notice, retention, withdrawal;
4. compensation, and recruitment without pressure (no students or staff supervised by the owner).

Task 3 uses the strict runner once the owner has reviewed it. Sessions take about 40 minutes, with
at least five participants.

**What C8 can show with five participants** (`DS usability`). Four of five correct are needed on each
question. If each critical question is understood by 80 % / 90 % / 95 % of researchers, all four
questions pass with chance 0.295 / 0.713 / 0.911 (independence assumed). A pass bounds the true rate
only weakly: 4 of 5 gives a lower bound of 34 %, and 5 of 5 gives 55 %. With 10 participants (8 of 10
needed) the chances are 0.211 / 0.748 / 0.953, and the lower bounds 49 % and 74 %. C8 is formative.
It cannot show that researchers in general understand the scope.

**Logistics before approval:** re-list the models; read the Gemini price; set the provider limits;
recruit for the preliminary round; and make the capacity run of section 13.7. None of these touches a
prospective paper.

## 12. Inconsistencies found in draft 2 (all resolved in draft 3)

**All nineteen are resolved in draft 3.** [`AMENDMENTS_DRAFT_3.md`](AMENDMENTS_DRAFT_3.md) gives, for
each, what changed, in which files, and the test that checks it. The list below is kept as it was
found in draft 2.

Items 1 to 7 and 13 change what the code computes or what a criterion decides. Items 8 to 10, 15,
18 and 19 are missing operational definitions. Items 11, 12, 14, 16 and 17 are wrong figures or
gaps in rules.

1. **The planted-error step is described wrongly.** Protocol 5.4 says `mutate.py` uses "the seed
   `prospective-2026`" and changes "up to four numbers". In fact `mutate.py` takes no seed: it uses
   `"claimcheck-mutation-v1:" + slug`. It changes each true derivable number with probability ½: 1 to
   9 per paper in v1 held-out (26 in 6 papers), and 1 and 13 in development (`gold.mutated.json`).
   *Fix:* describe `mutate.py` as it is. Alternatively write a v1.1 wrapper with a seed and a cap,
   which is new code to freeze.
2. **D1 pools planted and natural F numbers.** `score.judge` computes flag recall over all F numbers
   and applies the necessary condition and the wording rule to that pooled figure. Protocol 9a and
   criteria D1 keep planted and natural apart, with the necessary condition on planted errors.
   *Fix:* separate counters (`false_planted_total`, `correct_discrepancy_planted`), with both rules
   applied to planted errors; natural F reported separately.
3. **C1 and C3 are defined on originals, but the scorer's only driver merges the copies.**
   `score.demo` merges the original and the planted copy into one counter per paper before computing
   C1 and C3. *Fix:* the prospective driver computes C1 and C3 from counters for originals only, and
   C2 and D1 from both copies, with a test.
4. **C2c ignores clustering.** `score.judge` uses `upper_bound(misleading, flags)`, while criteria's
   assumptions say claim-level bounds use the design effect with the floor. On development data that
   is 63.2 % against 77.6 %. *Fix:* use `misleading_refutations_among_flags["conservative_upper_bound"]`,
   or state the exception explicitly.
5. **"Confirmation only" versus "no pilot".** Criteria C2c says that with too few flags "C2 is not
   met and the pilot scope is confirmation only". Protocol 9 says that all of C1 to C10 are required
   and that a criterion that cannot be evaluated is not met, which means no pilot at all. *Fix:* say
   which applies. Recommended: if C2a and C2b are met but C2c fails or is not evaluable, a pilot that
   meets everything else is confirmation only, and flags reach only the supervising PCS reviewer.
6. **Protocol 10a's tolerance rows do not match the scorer.** They report "C2a misleading flags
   allowed 1 / 2" and "C1 … 5 / 8" at 120 papers. `score.judge` accepts 2 / 6 and 6 / 6, and 1 / 1
   for C1 at 60 papers where 10a says 1 / 2 (section 6). *Fix:* replace the rows with the scorer's
   figures and the joint C2 statement (`DS C2_a_and_b_together`). Alternatively, if the owner prefers
   the stricter reading, change the scorer to divide only the opportunities. That decision is the
   owner's, before the freeze.
7. **The judge checks the paper count only.** `score.judge` checks only that there are at least 60
   papers and that A is at most 20 %. It does not check the 90 % primary-complete share, the 20 per
   context of the shortfall rule, or the fallback of the 120-paper design.
   `minimum_sample.papers` is 60 in both designs. *Fix:* the prospective driver checks all of these,
   with tests.
8. **C7's "supported size" is undefined**, while the frame admits up to 64,000 bytes and every
   statistic was accepted only up to 8,219 (section 4). *Fix:* before approval, define the supported
   size per statistic from a capacity run under the exact step-4 configuration. State that larger
   tables are still run, that their UNKNOWN results count as abstentions in C1 to C3, and that C7 is
   evaluated within the supported size, with all runs reported.
9. **No memory limit per process with two workers.** *Fix:* a 7 GB limit per process with two workers
   (the highest accepted peak measured was 6.19 GB), or one worker with C7's own 8 GB. A run over the
   limit yields UNKNOWN, fixed in advance.
10. **Time per claim versus time per file.** C7 is per claim; step 4 puts two claims in a file with
    900 s per file; perf measured one claim and 600 s. *Fix:* define time per claim for a file with
    two claims, and how a timeout of the file counts, then re-measure.
11. **Adjudication hours.** 35 to 57 minutes per paper gives 57.5, 115 and 230 h, not 55, 110 and 220
    (plan, protocol 10a, `DESIGN_120.json`). *Fix:* correct them, or set the per-paper maximum to 55
    minutes.
12. **Gemini tokens per call in `MODEL_ACCESS.md`** (2,600 and 300) divide by all attempts, including
    failed ones that report no usage. Per successful call they were 5,160 and 563 (day 2) and 2,846
    and 643 (later). The upper prompt figure of the protocol (4,400) was exceeded. *Fix:* report per
    successful call and recompute the token totals of 10a. Nemotron's figures are unaffected.
13. **Who enforces the cap.** Protocol 13 says the cap is enforced "by the calling code, not by a
    provider setting". `MODEL_ACCESS.md` says the hard limit is set in the provider account, with the
    code's call budget as a second limit. The frozen code counts attempts only (defaults 60 and 40)
    and has no notion of cost. *Fix:* both layers, as specified in section 3; the attempt budget set
    to 4 × calls.
14. **The Nemotron identifier.** Protocol 2 names `…:free`; configuration P uses the paid route.
    *Fix:* name the identifier of the chosen configuration.
15. **Critic calls.** v1's harness makes two critic calls per original; the protocol counts only
    proposal calls. *Fix:* name the prospective harness and state "no critic calls", or count them:
    360 calls at 60 papers, 720 at 120.
16. **The denominator of the 20 % ambiguity rule.** "Statistic-like numbers" in C6, all labelled
    numbers in the scorer. *Fix:* define one.
17. **A planted number whose original is adjudicated N or A** has no rule. *Fix:* the rule of section
    5.
18. **Pacing and re-sending failed calls.** There is no pacing rule under configuration F, and no rule
    on sending a failed call again later. *Fix:* pace F at the observed quota. Allow at most two
    further rounds, each at least 24 h later, for calls that failed only with retryable errors, all
    before step 4. No outcome can be seen at that point.
19. **Replay jobs lost to infrastructure.** There is no rule for them, although C4 requires 100 %.
    *Fix:* such a job may run again, and the event is recorded.

## 13. Recommendations, reasons, and the consequences of each alternative

### 13.1 ICC floor: keep 0.25

*Reasons:*

* In development, wherever an ICC could be estimated it was 0.06 to 0.41, mostly 0.26 to 0.41
  (section 6).
* A floor of 0 recreates draft 1's flaw: the "conservative" bound equals the bound that ignores
  clustering exactly when events are rare.
* 0.25 keeps C2a reachable at 60 papers (zero misleading flags, at least 5 exposed numbers per paper)
  and lets it tolerate 1 to 6 flags at 120.

*Addition:* a criterion met at 0.25 but not at 0.5 is reported as "not robust" (add to the
sensitivity rule of protocol 11). The scorer keeps using the estimate when it is larger.

*Alternatives:*

* **0.1:** C2a at 60 papers would tolerate up to 3 flags, and C1 is unchanged at 1. The value lies
  below the development estimates for coverage and detection, so it would be chosen for convenience,
  not from evidence.
* **0.5:** C2a cannot be met at 60 papers at all (lowest bound 2.47 %) and tolerates no flag at 120.
  C1 at 60 papers with 150 confirmations tolerates none. With 60 papers, this means the pilot cannot
  be justified, by construction.

### 13.2 Sample size: 120 papers, on conditions

*Reasons:*

* At 60 papers, C2 is a zero-tolerance test: one affected paper or one misleading flag fails it.
  With a 1 % true rate, the chance of passing is 55 %.
* At 120 papers, C2 tolerates one affected paper (66 %), and up to 5 flags in it with 10 exposed
  numbers per paper. C1 tolerates 6 instead of 1.
* The lower bound of D1 tightens a little: an observed recall of 24.6 % instead of 26.3 % is needed
  for 0.20.

*Conditions:*

* The preliminary round measures at most about an hour per paper.
* Adjudicators are recruited for 140 to 230 person-hours, or six people at 23 to 38 h each.
* Configuration P is chosen, because F at 120 papers needs at least 12 days of paced calls.

*Costs of 120:*

* adjudication doubles (140–230 person-hours against 70–115; resolver 22.5–37.5 h against
  11.2–18.8);
* model calls double (480 against 240), still under 30 USD;
* kernel time and replay double (about 20 h each, in 12 jobs).

*Consequences to accept in advance:*

* rules that tolerate zero events get harder with more papers. With a 1 % rate, all three contexts
  stay in scope with chance 0.30 at 120 papers against 0.55 at 60, and C6 is harder to meet;
* per context, a context without events still bounds its paper-level rate only at 7.2 %.

*Alternatives:*

* **60 papers:** half the work. A "not met" on C2 then says little about the system. The report
  must say so in advance.
* **105 papers (35 per context):** the smallest size at which C2b allows one affected paper, 12.5 %
  less work than 120. Its tables were not prepared and would have to be computed before approval.

### 13.3 Wording threshold: 0.20, on planted errors

*Definition to write into `criteria.json` (field `wording_rule`):* the lower bound, adjusted for the
design effect and using the ICC floor, of flag recall on planted errors; primary arm; contexts
pooled. Natural F numbers are reported separately and never used for the wording. If the threshold
is reached, the permitted wording is limited to: "in a test with deliberately altered numbers, it
flagged at least X % of them", followed by the measured recall and its interval. It is never
"finds errors in papers".

*Reasons:*

* Reaching 0.20 requires an observed recall of about 25 to 28 %, so only a detector whose true
  recall is around 0.3 or more is likely to qualify (chance 0.77 to 0.996).
* The threshold is a judgement, as protocol 9a says: no study of reviewers fixes it.

*Consequence:* at the development recall on planted errors (11.5 %), nothing may describe the tool
as finding errors. Every screen must then say that the absence of a flag carries no information.

*Alternatives:*

* **0.10:** needs an observed recall of 13.5 to 16.2 %. It allows "finds errors" for a tool that
  misses nearly nine in ten.
* **0.30:** needs 35 to 39 %.
* **Unset:** always "confirmation only". This is the simplest and fully conservative choice, but it
  gives up the incentive to measure detection.

### 13.4 C2c: keep 50 % and at least 5 flags, with two corrections

*Reasons:*

* 50 % is the weakest level at which a flag is an alert at all.
* 5 is the least number of flags at which zero misleading can pass, so the minimum is consistent
  with the bound.
* About 19 to 41 flags are expected at development recall, so the criterion should be evaluable.

*Corrections:*

1. Compute the bound with the design effect, as for every other claim-level bound. At least 8 flags
   are then needed when they come two per flagged paper.
2. Reword the meaning to say "among flags on original articles and planted-error copies". Report the
   share on originals separately, with its bound.

Also resolve item 5 as recommended.

*Alternatives:*

* **A threshold of 1/3:** needs at least 8 flags, and tolerates 2 misleading at 20 flags.
* **A threshold of 0.2:** needs at least 14 flags, and tolerates none at 20. At 60 papers, a single
  misleading flag would then fail it.
* **A minimum of 10 flags:** C2c is more often not evaluable, with no gain in meaning.
* **Keeping the bound that ignores clustering:** C2c is easier to pass than the criteria's own
  clustering assumption allows.

### 13.5 Screening cap: 600 per context for 120 papers (300 for 60), fallback as drafted

*Reasons* (`DS screening`):

* With a cap of 600, a context fills to 40 with chance 0.90 at an eligibility yield of 8 %, and 0.998
  at 10 %.
* At least 20 eligible papers (no shortfall) is near certain at any yield of 5 % or more (0.981).
* At v1's single measured yield (8 of 18), about 91 candidates fill a context.
* **The cost of the cap is screening effort.** At 10 to 20 minutes per candidate (**assumption**;
  nothing has been measured), the worst case is 300 to 600 h for three contexts at 600, and 150 to
  300 h at 300.

*The fallback:*

* Keep it. Falling back to 75 or 90 papers would not help C2b, which still allows no affected paper
  at those sizes.
* Decide now whether, after a fallback, steps 3 to 7 still cover every eligible paper (as drafted,
  for the pre-specified secondary analysis). That costs up to 120 papers' adjudication for a 60-paper
  primary analysis.

*Alternatives:*

* **A cap of 300 with 120 papers:** a context reaches 40 with chance 0.038 at a 10 % yield and 0.81
  at 15 % (`chance_40_within_300`). A fallback to 60 is then likely unless yields exceed about 15 %.
* **No cap:** unbounded screening effort.

### 13.6 Model configuration: P, capped at 30 USD (15 for 60), enforced in code

*Reasons:*

* Under F, Gemini's free tier failed 41 % of attempts in v1 and allowed about 20 calls a day. An
  unpaced run cannot reach the 90 % primary-complete rule (at most 8.3 % of papers at 120). A paced
  run takes at least 12 days, depends on a quota that cannot be verified, and is exposed to model
  changes for that long.
* The money at stake is small compared with the adjudication effort that a "not evaluable" result
  would waste: Nemotron costs 2.38 USD at measured sizes and 9.52 USD with four billed attempts per
  call.

*Required:*

* the budgeted transport and spend log of section 3;
* sub-caps (Nemotron 10 and Gemini 20 USD at 120 papers);
* the attempt budget set to 4 × calls;
* provider-side hard limits where offered;
* the Gemini price read and entered before authorisation. The run fits under the sub-cap if the
  average price is at most 14.56 USD per million tokens (3.64 USD if every call were billed four
  times);
* models re-listed before approval and before step 3. Keep `gemini-3.6-flash` and the paid
  Nemotron route, with the identifier in protocol 2 changed accordingly;
* exact identifiers, served versions, parameters and every response recorded (section 10).

*Alternatives:*

* **F:** costs nothing. It needs a pacing rule (at most about 20 Gemini calls a day: 6 days at 60
  papers, 12 at 120) and a rule for re-sending failed calls. The risk that the primary analysis is
  not evaluable is high. Inputs to free tiers may be used by the provider, which is acceptable only
  because they are public.
* **P with a cap enforced only by the provider:** a provider limit set by mistake or missing (an
  alert in place of a limit) would bound nothing. The code then has only an attempt budget, which
  does not bound money.

### 13.7 Before approval: a capacity run (no prospective data)

Run the kernel under the exact configuration of step 4 on the synthetic sizes of `../perf` and on
the eight development tables:

* two workers;
* at most two claims per proof file and 900 s per file;
* the proposed memory limit per process.

Record time per claim, peak memory per process and the share of runs that complete, for each
statistic. This run defines C7's supported size for each statistic (items 8 to 10) and confirms or
replaces the memory limit. It re-estimates the kernel time and the replay time that set the number
of replay jobs (section 4). In development, 2 of 33 kernel runs on a 617-row column did not
complete, already more than C7's 5 %. Whether C7 can be met is therefore an open question. It should
be settled on development data, not discovered in the prospective run.

## 14. Preliminary adjudication and operational feasibility study

**Is a study needed before committing to 120 papers? Yes.** The 120-paper design commits:

* 140–230 adjudicator person-hours and a resolver for 22.5–37.5 h;
* up to 300–600 h of screening (assumption: 10–20 minutes per candidate).

Every one of those figures rests on something nobody has measured:

* the plan's adjudication rates;
* the screening time;
* the yield in contexts B and C;
* a kernel time with no documented basis;
* supported sizes measured on synthetic data;
* provider reliability seen in 46 attempts.

Some of these failures would make the evaluation not evaluable at any size:

* more than 20 % ambiguous numbers;
* fewer than 90 % of papers primary-complete;
* fewer than 95 % of kernel runs completed (development already shows 2 of 33 incomplete).

A study on development and synthetic data finds this out for about 20 person-hours and a few
machine-hours. Its results are development-set findings. They enter no criterion and are reported
apart (adjudication plan, section 9).

**What it measures** (costs from `DS feasibility_study`):

* **A. Adjudication pilot.**
  * *Data:* the prepared `v1_discrepancies` package (3 papers, 30 numbers). Then a full-protocol
    package on the six held-out v1 papers, built by `build_package.py` and passed by
    `check_blinding.py`; the copies' labels are carried over (protocol 7).
  * *Measures:* minutes per paper per adjudicator (reading and per number); raw agreement and κ on
    the class; disagreement share; resolver minutes; the A share among T, F and A numbers; problems
    with the instructions.
  * *Needs:* the owner's authorisation to recruit two adjudicators and a resolver, with their
    independence confirmations. Time: 5.5–8.75 h per adjudicator and 1.1–1.9 h for the resolver,
    12–19 person-hours in all.
* **B. ICC estimate.**
  * *Data:* A's labels, with the cached v1 receipts, through `score.evaluate`.
  * *Measures:* the ICC of coverage and of detecting planted errors, which can be estimated.
    Development gave 0.49 and 0.32, both above the 0.25 floor, on six papers. The ICC of
    unsupported confirmations and misleading flags cannot be estimated from so few events; that is
    what the floor is for.
  * *Needs:* nothing beyond A.
* **C. Kernel resource profile** (the capacity run of 13.7).
  * *Data:* the synthetic sizes of `perf` and the eight development tables.
  * *Configuration:* that of step 4: 2 workers, one claim per proof file, 900 s, 7 GB under
    `lean_guard.py`.
  * *Measures:* by statistic and table size, time per claim, peak memory per process and completed
    share. From these: the supported sizes and kernel hours per paper, which give the total and the
    number of replay jobs.
  * *Needs:* Lean 4.28.0 on the reference machine; no people, no network.
* **D. Provider reliability** (optional).
  * *Data:* without a model call there is nothing beyond the v1 ledgers (Gemini 41 % of 29
    attempts failed; Nemotron 1 of 17). With authorisation, a smoke run through `budget.py` in the
    chosen configuration: the eight development papers that have a planted-error copy, 16 documents,
    32 calls.
  * *Measures:* per-call success and latency; served model versions; the spend log against the
    provider's statement.
  * *Needs:* the owner's authorisation of a model call. Nemotron costs 0.16 USD at measured sizes,
    plus Gemini at the price entered.
* **E. Screening time.**
  * *Data:* the 51 records of the v1 candidate pool. They are development material, already
    excluded from the prospective frame (protocol 4), and are screened again under draft 3's rules
    by the person who will screen.
  * *Measures:* minutes per candidate, and the yield under the draft-3 rules (context A only).
  * *Needs:* retrieving pool articles that are not in the repository is a network step the owner
    authorises.

**Not measurable before approval:**

* the yield in contexts B and C (the cap and fallback absorb it);
* failure rates of the providers at full scale;
* the rare-event ICC;
* the A share in other fields.

**Go / no-go for the 120-paper design.** All five must hold.

1. **Adjudication time:** the median minutes per paper on the full-protocol package is at most 60.
   At 120 papers that means at most 120 h per adjudicator with two, or 40 h with six
   (`adjudication_at_120_papers_by_measured_minutes_per_paper`). Between 60 and 90 minutes: 120
   papers only with six adjudicators (at most 60 h each). Above 90: 60 papers.
2. **Labels can carry the criteria:** κ on the class is at least 0.6 (a judgement: conventionally
   "substantial") and the A share is at most 10 %, half the protocol's limit. **Stop** if the A share
   exceeds 20 % or κ is below 0.4. The labels could not carry C1 to C3 at any size; revise the
   instructions and repeat the pilot.
3. **Kernel:** within the supported sizes, C7's limits hold on the development claims (median ≤ 60 s,
   95th percentile ≤ 300 s, peak ≤ 7 GB, ≥ 95 % complete). The projected kernel time at 120 papers is
   at most 60 h, which 12 replay jobs of 5 h absorb. Otherwise there are two options. If C7 fails
   within the supported size, shrink the supported sizes before approval, accepting lower coverage.
   If more than 60 h are projected, use more replay jobs, or 60 papers.
4. **Providers:** configuration P is chosen, and the guard is verified. If the owner authorises part
   D, that means every smoke call answered within its repeats, the spend log agreeing with the
   provider's statement, and served versions recorded. Configuration F is a no-go for 120 papers,
   since it needs at least 12 days of paced calls.
5. **Screening effort:** the measured minutes per candidate make the worst case (3 × 600 candidates)
   acceptable to the owner, for example at most 300 h at 10 minutes. Otherwise use a cap of 300 and
   60 papers.

**Outcomes:**

* If 1 or 5 fails while 2 to 4 hold: run the 60-paper design, with its zero-tolerance caveat stated
  in advance.
* If 2 fails: stop and revise; no prospective run.
* If 3 fails: change the supported sizes or the kernel configuration, then run C again.
* The owner decides at approval, with these measurements in hand.

## 15. Owner decisions: summary

| # | Decision | Options | Recommended | Main consequence |
| --- | --- | --- | --- | --- |
| 1 | ICC floor | 0.1 / **0.25** / 0.5 | **0.25**, grid reported, "not robust" if 0.5 changes the result | at 60 papers C2a needs 0 flags and ≥ 5 exposed numbers per paper; at 0.5 it is unattainable at 60 |
| 2 | Sample size | 60 / 105 / **120** | **120**, if the preliminary round confirms about 1 h per paper and adjudicators are recruited | removes the zero tolerance of C2 (one affected paper allowed); 140–230 person-hours of adjudication |
| 3 | Wording threshold (D1) | unset / 0.10 / **0.20** / 0.30 | **0.20**, on planted errors, contexts pooled, design-effect lower bound; limited wording | no "finds errors" wording is expected (development recall on planted errors 11.5 %) |
| 4 | C2c | 50 % with 5 flags / 1/3 / 0.2 | **50 %, 5 flags**, with the bound clustered as for the other criteria and the meaning reworded | evaluable at expected flag counts; ≥ 8 flags needed with clustering |
| 5 | Screening cap and fallback | 300 / **600** / none | **600** (300 for 60), fallback as drafted; decide whether all eligible papers proceed after a fallback | bounded worst-case screening effort of 300–600 h (assumption) |
| 6 | Model configuration | F / **P** | **P**, 30 USD total (15 for 60), sub-caps, cap enforced in code before every request, provider limits, Gemini price entered | evaluable within hours; owner authorises payment |
| 7 | Inconsistencies 1–19 (section 12) | review draft 3 | resolved in draft 3 (`AMENDMENTS_DRAFT_3.md`, each with its test) | the scorer computes what the protocol says |
| 8 | Capacity run on development and synthetic tables under the step-4 configuration | run / skip | run before approval (no prospective data) | defines C7's supported size, the memory limit and the kernel-time estimate |
| 9 | C2a: count each printed number once per paper | yes / as drafted | owner's choice; yes is more conservative | at 60 papers with 4 exposed numbers per document C2a then fails even with no flag |
| 10 | Re-list models; preliminary adjudication round; ethics submission for the usability study | authorise / wait | authorise; none of them touches a prospective paper | start of recruitment needs the owner's explicit authorisation |
| 11 | Preliminary adjudication and operational feasibility study (section 14) | run first / commit to 120 now | **run first**; commit to 120 only if every go criterion of section 14 holds | about 20 person-hours and a few machine-hours before committing hundreds of hours; adjudicator recruitment needs authorisation |
