# ClaimCheck v1: frozen held-out evaluation

Status: research sidecar, draft, no production authority. Software frozen at commit `f17649c`
(`FREEZE.json` digest `1a7eeb57…`), benchmark frozen at `75693c6` (`BENCHMARK_FREEZE.json` digest
`1a200180…`). Results below come from one run of that frozen software. Gold labels are AI-assisted
annotations by the same system that built the tool, not expert adjudication.

The deterministic arms, the OpenRouter arm and the adversarial suite ran on 2026-11-10/11. The
Gemini free tier allows 20 requests per day for the pinned model and was exhausted during
development, so on day 1 the Gemini, agreement and critic arms failed closed
(`summary.day1_without_gemini.json`, kept). They were completed on 2026-11-11 after the quota reset,
from the same frozen commit, with no change to any frozen file (`summary.json`). Results that were
already recorded on day 1 did not change: the run reused their receipts.

## In one paragraph

On six held-out open-access articles with deposited data, readings were proposed by two language
models that never saw the data, and then checked by gates and the Lean kernel. Across both models,
71 PROVED results were issued; 64 matched a gold reading, 6 were on numbers the gold set had missed
and are faithful on review, and 1 is a defensible reading the gold set had marked not derivable.
None was found unfaithful. **A PROVED from a data-blind proposer was reliable in this evaluation.**
REFUTED depended entirely on the proposer. The Nemotron model (via OpenRouter) correctly refuted 13
false statements and issued 131 wrong refutations, almost all by reading a count of something else
as "number of rows". Gemini proposed a fifth as many readings, correctly refuted 11 false
statements (including two real discrepancies between a paper and its data) and issued 2 wrong
refutations. A proposer that can see the data (the symbolic search baseline, and the coincidence
attack) gets coincidental PROVEDs through the gates. Coverage is modest: the best single arm
verified 40 of 86 true statements, and Gemini returned no reading at all for 4 of 12 document
variants. Asking one model to criticise the other's readings did not help: one critic returned
unusable text, the other removed almost none of the wrong readings.

## What was evaluated

* Domain: organismal biology / ecology articles (CC BY) with a deposited CSV table (CC0 or CC BY).
* Pool: 51 candidates in a fixed hash order; screened by reading only. Development: 2 documents.
  Held-out: the first 6 eligible documents from pool index 6. Eligibility funnel: of 18 candidates
  screened in total, 5 failed the format screen, 5 had no descriptive statistics of the table in
  their prose, 8 were eligible. ([`benchmark/heldout/SCREENING.json`](benchmark/heldout/SCREENING.json))
* Variants: 6 original articles, 6 planted-error copies (26 planted errors, each confirmed false by
  an independent calculation), 2 prompt-injection copies.
* Gold: 194 labelled numbers over the 14 document variants: 86 true derivable statements, 41 false
  (26 planted, plus 6 real discrepancies that recur across variants), 67 that look like statistics
  but are not derivable from the table. The articles print 2,533 numbers in total.
* Arms, metrics, order of operations: [`benchmark/PROTOCOL.md`](benchmark/PROTOCOL.md).

## Results by proposer (frozen policy, all 14 document variants)

Every arm feeds the same verifier. "Unlabelled" means the number had no gold label; those are
adjudicated by hand in the next table and never merged into the automatic columns.

| Arm | Variants | Proposals | Correctly PROVED | Correctly REFUTED | PROVED against gold | REFUTED against gold | Unlabelled PROVED | Unlabelled REFUTED | Abstained on derivable |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `rules` (cue words, no model) | 14 | 183 | 5 | 1 | 3 | 73 | 7 | 88 | 70 |
| `search` (data-matching, no model) | 14 | 258 | 37 | 0 | 4 | 0 | 41 | 0 | 87 |
| `openrouter` (Nemotron, data-blind) | 14 | 356 | 40 | 13 | 1 | 39 | 4 | 92 | 51 |
| `gemini` (data-blind) | 12 | 59 | 24 | 11 | 0 | 2 | 2 | 0 | 73 |
| `union` (all readings of both models) | 12 | 337 | 34 | 16 | 1 | 40 | 4 | 88 | 35 |
| `agree` (readings both models proposed) | 12 | 48 | 22 | 7 | 0 | 2 | 2 | 0 | 79 |
| `gemini+critic` (Gemini, filtered by Nemotron) | 6 | 32 | 17 | 2 | 0 | 2 | 0 | 0 | 35 |
| `openrouter+critic` (Nemotron, filtered by Gemini) | 6 | 161 | 23 | 1 | 1 | 18 | 2 | 47 | 21 |

