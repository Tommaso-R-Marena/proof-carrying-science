# Owner decision package: ClaimCheck integration (final pre-admission pass, 2026-11-18; decisions of 2026-11-19 recorded)

**Final consolidation, later on 2026-11-19.** The single approval package is
[`APPROVAL_PACKAGE.md`](APPROVAL_PACKAGE.md): one block per protected decision (C1, C2, C2b, D1, D2,
D3, D2b, T1, H1, R1, and the optional G1). Each block says what the decision changes, why, the
evidence, the assumptions, what approving authorises and what rejecting means. What changed since
the sections below were written:

* **Capacity study (A7 Part C):** complete. See `../../../research/claimcheck_v1_1/prospective/DECISION_PACKAGE.md`,
  section 16.
* **Licensing (L1–L3):** the archive tool is verified. Nothing is withheld yet, because no durable
  private destination is available to this session (owner action A1; `MODEL_OUTPUT_LICENSING.md`,
  section 7).
* **H1-b:** implemented and tested; 11 of 12 adversarial tests pass ([`H1B_CLEAN_HISTORY.md`](H1B_CLEAN_HISTORY.md)).
  Test 9 found a trust root that predates H1-b: a committed edit to
  `research/integration_v2/reconcile.py` or `test_reconcile.py` passes both gates.
* **C2b:** the dry run is all as expected.
* **D2b:** a pull request can make a required check vacuous by editing its own workflow. The
  pre-merge check and G1 are proposed.
* **T1:** validated against GitHub's REST description.
* **P1:** drafted, not sent.

