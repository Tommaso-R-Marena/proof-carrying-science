# Owner execution checklist: C1, C2, D1–D3, R1 (and the decisions that must precede them)

**Nothing in this file has been executed.** Each block is a separate decision: approving one
authorises only its own steps. No protected patch, tag, merge or deployment happens without the
owner's explicit authorisation of that block. The independent review
([`INDEPENDENT_REVIEW_CHECKLIST.md`](INDEPENDENT_REVIEW_CHECKLIST.md)) should pass first.

Order:

* **Core:** L1–L3, P1 and H1, then T1 (recommended), then C1, then C2 (and optionally C2b), then
  R1.
* **Website:** D1 and D3, then regenerate, then D2 (and optionally D2b).
* **Both, optional:** G1, the gate-definition guard, at any time; it changes how every later gate
  change is merged.
* **Both:** merge and deployment are separate decisions after these. Before any merge, run the
  gate-definition check in "Before every merge" below.

Any change to the branch after the evidence was generated (an L decision, D1, D3) changes the
source commit. The evidence must then be regenerated and reviewed again.

## Before admission

### L1–L3. Recorded model outputs ([`MODEL_OUTPUT_LICENSING.md`](MODEL_OUTPUT_LICENSING.md), sections 4 and 7)
* **Recommended:**
  * L1 keep the 23 Gemini outputs, with provenance in `model_outputs_inventory.json`;
  * L2 and L3: withhold the 21 Nemotron outputs and the 1 Cohere output from further publication.
    Replace them by provenance stubs, after you have archived the originals privately and checked
    them against the inventory's digests;
  * ask NVIDIA (L2(a)), and restore the originals if permitted;
  * squash-merge PR 212 only;
  * no history rewrite.
* **Authorised (2026-11-19):** preparation, and the replacement after a verified private archive.
* **Status:** the capacity study's cache-dependent work is finished. The archive tool is verified on a
  private container copy: 22 of 22 files match, archive SHA-256 `91acf4ff…69a3`. That copy is not an
  archive: the container is disposable. No genuinely private, durable destination is available to
  this session, so the originals are unchanged.
* **Your action (A1), one of:**
  * run `python3 -m research.claimcheck_v1_1.governance.archive_model_outputs --out <private dir>` on
    a machine you control. It must print `"recoverable_and_complete": true` and archive SHA-256
    `91acf4ff324f6547eaa51cc9a03e2a377c43a7544adc65f3cb2da38c2a6669a3`. Keep the archive privately
    and confirm;
  * or attach a computer folder to this session for the archive;
  * or name another private destination you authorise.
* **Steps after your confirmation:**
  1. Run `python -m research.claimcheck_v1_1.governance.withhold_model_outputs --apply --groups N,C --decision "<reference>"`
     and commit the result.
  2. Run the suites and `withholding_effect`.
  3. Regenerate the admission evidence.
* **Effect:** no frozen file and no test is affected. Regenerating the Nemotron arm offline then
  needs your archive. The measured effect on every offline tool is in `withholding/withholding-effect.json`
  (`MODEL_OUTPUT_LICENSING.md`, section 7). This is an ordinary commit, but it changes the census.
* **Not before:** the capacity run has finished reading the original caches, and you have confirmed
  the final archival and replacement plan (owner, 2026-11-19).
* **What it does not do:** withdraw public access. The originals stay reachable through PR 212,
  PR 216, clones and, under C1 as designed, the retained-source tag (`MODEL_OUTPUT_LICENSING.md`,
  section 5). See P1 and H1.

### P1. Provider clarification (NVIDIA), before C1
* **Decision:** whether to ask NVIDIA if research outputs obtained through trial access may be
  published (suggested wording: `MODEL_OUTPUT_LICENSING.md`, section 6).
* **Who sends it:** you; this work contacts no provider. Draft for your review:
  [`P1_NVIDIA_REQUEST_DRAFT.md`](P1_NVIDIA_REQUEST_DRAFT.md).
* **Not a prerequisite** for the capacity study, non-protected preparation or H1-b.
* **Outcome:** decides between H1-a and H1-b, and whether the 21 Nemotron originals may be restored.

### H1. Historical exposure: which retained commit C1 pins ([`H1B_CLEAN_HISTORY.md`](H1B_CLEAN_HISTORY.md))
* **H1-b (recommended):** the retained commit's first parent is a snapshot with the admitted tree on
  protected `main` (`bc78660b`), so the tag keeps no commit of this branch reachable. Implemented in
  the tooling (`prepare_core_admission --history clean`, the default) and tested: 12 adversarial
  tests (`h1b/h1b-adversarial.json`). The gates are unchanged and check the same things.
  * **Cost:** the protected tag retains the reviewed tree, not the branch's development history.
  * **What it does not do:** remove anything from pull requests 212 and 216, or from clones.
* **H1-a (fallback):** the original design; the tag keeps the whole branch reachable, including the
  commits that added the recorded responses.