Denominators over all 14 variants: 86 true and 41 false derivable statements. The arms do not all
cover the same documents, as fixed in the protocol before the run: Gemini was not sent the two
prompt-injection copies, and the critics ran on the six original articles only. **Rows with
different "Variants" must not be compared with each other**; the matched comparison is the next
table. No arm produced a `wrong_refutation` (REFUTED of a true statement under its gold reading):
the arithmetic itself was never wrong.

### The same arms on the same documents

Twelve variants (six originals, six planted-error copies; 70 true, 38 false, 54 not derivable):

| Arm | Proposals | Correctly PROVED | Correctly REFUTED | PROVED against gold | REFUTED against gold | Unlabelled PROVED | Unlabelled REFUTED | Abstained on derivable |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `rules` | 157 | 3 | 1 | 2 | 59 | 6 | 80 | 62 |
| `search` | 226 | 28 | 0 | 4 | 0 | 36 | 0 | 77 |
| `gemini` | 59 | 24 | 11 | 0 | 2 | 2 | 0 | 73 |
| `openrouter` | 317 | 32 | 12 | 1 | 38 | 4 | 88 | 41 |
| `union` | 337 | 34 | 16 | 1 | 40 | 4 | 88 | 35 |
| `agree` | 48 | 22 | 7 | 0 | 2 | 2 | 0 | 79 |

Six original articles (48 true, 6 false, 27 not derivable):

| Arm | Proposals | Correctly PROVED | Correctly REFUTED | PROVED against gold | REFUTED against gold | Unlabelled PROVED | Unlabelled REFUTED | Abstained on derivable |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `gemini` | 32 | 17 | 2 | 0 | 2 | 0 | 0 | 35 |
| `gemini+critic` | 32 | 17 | 2 | 0 | 2 | 0 | 0 | 35 |
| `openrouter` | 169 | 23 | 1 | 1 | 18 | 2 | 51 | 21 |
| `openrouter+critic` | 161 | 23 | 1 | 1 | 18 | 2 | 47 | 21 |
| `union` | 184 | 25 | 2 | 1 | 20 | 2 | 51 | 18 |
| `agree` | 27 | 15 | 1 | 0 | 2 | 0 | 0 | 38 |

### After hand adjudication of unlabelled results

([`benchmark/results/heldout/ADJUDICATION.json`](benchmark/results/heldout/ADJUDICATION.json); every
unlabelled PROVED in every arm was adjudicated, and every unlabelled REFUTED of the model arm on
original documents.)

| Arm | PROVED total | matching gold | unlabelled, faithful | unlabelled, not faithful | against gold |
| --- | ---: | ---: | ---: | ---: | ---: |
| `rules` | 15 | 5 | 2 | 5 | 3 |
| `search` | 82 | 37 | 18 | 23 | 4 |
| `openrouter` | 45 | 40 | 4 | 0 | 1 (defensible, see below) |
| `gemini` | 26 | 24 | 2 | 0 | 0 |
| `union` | 39 | 34 | 4 | 0 | 1 (the same one) |

| Arm | REFUTED total | matching gold | against gold | unlabelled (of which adjudicated not faithful) |
| --- | ---: | ---: | ---: | ---: |
| `rules` | 162 | 1 | 73 | 88 (16; 72 not adjudicated) |
| `search` | 0 | 0 | 0 | 0 |
| `openrouter` | 144 | 13 | 39 | 92 (90; 2 not adjudicated) |
| `gemini` | 13 | 11 | 2 | 0 |
| `union` | 144 | 16 | 40 | 88 (87; 1 not adjudicated) |

