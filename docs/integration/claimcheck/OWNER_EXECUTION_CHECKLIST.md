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
* **Done (2026-11-24).** You confirmed both archive copies and authorised L1 to L3. The withholding
  is `bed633654eca603da4c4975c547853a630f27532`, G2's workflow `0f0fe0313db3fac8b0fd208e3f3e1ce3197bc6dd`, and the
  consolidated gate's successor `8631e9c2924f2618df264dda3f69ceeede56e624`. The evidence was regenerated afterwards at
  the source commit named in `dry-run.json`. The steps below are kept as they were run.
* **Status (2026-11-21):** the capacity study's cache-dependent work is finished. The originals are
  unchanged. The archive tool was tested end to end:
  * a fresh clone from GitHub at commit `e6099049`, the tool run as a plain script in isolated mode;
  * Python 3.11, 3.12 and 3.13: 22 of 22 files, the same archive SHA-256 `91acf4ff…69a3`;
  * the four damaged-copy controls fail, and the archive rebuilds byte-identically after a simulated
    withholding.

  Every copy made here was deleted. No durable private destination is available to this session.
* **Your action (A1):** follow [`A1_ARCHIVE_PROCEDURE.md`](A1_ARCHIVE_PROCEDURE.md) (Windows
  PowerShell, local only, a second copy on a drive you own). Then send the SHA-256 and
  `recoverable_and_complete` from both checks. Expected:
  `91acf4ff324f6547eaa51cc9a03e2a377c43a7544adc65f3cb2da38c2a6669a3` and `true`.
* **Steps after your confirmation (done):**
  1. Run `withhold_model_outputs --apply --groups N,C --decision "<your confirmation: date, SHA-256>"`.
     It writes the provenance stubs and touches nothing else.
  2. Check:
     * the stubs' digests equal the inventory's;
     * the freeze check, and the v1 and v1.1 suites;
     * the regenerated `withholding_effect`.
  3. Commit the withholding as one commit and push it.
  4. Commit G2's workflow edit (`g2/proposed-g2-core-workflow.patch`). G2 was approved in principle
     on 2026-11-22 for inclusion in the final C1 admission.
  5. Regenerate the admission evidence at that exact commit:
     * `prepare_core_admission --history clean`;
     * `check_admission_consistency --history clean`;
     * the H1-b tests;
     * the C2b dry run, and the G2 dry run if chosen.

     H1-b's `all_as_expected` must now be `true`, with no withheld response reachable.
  6. An independent subagent, under the same restrictions, reviews the regenerated evidence against
     `INDEPENDENT_REVIEW_CHECKLIST.md`.
* **Effect:** no frozen file and no test is affected. Regenerating the Nemotron arm offline then
  needs your archive. The measured effect on every offline tool is in `withholding/withholding-effect.json`
  (`MODEL_OUTPUT_LICENSING.md`, section 7). This is an ordinary commit, but it changes the census.
* **Not before:** your confirmation of the archive's SHA-256 and `recoverable_and_complete: true`
  (owner, 2026-11-21).
* **What it does not do:** withdraw public access. The originals stay reachable through PR 212,
  PR 216 and clones, and, under H1-a only, through the retained-source tag
  (`MODEL_OUTPUT_LICENSING.md`, section 5). See P1 and H1.

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
  the tooling (`prepare_core_admission --history clean`, the default) and tested
  (`h1b/h1b-adversarial.json`): 11 of 12 adversarial tests pass. Test 9 fails under either design:
  a committed edit to `reconcile.py` or `test_reconcile.py` passes both gates. The gates are
  unchanged and check the same things.
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
     equal `proposed_retained_source_commit.commit` in `D1/dry-run.json`. The dry run must report:
     * `retained_history_as_designed: true`;
     * `proposed_retained_source_commit.history` equal to the chosen design;
     * under H1-b, an empty `retained_history_review.withheld_blobs_reachable`. **Stop if it is not**:
       the withholding commit is missing.
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
* **Dry run of 2026-11-19:** all as expected (`c2b/c2b-dry-run.json`; `REQUIRED_CHECKS.md`, "C2b").
* **Before:** regenerate with `prepare_c2b` at the commit after C1. The dry run must report
  `all_as_expected: true`: the negative controls (tag deleted, tag moved, untracked file) pass under
  C1 alone and are rejected with C2b.
* **Review:** C2b edits `reconcile.py`, which no gate can check (H1-b test 9). Read its diff line
  by line.
* **Verify:** on the control commit, `source-policy` and `verified-public-integration` pass, and the
  gate's output includes `retained_source.passed: true`.
* **Undo:** revert the control commit.