* **H1-c:** rewrite history. Not recommended.
* **Authorises:** which of the two designs C1 pins. Nothing is created by this decision itself.

### T1. Retained-source tag ruleset ([`REQUIRED_CHECKS.md`](REQUIRED_CHECKS.md), "Retained-source tags")
* **Authorises:** in each repository, the tag ruleset specified in
  [`REQUIRED_CHECKS.md`](REQUIRED_CHECKS.md), "T1":
  * pattern `pcs-source-intake/*`;
  * Restrict creations, updates and deletions;
  * Block force pushes;
  * bypass only for the repository-admin role.
* **Checked against GitHub's published REST description** (2026-11-19): the body validates and four
  malformed variants are rejected (`REQUIRED_CHECKS.md`). Choose "Repository admin" in the UI rather
  than relying on the role number `5`, which the description does not document.
* **Verify:** listing tags still shows the two existing intake tags at `0b521f39…` (core) and
  `d35e2b5e…` (site). A push of a `pcs-source-intake/*` tag by anyone but you is refused.
* **Undo:** delete the ruleset.

## Core

### C1. Admit the ClaimCheck sidecar (protected)
* **Authorises:**
  * the retained commit;
  * the annotated tag `pcs-source-intake/core-claimcheck-v1-20261114` on it;
  * one control commit with the four files from `--emit`;
  * merging that control commit after its checks pass.
* **Does not authorise:** any other file change, ruleset change (C2), deployment, or the research
  branch (R1).
* **Steps:**
  1. Fix `H`, the PR 212 head after the L decisions. Run
     `python -m research.claimcheck_v1_1.governance.check_admission_consistency`; it must report
     `consistent: true`.
  2. Run
     `python -m research.claimcheck_v1_1.governance.prepare_core_admission --out D1 --pytest-python <python> --emit D2`.
     It must report `all_as_expected: true`. The V23 digest, the control-file digests and the
     retained commit must equal the PR description for `H`, and
     `review_v23_manifest --emit D2 --head H` must report `consistent: true`.
  3. Create the retained commit with the exact commands in `ADMISSION_PROPOSAL.md`, step 4, for the
     design chosen under H1 (fixed identity, date and messages; two commands under H1-b). Its ID must
     equal `proposed_retained_source_commit.commit` in `D1/dry-run.json`, and the dry run must report
     `retained_history_as_designed: true`.
  4. Check that the tag name is free:
     `git ls-remote --tags origin 'refs/tags/pcs-source-intake/core-claimcheck-v1-20261114'` prints
     nothing. Then run
     `git tag -a pcs-source-intake/core-claimcheck-v1-20261114 <retained commit> -m "<message>"` and
     `git push origin refs/tags/pcs-source-intake/core-claimcheck-v1-20261114`. If T1 is in force,
     act as the admin bypass.
  5. On top of `H`, commit exactly the four files from `D2` as one commit, and open or update the
     pull request.
* **Verify:**
  * on the control commit, `source-policy` and `verified-public-integration` pass;
  * `model-assurance-studio-research.yml` runs (the control commit touches integration paths) and
    `check_reconciled_prs.py --core` passes;
  * `claimcheck-required` passes.
* **Stop if:**
  * any digest differs from the reviewed value;
  * the tag name already exists;
  * the control commit touches a fifth file;
  * any required check fails.
* **Undo before merge:**
  * delete the tag (`git push origin :refs/tags/pcs-source-intake/core-claimcheck-v1-20261114`);
  * drop the control commit;
  * the retained commit then becomes unreferenced.

  After merge, undoing it is a new reviewed change.

### C2. Require `claimcheck-required` on core `main` (ruleset)
* **Authorises:** adding the GitHub Actions check `claimcheck-required` to the core `main` ruleset,
  after C1 is merged.
* **Verify:** an unrelated pull request still gets `claimcheck-required` reported (it runs on every
  pull request) and is not left pending.
* **Undo:** remove it from the ruleset.

### C2b (optional). Make the core retained-source gate bind on every pull request (protected code)
* **Authorises:** one control commit after C1 applying `docs/integration/claimcheck/c2b/proposed-c2b.patch`:
  * `reconcile.py --require-committed`, already in the required `source-policy` path, also runs the
    retained-source gate;
  * two control files change; no workflow, manifest or ruleset.

  Specification: [`REQUIRED_CHECKS.md`](REQUIRED_CHECKS.md), "C2b".
* **Before:** regenerate with `prepare_c2b` at the commit after C1. The dry run must report
  `all_as_expected: true`: the negative controls (tag deleted, tag moved, untracked file) pass under
  C1 alone and are rejected with C2b.
* **Verify:** on the control commit, `source-policy` and `verified-public-integration` pass, and the
  gate's output includes `retained_source.passed: true`.
* **Undo:** revert the control commit.

### R1. Research assurance branch (PR 216)
* **Decision:** confirm the route. Recommended: a separate V24 successor after C1 is merged, built by
  the same script on the research branch.