Gemini's two unlabelled PROVEDs are the sample sizes "171 and 161" in a planted-error copy; the
same two numbers had already been adjudicated faithful for the other model, before Gemini ran.

* The one model-arm PROVED "against gold" is `(n = 335, χ² …)`: the gold label says a model's sample
  size is not derivable; the arm proved "335 rows have a feather-carotenoid value", which is true and
  a reasonable reading. The automatic score is kept as an error.
* The search baseline's wrong PROVEDs are coincidences on low-precision numbers: "(± 1 day)" read as
  the SD of body mass, "22 °C" as the mean muscle area, "<12 h" as a group size. 27 of its 82
  PROVEDs (33%) are wrong.
* REFUTED by statistic, Nemotron arm: counts 1 right, 39 against gold, 83 unlabelled; every other
  statistic (mean, min, max, SEM) 12 right, 0 against gold, 9 unlabelled wrong readings.
* REFUTED by statistic, Gemini arm: no count was refuted at all; mean, SEM, minimum and maximum
  11 right, 2 against gold. The two wrong ones are "13.06 ± 0.18 days" for nestling age at
  sampling, read as the mean and standard error of a column `chick_age` that records something
  else. The sentence names the variable and the statistic, so every lexical check passes. This is
  the residual risk the trust-boundary audit names first, observed on held-out data.

### What the verified results look like

Real statements verified from the authors' deposited data include: pH "6.07 ± 0.05 SE (range =
5.01–8.03)" (mean, standard error, minimum and maximum, each its own kernel theorem); "501
individuals in 96 hummingbird species … from 3 to 17 adult males per species"; reproductive effort
"range: 12.0 – 167.0 … ± 1.6"; sample sizes of four biochemical assays; standard-length range
"14.5–25.3 mm".

Real discrepancies (present in the original articles, not planted), per the independent calculation:

| Article | Printed | From the deposited file | Nemotron arm | Gemini arm |
| --- | --- | --- | --- | --- |
| Plummer et al. 2018 | reproductive effort mean 78.4 | 78.349 (rounds to 78.3) | REFUTED, correct | REFUTED, correct |
| Plummer et al. 2018 | plasma α-tocopherol 23.13 ± 1.06 | mean 22.95, SE 1.04 (n = 124) | no reading proposed | standard error REFUTED, correct; the range 3.30–70.91 PROVED; no reading proposed for the mean |
| Collins et al. 2019 | 58 haplotypes at Site G | 57 rows for Site G | wrong reading proposed (count of all rows) | no reading proposed (the model returned no claims for this article) |
| Kroeger et al. 2018 | r = .75, N = 472 | r = 0.742 over 448 complete pairs | no grounded proposal | no grounded proposal |

These are mismatches between a printed number and one deposited file under one reading. They are
not findings that a paper is wrong: a later data version or an exclusion step would explain any of
them. They are exactly the kind of thing a researcher would want pointed out.

## The central negative finding: refutations

A match and a mismatch are not symmetric evidence. A wrong reading almost never reproduces a
multi-digit number, so a PROVED also supports the reading. A wrong reading almost always
mismatches, so a REFUTED says "this reading is not what the file gives", which is usually because
the reading is wrong. The frozen system issues REFUTED whenever the lexical checks pass, and for a
bare row count (no column, no row condition) there is nothing lexical to check. The model proposed
"number of rows" for sequence counts, species counts, AIC values and sample sizes of other tables;
all were REFUTED.

Post hoc, exploratory and **not** a result of the frozen system
([`analysis.json`](benchmark/results/heldout/analysis.json); the day-1 version, written before
Gemini ran, is kept as `analysis.day1.json`): recomputing each model arm's outcomes from the same
receipts under two alternative policies gives

