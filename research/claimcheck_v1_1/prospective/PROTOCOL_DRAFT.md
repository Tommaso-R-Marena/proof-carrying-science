# ClaimCheck v1.1 prospective evaluation: protocol for owner review

**Status: DRAFT 2 (2026-11-15), amended after the owner's decision "amend before approval". Not
approved, not frozen, not run.** Every change from draft 1 and its reason is in
[`AMENDMENTS_DRAFT_2.md`](AMENDMENTS_DRAFT_2.md). No new paper has been fetched, screened,
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
  **What the decoy limit does and does not bound (found 2026-11-15, proved in
  `claimcheck_assurance_v1/formal/ClaimCheckAssurance/Selection.lean`):** the limit caps the share of
  reproducible comparable numbers within ±50 of the printed one. Against a chooser who has seen the
  data, the share of unrelated printed numbers that can be confirmed is at most 2/51 ≈ 3.9 %, and a
  pattern reaching 2/52 ≈ 3.8 % exists, so "2 %" is not a bound on coincidental confirmation. A rule
  whose bound is 2 % (no decoy reproduced, or fixed blocks of 100) would have to be adopted before
  the software freeze; that is owner decision A6, and every result so far was produced with the
  current rule.
* **Arms** (every arm feeds the same pipeline):
  * `union` (primary): readings proposed by both models, each given only numeric sentences and the
    column vocabulary;
  * `gemini`, `openrouter`: each model alone (secondary);
  * `search`: the data-aware symbolic proposer of v1 (secondary; expected to be the hardest
    non-adversarial case);
  * `rules`: cue-word rules (secondary);
  * `adversary`: the free-choice adversary of `dev/adversary.py`, on every printed number.
* **Models:** `gemini-3.6-flash` and `nvidia/nemotron-3-ultra-550b-a55b:free`, as in v1. A provider
  failure is recorded as a failure of that arm for that paper. No substitute model is used.
  Both identifiers were still served on 2026-11-15 ([`MODEL_ACCESS.md`](MODEL_ACCESS.md)); they are
  checked again and frozen, with prompt version and sampling parameters (temperature 0), at approval.
* **Calls:** one call per model per document. A paper has two documents, the original and the
  planted-error copy, so **240 calls** for 60 papers. As implemented in
  `claimcheck_v1/providers.py` (to be frozen): a transport failure, a quota refusal (HTTP 429) or a
  server error is repeated with the identical request at most three times, after 15, 30 and 45 s
  (40, 80 and 120 s after a 429); a deterministic failure (HTTP 400, 401, 403, 404, or an answer with
  no text) is not repeated; an answer whose text does not parse is not repeated either (at
  temperature 0 a repeat would most likely return the same text). Every attempt is recorded and
  every answer is cached by request digest, so no request is ever sent twice after it succeeded. A paper is *primary-complete* when both
  models returned a parseable answer for both of its documents. **If fewer than 90 % of papers are
  primary-complete, the primary analysis is not evaluable.** (In v1, 7 of 14 first calls to one
  provider failed on its free tier; a free-tier run is therefore likely to end "not evaluable".)

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
  Screening stops at 20 eligible papers per stratum or 300 screened candidates per stratum,
  whichever comes first. Every screened candidate and its reason is recorded
  (`SCREENING.json`). **A stratum with fewer than 20 eligible papers is not topped up from another
  stratum; C1 to C3 are then not evaluable.** The numbers 20 per stratum and 60 in total are the
  same in `criteria.json` (draft 1 said 15 there).

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

* **E6, independence of papers:** at most one paper per author group. A candidate that shares any
  author with an already accepted candidate, or with a v1 document, is excluded (the later one in
  the fixed order). Every bound in section 10 treats papers as independent; shared authors, a shared
  laboratory pipeline or a shared deposit template would break that.

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

### Denominators (draft 2)

Misleading refutations are reported with three denominators, and criterion C2 uses all three:

* **per exposed number:** misleading flags / numbers adjudicated T, N or A for which the arm
  proposed at least one reading. (Draft 1 divided by all T and N numbers, which a proposer that
  proposes little can inflate; that figure is still reported.)
