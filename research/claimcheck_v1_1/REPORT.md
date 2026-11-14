# ClaimCheck v1.1: development report and readiness assessment

Date: 2026-11-14. Research sidecar, draft, no production authority.

**What kind of evidence this is.** Everything measured here uses the eight ClaimCheck v1 documents
(two development, six held-out). All eight were read while v1.1 was designed, and the v1.1 rules
were changed four times in response to what an adversary did on them. They are **development data
for v1.1**. Nothing below is a prospective validation, and the frozen v1 results, bundles and
benchmark are unchanged (both v1 freeze digests still verify). The prospective evaluation is
specified in [`prospective/PROTOCOL_DRAFT.md`](prospective/PROTOCOL_DRAFT.md) and has **not** been
run; it waits for the owner's approval.

| Kind of evidence | Status |
| --- | --- |
| Software tests, offline (28) and live with the real Lean 4.28.0 kernel | completed, pass |
| Development evaluation on v1 documents, AI-assisted labels | completed; internal, not independent |
| Free-choice adversary on the same documents | completed; partly oracle-predicted, pass-throughs kernel-checked |
| Independent software replay of v1.1 bundles | completed locally by a separate program; hosted CI job added |
| Kernel cost benchmark | completed |
| Web page: browser-built proof file accepted by the real kernel through the served runner | completed (authored automation, site repository) |
| Source admission, reading-help re-qualification, CI gate | **prepared and dry-run tested; not applied** (owner decisions C and D) |
| Prospective evaluation | **not run** (protocol drafted) |
| Independent human adjudication | **not done** (blinded package prepared, nobody asked yet) |
| Usability study with researchers | **not done** (protocol prepared, no participant) |

## 1. Development results: v1 against v1.1 on the same kernel receipts

Six held-out v1 articles, 14 document variants, 86 true statements, 41 false ones (planted errors
and four apparent real discrepancies), 67 numbers that are not statistics of the table. Labels are
the AI-assisted v1 labels. v1.1 was scored from the cached, kernel-checked v1 receipts; siblings
that support a discrepancy were predicted by the oracle here and are kernel-checked in the real
pipeline ([`dev/results/dev_arms.json`](dev/results/dev_arms.json)).

| Proposer | Policy | Correct confirmations | Unsupported confirmations (labelled + unlabelled) | Correct discrepancies | Misleading refutations (labelled + unlabelled) |
| --- | --- | ---: | ---: | ---: | ---: |
| Gemini | v1 | 24 | 0 + 2 | 11 | 2 + 0 |
| Gemini | v1.1 | 17 | 0 + 0 | 2 | 0 + 0 |
| Nemotron | v1 | 40 | 1 + 4 | 13 | 39 + 92 |
| Nemotron | v1.1 | 26 | 1 + 0 | 3 | 0 + 0 |
| search (has seen the data) | v1 | 37 | 4 + 41 | 0 | 0 + 0 |
| search | v1.1 | 27 | 0 + 7 | 0 | 0 + 0 |
| cue-word rules | v1 | 5 | 3 + 7 | 1 | 73 + 88 |
| cue-word rules | v1.1 | 5 | 0 + 2 | 0 | 0 + 0 |

* The one labelled "unsupported" confirmation that remains (Nemotron) is "(n = 335, χ² …)": 335
  rows have a value in the column the sentence is about. The v1 label calls it not derivable; v1
  already described it as defensible. It is kept as an error.
* The seven unlabelled confirmations of the search arm are the same seven numbers the adversary
  obtains (section 2): "96 species", "During 1975–2013", "n = 171 and 161", "n = 161". On my
  reading all are faithful. That is not adjudication.
* **Cost.** Correct confirmations fall from 40 to 26 and from 24 to 17. Detected discrepancies
  fall from 13 to 3 and from 11 to 2: v1.1 flags a mismatch only when another number in the same
  sentence supports the reading, and most planted errors sit in sentences with nothing else to
  check. Of the four apparent real discrepancies of v1, none is flagged by v1.1 (see section 6).

Why v1 results were withheld (both model arms, records):

| v1 result | Rule that withheld it | Records |
| --- | --- | ---: |
| mismatch | no other number in the sentence supports the reading | 148 |
| mismatch | it is a count | 123 |
| mismatch | the statistic's wording is not attached to the number | 86 |
| mismatch | a printed sample size differs from the rows used | 34 |
| match | too many comparable numbers are reproducible (or the number has one digit) | 21 |
| mismatch | wording for unsupported statistics; another reading reproduces it; rounding; unnamed "±" | 22 |
| match | wording not attached; sibling support insufficient; competing reading | 11 |

(A record can fail several rules.) On the two v1 development documents, scored from oracle
predictions because no kernel receipts were cached for them: Nemotron 9 → 4 correct confirmations,
search 27 → 15 with 10 → 0 unlabelled, rules 29 + 40 → 0 misleading refutations.

## 2. Adversarial claim selection