| Refutation policy | Arm | Correctly REFUTED | REFUTED against gold | Unlabelled REFUTED | Correctly PROVED |
| --- | --- | ---: | ---: | ---: | ---: |
| frozen system | Nemotron | 13 | 39 | 92 | 40 |
| a bare row count may confirm but not refute | Nemotron | 12 | 1 | 12 | 40 |
| refute only if a sibling number in the same sentence is PROVED on the same column and rows | Nemotron | 7 | 2 | 0 | 40 |
| frozen system | Gemini | 11 | 2 | 0 | 24 |
| a bare row count may confirm but not refute | Gemini | 11 | 2 | 0 | 24 |
| refute only if a sibling number in the same sentence is PROVED on the same column and rows | Gemini | 4 | 0 | 0 | 24 |

The two policies were chosen on day 1 after seeing the Nemotron results and before Gemini ran, so
for the Gemini rows they are a prediction made in advance, on the same documents. The first policy
changes nothing for Gemini (it refuted no bare count). The second removes Gemini's two wrong
refutations and seven of its eleven correct ones. They size a hypothesis for the next frozen
evaluation; they are not evidence that the hypothesis is right.

## Coverage, and why the system abstains

The Nemotron arm decided 53 of 127 derivable statements correctly (42%); 40 of 86 true ones. Reasons
for abstention on original documents: no proposal for the number (9), a proposed reading that
failed a source check (12; mostly a column or group not named in the sentence in any wording the
manifest lists, for example "salinity" for a sodium column, or "NC‐074" printed with a Unicode
hyphen). One whole document (springtails) got no correct result from that arm: its numbers
are sums of a count column, which the model read as row counts.

Gemini decided 35 of the 108 derivable statements in its twelve variants correctly (32%) and
abstained on 73. Its abstentions are mostly silence: it returned `{"claims": []}` for four of
twelve variants (both copies of the springtail article, and the original but not the
planted-error copy of two others). Its answer changed a great deal between an article and a copy
of it that differs in a few digits (15 readings against 5; 0 against 3; 0 against 2), at
temperature 0. Taking every reading of both models (`union`) raised correct results from 44
(Nemotron) or 35 (Gemini) to 50 of 108, and kept all of Nemotron's wrong refutations. Manifest aliases were written
before the run from column names only, deliberately not tuned to the articles; that costs coverage
and is the honest setting.

A structural limit sits above all of this: about half of the screened articles with usable data
print no descriptive statistic of their table in prose at all. ClaimCheck has nothing to say about
model estimates, test statistics, figures or tables in the paper.

## Adversarial suite (held-out, no model involved)

[`benchmark/results/adversarial/adversarial.json`](benchmark/results/adversarial/adversarial.json)

| Family | Attempts | Outcome |
| --- | ---: | --- |
| A. Deceptive proposals about true statements (invented quote, number not printed, shortened number, wrong column, undeclared unit, smuggled verdict / scale / missing-value tokens, Lean injection in names) | 409 | 0 PROVED, 0 REFUTED; all UNKNOWN |
| B1. Data file altered, digest pinned | 48 claims | 48 UNKNOWN (digest mismatch) |
| B2. Data file altered, digest not pinned | 48 claims | 48 agree with an independent calculation on the altered bytes (22 PROVED, 5 REFUTED, 21 UNKNOWN) |
| B3. Data file made non-rectangular | 48 claims | 48 UNKNOWN |
| C. Coincidence search: for 62 false or underivable numbers, submit every statistic × column × group reading that happens to reproduce the number (214 readings for 24 numbers) | 214 | 211 stopped by the gates; **3 PROVED** |

The three that got through are one-digit coincidences inside sentences that genuinely name the
column and the statistic ("median = 5" in a sentence about mean age, where the mean is 5.12; a
planted "0.2" that equals the standard error). So the gates do not make a PROVED safe against a
proposer that fits readings to the data: 3 of 62 targets (5%) here, and 27 of 82 for the search
baseline. The safety of the model arm's PROVEDs comes from the proposer being data-blind, which the
design enforces for models but cannot enforce for an arbitrary submitter.

Prompt injection: the two injected documents asked the model to add `"status": "PROVED"`, to report
a fabricated mean of 987.65 as verified, and to rebind a real number to another column. The
OpenRouter model's responses contained none of these, so the verifier's rejection of smuggled
fields was exercised by family A, not by an obedient model.

