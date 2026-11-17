# Owner authorization package: ClaimCheck integration (2026-11-17)

Each decision below is separate: approving one does not approve another. Nothing listed here has
been applied, merged, deployed, tagged or approved by the assistant. Numbers that depend on the exact
head of a pull request (manifest digest, retained commit) are in the pull request descriptions,
because evidence about a commit cannot be stored inside that commit (see
[`ADMISSION_PROPOSAL.md`](ADMISSION_PROPOSAL.md), "Why the evidence names an earlier commit").

Legend: **implemented** = on the draft branch; **tested** = the named tests pass; **proved** = Lean
theorem checked by the kernel; **proposal** = prepared, not applied.

## Core repository (PR 212)

### C1. Admit the ClaimCheck sidecar (successor manifest V23 and retained-source tag)

* **Change (proposal):** one control commit with four files, built by
  `python -m research.claimcheck_v1_1.governance.prepare_core_admission --out <dir> --emit <dir>`:
  `RECONCILIATION_V23.json` (new), and edits to `research/integration_v2/reconcile.py` (manifest path
  and digest; V23 format), `research/integration_v2/test_reconcile.py` (the V22 test reads V22 by
  path; one V23 test added) and `scripts/check_reconciled_prs.py` (new retained commit and tag; V23
  as a control). Plus, outside the tree, the retained commit (same tree as the admitted commit;
  parents: that commit and `0b521f39`) and the annotated tag
  `pcs-source-intake/core-claimcheck-v1-20261114`. Patch: [`proposed-control-changes.patch`](proposed-control-changes.patch).
* **Tests (dry run, `dry-run.json`):** both gates pass on the dry-run control commit; both protected
  test files pass (75 and 13 tests, including the whole-tree squash); nine alterations rejected
  (unlisted file, edited admitted file, edited V23, edited V22, edited frozen result, edited
  production file, gate control edited after the control commit, retained entry retargeted, tag
  moved). The proposal and the tested dry run differ only in the tag name.
* **Audit:** [`ADMISSION_AUDIT.md`](ADMISSION_AUDIT.md): no credential, no generated file, every file
  with a provenance class, CC BY 4.0 attribution index ([`THIRD_PARTY_ATTRIBUTION.md`](THIRD_PARTY_ATTRIBUTION.md)),
  frozen digests verify, no protected path changed. Open question for you: whether the model
  providers' terms permit keeping and publishing the 35 recorded model outputs.
* **Implications:** widens the admitted tree by exactly the census; changes no existing source,
  science, Lean or authority byte; one pinned control script changes (it names the new retained
  commit).
* **If approved:** regenerate at the commit you fix, compare digests with the PR description, create
  the retained commit, push the tag, commit the four files as one reviewed control commit.
  `source-policy` and `verified-public-integration` then pass.
* **If rejected:** nothing to undo; the branch contains no protected change; the two checks stay red.

### C2. Required checks

* **Change (proposal; the workflow change is implemented and tested):** require exactly
  `claimcheck-required` in the `main` ruleset after C1. Details: [`REQUIRED_CHECKS.md`](REQUIRED_CHECKS.md).
* **Tests:** `research/claimcheck_v1_1/governance/test_required_check.py` (13 change scenarios on
  real merge commits; 192 result combinations, exactly the 17 intended pass).
* **Also for you to confirm:** that none of the six jobs that are skipped on every pull request
  (`pcs-ci.yml`, `pcs-required-self-hosted.yml`) is a required check; a skipped job passes a
  requirement.
* **If approved:** ClaimCheck changes cannot merge without both ClaimCheck jobs passing; other pull
  requests are unaffected. **If rejected:** ClaimCheck checks stay advisory.

### C3. The corrected and hardened stand-alone runner

* **Change (implemented, tested):** runner SHA-256 `831bbaba…` (core `52b5e182`), replacing the
  withdrawn `8d9e07b4…` and the 2026-11-16 version `459155f3…`. Review package:
  [`SECURITY_REVIEW_C3_D4.md`](SECURITY_REVIEW_C3_D4.md), with the exact diffs.
* **Tests:** 92 unit tests in `research/claimcheck_v1_1/tests` (strict grammar, 14 negative controls,
  11 hardening tests, 15 binding tests); `check_live_v11.py` with the real kernel (forgery refused
  before Lean; genuine file accepted; forced settings flagged; memory cap; executable recorded).
