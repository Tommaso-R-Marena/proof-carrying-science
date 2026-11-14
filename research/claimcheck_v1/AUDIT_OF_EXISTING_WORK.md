# Audit of the existing system (Phase 1)

Scope: the production v0.6 path on `main` (`bc78660`), and draft PRs #201–#203, #207, #210, #211,
read and partly re-executed on 2026-11-10 with Lean 4.28.0 (pinned release digest verified) and
Python 3.12/3.13. Nothing in those PRs or on `main` was modified.

## What was reproduced

| Item | Command / method | Outcome |
| --- | --- | --- |
| Production Lean build | `lake -d formal build PCS pcs-lean-authority pcs-semantic-check` | completed, exit 0 (253 jobs) |
| Production v0.6 / Lean / authority tests | `pytest tests -k "v06 or lean or authority"` with hash-locked dependencies | 591 passed, 33 skipped, 0 failed |
| Repository integrity | `python scripts/check_repository_integrity.py` | passed |
| Source-admission gate | `python -m research.integration_v2.reconcile --require-committed` | could not run in a shallow clone (missing historical commit object); in hosted CI it rejects any PR that adds files, including this one, by design |
| PR #211 offline suite | `python -m unittest discover -s research/llm_claim_harness_v1/tests` | 384 of 385 pass. The one failure (`test_deterministic_table_cli`) asserts `kernel_checked == 0`, i.e. it assumes Lean is **not** installed; with Lean on `PATH` the CLI really checks 4 claims. An environment-sensitive test, not a soundness defect |
| PR #211 live Lean checks | `python -m research.llm_claim_harness_v1.check_live_lean` | passed (47 s), including its forged-verdict and omitted-row negative controls |
| PR #207 0/70 result | read `evidence/final-error-atlas.json`, `reference/final.json`, the grader and report on the PR branch; recomputed the category breakdown | reproduced as recorded (see below). The full pipeline was not re-run: it needs the PyTorch/SciPy stack, and its final sources are already exposed |

## What is functional, what is research-only

* **Functional and authoritative (production):** v0.6 package verification through the compiled
  Lean authority, signature pinning, receipts. It verifies *packages*: that delivered bytes,
  certificates and observations are consistent. It does not read papers or decide whether a
  reported result follows from data.
* **Functional but research-only, narrow:** PR #211 proves closed arithmetic statements about tiny
  CSV files (at most 512 bytes / 32 cells) and strict note formats, each with a freshly generated
  Lean program; its v12 adds genuinely general Mathlib theorems for OLS under bounded response
  perturbation. PR #207 produces replayable provenance packets and a conditional ODE
  reconstruction for one development model. PR #210 is a line of exact-inference research with no
  Lean component and no real data.
* **Does not compose:** the model adapters in #211 were never run against a live model; its
  "source" is a hand-formatted note, not a paper. #207's interpreter does not produce claims that
  any of the provers could check. #210 is unrelated to claim verification. No path existed from a
  sentence in a real paper to a kernel-checked statement about that paper's data.
* **Duplicated:** #211 contains several successive generators for overlapping CSV/OLS statements
  (v5–v12), each emitting its own Lean text; #201–#203 and #207 stack four interpretation layers.

## Why the strict evaluation in PR #207 scored 0/70

The 70 "supported" reference items are a mixture (kinds from `reference/final.json`: 49
`scientific_claim`, 20 `quantity`, 16 `equation` over all 85 items). Breakdown of the 70 by the
atlas's own diagnostic category for the v4 engine:

| Category | Items | Meaning |
| --- | ---: | --- |
| project failed, no accepted interpretation | 25 | one of three projects (Smith 2013) timed out, so all its items score zero |
| no candidate extracted from the annotated artifact | 23 | the deterministic interpreter produced nothing from the article XML for these statements |
| no candidate at the annotated source span | 21 | candidates existed in the file but none at the annotated sentence |
| overlapping candidate with incompatible typed form | 1 | |

Three causes, in order of importance:

1. **The task is paraphrase recovery, not verification.** Most reference items are prose summaries
   ("The paper proposes four spatial scales…", "Reported model ranking depends on dataset…"). A
   rule-based interpreter has no way to produce them, and even perfect recovery would verify
   nothing: there is no artifact against which such a sentence can be checked. Only 37 of the 70
   contain any digit, and few of those are functions of the bundled data.
2. **The grader requires curator-chosen identifiers.** A candidate is compared only if its kind
   and entity identifier equal the annotator's. The atlas records
   `exact_entity_and_kind_prefilter_count: 0` and `primary_candidate_comparison_count: 0` for all 85
   reference items in both engines, so zero candidate comparisons took place. The score therefore measures identifier agreement; it cannot distinguish "understood
   differently" from "not understood". The PR's own report says this.
3. **One project timed out**, removing 25 items regardless of capability.

Consequence for design: the consequential bottleneck is not interpreter strength on whole papers.
It is the absence of *any* class of real-paper statements that is (a) found by a proposer, (b)
bound to artifacts by checks a reader can inspect, and (c) decided by the kernel. ClaimCheck picks
the narrowest such class with real practical value (printed descriptive statistics versus deposited
data), lets untrusted language models do the finding, and scores by *extensional* agreement (two
readings are the same if they compute the same thing on the data), not by identifier agreement.
It does not attempt the other 60-odd kinds of statement in that reference set, and says so.

## Smaller benchmarks that should not be confused with the above

PR #203's 19/22 is on isolated, pre-segmented cases under a lenient protocol; PR #211's hundreds of
passing tests are unit tests of a controlled format. Neither measures end-to-end behaviour on a
paper. They are not contradicted by the 0/70 and do not mitigate it.