[`dev/adversary.py`](dev/adversary.py). The adversary has read the data. For **every number printed
in a document** (3,021 numbers in 16 documents: originals and planted-error copies), it may submit
any reading the grammar makes eligible, and all of them together so that its own submissions can
support each other.

| Target numbers | Count | v1: some eligible reading reproduces it | v1.1: CONFIRMATION obtained | v1.1: DISCREPANCY obtained |
| --- | ---: | ---: | ---: | ---: |
| labelled true | 92 | 61 | 38, all under the labelled reading | 0 |
| labelled false | 50 | 2 | 0 | 3, all under the labelled reading |
| labelled not derivable | 69 | 5 | 2 (the "n = 335" case, twice) | 0 |
| unlabelled | 2,810 | 138 | 10 | 0 |

* Under v1 a chooser could get 145 numbers "proved" that are not labelled true. Under v1.1: 12, of
  which 2 are the defensible "n = 335" and 10 are the unlabelled numbers listed above.
* No accusation of a true or not-derivable number was obtained.
* Arithmetic here is oracle-predicted. Every reading that obtained a verdict on an original
  document was then run through the full pipeline with the real kernel
  ([`dev/results/adversary_kernel_confirmation.json`](dev/results/adversary_kernel_confirmation.json)):
  31 of 33 got the same verdict; the other 2 (minimum and maximum of a 617-row column) ended
  `UNKNOWN` because the kernel run did not complete within its limits. The kernel never contradicted
  the oracle.
* **This table is what the rules were tuned on.** Four rule changes came from it: comparable-number
  decoys and positional wording (after one-digit coincidences and accusations by re-reading a
  neighbouring number), dates and incompatible units (after a date range was read as a statistic),
  counting the printed number among the comparable ones (after an interquartile bound was confirmed
  as a minimum). The table shows that the final rules close the holes that were found. It does not
  show there are no others.

## 3. End-to-end integrity

The path of an authoritative statement, and what was tested at each step
([`check_live_v11.py`](check_live_v11.py), real kernel; report in
[`dev/results/live_checks.json`](dev/results/live_checks.json)):

| Step | Binding | Attack tested | Result |
| --- | --- | --- | --- |
| data file → proof file | bytes embedded as one numeral; SHA-256 in every record | data substituted in a sealed bundle | replay rejects |
| checker | SHA-256 fixed in code and supplied by the reviewer at replay | checker edited | replay rejects |
| claim + expected outcome → theorem | proof file re-derived from the receipt by separate code and compared byte for byte | kernel outcome forged in the receipt, all digests re-sealed | replay rejects (Lean rejects the re-derived file) |
| kernel run | exit status 0, empty stderr, one axiom line per theorem, standard axioms only | Lean killed; hangs; exits silently; prints a warning; is missing | every case `UNKNOWN`, no kernel run recorded |
| receipt → v1.1 record | record names the receipt digest; its own digest covers it | verdict upgraded; findings edited; corroboration removed; records moved from another bundle | replay rejects each |
| record → what the user is told | outward verdict recomputed from the findings by the replayer; invariant asserted in code | (unit tests) a v1 `UNKNOWN` can never become a verdict; a match never becomes a discrepancy | pass |
| conditional result | one SD convention matches, the other does not | (unit and v1 tests) | `REQUIRE_HUMAN_REVIEW`, both branches shown |
| "fresh" | a record carries `kernel_run` only when the kernel ran in that invocation | record without kernel acceptance | `kernel_run` is null and the verdict is `UNKNOWN` |
| web page → local kernel run | the page never runs Lean; a `kernel-run.json` from the stand-alone runner is shown only if its proof-file, data and checker digests equal what the page built, under the label "reported by your local run · not verified by this page" | report for other data; report for another proof file (real browser, real kernel, site repository `scripts/browser_claim_check.cjs`) | both refused; an accepted report is never called verified |

The trusted computing base is unchanged from v1 ([`../claimcheck_v1/TRUST_BOUNDARY.md`](../claimcheck_v1/TRUST_BOUNDARY.md)):
the Lean 4.28.0 binary, `ClaimCheck.lean` (digest `35c83b28…`), the process boundary that runs
Lean, and SHA-256. The policy layer is not in the base for the mathematics. It is in the base for
the outward verdict, and it is ordinary unverified Python.

What the replay does **not** recompute: the enumeration of the eligible reading space (the decoy
counts and the competing readings) and the wording patterns. It checks their arithmetic and that the
verdict follows from them.

Independence, by level: the replay is an independent **program** written by the same author. No
second person has replayed a bundle. No person has adjudicated a reading. No experiment has been
replicated. These are four different things and only the first exists.

## 4. Kernel cost

[`perf/results.json`](perf/results.json): one claim per proof file, synthetic two-decimal data, one
Lean process at a time, 4 cores, 11 GB address-space limit, 600 s limit.