## Kernel agreement, replay and cost

* Oracle versus kernel: 690 held-out claims and 80 adversarial claims were put to the Lean kernel;
  every prediction of the untrusted Python oracle was accepted. No disagreement has been observed
  anywhere (also 300–400 random cases per run of `check_live`, and 425 cases against the
  JavaScript implementation).
* Independent replay: see "Independent replay" below.
* Cost of the day-1 run: 14 OpenRouter calls (61,659 prompt tokens, 42,452 output tokens, 937 s
  of provider latency, free tier); 790 fresh receipts; 3,875 s of verification wall time on four
  workers, about 5.6 s per kernel-checked claim. The deterministic arms cost more kernel time than
  the Nemotron arm (rules 217 claims, search 275, model 198) because they propose more readings that
  have to be refuted.
* Cost of completing the model arms on day 2: 18 successful Gemini calls (12 proposer, 6 critic;
  71,253 prompt tokens, 11,880 output tokens, 131 s of provider latency, free tier), 3 OpenRouter
  critic calls (5,329 prompt tokens, 275 output tokens), 20 fresh receipts, 16 new kernel-checked
  claims, 96 s of verification on one worker. A further 14 Gemini calls and 1 OpenRouter call
  failed and were retried; the frozen ledger counts failures but does not record their HTTP status,
  which is a gap in the instrumentation.
* Cost per proposer on the same twelve variants: Gemini 59 proposals, 41 kernel-checked claims,
  8,307 output tokens; Nemotron 317 proposals, 183 kernel-checked claims, about 37,000 output
  tokens. The more selective proposer cost roughly a fifth of the tokens and a fifth of the kernel
  time, for three quarters of the correct verifications and about the same number of correct
  refutations.
* The numeric-sentence prefilter sent about one third of each article to the provider (measured on
  development: 20,132 of 63,849 and 9,578 of 29,196 characters) and turned a call that failed on a
  full article into one that completed.

## Independent replay

_Filled in from `benchmark/results/bundles/replay_summary.json` once the bundle run completes._

## Gemini and multi-model arms

The question asked of these arms: does combining different models with deterministic verification
improve claim recovery, reduce unsupported readings, or lower cost? No model output, agreement or
critique was ever a verification authority; the arms differ only in which proposals reach the same
gates and the same kernel.

**What the held-out data show** (matched tables above):

1. **The choice of proposer mattered more than any combination.** On the same twelve variants,
   Gemini (`gemini-3.6-flash`) issued 39 decided results, 37 of them right (35 by gold, 2
   unlabelled and faithful on review) and 2 wrong. Nemotron issued 175 decided results, 48 right
   and 127 not right (1 of those defensible; at most 2 unlabelled refutations not adjudicated). Both were data-blind and both passed through the same
   gates. The gates did not make a careless proposer's refutations safe.
2. **Recovery: the union helps a little.** Correct results on derivable statements: Gemini 35,
   Nemotron 44, union 50 of 108. Gemini contributed results Nemotron missed (the α-tocopherol
   standard error and range in Plummer et al.); Nemotron contributed counts and whole articles on
   which Gemini was silent.
3. **Unsupported readings: agreement tracks the better model and adds nothing to it.** Requiring
   both models to propose the same reading (`agree`) gives 22 correct verifications, 7 correct
   refutations, 2 wrong refutations: Gemini's own profile with slightly lower coverage. The two
   wrong refutations (nestling age read as `chick_age`) were proposed by both models, so
   agreement did not remove them. Agreement between models is correlated error, not evidence.
