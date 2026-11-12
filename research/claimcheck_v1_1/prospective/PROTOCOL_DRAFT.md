# ClaimCheck v1.1 prospective evaluation: protocol for owner review

**Status: DRAFT. Not approved, not frozen, not run.** No new paper has been fetched, screened,
labelled or scored for this evaluation. On approval, this file and `criteria.json` are frozen by
digest (section 12) and nothing in them changes afterwards.

The seven items requested for review are: the protocol (sections 1 to 8), thresholds (9), sample
size and uncertainty (10), the analysis plan (11), exclusions and contamination safeguards (4),
definitions (7), and readiness criteria for three levels (9 and `criteria.json`).

## 1. Question

On papers and datasets that nobody involved has seen, how often does ClaimCheck v1.1

* confirm a printed number that it should not have confirmed (unsupported confirmation),
* flag a discrepancy that is not one (misleading refutation),
* confirm true statements and detect real mismatches (coverage),
* and abstain,

when readings are proposed (a) by language models that never see the data and (b) by an adversary
that has seen the data and may choose any reading the tool accepts?

This evaluates the software frozen in section 12. It says nothing about scientific correctness of
any paper.

## 2. What is evaluated

* **System:** ClaimCheck v1.1 = the frozen v1 pipeline (gates, Lean 4.28.0 kernel, checker digest
  `35c83b28…`) plus the v1.1 policy (`policy.py`, `space.py`, `binding.py`; decoy limit 2 %).
* **Arms** (every arm feeds the same pipeline):
  * `union` (primary): readings proposed by both models, each given only numeric sentences and the
    column vocabulary;
  * `gemini`, `openrouter`: each model alone (secondary);
  * `search`: the data-aware symbolic proposer of v1 (secondary; expected to be the hardest
    non-adversarial case);
  * `rules`: cue-word rules (secondary);
  * `adversary`: the free-choice adversary of `dev/adversary.py`, on every printed number.
* **Models:** `gemini-3.6-flash` and `nvidia/nemotron-3-ultra-550b-a55b:free`, as in v1. A provider
  failure is recorded as a failure of that arm for that paper. No substitute model is used. If the
  primary arm lacks both models' proposals for more than 10 % of papers, the primary analysis is
  declared not evaluable.

## 3. Sampling frame and selection

* **Frame:** Zenodo dataset records under CC0 or CC BY that contain at least one CSV file of at
  most 64,000 bytes and are linked to an article in the Europe PMC open-access subset under CC BY.
* **Scientific contexts (strata):** at least three, 20 papers each:
  A. ecology and organismal biology (the v1 context);
  B. biomedical and health research;
  C. psychology, behavioural and social science.
  A fourth (agricultural and environmental science) is added only if the owner asks for it before
  approval. Strata are assigned from the journal's subject in Europe PMC, before screening.
* **Enumeration:** fixed query strings per stratum, in `queries.json` (draft, approved together
  with this protocol). Queries name subject areas and kinds of measurement, never results.
* **Order:** candidates are ordered by SHA-256 of `claimcheck-v1.1-prospective-2026|<Zenodo id>`.
  The seed string is fixed here.
* **Screening**, in that order, by reading the article and the deposit only. No proposer, verifier,
  oracle or other computation of any statistic is run during screening. A candidate is eligible if:
  * E1 the CSV is accepted by the strict parser (format only);
  * E2 the prose prints at least three numbers that a reader would take to be descriptive statistics
    of that table (judged by reading; not computed);
  * E3 the licences allow redistribution of article text and data;
  * E4 the deposit says, or makes plain, what one row represents;
  * E5 it passes every contamination check of section 4.
  Screening stops at 20 eligible papers per stratum or 150 screened candidates per stratum,
  whichever comes first. Every screened candidate and its reason is recorded
  (`SCREENING.json`). A shortfall is reported, not repaired.

## 4. Exclusions and contamination safeguards