* **per paper:** papers with at least one misleading flag / all papers.
* **among flags:** misleading flags / all flags issued.

Three words are kept apart everywhere, in records, reports and exports: a **mathematical mismatch**
(the kernel proved the typed statement false of the file), a **discrepancy for review** (a mismatch
under a reading that another confirmed number supports), and a **scientific error** (never asserted
by the system; only people decide that, outside this evaluation).

**Ambiguous numbers (A).** Primary analysis, chosen to be the unfavourable one for the system in
each metric: a CONFIRMATION or a flag on an A number is an error (C1 and C2 numerators); A numbers
count in the C2 denominators; A numbers count *against* coverage (C3 denominator T + A). All A
numbers stay in the evidence with both adjudicators' notes. If more than 20 % of the statistic-like
numbers are A, the labels cannot carry the criteria and C1 to C3 are not evaluable.

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

In `criteria.json` (machine-readable; the scorer reads it; tested to agree). Supervised pilot:

| | Criterion | Threshold |
| --- | --- | --- |
| C1 | unsupported confirmations among confirmations (primary arm, originals) | estimate ≤ 2 %; claim-level upper bound ≤ 5 % with the assumed minimum clustering; papers with one, among papers with a confirmation: upper bound ≤ 10 % |
| C2a | misleading flags per exposed T, N or A number | estimate ≤ 0.5 %; claim-level upper bound ≤ 2 % with the assumed minimum clustering |
| C2b | papers with a misleading flag | upper bound ≤ 5 % |
| C2c | misleading flags among all flags | upper bound ≤ 50 %; needs at least 5 flags |
| C3 | correct confirmations among T and A numbers | estimate ≥ 25 %; lower bound ≥ 15 % |
| D1 | discrepancy detection | reported; governs wording (9a); no pass mark |
| C4 | independent replay on a clean runner | 100 % of bundles |
| C5 | adversary: unsupported confirmations among its confirmations; papers with an adversarial flag on a T or N number | ≤ 5 % (upper bound ≤ 10 %); paper-level upper bound ≤ 5 % |
| C6 | decided verdicts on numbers adjudicated ambiguous; share of ambiguous numbers | none; ≤ 20 % |
| C7 | kernel cost on the reference machine | median ≤ 60 s, 95th percentile ≤ 300 s per claim, ≤ 8 GB, ≥ 95 % of runs complete |
| C8 | usability study, ≥ 5 researchers new to PCS and Lean | ≥ 80 % task completion; ≥ 80 % correct on each critical scope question |
| C9 | independent human adjudication | done |
| C10 | owner authorisation | given |

All of C1 to C10 are required. A criterion that cannot be evaluated is **not met**. Thresholds are
not changed after approval. They were set from what a supervised screening aid may get wrong, not
from development results; on development data coverage was 24 % and 31 %, and one confirmation of 23
is counted as unsupported.

C2c is new. Its meaning: with 95 % confidence, a flag is more often a real discrepancy than not. It
is the weakest requirement under which a flag is an alert at all, and it is not derived from what
the system achieves. With the few flags expected (two or three per six papers in development) a
tighter bound could not be shown by 60 papers: 25 flags with none misleading give an upper bound of
11 %.

**Scope by context.** A context in which any paper has a misleading flag, or whose C1 estimate
exceeds 2 %, is outside the scope of a pilot even if the pooled criteria are met.

### 9a. Discrepancy detection: measured, with a rule on wording, without a pass mark

Development showed the price of withholding: detected planted or apparent discrepancies fell from
13 to 3 and from 11 to 2 of 41. A verifier that abstains nearly always is safe and of little use
for finding errors. Draft 2 therefore measures detection explicitly:

* **flag recall** = correct flags / numbers adjudicated F, separately for planted errors (known by
  construction, enough of them) and for F numbers found in original articles (few; reported with
  their interval and not pooled with planted ones);
* **mismatch shown** = F numbers for which some record shows a kernel-proved mismatch under the
  adjudicated reading, flagged or under REQUIRE_HUMAN_REVIEW / F numbers. This is what a reviewer
  who reads the review list could find;
