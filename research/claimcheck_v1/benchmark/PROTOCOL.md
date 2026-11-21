# ClaimCheck v1 benchmark protocol (frozen before any held-out document is opened)

This protocol is written and committed **before** the held-out documents are acquired, read or
annotated. The commit that adds `FREEZE.json` fixes the software; later commits may add held-out
material, results and documentation but may not change any file listed in `FREEZE.json`. If a
defect is found after the freeze, the frozen result stays as recorded and any fix is reported
separately and labelled post hoc.

## Question

For numbers printed in the prose of open-access research articles, can a system decide, with
kernel-checked arithmetic and inspectable source bindings, whether the number is the stated
descriptive statistic of the article's deposited data table, without ever asserting more than that?

## Domain and scope

* Articles: open-access, CC BY (or CC0) organismal biology, ecology and evolution articles with full
  text in Europe PMC.
* Data: an openly licensed (CC0 or CC BY) tabular deposit on Zenodo linked to the article.
* Claims in scope: counts, shares/percentages, sums, means, medians, minima, maxima, standard
  deviations, standard errors, sample variances, Pearson correlations and two-variable least-squares
  slope/intercept, each over one table with optional row conditions.
* Out of scope (must end as UNKNOWN): test statistics, model estimates, quantiles, distinct counts,
  transformed or weighted values, numbers in tables/figures of the article, values from other
  studies, anything needing more than one table.

## Candidate pool and selection (no outcome-dependent choices)

1. `candidates.json` is the pool: 51 Zenodo dataset records found on 2026-11-10 by twelve fixed
   keyword queries, restricted to records with an openly licensed CSV file of 300–64,000 bytes, at
   most 12 files, and a related article that Europe PMC lists as open access under CC BY/CC0 with a
   PMCID. The pool is ordered by SHA-256 of `zenodo:<record id>`.
2. Documents are screened strictly in that order. A candidate is **eligible** if
   (E1) the Europe PMC full-text XML is retrievable;
   (E2) at least one CSV of at most 64,000 bytes (not a README) is read by Python's `csv` module as
        a rectangular comma-separated table with at least two columns; the **largest** such file is
        the document's table (chosen by size, never by results);
   (E3) reading the article prose (title, abstract, body paragraphs, captions; not tables) finds at
        least two printed numbers that appear to be descriptive statistics of that table's rows.
   E3 is judged by reading only. ClaimCheck is never run on a candidate during screening.
3. Development set: the eligible documents among pool indices 0–5 (indices 1 and 3; indices 0, 2, 4, 5
   were screened out: 0 and 5 fail E2, 2 and 4 fail E3).
4. Held-out set: the first **six** eligible documents from pool index 6 onward. Every screened
   candidate and the reason for any exclusion is logged in `heldout/SCREENING.json`.

## Annotation (gold labels)

Prepared by the same AI system that built the software, from the article text and the data file,
using only spreadsheet-style inspection and an independent calculation (`csv` module + `Decimal`);
**ClaimCheck's oracle, gates and Lean checker are not run on held-out material before the
benchmark freeze commit.** These are internal AI-assisted annotations, not expert adjudication.

* The dataset manifest (units, missing-value tokens, column and group aliases, out-of-scope terms)
  is written first, from the data file's headers, values and the deposit's own description, using
  ordinary English forms of the column names (for example `Body_Mass` → "body mass", "weigh"). It is
  not tuned to the article's sentences.
* Every prose number that the annotator judges to be an in-scope descriptive statistic of the table
  gets a gold item with one or more typed readings and a truth value (`consistent`, `inconsistent`,
  or `conditional` when the value matches under only one standard-deviation convention), computed
  with the independent calculation.
* Numbers that look like such statistics but are not derivable (other table, other study,
  unsupported statistic, unit without exact conversion) are labelled `not_derivable` with a reason.
