# ClaimCheck v1: frozen held-out evaluation

Status: research sidecar, draft, no production authority. Software frozen at commit `f17649c`
(`FREEZE.json` digest `1a7eeb57…`), benchmark frozen at `75693c6` (`BENCHMARK_FREEZE.json` digest
`1a200180…`). Results below come from one run of that frozen software. Gold labels are AI-assisted
annotations by the same system that built the tool, not expert adjudication.

**Gemini arms: see the section "Gemini and multi-model arms".** The deterministic arms, the
OpenRouter arm and the adversarial suite ran on 2026-11-10/11. The Gemini free tier allows 20
requests per day for the pinned model and was exhausted during development, so the Gemini,
agreement and critic arms fail closed in `summary.day1_without_gemini.json` and are completed from
the same frozen commit after the quota reset.

## In one paragraph

On six held-out open-access articles with deposited data, readings proposed by a language model
that never saw the data and then checked by gates and the Lean kernel produced 45 PROVED results;
40 matched a gold reading, 4 were on numbers the gold set had missed and are faithful on review,
and 1 is a defensible reading the gold set had marked not derivable. None was found unfaithful.
The same arm correctly REFUTED 13 false statements (12 planted, 1 real discrepancy between a paper
and its data). But it also issued 131 REFUTED results that are wrong readings, almost all of them
the model treating a count of something else as "number of rows". **A PROVED from a data-blind
proposer was reliable in this evaluation; a REFUTED, as the frozen system issues it, was not.** A
proposer that can see the data (the symbolic search baseline, and the coincidence attack) gets
coincidental PROVEDs through the gates. Coverage is modest: 40 of 86 true statements verified.

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

| Arm | Proposals | Correctly PROVED | Correctly REFUTED | PROVED against gold | REFUTED against gold | Unlabelled PROVED | Unlabelled REFUTED | Abstained on derivable |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `rules` (cue words, no model) | 183 | 5 | 1 | 3 | 73 | 7 | 88 | 70 |
| `search` (data-matching, no model) | 258 | 37 | 0 | 4 | 0 | 41 | 0 | 87 |
| `openrouter` (Nemotron, data-blind) | 356 | 40 | 13 | 1 | 39 | 4 | 92 | 51 |

Denominators: 86 true and 41 false derivable statements. No arm produced a `wrong_refutation`
(REFUTED of a true statement under its gold reading): the arithmetic itself was never wrong.

### After hand adjudication of unlabelled results

([`benchmark/results/heldout/ADJUDICATION.json`](benchmark/results/heldout/ADJUDICATION.json); every
unlabelled PROVED in every arm was adjudicated, and every unlabelled REFUTED of the model arm on
original documents.)

| Arm | PROVED total | matching gold | unlabelled, faithful | unlabelled, not faithful | against gold |
| --- | ---: | ---: | ---: | ---: | ---: |
| `rules` | 15 | 5 | 2 | 5 | 3 |
| `search` | 82 | 37 | 18 | 23 | 4 |
| `openrouter` | 45 | 40 | 4 | 0 | 1 (defensible, see below) |

| Arm | REFUTED total | matching gold | against gold | unlabelled (of which adjudicated not faithful) |
| --- | ---: | ---: | ---: | ---: |
| `rules` | 162 | 1 | 73 | 88 |
| `search` | 0 | 0 | 0 | 0 |
| `openrouter` | 144 | 13 | 39 | 92 (90; 2 not adjudicated) |

* The one model-arm PROVED "against gold" is `(n = 335, χ² …)`: the gold label says a model's sample
  size is not derivable; the arm proved "335 rows have a feather-carotenoid value", which is true and
  a reasonable reading. The automatic score is kept as an error.
* The search baseline's wrong PROVEDs are coincidences on low-precision numbers: "(± 1 day)" read as
  the SD of body mass, "22 °C" as the mean muscle area, "<12 h" as a group size. 27 of its 82
  PROVEDs (33%) are wrong.
* REFUTED by statistic, model arm: counts 1 right, 39 against gold, 83 unlabelled; every other
  statistic (mean, min, max, SEM) 12 right, 0 against gold, 9 unlabelled wrong readings.

### What the verified results look like

Real statements verified from the authors' deposited data include: pH "6.07 ± 0.05 SE (range =
5.01–8.03)" (mean, standard error, minimum and maximum, each its own kernel theorem); "501
individuals in 96 hummingbird species … from 3 to 17 adult males per species"; reproductive effort
"range: 12.0 – 167.0 … ± 1.6"; sample sizes of four biochemical assays; standard-length range
"14.5–25.3 mm".

Real discrepancies (present in the original articles, not planted), per the independent calculation:

| Article | Printed | From the deposited file | Model arm |
| --- | --- | --- | --- |
| Plummer et al. 2018 | reproductive effort mean 78.4 | 78.349 (rounds to 78.3) | REFUTED, correct |
| Plummer et al. 2018 | plasma α-tocopherol 23.13 ± 1.06 | mean 22.95, SE 1.04 (n = 124) | no reading proposed for these two numbers (the search baseline proved the accompanying range 3.30–70.91; by construction it never refutes) |
| Collins et al. 2019 | 58 haplotypes at Site G | 57 rows for Site G | wrong reading proposed (count of all rows) |
| Kroeger et al. 2018 | r = .75, N = 472 | r = 0.742 over 448 complete pairs | no grounded proposal |

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
([`analysis.day1.json`](benchmark/results/heldout/analysis.day1.json)): recomputing the model arm's
outcomes from the same receipts under two alternative policies gives

| Refutation policy (model arm) | Correctly REFUTED | REFUTED against gold | Unlabelled REFUTED | Correctly PROVED |
| --- | ---: | ---: | ---: | ---: |
| frozen system | 13 | 39 | 92 | 40 |
| a bare row count may confirm but not refute | 12 | 1 | 12 | 40 |
| refute only if a sibling number in the same sentence is PROVED on the same column and rows | 7 | 2 | 0 | 40 |

These were chosen after seeing the results. They size a hypothesis for the next frozen evaluation;
they are not evidence that the hypothesis is right.

## Coverage, and why the system abstains

The model arm decided 53 of 127 derivable statements correctly (42%); 40 of 86 true ones. Reasons
for abstention on original documents: no proposal for the number (9), a proposed reading that
failed a source check (12; mostly a column or group not named in the sentence in any wording the
manifest lists, for example "salinity" for a sodium column, or "NC‐074" printed with a Unicode
hyphen). One whole document (springtails) got no correct result from the model arm: its numbers
are sums of a count column, which the model read as row counts. Manifest aliases were written
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
* Cost of the held-out run: 14 OpenRouter calls (61,659 prompt tokens, 42,452 output tokens, 937 s
  of provider latency, free tier); 790 fresh receipts; 3,875 s of verification wall time on four
  workers, about 5.6 s per kernel-checked claim. The deterministic arms cost more kernel time than
  the model arm (rules 217 claims, search 275, model 198) because they propose more readings that
  have to be refuted.
* The numeric-sentence prefilter sent about one third of each article to the provider (measured on
  development: 20,132 of 63,849 and 9,578 of 29,196 characters) and turned a call that failed on a
  full article into one that completed.

## Independent replay

_Filled in from `benchmark/results/bundles/replay_summary.json` once the bundle run completes._

## Gemini and multi-model arms

Development evidence (two documents; not held-out):

* Gemini (`gemini-3.6-flash`) proposed 19 readings; 9 correct verifications, 1 false alarm (a mean
  male body mass read against a females-only table).
* The OpenRouter model, asked to criticise Gemini's readings, flagged exactly that one, with the
  right explanation. A critic can only remove a proposal before verification; it has no authority.
* The OpenRouter model found counts Gemini had missed, and proposed more wrong readings.
* A cheaper model (`gemini-3.5-flash-lite`) returned no claims on either document and was dropped.
* Three free reasoning models on OpenRouter spent their entire output budget on hidden reasoning
  and returned nothing until reasoning was disabled.

Held-out results for `gemini`, `union`, `agree`, `gemini+critic` and `openrouter+critic` are
appended below when the run completes. Until then, no claim is made about whether combining models
improves recovery or reduces unsupported readings on held-out data.

## Limitations

1. Six held-out articles from one field, one annotator (an AI system), no expert adjudication.
   Counts are small; no confidence intervals are claimed and none should be inferred.
2. REFUTED is unreliable as issued (above). Treat it as "this reading does not hold for this file".
3. A PROVED is only as safe as the proposer is data-blind; the tool cannot verify that property of
   a human or third-party submitter.
4. Prose only, one table, at most 64 KB, descriptive statistics only. Tables and figures in the
   paper, model estimates and tests are out of scope.
5. Manifests (aliases, units, scope terms) are human input and determine coverage.
6. Custody is not addressed: the deposited file may not be the analysed file.
7. The checker is a reviewed definition, not a verified implementation of any external standard.
8. Provider quotas (20 and about 50 requests per day) limited the size of the model experiments.
9. One development-driven design choice (the statistic-wording gate) was tuned on two documents.
   Its ablation on held-out: the search baseline's unlabelled PROVEDs go from 41 to 182 without it,
   while the model arm changes by one verification. It is doing real work, on little tuning data.

## What would make this stronger

A new frozen evaluation with (a) asymmetric refutation (bare counts cannot refute; corroboration
required), (b) expert-adjudicated gold on more articles and a second field, (c) Unicode-normalised
alias matching, (d) support for sums of count columns and distinct counts, (e) a compiled,
separately audited checker path for tables above 64 KB, and (f) a signed statement by the
submitter that readings were proposed without access to the data.