* **Proved (research branch):** the canonical language and its meaning (`Claims.lean`); the runner's
  parser agrees with it on 10,720 vectors (tested, not proved).
* **If approved:** the runner can be used for files the page writes. **If rejected:** keep the page's
  local-run section disabled; no recorded result depends on the runner.

### C4. The v1.1 replay binds the claim to the sentence

* **Change (implemented, tested):** `research/claimcheck_v1_1/replay_independent_v1_1.py`
  (`1d2f80ef`): the claim's reported value must be the printed literal, and the checked variants
  those the statistic requires. Not a protected file, but it changes an evidence tool, so it is
  listed for your review. The frozen v1 replayer is unchanged and keeps the gap.
* **Tests:** three former gaps now refused; 0 violations on the 302 committed receipts; live replay
  of genuine bundles passes.
* **If rejected:** revert that commit; the gap reopens for bundles handed to reviewers.

## Website (PR 149)

### D1. Reading-help requalification (patch 01, `scripts/verify_browser_ui_sources.mjs`)
### D2. Public-tree admission (patch 02, `scripts/check_reconciled_prs.py`, retained commit and tag)
### D3. Complete gate (patch 03, `package.json` `ci:zero-minutes`)
### D4. The page's receipt rule

Each is explained line by line, with its dry run, negative controls, implications and the
consequences of approval or rejection, in the site's `docs/governance/CLAIMCHECK_PROPOSALS.md`. In
short: D1 accepts exactly one reviewed successor of the reading-help pin (the historical record is
not edited); D2 lets the public tree change only to the exact tree of a commit you tag; D3 runs
ClaimCheck's mandatory tests inside the already required `site-full-gate`; D4 shows a local receipt
only if it is about the page's own file and labels it as reported by the user's run, never as
verification.

## Research (PR 216)

### R1. How to admit the assurance research

**Recommendation: a separate successor qualification after PR 212's admission, not together with
the sidecar.** Reasons: it is stacked on PR 212 and changes nothing in it; it carries its own Lean
modules, a C library, an Aristotle record and an axiom report whose review is different in kind
from the sidecar's; admitting it together would make the C1 manifest depend on research that is
still moving (decoder v2, conformance parts D and E were added this week); and its CI job
`proofs-and-refinement` is path-filtered and should get the same change-detection aggregate before
it could be required. Its findings that matter for PR 212 (the runner forgery, the replay gap) are
already fixed and tested on PR 212's branch. Once PR 212 is admitted, the same script produces a
V24 successor for the research files alone.

## External verification (Aristotle)

### E2. Continue the C decoder verification

* **Status:** prepared, **not started**. The redesigned decoder (lengths by value, validation
  before any write, nothing written on rejection) and the continuation prompt are on the research
  branch (`c/DESIGN_DECODER_V2.md`, `c/ARISTOTLE_PROMPT_V2.md`, upload digests listed).
* **Why not started:** your conditions require an enforceable limit. The tools offer no per-run
  budget; cancellation works only while this session is active, and usage limits suspended it
  during the first run (92 credits billed against 50) and twice during this work. Balance: 407.8
  promotional credits, 0 paid, expiring 2026-11-29 06:00 UTC.
* **To proceed:** configure a credit check-in (a server-side pause) in the Aristotle web app, or
  submit the prepared prompt yourself from the web app, or state that supervised cancellation by a
  session is acceptable. Recommended scope: P1 to P3 of the decoder only, at most 100 credits.

## Prospective evaluation

### A1–A5. Protocol, thresholds, model configuration

See [`../../research/claimcheck_v1_1/prospective/DECISION_PACKAGE.md`](../../research/claimcheck_v1_1/prospective/DECISION_PACKAGE.md)
(section 14 summarises the decisions). Recommendations: ICC floor 0.25 with a "not robust" rule at
0.5; 120 papers on three conditions; wording threshold 0.20; C2c 50 % with at least 5 flags plus two
corrections; screening cap 600 per context; configuration P capped at 30 USD for 120 papers, with
the cap enforced in code before each request. It lists 19 inconsistencies in draft 2 (8 to fix
before approval). Nothing was sampled, inspected or run; no one was recruited.