### R1. Research assurance branch (PR 216)
* **Decision:** confirm the route. Recommended: a separate V24 successor after C1 is merged, built by
  the same script on the research branch:
  * the H1-b way, on post-C1 `main`, with C1's retained commit as the previous intake;
  * only after the research branch's tree carries the withholding stubs;
  * and PR 216 squash-merged only, because a merge commit would bring its development history,
    with the three response commits, into `main`. A rebase merge would too, and the same holds for
    PR 212.

  Built that way, the V24 retained commit reaches the snapshot on post-C1 `main`, and C1's retained
  commit with its clean chain. It reaches none of the three response commits (H1-b test 12). The
  required ancestry, the exact tree and every digest pin stay as for C1.
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
* **Deferred (owner, 2026-11-22).** With G2, the pre-merge check covers the rest as a procedure, and
  you are the only person who can merge. The remaining risk:
  [`WORKFLOW_SELF_MODIFICATION_RISK.md`](WORKFLOW_SELF_MODIFICATION_RISK.md).
* **What it does:** a `pull_request_target` job, defined on `main` only. It fails whenever a pull
  request changes:
  * any workflow;
  * a gate-defining file;
  * an import path of a gate (root `*.py`, `*.pyc`, `*.so` and packages, `scripts/`, bytecode or a
    compiled module anywhere, a new `research/__init__.py`, `conftest.py`, `sitecustomize.py` or
    `usercustomize.py`).

  It compares against `main` fetched at run time, and runs again when a pull request is retargeted.
  It reads the pull request as data and runs nothing from it; the token is read-only and no secret
  is used.
* **On the site, G1 alone does not protect `site-full-gate`:** its tests and build scripts are bound
  only by D2b's retained-source rule.
* **Consequence:** every later gate change (C1, C2b, D2 and later admissions) merges only through
  your recorded ruleset bypass.
* **Before relying on it:** check two undocumented behaviours in a scratch repository
  (`REQUIRED_CHECKS.md`, "G1"):
  * that its failing check blocks the pull request's head;
  * that a later, same-named, passing job a pull request adds does not unblock it.
* **Undo:** remove the check from the ruleset, then remove the workflow.

### G2 (approved in principle 2026-11-22; core, in the final C1). The source gates run first, with isolated imports ([`G2_IMPORT_ISOLATION.md`](G2_IMPORT_ISOLATION.md))
* **Authorises:**
  * core: committing `g2/proposed-g2-core-workflow.patch` on the ClaimCheck branch before C1 is
    regenerated. C1's control commit then carries G2's two control edits
    (`g2/proposed-g2-core-controls.patch`): `reconcile.py` binds exactly this workflow successor, and
    `test_reconcile.py` tests it. V23 is unchanged;
  * site: committing `g2/proposed-g2-site.patch`, one control file. Meaningful together with D2b.
* **Why:** a file a pull request adds can run before either gate checks anything, and forge the
  gate's report without changing a gate file. 19 working vectors were reproduced.
* **Evidence:** `g2/g2-dry-run.json`, all as expected (24 rows, the site, C2b compatible). An
  independent security review found that the claim holds, with two minor findings, both fixed
  (`G2_IMPORT_ISOLATION.md`, section 7).
* **Does not cover:** edits of the workflow or of the gate's own sources: review, the pre-merge
  check, or G1.
* **If decided after C1:** G2 needs an admission cycle of its own.
* **Undo:** before C1, drop the workflow commit and regenerate. After C1, a new admission.

## Before every merge (no change; required by the owner's decision of 2026-11-22 while G1 is deferred)

Run, from a full clone:

* core: `git diff --name-only --no-renames origin/main...<head> -- .github scripts research/integration_v2 research/__init__.py docs/reconciliation/OPEN_PRS.json docs/integration/2026-11-05 docs/integration/2026-11-14 ':(top,glob)*.py' ':(top,glob)*.pyc' ':(top,glob)*.so' ':(top,glob)*/__init__.*' ':(glob)**/__pycache__/**' ':(glob)**/*.pyc' ':(glob)**/*.so' ':(glob)**/conftest.py' ':(glob)**/sitecustomize.py' ':(glob)**/usercustomize.py'`;
* site: `git diff --name-only --no-renames origin/main...<head> -- .github scripts docs/reconciliation/OPEN_PRS.json package.json package-lock.json ':(top,glob)*.py' ':(top,glob)*.pyc' ':(top,glob)*.so' ':(top,glob)*/__init__.*' ':(glob)**/__pycache__/**' ':(glob)**/*.pyc' ':(glob)**/*.so' ':(glob)**/conftest.py' ':(glob)**/sitecustomize.py' ':(glob)**/usercustomize.py'`.

Any output means the pull request changes the definition of a gate, or a path through which a gate's
own imports could be replaced. Examples: a `json.py`, a `json/` package, a `json.pyc` or a compiled
`json` module at the root or in `scripts/`, or cached bytecode beside the gate. Each runs before
either gate checks anything (`G2_IMPORT_ISOLATION.md`). Merge such a pull request only as its own
approved protected change.

The list gained the bytecode and compiled-module entries on 2026-11-21: the G2 dry run showed three
vectors that the earlier list missed. With G2 in place, the import-path entries become a second line
of defence for the core's required path, and the gate-definition entries remain the check that
matters.

## After all of the above (separate decisions)

* **Merge** each pull request under the existing linear-history rules.
* **Deploy** the website page: a separate decision, not requested.