Mechanical, in `contamination.py`, applied to every candidate and recorded:

* every record of the v1 candidate pool (51 records), by Zenodo id, data DOI, article DOI, PMCID;
* a title with token Jaccard similarity ≥ 0.6 to a v1 pool title;
* a data file whose SHA-256 equals a data file already used;
* an article sharing ≥ 20 % of its 8-word shingles with an article already used (companion papers,
  preprints, corrected versions);
* within the new benchmark: two candidates sharing a data record, or an article shingle overlap
  ≥ 20 % with an earlier accepted candidate (the later one is excluded).

Separation of materials:

* development and calibration: the eight v1 documents (`dev/`), nothing else;
* evaluation infrastructure tests: synthetic fixtures and the eight v1 documents;
* final evaluation: the new documents only, in a separate directory, created after approval.

Not controllable, and stated in the report: the language models may have seen the open-access
articles during their training. They never see data rows.

## 5. Materials prepared for each paper, before any system run

1. Article text by the deterministic JATS-to-text conversion of v1, with source URL, digest,
   licence and retrieval time. Data file likewise.
2. **Manifest**, written by rule: aliases from column names and the deposit's own data dictionary
   only (not from the article's wording); units and missing-value tokens from the deposit;
   `row_unit` from the deposit's description of a row; out-of-scope terms only where the deposit
   states that the table covers a subset. Where the deposit is silent, the field is left empty.
3. **Provisional labels** by the annotation procedure of v1 (AI-assisted, each truth value
   confirmed by a separate calculation). These are needed to plant errors and as a fallback. They are
   never called expert labels and are superseded by human adjudication wherever it exists.
4. **Planted-error copy:** one per paper, by `claimcheck_v1/benchmark/mutate.py` with the seed
   `prospective-2026`, up to four numbers that the provisional labels mark as true.
5. No prompt-injection copies (v1 measured that separately; the verifier ignores model obedience).

Then the benchmark is frozen by digest. After that, steps 6 to 8 run once.

## 6. Order of operations

0. Owner approves this protocol and `criteria.json`. Their digests are recorded.
1. Software freeze: digest over `research/claimcheck_v1_1/` (code) and the v1 freeze files.
2. Enumeration, contamination check, ordering, screening (section 3), acquisition, materials
   (section 5). Benchmark freeze.
3. Model calls for the proposer arms, cached. Budget: one call per model per document.
4. One verification run of all arms. Kernel runs use two workers, at most two claims per proof
   file, a 900 s limit per file. A run that is killed or times out yields UNKNOWN and is counted.
5. Free-choice adversary on every original article; everything it gets through is put to the kernel.
6. Independent replay of every bundle on a clean hosted runner.
7. Blinded adjudication package to the adjudicators (section 8).
8. Analysis exactly as in section 11. Report everything, including failures, time-outs and arms
   that did not run.

An infrastructure crash may be resumed from cached state; the crash is recorded. A change to any
frozen file ends the prospective evaluation; whatever follows is exploratory and reported apart.

## 7. Definitions

Unit of analysis: one printed number at one position in one document. Cluster: one paper (its
original and its planted-error copy belong to the same cluster).

Adjudicated class of a number (section 8):

* **T** it is a descriptive statistic of the table, expressible in the supported grammar, and the
  file reproduces it under that reading;
* **F** as T, but the file does not reproduce it (including planted errors);
* **N** it is not a statistic of this table, or not one the grammar can express;
* **A** ambiguous: the adjudicators cannot agree on what it is.

System outcome for a number in an arm: CONFIRMATION, DISCREPANCY_FOR_REVIEW, or abstention
(REQUIRE_HUMAN_REVIEW, UNKNOWN, or no proposal). If an arm's records for one number disagree, the
outcome is an abstention.

* **Correct confirmation:** CONFIRMATION of a T number where the adjudicated reading is the
  confirmed reading or one of its equivalent row selections.
* **Unsupported confirmation** (false confirmation): any other CONFIRMATION (of an F, N or A number,
  or of a T number under a different reading).
* **Correct discrepancy:** DISCREPANCY_FOR_REVIEW of an F number under the adjudicated reading.
* **Misleading refutation** (false accusation): any other DISCREPANCY_FOR_REVIEW.
* **Abstention:** neither verdict. Reported separately for T, F, N, and split into "review
  requested" and "no result".
* **Coverage:** correct confirmations / T numbers. **Discrepancy detection:** correct discrepancies
  / F numbers. Both use all adjudicated T or F numbers as denominator, whether or not any arm
  proposed a reading.

## 8. Independent human adjudication

* **Who:** two people with graduate training in a quantitative science, who took no part in
  building PCS, plus a third to resolve disagreements. They are named in the report with their
  consent. AI-assisted labels, a second automated implementation, or the builder's own reading are
  not adjudication.
* **Blinding:** adjudicators see the article, the data file, its dictionary and a list of numbers
  with their sentences. They do not see any system output, proposed reading or verdict. Numbers that
  received a verdict are mixed with sampled numbers that did not, in random order.
* **What is adjudicated:** every number that received CONFIRMATION or DISCREPANCY_FOR_REVIEW from
  any arm including the adversary; every number with a provisional label; and a random sample of ten
  further numbers per paper from sentences that name a column.
* **Form:** class (T/F/N/A), the reading in words, the statistic, column and rows, and a free-text
  note. Package and instructions: `adjudication/`.
* **Agreement:** raw agreement and Cohen's κ on the class before resolution are reported.
* **If no adjudicators are available:** the evaluation is still run and reported on provisional
  labels, every table is marked "not independently adjudicated", criterion C9 is not met, and
  supervised-pilot readiness cannot be declared.

The apparent real discrepancies found in v1 (four numbers in three papers) are included in the
first adjudication package regardless; see `adjudication/v1_discrepancies/`.

## 9. Thresholds

In `criteria.json` (machine-readable; the scorer reads it). Summary for the supervised pilot:

| | Criterion | Threshold |
| --- | --- | --- |
| C1 | unsupported confirmations among confirmations (primary arm, originals) | estimate ≤ 2 %; conservative upper bound ≤ 5 %; paper-level upper bound ≤ 10 % |
| C2 | misleading refutations per true or not-derivable number with a proposal | estimate ≤ 0.5 %; conservative upper bound ≤ 2 %; paper-level upper bound ≤ 5 % |
| C3 | coverage of true statements | estimate ≥ 25 %; lower bound ≥ 15 % |
| C4 | independent replay on a clean runner | 100 % of bundles |
| C5 | adversary: unsupported confirmations among its confirmations; papers with an adversarial accusation of a T or N number | ≤ 5 % (upper bound ≤ 10 %); paper-level upper bound ≤ 5 % |
| C6 | decided verdicts on numbers adjudicated ambiguous | none |
| C7 | kernel cost on the reference machine | median ≤ 60 s, 95th percentile ≤ 300 s per claim, ≤ 8 GB, ≥ 95 % of runs complete |
| C8 | usability study, ≥ 5 researchers new to PCS and Lean | ≥ 80 % task completion; ≥ 80 % correct on each critical scope question |
| C9 | independent human adjudication | done |
| C10 | owner authorisation | given |

All of C1 to C10 are required. A criterion that cannot be evaluated (too few papers, too few
confirmations, missing adjudication) is **not met**. Thresholds are not changed after approval; if
they are not met, the status stays research-only and the shortfall is reported.

The thresholds were set from what a supervised screening aid may get wrong, not from development
results. Two of them are not comfortably met on development data: coverage there was 24 % (Gemini)
and 31 % (union) against a floor of 25 %, and one confirmation of 23 in the union arm is counted as
unsupported under the AI-assisted labels.

## 10. Sample size and uncertainty

* **Papers: 60 at least** (three contexts of 20). Reason: the misleading-refutation criterion needs
  a paper-level upper bound of 5 % with no affected paper, and the exact one-sided 95 % bound for
  zero events in *n* independent units is 1 − 0.05^(1/n), which reaches 5 % at n = 59.
* **Confirmations: 150 at least** in the primary arm. With 2 errors in 150 the exact upper bound is
  4.1 % before any clustering penalty; with fewer than 150 the 5 % bound cannot be met with any
  realistic error count. Development data suggest 3 to 4 confirmations per paper, so 60 papers may
  give 180 to 240. If fewer than 150 result, C1 is not evaluable and not met.
* **Why not more:** each paper needs screening, a manifest, labels, about ten minutes of kernel time
  and two adjudicators. Sixty is the smallest number that can meet the criteria at all. It supports
  a supervised pilot at most. Public release would need about 300 (see `criteria.json`).
* **Uncertainty**, for every proportion (`stats.py`):
  * exact (Clopper–Pearson) one-sided 95 % bound ignoring clustering (shown for reference only);
  * the same bound on the effective sample size n / design effect, design effect
    1 + (size-weighted mean cluster size − 1) × ICC, ICC by the ANOVA estimator across papers;
  * a percentile interval from 10,000 bootstrap resamples of whole papers, seed 20261112;
  * the paper-level proportion (papers with at least one event) with its exact bound.
  The **conservative upper bound** used by C1, C2 and C5 is the larger of the design-effect bound
  and the bootstrap upper limit. When no event is observed the bootstrap is degenerate and the ICC is
  not estimable; the paper-level bound then carries the claim, which is why C1, C2 and C5 also have
  paper-level thresholds.
* A zero-error result on this sample bounds the error rate; it does not show the rate is zero and
  the report will not say so.

## 11. Statistical analysis plan

* **Primary analysis:** C1, C2, C3 for the `union` arm, on human-adjudicated classes, all contexts
  pooled, clustered by paper.
* **Analysis population:** all frozen papers. Papers where the primary arm had no model proposals
  are kept (they contribute abstentions) and listed.
* **Ambiguous (A) numbers:** excluded from the denominators of C1 to C3, counted in C6.
* **Per context:** the same proportions with intervals for each context, reported for all three
  whatever they show. No pooled claim is extended to a context that was not sampled.
* **Claim level and paper level:** every table gives both.
* **Secondary:** each proposer arm; `search` (data-aware) against the model arms; planted-error
  copies against originals; reasons for every withheld verdict, by rule; replay and cost.
* **Sensitivity:** (a) provisional labels instead of human adjudication; (b) papers with a provider
  failure removed; (c) the v1 policy on the same receipts, to state what v1.1 changed.
* **Multiplicity:** all criteria must hold jointly, so no adjustment is applied; no single
  favourable interval is reported as a success on its own.
* **No interim looks.** Steps 3 to 5 of section 6 run once.
* **Exploratory:** anything not listed here, any other decoy limit, any policy change. Labelled as
  exploratory and kept out of the criteria.

## 12. Freeze and approval record (to be completed)

| Item | Digest | Date |
| --- | --- | --- |
| This protocol | _on approval_ | |
| `criteria.json` | _on approval_ | |
| `queries.json` | _on approval_ | |
| v1.1 software | _after approval, before step 2_ | |
| Prospective benchmark | _after step 2, before step 3_ | |
| Owner approval (who, when, how recorded) | | |

## 13. Cost

About 120 model calls (the Gemini free tier allows 20 per day, so at least three days, or a paid
tier supplied by the owner), about 10 hours of kernel time on the reference machine, and roughly
1,500 numbers for each adjudicator.

## 14. What this evaluation cannot show

General scientific correctness; behaviour outside the three contexts; behaviour on tables above
64 KB, on statistics outside the grammar, or on text other than prose; that a deposited file is the
analysed file; anything about users, which the usability study addresses separately.