* **Authorises now:** nothing. A V24 proposal, with its own census, dry run and review, would be
  prepared on request after C1.

## Website

### D1. Reading-help successor (protected verifier, patch 01)
* **Authorises:** `git apply -p0 docs/governance/claimcheck-proposals/01-reading-help-verifier.patch`
  as one commit on the site branch (digest `98218343…d398`).
* **Verify:** `beginner-browser` and `lean-learning-browser` pass. `site-full-gate` passes once D3
  also holds and the evidence is regenerated.
* **Undo:** revert the commit.

### D3. ClaimCheck tests in the complete gate (patch 03)
* **Authorises:** `git apply docs/governance/claimcheck-proposals/03-complete-gate.patch` as one
  commit (digest `53e96704…98fd1`).
* **Verify:** `npm run ci:zero-minutes` runs the 15 ClaimCheck tests.
* **Undo:** revert the commit.

### Regenerate (after D1 and D3, not protected)
Fix the new site head `S_site'` and run:

* `python3 scripts/dry_run_claimcheck_proposals.py --commit S_site'`;
* `python3 scripts/prepare_claimcheck_site_admission.py --commit S_site'`;
* `python3 scripts/check_claimcheck_proposals_consistency.py`, which must report `consistent: true`;
* `python3 scripts/claim_check_journey_record.py check --record docs/evidence/claim-check-v2`, which
  must pass.

The retained commit changes from `6c1ec33e…`, because `S_site'` differs from `e0b9136`. Review the
new values.

### D2. Admit the website change (protected gate, patch 02, retained commit and tag)
* **Authorises:**
  * the retained commit recorded in the regenerated `02-reconciliation-gate.dry-run.json`;
  * the annotated tag `pcs-source-intake/site-claimcheck-v1-20261117` on it;
  * the regenerated patch 02 as one separate control commit.
* **Steps:**
  1. Reproduce the retained commit (`successor.reproducible_with`); its ID must equal
     `successor.retained_commit`.
  2. Check that the tag name is free with `git ls-remote`, then create and push the annotated tag.
  3. Apply patch 02 and commit.
* **Verify:** `original-pr-ancestry-and-production-preservation`, `beginner-browser`,
  `lean-learning-browser` and `site-full-gate` pass.
* **Stop if:** an ID or digest differs, the tag exists, or a check fails.
* **Undo before merge:** delete the tag and drop the control commit.

### D2b (optional). Require `original-pr-ancestry-and-production-preservation` on site `main` (ruleset)
* **Caveat (verified 2026-11-19):** a pull request that edits its own workflow can make this check
  pass without the gate running (`REQUIRED_CHECKS.md`, "D2b: can a pull request make the required
  check vacuous?"). The same holds for every required check in both repositories. Smallest protection:
  the gate-definition check before every merge (below), or G1.
* **Authorises:** adding exactly that check, with the source GitHub Actions, to the active site
  `main` ruleset ([`REQUIRED_CHECKS.md`](REQUIRED_CHECKS.md), "D2b"). It runs on every pull request
  and so can never stay pending.
* **Why:** after D2, it is the only check that enforces the `public/` anchor and the retained-source
  rule.
* **Consequence:** every later website change needs a retained-source admission.
* **Undo:** remove it from the ruleset.

### G1 (optional, both repositories). Gate-definition guard (protected: one workflow on `main` and one required check)
* **Authorises:** committing `docs/integration/claimcheck/g1/gate-definition-guard.<repo>.yml` to
  `.github/workflows/` on `main`, through a reviewed pull request, and then adding
  `gate-definition-unchanged` (GitHub Actions) to the `main` ruleset.
* **What it does:** a `pull_request_target` job, defined on `main` only, fails whenever a pull
  request changes any workflow or a gate-defining file. It reads the pull request as data and runs
  nothing from it; the token is read-only and no secret is used.
* **Consequence:** every later gate change (C1, C2b, D2 and later admissions) merges only through
  your recorded ruleset bypass.
* **Before relying on it:** check in a scratch repository how GitHub decides a required check when two
  workflows report the same job name (`REQUIRED_CHECKS.md`, "G1").
* **Undo:** remove the check from the ruleset, then remove the workflow.

## Before every merge (no change; recommended now)

Run, from a full clone:

* core: `git diff --name-only origin/main...<head> -- .github/workflows scripts/check_reconciled_prs.py scripts/test_reconciled_prs.py docs/reconciliation/OPEN_PRS.json research/integration_v2 docs/integration/2026-11-05 docs/integration/2026-11-14`;
* site: `git diff --name-only origin/main...<head> -- .github/workflows scripts/check_reconciled_prs.py scripts/test_reconciled_prs.py docs/reconciliation/OPEN_PRS.json`.

Any output means the pull request changes the definition of a gate. Merge it only as its own
approved protected change.

## After all of the above (separate decisions)

* **Merge** each pull request under the existing linear-history rules.
* **Deploy** the website page: a separate decision, not requested.