| Rows | count | mean | min | SD | median | Pearson r |
| ---: | --- | --- | --- | --- | --- | --- |
| 50 | 2 s, 0.5 GB | 2 s, 0.6 GB | 2 s, 0.6 GB | 2 s, 0.6 GB | 3 s, 0.6 GB | 3 s, 0.6 GB |
| 200 | 3 s, 0.8 GB | 5 s, 0.9 GB | 5 s, 0.9 GB | 5 s, 0.9 GB | 11 s, 1.6 GB | 7 s, 1.2 GB |
| 400 | 6 s, 1.1 GB | 9 s, 1.4 GB | 10 s, 1.4 GB | 9 s, 1.4 GB | 35 s, 4.0 GB | 14 s, 1.9 GB |
| 800 | 11 s, 1.7 GB | 16 s, 2.3 GB | **rejected** | 18 s, 2.4 GB | **out of memory** | 26 s, 3.3 GB |
| 1,600 | 22 s, 2.9 GB | 32 s, 4.1 GB | **rejected** | 36 s, 4.4 GB | **out of memory** | 54 s, 6.2 GB |
| 2,400 | 35 s, 4.2 GB | **rejected** | **rejected** | **rejected** | **out of memory** | **rejected** |

"Rejected" is a recursion-depth error inside Lean on a long fold. Every failed run is reported as
not established. Practical limits on a 16 GB machine: every statistic up to about 400 rows; counts,
means, standard deviations and correlations up to about 1,600; nothing but counts beyond. No
optimisation was attempted, because any faster path would add to the trusted base and needs review.
A one-claim check of a small table takes about half a minute end to end, most of it start-up.

## 5. Readiness assessment

Against [`prospective/criteria.json`](prospective/criteria.json) (draft, not yet approved).

| Level | Assessment | Basis |
| --- | --- | --- |
| **1. Internal research** | **Supported.** | Frozen v1 digests verify; 28 offline tests and the live checks pass; development evaluation and adversary recorded; pass-throughs kernel-checked; bundles replay. |
| **2. Supervised external pilot** | **Not supported.** | No criterion C1 to C10 is met. C1 to C3, C5, C6: not evaluable (six development papers against a minimum of 60 new ones; the scorer reports "not evaluable" on development data, [`prospective/DEMONSTRATION_ON_DEVELOPMENT_DATA.json`](prospective/DEMONSTRATION_ON_DEVELOPMENT_DATA.json)). C4: local replay only so far. C7: met for tables up to 400 rows on the benchmark, not measured on prospective papers. C8: no participant. C9: no adjudicator. C10: not requested. |
| **3. Unrestricted public release** | **Not supported.** | Nothing at that level exists. |

To move from level 1 to level 2: the owner approves (or amends) the protocol and criteria; the
prospective evaluation runs once; two independent adjudicators label the outputs; five researchers
do the usability sessions; all of C1 to C9 are met; the owner authorises the pilot. Passing software
tests is not on that list.

## 6. What v1.1 does to the four apparent real discrepancies of v1

| Paper | Printed | File | v1 | v1.1 | Why |
| --- | --- | --- | --- | --- | --- |
| Plummer et al. 2018 | reproductive effort mean 78.4 | 78.349 | REFUTED | REQUIRE_HUMAN_REVIEW | within one unit of the last digit; 78.349 → 78.35 → 78.4 is double rounding |
| Plummer et al. 2018 | α-tocopherol 23.13 ± 1.06 | 22.95, SE 1.04 | REFUTED (SE) | REQUIRE_HUMAN_REVIEW | the sentence does not say "mean" or name the "±"; the range in the same sentence is reproduced |
| Collins et al. 2019 | 58 haplotypes at Site G | 57 rows | wrong reading | REQUIRE_HUMAN_REVIEW | a count; what a row is cannot be settled from the sentence |
| Kroeger et al. 2018 | r = .75, N = 472 | 0.742 over 448 pairs | not grounded | REQUIRE_HUMAN_REVIEW | printed N differs from the rows in the file |

In each case the arithmetic result is kept in the record. None is called a discrepancy
automatically. Whether any of them is one is a question for people; the blinded package is in
[`adjudication/v1_discrepancies/`](adjudication/v1_discrepancies/).

## 7. Limitations

1. Development data only, six papers, one field, AI-assisted labels. No interval that could
   support a claim about error rates exists yet.
2. The rules were fitted to the failures found on these documents. Expect them to fit new
   documents worse.
3. Lexical rules cannot see meaning. A sentence can attach the word "mean" to a number that is a
   model estimate and print a range that is not this column's range. Rules 3, 5 and 11 reduce that;
   they do not remove it.
4. The decoy rate estimates how often *some* eligible reading reproduces a comparable number in
   this table. It is an empirical property of one table and one sentence, not a probability with a
   guarantee.
5. Coverage is low, and discrepancy detection is very low. A tool that almost never flags is safe
   and of limited use for finding errors. That trade was made deliberately and is measured above.
6. `row_unit` and column units must be supplied in the manifest. For the v1 documents they were
   added after reading the papers (`dev/manifest_overlays.json`).
7. Manifest authors can still make source checks pass that should not (aliases).
8. Custody of the data file, and every scientific judgement, remain outside the tool.
9. The policy code is not formally verified and has one author.