* All other numbers are unlabelled. A PROVED or REFUTED on an unlabelled number is reported as
  `unannotated_proved` / `unannotated_refuted`, and each is adjudicated by hand **after** the run in
  a separate, clearly labelled table. The automatic counts are never overwritten.

## Document variants

* `original`: the article text as acquired.
* `mutated`: a synthetic copy with planted errors (`mutate.py`, seeded by the slug): about half of
  the true derivable numbers are changed (value perturbation, or unit swap where convertible), each
  confirmed false by the independent calculation.
* `injected` (two documents, the first two held-out slugs in order): a synthetic copy with three
  appended hostile paragraphs (`inject.py`). Because of the Gemini daily quota, injection variants
  are run with the deterministic arms and the OpenRouter model only.

## Arms

Every arm only produces untrusted proposals; all share one verifier (gates + Lean kernel).

| Arm | Proposer |
| --- | --- |
| `rules` | cue-word rules; no model; never looks at data values |
| `search` | exhaustive data-matching search; no model |
| `gemini` | `gemini-3.6-flash` (Google AI Studio API), numeric-sentence prefilter, data dictionary only |
| `openrouter` | `nvidia/nemotron-3-ultra-550b-a55b:free` (OpenRouter), same prompt |
| `union` | both models' proposals |
| `agree` | readings both models proposed independently (same number, extensionally the same reading) |
| `gemini+critic` | Gemini proposals minus those the OpenRouter model judges unfaithful (original variant only) |
| `openrouter+critic` | the reverse (original variant only) |

Model agreement, critic approval and model confidence are never verification authority. They decide
only which proposals are submitted to the verifier.

Provider constraints (free tiers): 20 requests per day for `gemini-3.6-flash`, about 50 per day on
OpenRouter. One proposer call per document variant per model; critic calls on original variants
only. Model responses are cached and committed, so the benchmark replays without any API call.
Only article sentences that print a number, column names, units, aliases and group labels are sent
to a provider; data rows are never sent. All sent text is already public under CC BY/CC0.

## Outcomes and metrics

Unit of evaluation: one printed number in one document variant. If an arm yields distinct grounded
readings of the same number with different verdicts, its outcome for that number is UNKNOWN.

Primary policy: the receipt result as issued (all gates). Ablation: the same receipts with the
statistic-wording gate ignored.

Per arm, over all gold items of all held-out document variants:

* `correct_verification`: PROVED, reading extensionally equal to a gold reading, truth consistent
* `correct_refutation`: REFUTED, reading equal to gold, truth inconsistent
* `unsupported_positive`: PROVED where the truth is inconsistent/conditional/not derivable, or with
  a reading that is not a gold reading
* `unsupported_refutation`: REFUTED of a not-derivable number or with a non-gold reading;
  `wrong_refutation`: REFUTED of a true statement under its gold reading (would indicate a defect)
* `abstained` / `correct_abstention` / `conditional_only` / `correct_conditional`
* `unannotated_proved`, `unannotated_refuted` (adjudicated after the run, reported separately)
* coverage = decided gold items / derivable gold items
* cost: model calls, prompt and output tokens, kernel-checked claims, verification wall time

Also reported: the adversarial suite (`adversarial.py`, families A, B, C), independent replay of
every arm's receipts for one bundle per held-out document, agreement between the Python oracle and
the Lean kernel, and the eligibility funnel.

## Order of operations

1. Commit this protocol, the software and `FREEZE.json` (software freeze). Push.
2. Screen and acquire held-out candidates in pool order; write manifests, then gold labels; build
   variants. Commit `heldout/` and `BENCHMARK_FREEZE.json` (benchmark freeze). Push.
3. Run the benchmark and adversarial suite once from the frozen software. Commit all results,
   including failures. Provider quota may force the model arms to run on a later day than the
   deterministic arms; the software and benchmark freezes are the same for both.
4. Hand-adjudicate unannotated results; write the report. Negative findings stay in.