* both with paper-clustered intervals, per context and pooled.

**No minimum is proposed, because none can be justified.** The value of flags to a reviewer is the
share of real errors they need not find by hand, and the chance that an unflagged number is wrong
falls only in proportion to recall (prevalence × (1 − recall)). There is no level at which that
changes character, and no study of reviewers tells us what share makes the tool worth using. A
number chosen now would be either arbitrary or fitted to the 5 to 8 % seen in development.

What is fixed instead:

1. a **necessary condition**: the lower bound of flag recall on planted errors must exceed the
   upper bound of C2a. Otherwise flags are not associated with real mismatches at all;
2. a **rule on wording**: unless the lower bound of flag recall reaches a level the owner sets
   before the run (field `wording_rule` in `criteria.json`, empty in this draft; 20 % is suggested
   as a judgement, not a derivation), a pilot is *confirmation only*: nothing may describe the tool
   as finding errors, and every screen and report says that the absence of a flag carries no
   information;
3. the measured recall, with its interval, is printed wherever flags are described.

## 10. Sample size and uncertainty

**What each bound assumes.** The paper-level bounds assume only that papers are independent (E6).
They are exact (Clopper–Pearson, one-sided 95 %). Claim-level bounds need an assumption about how
strongly errors cluster within a paper. Draft 1 estimated the intraclass correlation (ICC) from the
data and used 0 when no event was observed, which made its "conservative" bound equal to the bound
that ignores clustering exactly when it matters most. Draft 2 uses max(estimated ICC, **0.25**) and
always prints the bound for ICC 0, 0.1, 0.25, 0.5 and 1. The value 0.25 is an assumption for the
owner to confirm; with it and about 10 exposed numbers per paper the effective sample is about a
third of the number of claims.

**Is 60 papers enough?** It is the smallest number that can meet the criteria, and it protects
against accepting a poor system. It gives a good system only a moderate chance of passing:

| Criterion (paper level) | Papers | Affected papers allowed | Chance of passing if the true share of affected papers is 0.5 % / 1 % / 2 % / 5 % |
| --- | ---: | ---: | --- |
| C2b, bound ≤ 5 % | 60 | 0 | 74 % / 55 % / 30 % / 4.6 % |
| | 120 | 1 | 88 % / 66 % / 31 % / 1.6 % |
| | 180 | 3 | 99 % / 89 % / 51 % / 1.9 % |
| C1 paper level, bound ≤ 10 % | 60 | 1 | 96 % / 88 % / 66 % / 19 % (1.4 % at 10 %) |
| | 120 | 6 | 100 % / 100 % / 99 % / 61 % (3.8 % at 10 %) |

(`stats.power_table`; the C1 rows assume every paper has a confirmation, otherwise fewer.)

* **C2b at 60 papers is a zero-tolerance test.** One paper with a misleading flag fails it. A system
  whose true rate is 1 % of papers fails 45 % of the time. A failure at 60 papers therefore does not
  show the system is bad; a pass does show the rate is below 5 %.
* **C2a's claim-level bound of 2 % is borderline at 60 papers under the assumed clustering.** With
  ICC 0.25 and no misleading flag, the bound is 2.2 % with about 5 exposed numbers per paper, 2.0 %
  with 8 and 1.9 % with 10 or more (the effective sample cannot exceed about 60 / 0.25 = 240 however
  many numbers a paper has). **One misleading flag anywhere fails C2a at 60 papers** (bound about
  3 %). At 120 papers no flag gives about 1 % and one flag about 1.5 to 1.8 %, which passes. So at 60
  papers C2a can be met only with zero misleading flags and a reasonably rich set of exposed numbers.
* **C1's claim-level bound of 5 %** at 150 confirmations and ICC 0.25 with about four confirmations
  per paper (effective sample about 85) tolerates no unsupported confirmation (bound 3.5 %) and
  fails with one (5.5 %); spread three per paper (design effect 1.5) it tolerates one (4.6 %).
  The tolerance therefore depends on how confirmations cluster, which is fixed only by the data. At
  240 confirmations with about five per paper it tolerates one (3.9 %).
