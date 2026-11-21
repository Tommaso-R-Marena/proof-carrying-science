# ClaimCheck: the owner's approval package (2026-11-19)

One page per decision. **Nothing here has been applied, merged, deployed, tagged or approved.**
Approving one decision does not approve another. Steps, stop conditions and undo for each are in
[`OWNER_EXECUTION_CHECKLIST.md`](OWNER_EXECUTION_CHECKLIST.md); the independent review steps are in
[`INDEPENDENT_REVIEW_CHECKLIST.md`](INDEPENDENT_REVIEW_CHECKLIST.md).

**One prerequisite is open: your action A1** (a private archive of the 22 responses to withhold;
[`MODEL_OUTPUT_LICENSING.md`](MODEL_OUTPUT_LICENSING.md), section 7). Until it is done and the
withholding commit exists, the C1 numbers (V23 digest, retained commit, control-file digests) cannot
be final: they are regenerated at the commit you admit, as before.

## Order

* **First:** A1 and the withholding commit; P1 (optional, yours to send); then H1.
* **Core:** T1 (recommended), then C1, then C2, then C2b (optional), then R1.
* **Website:** D1 and D3, then regenerate, then D2, then D2b (optional).
* **Either repository, at any time (optional):** G1.

## The decisions

### H1. Which retained commit C1 pins
* **Changes:** the parents of the commit that the retained-source tag protects. Under H1-b (proposed)
  they are a snapshot of the admitted tree on protected `main`, and the previous intake. Under H1-a
  they are the branch head and the previous intake.
* **Why:** under H1-a the protected tag would keep the commits that added the withheld responses
  reachable for good.
* **Evidence:** [`H1B_CLEAN_HISTORY.md`](H1B_CLEAN_HISTORY.md); `h1b/h1b-adversarial.json`;
  `tests/test_retained_history.py`. 11 of the 12 tests pass. Test 9 fails for a reason that predates
  H1-b: a committed edit to the manifest gate's own `reconcile.py` or `test_reconcile.py` passes both
  gates, under either design.
* **Assumptions:** the gates accept both designs and check the same things. The design is fixed by
  the commit ID you pin.
* **Approving H1-b:** C1 pins the clean commit. The tag then keeps the reviewed tree, not the
  development history.
* **Rejecting (H1-a):** C1 as originally designed, with the exposure documented.
* **Neither:** removes anything from pull requests 212 and 216, or from clones.

### T1. Tag rulesets for `pcs-source-intake/*` (both repositories)
* **Changes:** a tag ruleset: restrict creation, update and deletion, block force pushes; bypass for
  the repository-admin role only.
* **Why:** without it, anyone with write access (including apps and workflow tokens) could delete or
  move a retained-source tag and break every pull request's gate. It cannot widen authority either
  way.
* **Evidence:** the body validates against GitHub's published REST description, with negative
  controls (`REQUIRED_CHECKS.md`).
* **Assumptions:** the role number is not documented; choose "Repository admin" in the UI.
* **Approving:** you create both rulesets.
* **Rejecting:** the tags stay unprotected. The gates still fail closed, so the cost is availability,
  not authority.

### C1. Admit the ClaimCheck sidecar (core, protected)
* **Changes:**
  * the retained commit (per H1) and the annotated tag `pcs-source-intake/core-claimcheck-v1-20261114`;
  * one control commit with four files: V23, `reconcile.py` constants, the protected test's
    successor, and the retained-source entry.
* **Why:** the protected gate pins every tracked file, so new files can only be admitted this way.
* **Evidence:** [`ADMISSION_PROPOSAL.md`](ADMISSION_PROPOSAL.md); the dry run, the audit and the
  census, regenerated at the commit you admit; `review_v23_manifest`.
* **Assumptions:**
  * the withholding commit is in place (A1);
  * the gate's own source files are trusted configuration, which no gate can check (H1-b test 9);
    review of the control commit is what protects them;
  * a module a pull request adds at the root or in `scripts/` would run before either gate checks
    anything (independent review F2, reproduced); the pre-merge check, G1 or G2 is what covers it.
* **Approving:** exactly the retained commit, the tag and the control commit, after their checks
  pass.
* **Rejecting:** nothing to undo; the branch has no protected change.

### C2. Require `claimcheck-required` on core `main` (ruleset)
* **Changes:** one required check, after C1.
* **Why:** so that ClaimCheck's tests bind on every later pull request.
* **Evidence:** it runs on every pull request through an always-reporting aggregate
  (`REQUIRED_CHECKS.md`).
* **Approving:** add it.
* **Rejecting:** ClaimCheck's tests stay advisory.

### C2b. Run the retained-source gate in the required `source-policy` path (core, protected, optional)
* **Changes:** two control files (`reconcile.py`, `test_reconcile.py`): `--require-committed` also
  runs `check_reconciled_prs.py --core`. It runs as a separate process, in Python's isolated mode
  (`-I`) and without `PYTHONOPTIMIZE`.