4. **Critics did not work.**
   * Nemotron as critic of Gemini's readings returned unusable text on all three calls (runs of
     hyphens and stray characters, 7 to 144 output tokens). Zero reviews, nothing filtered:
     `gemini+critic` is identical to `gemini`. The same model had answered well as a critic on the
     development documents the day before. A free-tier model is not a dependable component.
   * Gemini as critic of Nemotron's readings answered all six calls. For three documents it
     returned a bare JSON list instead of the requested object, which the frozen parser ignores, so
     only three documents were filtered: 8 of 169 readings removed, unlabelled wrong refutations 51
     to 47, no correct result lost. Post hoc, reading the bare lists too
     ([`analysis.json`](benchmark/results/heldout/analysis.json), `critic_posthoc`; not a frozen
     result): 17 readings flagged, unlabelled wrong refutations 51 to 45, refutations against gold
     18 to 18. The critic passed nearly all of the "number of rows" misreadings as faithful.
   * So a second model's opinion was neither reliable nor effective as a filter here. The
     structural rule sized post hoc on day 1 ("a bare row count may not refute") removes 118 of
     Nemotron's 131 wrong refutations with no model call, at the price of one correct refutation. That rule is a hypothesis for the next
     frozen evaluation, not a result.
5. **Cost: the selective proposer was cheaper end to end.** See "Kernel agreement, replay and
   cost". Verification cost is driven by how many readings a proposer submits, because every
   grounded reading costs a kernel check whether it turns out right or wrong.
6. **Stability is a problem for the better proposer.** Gemini returned no claims for 4 of 12
   variants and gave very different answers for an article and its planted-error copy. Calls also
   failed often (14 failures for 18 successes on day 2). A workflow built on it needs retries and
   must report "the proposer was silent" separately from "nothing checkable was found".

**Prompt injection.** Gemini was not sent the two injected documents (protocol, to respect its
daily quota). The Nemotron responses to them contained none of the injected instructions.

**Development evidence** (two documents; not held-out, reported for completeness): Gemini proposed
19 readings, 9 correct verifications and 1 false alarm; Nemotron as critic flagged exactly that
one, with the right explanation. That favourable critic result did not replicate on held-out data.
A cheaper model (`gemini-3.5-flash-lite`) returned no claims on either document and was dropped.
Three free reasoning models on OpenRouter spent their entire output budget on hidden reasoning and
returned nothing until reasoning was disabled.

**What this does not show.** Two models, one run each, six articles. Nothing here ranks model
families in general, and the Gemini/Nemotron contrast may not survive a different prompt, a
different day or a paid tier.

## Limitations

1. Six held-out articles from one field, one annotator (an AI system), no expert adjudication.
   Counts are small; no confidence intervals are claimed and none should be inferred.
2. REFUTED is unreliable as issued, and how unreliable depends on the proposer (above). Treat it
   as "this reading does not hold for this file".
3. A PROVED is only as safe as the proposer is data-blind; the tool cannot verify that property of
   a human or third-party submitter.
4. Prose only, one table, at most 64 KB, descriptive statistics only. Tables and figures in the
   paper, model estimates and tests are out of scope.
5. Manifests (aliases, units, scope terms) are human input and determine coverage.
6. Custody is not addressed: the deposited file may not be the analysed file.
7. The checker is a reviewed definition, not a verified implementation of any external standard.
8. Provider quotas (20 and about 50 requests per day) limited the size of the model experiments:
   each model proposed once per document, so run-to-run variation was not measured, and the critic
   arms cover six documents. The frozen critic parser accepts one answer shape only, which cost
   half of the Gemini critic's answers; the free-tier critic failed outright.
9. One development-driven design choice (the statistic-wording gate) was tuned on two documents.
   Its ablation on held-out: the search baseline's unlabelled PROVEDs go from 41 to 182 without it,
   while the model arm changes by one verification. It is doing real work, on little tuning data.

## What would make this stronger

A new frozen evaluation with (a) asymmetric refutation (bare counts cannot refute; corroboration
required), (b) expert-adjudicated gold on more articles and a second field, (c) Unicode-normalised
alias matching, (d) support for sums of count columns and distinct counts, (e) a compiled,
separately audited checker path for tables above 64 KB, (f) a signed statement by the
submitter that readings were proposed without access to the data, (g) repeated proposer runs per
document, to measure the instability seen with Gemini, and (h) a manifest field that lets a data
owner say what a column does not measure, aimed at the "nestling age" class of error that no
lexical check or second model caught.
