# ClaimCheck: the owner's approval package (2026-11-19; G1, G2 and A1 updated 2026-11-21; decisions of 2026-11-22 recorded)

One page per decision. **Nothing here has been applied, merged, deployed, tagged or approved.**
Approving one decision does not approve another. Steps, stop conditions and undo for each are in
[`OWNER_EXECUTION_CHECKLIST.md`](OWNER_EXECUTION_CHECKLIST.md); the independent review steps are in
[`INDEPENDENT_REVIEW_CHECKLIST.md`](INDEPENDENT_REVIEW_CHECKLIST.md).

**A1 is done (2026-11-24).** You confirmed both private archive copies (SHA-256 `91acf4ff…69a3`,
`recoverable_and_complete: true`, 22 of 22) and authorised L1 to L3. The 22 responses are withheld in
`bed63365`, and G2's workflow is committed in `0f0fe031`.

The C1 evidence in this directory is regenerated at the source commit named in `dry-run.json`, after
both commits. The exact values for the head you admit are in the PR description, and you regenerate
them at that head (`OWNER_EXECUTION_CHECKLIST.md`, C1).

## Order

* **Done:** A1 and the withholding commit (`bed63365`); H1 (H1-b) and G2 (in principle) decided; G2's
  workflow committed (`0f0fe031`), with the consolidated research gate's successor (`8631e9c2`). P1 stays
  optional, yours to send.
* **Core:** T1 (recommended), then C1, then C2, then C2b (optional), then R1.
* **Website:** D1 and D3, then regenerate, then D2, then D2b (optional).
* **Either repository, optional, not recommended now:** G1 (see its entry).

## The decisions

### H1. Which retained commit C1 pins
* **Owner decision (2026-11-22): H1-b confirmed**, for C1 and for the later R1 admission. No
  permanent retained-source tag may reference the original model-response development history.
  Retained commits and tags still need your explicit approval.
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
* **Evidence:** [`ADMISSION_PROPOSAL.md`](ADMISSION_PROPOSAL.md):
  * the dry run, the audit and the census, and the H1-b, C2b and G2 dry runs, regenerated at the source
    commit named in `dry-run.json`;
  * `review_v23_manifest`;
  * an independent review of the whole package (PR description).

  The values for the head you admit are in the PR description.
* **Assumptions:**
  * the withholding commit is in place (`bed63365`), so no withheld response is reachable from the
    retained commit;
  * G2 is included: the branch carries its workflow (`0f0fe031`) and the consolidated gate's
    successor (`8631e9c2`), and the control commit binds both;
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

### G1. Gate-definition guard (either repository, optional, protected; not recommended now)
* **Owner decision (2026-11-22): deferred.** G2 and your explicit review of changes to gate
  definitions and workflows are sufficient for this stage. The remaining risk is in
  [`WORKFLOW_SELF_MODIFICATION_RISK.md`](WORKFLOW_SELF_MODIFICATION_RISK.md).
* **Changes:**
  * one `pull_request_target` workflow on `main`, which runs only the definition on `main`, reads the
    pull request as data and executes nothing from it;
  * one required check, `gate-definition-unchanged`.
* **Why:** to enforce, rather than check by hand, that no pull request changes a workflow, a gate's
  own files or an import path without its own decision. This includes D2b's caveat.
* **Evidence:**
  * the logic was tested on scratch repositories: 14 cases in each repository, all as intended;
  * its path list was extended on 2026-11-21 with three vectors the G2 dry run found it missed;
  * evaluation: [`G2_IMPORT_ISOLATION.md`](G2_IMPORT_ISOLATION.md), section 6.
* **Not documented by GitHub, to test first in a scratch repository:**
  * which commit a `pull_request_target` check attaches to;
  * whether a same-named passing job that a pull request adds can satisfy the requirement.
* **Recommendation:** not necessary now. With G2, the pre-merge check covers the rest as a
  procedure. You are the only person who can merge. Adopt G1 only if others gain merge rights, after
  the two tests.
* **Approving:** every later gate change merges only through your recorded ruleset bypass.
* **Rejecting:** the pre-merge check stays a manual step.

### G2. The source gates run first, with isolated imports (core and site, protected; recommended)
* **Owner decision (2026-11-22): approved in principle,** to be included in the final C1 admission,
  preserving all existing integrity checks. Its workflow (`0f0fe031`) and the consolidated gate's
  successor (`8631e9c2`) are committed in the admitted tree.
  Its two control edits are part of C1's proposed control commit, which is not applied: the final
  reviewed transaction needs your separate authorisation.
* **Changes:**
  * core: in `source-policy`, the manifest gate becomes the first step after checkout and
    setup-python, as `python -I -B -X pycache_prefix="$(mktemp -d)"` through a fixed 16-line launcher.
    The launcher refuses to go on unless it runs isolated, without writing bytecode and with a new,
    empty bytecode directory;
  * the consolidated research gate (`research/integration_v1/source_gate.py`), which pins this
    workflow's bytes, names its new identity through a new successor record (`8631e9c2`). **This was
    found by CI after your approval in principle; please confirm it.** Without it, five existing jobs
    fail;
  * `reconcile.py` (+49 −3) binds exactly these two successors, and `test_reconcile.py` (+70) tests
    them. V23 is unchanged;
  * site: `open-pr-reconciliation.yml` runs `python -I scripts/check_reconciled_prs.py` first.
* **Why:** a file a pull request adds can run before either gate checks anything and forge its
  report, without changing any gate file. The dry run reproduced 19 working vectors, among them
  `json.py`, a root package, cached bytecode carrying the genuine source's hash, a compiled module
  beside the gate, `nt.py` and `PYTHONPATH`.
* **Evidence:** `g2/g2-dry-run.json`, all as expected (24 rows):
  * at C1 + G2, the same report as the current invocation (72 PRs);
  * the protected suites pass (79 tests), and with C2b too (80);
  * fail-closed with the same error without C1;
  * every vector: planted code never ran, and the gate failed;
  * the site's positive case and its planted `scripts/json.py` case behave as expected.

  Patches are in `g2/`. Design and limits: [`G2_IMPORT_ISOLATION.md`](G2_IMPORT_ISOLATION.md).
* **Independent security review (2026-11-21):** the claim holds. Nothing ran early in about 380
  planted-file cases, and a trace of the real step agreed. No critical or important finding. The
  two minor findings are fixed: the launcher checks its own flags, and the inclusion check binds
  the file mode.
* **Does not cover:** edits of the workflow or of the gate's own sources. Review, the pre-merge check,
  or G1 covers those.
* **Timing:** core, before C1's final regeneration. C1 then carries G2's two control edits
  automatically, and only if the branch carries G2's exact workflow. After C1, G2 would need an
  admission of its own. Site: any time, meaningful together with D2b.
* **Approving:** I commit the workflow edit on the branch, regenerate C1 with it, and rerun every dry
  run; the independent review follows. The site edit is one control-file commit.
* **Rejecting:** the pre-merge check stays the only protection against these vectors.

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