* **Why:** today the retained-source gate runs on the core only in a path-filtered workflow that is
  not required.
* **Evidence:** `c2b/c2b-dry-run.json`, all as expected:
  * on top of C1 (H1-b), the gate passes on 72 PRs and reports the retained source;
  * the protected suites pass (76 tests, and OK);
  * the CI steps before the gate leave no untracked file;
  * tag deleted, tag moved and an untracked file: each passes under C1 alone and is rejected with
    C2b;
  * the required workflow cannot skip `source-policy` silently.
* **Assumptions:** the PR's own workflow runs it (see D2b's caveat, and G1).
* **Approving:** one control commit after C1, regenerated there.
* **Rejecting:** the gap stays documented.

### D1. Reading-help successor (site, protected)
* **Changes:** patch 01, one commit (digest `98218343…d398`).
* **Why:** the page-help verifier pins the previous bytes. The successor record binds the new ones;
  the predecessor record is unchanged.
* **Evidence:** the patched verifier passes 22 of 22 tests and rejects five alterations.
* **Approving:** apply.
* **Rejecting:** the page cannot pass the site gate.

### D3. ClaimCheck tests in the complete site gate (site)
* **Changes:** patch 03 (digest `53e96704…98fd1`): `site-full-gate` runs the 15 ClaimCheck tests.
* **Evidence:** the complete gate runs them and rejects all eight alterations.
* **Approving:** apply.
* **Rejecting:** the tests stay outside the required gate.

### D2. Admit the website change (site, protected)
* **Changes:**
  * the retained commit and the annotated tag `pcs-source-intake/site-claimcheck-v1-20261117`;
  * patch 02, which re-anchors `public/` to the retained commit.
* **Why:** the site gate pins the non-control tree and `public/`.
* **Evidence:** the site dry run and the consistency check, regenerated after D1 and D3. The site's
  history holds none of the 22 withheld responses (checked: 0 of 22 blobs), so no H1-b change is
  needed there.
* **Approving:** exactly those objects and the patch, after regeneration.
* **Rejecting:** nothing to undo.

### D2b. Require `original-pr-ancestry-and-production-preservation` on site `main` (ruleset, optional)
* **Changes:** one required check, after D2. It runs on every pull request and never stays pending.
* **Why:** after D2 it is the only check that enforces the `public/` anchor and the retained-source
  rule.
* **Caveat (verified):** a pull request that edits its own workflow can make any required check pass
  without the gate running. GitHub's rule that pins a workflow exists only at organisation level.
* **Approving:** add it, together with the pre-merge gate-definition check, or with G1.
* **Rejecting:** those rules stay advisory.

### G1. Gate-definition guard (either repository, optional, protected)
* **Changes:**
  * one `pull_request_target` workflow on `main`, which runs only the definition on `main`, reads the
    pull request as data and executes nothing from it;
  * one required check, `gate-definition-unchanged`.
* **Why:** it is the smallest enforced protection against three things:
  * D2b's caveat;
  * committed edits to the gate's own source, which no gate detects;
  * modules a pull request adds where a gate imports from (`scripts/`, root `*.py`, a new
    `research/__init__.py`).
* **Evidence:** the logic was tested on scratch repositories: 14 cases in each repository, all as
  intended. On the site it assumes D2b, which binds `site-full-gate`'s own files.
* **Assumption to test first:** how GitHub decides a required check when two workflows report the
  same job name.
* **Approving:** every later gate change merges only through your recorded ruleset bypass.
* **Rejecting:** the pre-merge check stays a manual step.

### G2. Isolate the gates' imports (either repository, optional, protected)
* **Changes:** the workflows run the retained-source gate as `python -I …`, and the manifest gate
  through an isolated launcher, so no module a pull request adds can replace a gate's imports.
* **Why:** independent review F2, reproduced: a marker `json.py` at the root or in `scripts/` ran
  before either gate checked anything.
* **Evidence:** under `-I` the marker did not run, and the retained-source gate ran its own checks.
  A dry run for both gates is to be prepared on request.
* **Approving:** one workflow commit per repository, after its dry run.
* **Rejecting:** the pre-merge check and G1 remain the protection.

### R1. Assurance research (PR 216)
* **Changes:** nothing now.
* **Recommendation:** a separate V24 successor after C1, built the H1-b way, on post-C1 `main`, with
  C1's retained commit as the previous intake. Its tree must carry the withholding stubs first
  (H1-b test 12 shows that a V24 built the H1-a way would bring the development history back).
  Squash-merge PR 216 only: a merge commit would bring its history, with the three response commits,
  into `main`.
* **Approving:** a V24 proposal will be prepared after C1, with its own dry run and review.
* **Rejecting:** the research stays on its draft branch.

### Merge and deployment
Separate decisions after all of the above; not requested.