* **Recommendation: 120 papers, 40 per context**, if adjudicators can be found for about 3,000
  numbers each. If only 60 are feasible, the report must say in advance that C2 then tolerates no
  misleading flag at all, so a "not met" on C2 says little about the system. The sample is not
  reduced below 60.
* **Uncertainty reported for every proportion** (`stats.py`, checked against an independent exact
  implementation in `tests/test_stats_oracle.py`): the exact bound ignoring clustering (reference
  only); the bound on the effective sample under the assumed minimum ICC; the grid of assumed ICCs;
  the paper-level proportion with its exact bound; a percentile interval from 10,000 bootstrap
  resamples of whole papers, seed 20261112. The bootstrap interval is two-sided 95 %, so its upper
  limit is a 97.5 % limit; with no event it is degenerate and carries nothing. With one or two
  events percentile intervals are known to be too short; they are reported, and the criteria rest on
  the exact bounds.
* A zero-error result bounds a rate. It does not show the rate is zero and the report will not say so.

## 11. Statistical analysis plan

* **Primary analysis:** C1, C2a to C2c and C3 for the `union` arm, on human-adjudicated classes,
  all contexts pooled, clustered by paper, ambiguous numbers handled as in section 7.
* **Fixed before the run and not changed:** the primary arm; the secondary arms and comparisons
  listed here; the ICC floor; the wording threshold of 9a; the list of sensitivity analyses.
* **Analysis population:** all frozen papers. Papers that are not primary-complete are kept (they
  contribute abstentions) and listed.
* **Per context:** every proportion with its interval for each context, reported whatever it shows.
  What may generalise across contexts is what does not depend on how a field writes: that a decided
  verdict implies the kernel result (proved, `claimcheck_assurance_v1`), replay, fail-closed
  behaviour. What does not generalise without evidence: coverage, the wording rules, units, what a
  row is, and therefore C1 to C3. No pooled figure is presented as a figure for a context that was
  not sampled, and a context is excluded from a pilot under the scope rule of section 9.
* **Arms kept apart:** model proposals (`union`, each model), data-aware symbolic search
  (`search`), and the free-choice adversary are never pooled. Secondary: each proposer arm; `search`
  against the model arms; planted-error copies against originals; reasons for every withheld
  verdict, by rule; replay and cost.
* **Sensitivity analyses** (all reported; a conclusion that changes under any of them is stated as
  not robust): ambiguous numbers treated as T, as N, and removed; provisional labels in place of
  adjudicated ones; either adjudicator's "error" counted as an error before resolution; papers that
  are not primary-complete removed; the v1 policy on the same receipts; each context alone.
* **Multiplicity:** all criteria must hold jointly, so no adjustment is applied; no single
  favourable interval is reported as a success on its own.
* **No interim looks.** Steps 3 to 5 of section 6 run once. No result is inspected before every
  adjudication form is returned and sealed.
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

240 model calls for 60 papers (480 for 120), before repeats: one per model per document, two
documents per paper. Draft 1 said 120 and had forgotten the planted-error copies. Measured in v1,
per call: about 2,600 to 4,400 prompt tokens and 300 to 3,000 output tokens. Free tiers and a capped
paid configuration are in [`MODEL_ACCESS.md`](MODEL_ACCESS.md). The Nemotron half of a paid run
(120 calls) is estimated at about 1.2 US dollars, at most about 5 if every call were repeated three
times; the Gemini price could not be read from the provider's model listing and must be confirmed
before any paid use. A total cap of 15 US dollars is proposed. No paid call has been made. Kernel
time about 10 hours per 60 papers on the reference machine. Adjudication: roughly 1,500 numbers per
adjudicator per 60 papers, estimated 35 to 50 hours each
([`../adjudication/RECRUITMENT_AND_ADJUDICATION_PLAN.md`](../adjudication/RECRUITMENT_AND_ADJUDICATION_PLAN.md)).

## 14. What this evaluation cannot show

General scientific correctness; behaviour outside the three contexts; behaviour on tables above
64 KB, on statistics outside the grammar, or on text other than prose; that a deposited file is the
analysed file; anything about users, which the usability study addresses separately.