**Recorded on 2026-11-19 (owner's statements).**

* The C3, C4, C5 and D4 fixes are accepted as the proposed internal-research baseline, subject to
  final source review, and are not to be reverted.
* The core `main` ruleset requires `verified-public-integration`, the site `main` ruleset requires
  `site-full-gate`, and neither has a bypass actor.
* Part C of the feasibility study only is authorised.
* Draft 3 stays unapproved.

**Prepared for the next steps:**

* [`INDEPENDENT_REVIEW_CHECKLIST.md`](INDEPENDENT_REVIEW_CHECKLIST.md): independent review of C1 and
  D1–D3;
* [`OWNER_EXECUTION_CHECKLIST.md`](OWNER_EXECUTION_CHECKLIST.md): one block per decision;
* [`ORACLE_SWITCH_ISOLATION.md`](ORACLE_SWITCH_ISOLATION.md): the development switches, and the
  isolation needed before a public release;
* [`MODEL_OUTPUT_LICENSING.md`](MODEL_OUTPUT_LICENSING.md): disposition L1 to L3;
* [`REQUIRED_CHECKS.md`](REQUIRED_CHECKS.md): which gates bind on every pull request; retained-source
  tag protection (T1).

Each decision below is separate: approving one does not approve another. **Nothing here has been
applied, merged, deployed, tagged or approved by the assistant.** The three pull requests (core 212,
research 216, website 149) are drafts.

Some numbers depend on the exact head of a pull request: the core head itself, the V23 manifest
digest and the retained commit. Those are in the pull request description, because evidence about a
commit cannot be stored inside that commit (see [`ADMISSION_PROPOSAL.md`](ADMISSION_PROPOSAL.md),
"Why the evidence names an earlier commit"). For the same reason, the CI results of the final heads
are in the pull request descriptions.

The words used below:

* **implemented**: on a draft branch, not merged or deployed;
* **tested**: the named tests pass;
* **proved**: a Lean theorem checked by the kernel;
* **proposal**: prepared, not applied.

## 1. Security fixes that are implemented and tested

| | Fix | Commit | Tests |
| --- | --- | --- | --- |
| C3 | **Strict, hardened stand-alone runner.** It refuses any proof file whose tail is not exactly the generator's canonical form, before Lean starts, so the tail forgery is closed. It takes Lean only from an explicit path or an absolute PATH entry, never the working directory. It runs Lean with a minimal environment and a memory cap, limits literal size, writes its output atomically and records the Lean executable and its digest. SHA-256 `831bbaba…f75e9`. It replaces the withdrawn `8d9e07b4…` and `459155f3…`. | core `52b5e182`; site serves the same bytes (`b95a34b`) | `tests/test_runner_strict.py`, `test_runner_hardening.py` (11), `runner_negative_controls.py` (14), `check_live_v11.py` with the real kernel |
| C4 | **The v1.1 replay binds the claim to the sentence.** The reported value must be the printed literal, and the checked variants must be those the statistic requires. | `1d2f80ef` | `tests/test_binding_offline.py`: three former gaps refused; 0 violations on 302 committed receipts |
| C4 | **Checked replay of v1 bundles.** It runs the frozen v1 replayer unchanged, then adds the binding and result-consistency checks v1 lacks. A warning file stands beside the frozen replayer. | `035afec2` | six held-out bundles (302 receipts) pass, bundle 08 with the real kernel in CI; the three forgeries are refused while the frozen replayer alone accepts them |
| C5 | **The outward verdict follows the kernel-established status.** `established_status` recomputes the status from the kernel-accepted variants and requires `result`, `q1.status`, `q1.conditional` and `reason` to agree. `binding_problem` ties the claim to the sentence. An inconsistent receipt gives UNKNOWN and corroborates nothing, and the last check is no longer an `assert`. | `5a18afd7` | `tests/test_decide_guard.py` (7, including all 240 summary-field combinations, forged, downgraded and missing variants, another number or statistic, a dropped convention, forged siblings); 1,590 committed receipts consistent; site catalog re-exports byte-identical |
| C5 | **Follow-up: development evaluation.** It passed no development switch for its oracle receipts and silently scored five development documents as UNKNOWN. | `2830547d` | `tests/test_oracle_opt_in.py`: the pipeline and site export pass no development switch; `dev_arms.json` reproduced on every recorded value |
| D4 | **The page's receipt rule.** Only v2 receipts about the page's own proof file, data and pinned checker are shown, labelled as reported by the user's run, never as verification. Fixed refusal messages; a snapshot at Check; reset on any input change. | site `e2e7451` | `npm run test:claim-check` (15); browser journey with the real kernel (successor record `docs/evidence/claim-check-v2/`, bound to the page bytes at site `c216672`) |
| C2 | **Required-check workflow.** It runs on every pull request; `changes` diffs the merge commit with renames off, and `claimcheck-required` always reports. Actions are pinned and the checkout keeps no credentials. | in the workflow on PR 212 | `governance/test_required_check.py`: 13 scenarios on real merge commits; of 192 result combinations, exactly the 17 intended pass |
| A5/A1 | **Enforcement code for a future prospective run.** It is not a fix to deployed function, and it has been tested with synthetic stand-ins only. `prospective/budget.py` refuses, before sending, any request whose worst case (whole request body, maximum output, frozen prices) could pass a cap, and halts if a response ever costs more than its worst case. `prospective/lean_guard.py` stops Lean at 7 GB and ties Lean to itself, so a timeout leaves no unguarded process. | `bcf62944`, review fixes `cf15770f` | `tests/test_budget.py` (15), `tests/test_lean_guard.py` (3); each review fix has a test that fails on the reviewed draft |

Whole v1.1 suite at the final source commit: 132 tests and 69 subtests pass. The frozen v1 freeze
check passes: software `1a7eeb57…ae2d`, benchmark `1a200180…c890`. No frozen file or historical
record was changed.

## 2. Source-admission and qualification changes: proposed, not applied

| | Proposal | Where | What you would do |
| --- | --- | --- | --- |
| C1 | **Admit the ClaimCheck sidecar** (2,006 added files as of the committed evidence, which describes `763aaa8b` under the H1-a design; the head on 2026-11-19 adds 2,048; no existing file changed; regenerate after A1 with `--history clean`). Successor manifest V23, edits to `reconcile.py`, `test_reconcile.py` and `check_reconciled_prs.py`, a retained commit whose tree equals the admitted commit, and the tag `pcs-source-intake/core-claimcheck-v1-20261114`. | [`ADMISSION_PROPOSAL.md`](ADMISSION_PROPOSAL.md), [`ADMISSION_AUDIT.md`](ADMISSION_AUDIT.md), [`proposed-control-changes.patch`](proposed-control-changes.patch), [`dry-run.json`](dry-run.json) | the exact steps in `ADMISSION_PROPOSAL.md`, "What the owner would do"; start with `check_admission_consistency` |
| C2 | Require exactly `claimcheck-required` on core `main` after C1. | [`REQUIRED_CHECKS.md`](REQUIRED_CHECKS.md) | ruleset change |
| D1 | The reading-help verifier accepts exactly one reviewed successor of its pin. | site `docs/governance/CLAIMCHECK_PROPOSALS.md`, patch 01 | apply patch 01 |
| D2 | Public-tree admission. The retained commit `6c1ec33e…` has the same tree as site `e0b9136`, its parents are that commit and `d35e2b5e…`, and its tag is `pcs-source-intake/site-claimcheck-v1-20261117`. | patch 02, census (51 files) | the site's section 5 steps |
| D3 | ClaimCheck's mandatory page tests become part of the required `site-full-gate`. | patch 03 | apply patch 03 |
| R1 | Admit the assurance research separately, after C1, as a V24 successor. | PR 216 | decide the route |

The dry runs are reproduced from scripts at the final source commits. Each is checked by an
independent consistency checker, which recomputes the following from the repository itself: the
census against the commit, the patch against the proposed digests, the gate against the proposed
manifest digest, and the retained commit by `git commit-tree`, which creates no ref.

* core: `python -m research.claimcheck_v1_1.governance.check_admission_consistency`;
* site: `python3 scripts/check_claimcheck_proposals_consistency.py`.

Rulesets cannot be read with the tools available here. Both `main` branches are reported protected.
The settings to verify by hand are listed in [`REQUIRED_CHECKS.md`](REQUIRED_CHECKS.md), "What to
verify by hand in the rulesets".

## 3. Formal guarantees versus executable conformance tests

| Kind | What | Where |
| --- | --- | --- |
| **Proved** (Lean 4.28, kernel-checked; 67 theorems, axioms only `propext`, `Classical.choice`, `Quot.sound`; no `sorry`) | the canonical claims-part language: renderer and parser round trip, canonicity, injectivity, one meaning one text; the header binding chain: decoder correctness, hex value = `ofBytes`; the abstract outward-verdict function | research branch, `formal/`, `AXIOMS.expected` |
| **Tested, not proved** | the runner's Python parser agrees with the proved Lean parser on 10,720 vectors (0 disagreements); the Python outward decision agrees with the Lean function on all 983,040 reachable points of its 1,310,720-point domain; the real guard accepts every receipt the pipeline can write (84 status patterns) and decides nothing outside its input condition | research `conformance/` (`CORRESPONDENCE.md`) |
| **Tested** | everything in section 1 | named tests |
| **Reported by an external service, not replayed here** | Aristotle's results for the first C decoder (properties, unresolved obligations, a counterexample). No proof artifact was returned, so nothing is claimed to be kernel-checked. They are not a statement about the Python code. | research `c/ARISTOTLE_RESULTS.md` |
| **Not established** | the correctness of the Python or JavaScript implementations as a whole (there is no refinement proof); the scientific correctness of any confirmed or flagged claim (a confirmation says only that the stated arithmetic holds on the bound data under the stated reading); human usability (no participant) | |

## 4. Existing vulnerabilities and unresolved authority gaps

1. **The frozen v1 replayer keeps the claim-binding gap** (by design, not modified). It must not be
   used to establish the integrity of untrusted verification bundles. Use the v1.1 replayer, or
   `replay_v1_bundle_checked.py` for v1 bundles (`research/claimcheck_v1/LEGACY_REPLAY_WARNING.md`).
2. **The withdrawn runners** (`8d9e07b4…`, `459155f3…`) remain in history. The research branch
   keeps one deliberately as reproduction evidence. Any copy of them still accepts forged tails. The
   page serves and pins only `831bbaba…`. No recorded result depends on a runner.
3. **A receipt is a report, not a verification.** The guard detects inconsistency; it cannot detect
   a consistent lie in the kernel record itself. Only re-running the kernel (replay) re-establishes a
   result.
4. **The development switches** `oracle_receipts` and `oracle_siblings` are part of the policy's
   interface. The pipeline and the site export pass neither, and a test checks it, but no runtime
   control would stop a new outward caller that passed one.
5. **Until C1 and C2:**
   * `claimcheck-required` is not required;
   * a pull request can edit the ClaimCheck workflow, which is not yet pinned by a manifest;
   * the site's `claim-check-page` is path-filtered;
   * the live rulesets are unverified (manual checklist).
6. **Prospective guards have stated limits.**
   * The memory guard samples every 0.05 s, so a shorter spike can exceed 7 GB.
   * The spending guard assumes billed tokens do not exceed request bytes, and that the output
     maximum covers reasoning tokens. If either assumption is wrong, the tripwire stops it, after an
     overshoot of at most one request.
   * Provider-side hard limits are still needed.
   * The Gemini price is unset, so paid Gemini requests are refused.
7. **Aristotle:** the available tools offer no enforceable per-run spending limit. The first run
   exceeded its allowance (92 credits billed against 50, promotional, no paid charge).
8. **Licensing:** there are 45 recorded model outputs, not 35; the audit had missed the 10
   development responses. On the providers' terms:
   * Gemini (23): redistribution is supported.
   * Nemotron (21): not established (NVIDIA's trial terms: internal testing and evaluation, not
     production).
   * Cohere (1): not permitted.

   All 45 are already readable on the public draft branch. Decide L1–L3 before C1
   ([`MODEL_OUTPUT_LICENSING.md`](MODEL_OUTPUT_LICENSING.md)).

   Withholding stubs and a squash merge do not remove public access. The retained commit's first
   parent reaches the commits that added the outputs, so under C1 as designed the public tag keeps
   them reachable. Decide P1 (NVIDIA clarification) and H1 (historical exposure) before C1
   (sections 5 and 6).
9. **Gates that bind less than they appear to** ([`REQUIRED_CHECKS.md`](REQUIRED_CHECKS.md), "Which
    gates bind"):
    * The core retained-source gate runs only on pull requests that touch integration paths.
    * The site's retained-source and `public/` gate is not a required check.
    * Options C2b and D2b address these.
10. **Red checks by design** until you decide:
   * core: `source-policy` and `verified-public-integration` (C1);
   * site: `beginner-browser`, `lean-learning-browser` and `original-pr-ancestry-and-production-preservation` (D1, D2), and `site-full-gate`, which requires `lean-learning-browser` to pass.

## 5. Exact commits, digests, CI and owner-held actions

**Core (PR 212).**

* Fixes: `52b5e18287682619480e6e5da2d4582d002aa8ca` (runner), `1d2f80efa104b6be051cec02fd95403f7ff5cde7` (replay binding),
  `5a18afd71f8253bb078e5280acfee4d8292ddca3` (guard), `035afec20e708ada335114eb16b2a9a25f775483` (legacy warning, checked v1 replay),
  `2830547d45b1e3f7048dd494cba6dbb7aa62bed0` (development evaluation), `bcf629443b52e0dbe3ae126131c4ea07c77b2125` (protocol draft 3),
  `cf15770f820ad9eb65c5255aa6918679f0b5d980` (review fixes), `ca35bf94b5bcec189e4ff06e7d857188269a37cd` (consistency checker).
* The final source commit, its evidence commit, the V23 digest, the retained commit and the CI
  results are in the PR description.
* Protected baseline: `main` at `bc78660b5fac857fce3873eb6cda0445d1903da1`; V22 `28cc42a65a20f1d7697833d8a6ecca0f8cb37ac787f9eaeeb7ffc3686d26ce83`; retained intake
  `0b521f39af99f5856b69dfcc25bc274ec9dc804a` (`pcs-source-intake/core-open-prs-v1-20261105`).
* Runner `831bbababd2f48e5b9f62fa33433fe7edfbc8ee1f2271e3e7700b883745f75e9`.

**Website (PR 149).**

* Final source commit `e0b9136cf7e8480cfcf55c9bfa86b9582f22e39e`; evidence commit `fc6c7a468f3a614c5126f65092aa5e2d7b817974`.
* Retained commit `6c1ec33e51c3ead21fcaa07f368b7a1c791771dc` (tree `1a2ab000ce15f14ad942240105a5efabda8a21e3`).
* Journey record bound to `c21667253e5725aae7e3b1fa90e61a87287dd29b`. The predecessor record is unchanged.
* `main` at `e8136625`.

**Research (PR 216):** its head is in the PR description. It merges this branch and changes nothing in it.

**Owner-held actions.** None has been taken.

1. **C1:** fix the commit to admit, run the consistency check, then regenerate with `--emit` and
   compare digests with the PR description. Create the retained commit exactly as recorded, and
   create and push its tag. Commit the four control files as one reviewed commit.
2. **C2:** add `claimcheck-required` after C1. Rulesets: required checks and bypass confirmed by you on 2026-11-19; still open are T1 (tag ruleset), C2b and D2b (`REQUIRED_CHECKS.md`).
3. **C3 to C5, D4:** accepted on 2026-11-19 as the internal-research baseline, subject to final source review.
4. **D1 to D3:** apply patches 01 to 03; for D2, create the retained commit and push its tag.
   Deploying the page is a separate decision.
5. **R1:** choose the research route.
6. **Aristotle (E2):** no run unless an enforceable limit exists and you authorise it separately.
7. **Prospective:**
   * review draft 3 and choose the open values (ICC floor, 60 or 120, wording threshold, C2c,
     screening cap, configuration and the Gemini price);
   * decide the feasibility study (A7), and separately authorise recruitment, any model call and
     re-fetching pool articles;
   * set provider-side hard limits;
   * approval freezes the protocol by digest.
8. **Licensing** of the recorded model outputs: L1 to L3, before C1.
9. **Merges and deployment.**

The prospective decisions in detail: [`../../research/claimcheck_v1_1/prospective/DECISION_PACKAGE.md`](../../../research/claimcheck_v1_1/prospective/DECISION_PACKAGE.md)
(section 14, the feasibility study; section 15, the summary). The decision register:
[`../../research/claimcheck_v1_1/OWNER_DECISIONS.md`](../../../research/claimcheck_v1_1/OWNER_DECISIONS.md).
