# Proposed source admission of the ClaimCheck research sidecar

**Status: a proposal, prepared and dry-run tested. Nothing protected has been changed and nothing
is approved.** `source-policy` and `verified-public-integration` are red on the draft PR and stay
red until the owner decides.

## What the protected gates require

1. `research/integration_v2/reconcile.py` (run by `source-policy`) compares the complete set of
   tracked files, and every file's bytes and mode, with the reviewed manifest
   `RECONCILIATION_V22.json`, whose SHA-256 is compiled into the gate. A branch that adds a file
   fails with `combined tracked file census differs`. This is the intended behaviour.
2. `scripts/check_reconciled_prs.py` requires every non-control file to equal a retained source
   commit that is identified by commit id **and** by an annotated tag.

So admitting new files takes one control commit (a successor manifest and new constants in three
protected files) and, outside the tree, a new retained commit with a tag pushed to the repository.
None of this can be approved by an assistant.

## What this branch adds

[`ADMISSION_CENSUS.json`](ADMISSION_CENSUS.json): every added file with SHA-256 and mode, generated
from the commit named in [`dry-run.json`](dry-run.json) (`generated_from_commit`). No existing file
is changed or removed (checked against every entry of the V22 snapshot, using the gate's own rule for
its one reviewed test repair).

| Added | Files | What |
| --- | ---: | --- |
| `research/claimcheck_v1/**` | 1,901 | frozen v1 software, Lean checker and Mathlib meaning theorems, benchmark documents (open-licence article text and data), receipts, bundles; one added file beside them, the legacy-replay warning (no frozen file changed) |
| `research/claimcheck_v1_1/**` | 92 | v1.1 policy layer with the outward-verdict guard, the hardened runner, the v1.1 replayer and the checked replay of v1 bundles, tools, tests, development results, protocol draft 3 (unapproved) with its spending guard and Lean memory guard and the prospective decision package, prepared adjudication and usability materials, these governance scripts |
| `.github/workflows/pcs-claimcheck-v1.yml` | 1 | path-scoped research CI (read-only permissions) |
| `docs/integration/claimcheck/**` | 12 | this proposal, the census, the dry-run record, the proposed control changes as a patch, the audit (narrative and record), the third-party attribution index, the required-check recommendation, the runner's security-review package with its two source diffs, the owner authorization package |

An audit of every added file finds nothing that blocks admission: no credential values or key
formats, no generated or unnecessary files, no links, submodules or executables, every file given a
provenance class by an explicit rule, the frozen v1 digests verified, no protected path changed. The
bundled articles state CC BY 4.0 in their own XML; the data are CC0; the attribution and the changes
made (plain-text extraction; deliberately altered copies for adversarial testing) are recorded in
[`THIRD_PARTY_ATTRIBUTION.md`](THIRD_PARTY_ATTRIBUTION.md), which the audit regenerates and requires
to be current. Details and how to review the addition by replay and digests rather than by reading:
[`ADMISSION_AUDIT.md`](ADMISSION_AUDIT.md).

## The proposed control commit, exactly

Four files, built by `python -m research.claimcheck_v1_1.governance.prepare_core_admission` in this
order, because each depends on the one before:

| # | File | Change | Security implication |
| --- | --- | --- | --- |
| 0 | retained source commit (not a file; tag pushed by the owner) | **H1-b (proposed, owner decision H1):** a snapshot `S = commit-tree <source tree> -p bc78660b`, then `R = commit-tree <source tree> -p S -p 0b521f39`. **H1-a (original):** `R = commit-tree <source tree> -p <source commit> -p 0b521f39`. Fixed identity, date and messages. In both, the tree is identical to the source commit and the previous retained commit stays an ancestor, so every original PR head remains retained | Moves the "non-control files must equal a retained snapshot" rule to a snapshot whose tree is exactly the admitted source. Under H1-b the tag keeps no commit of the ClaimCheck branch reachable ([`H1B_CLEAN_HISTORY.md`](H1B_CLEAN_HISTORY.md)); the gates check the same things under both. |
| 1 | `scripts/check_reconciled_prs.py` | the core entry of `INTAKES` names the new retained commit and tag; `CONTROLS` names the V23 manifest instead of V22 | V22 becomes an ordinary pinned file, compared byte for byte. This file is itself pinned by bytes in the manifest, so V23 must record its new digest; it is the only existing pinned file whose bytes change. |
| 2 | `docs/integration/2026-11-14/RECONCILIATION_V23.json` (new, about 4.7 MB) | V22 with `format` v23 and `predecessor_manifest` naming V22 at the protected commit that introduced it (`bc78660b`); V22 itself pinned as an immutable file; the added files pinned by digest and mode; the new digest of file 1. PR census, held PR117, workflow predecessors: unchanged. | Widens the admitted tree by exactly the census. A wrong digest would admit wrong bytes, so the manifest is generated by script from one commit and its own digest is compiled into the gate. |
| 3 | `research/integration_v2/reconcile.py` | manifest path and digest; `v23` accepted and required as current; the relation-scope label | The gate's logic is unchanged; only which reviewed manifest it enforces changes. |
| 4 | `research/integration_v2/test_reconcile.py` | the existing test "V22 keeps the V21 intake manifest" reads V22 by path instead of as "the current manifest"; one test is added: V22 unchanged (digest), predecessor recorded, PR census unchanged, control list updated, exactly one V22 entry changed (file 1), every added file under the admitted roots | Keeps every existing check of the history; adds the successor's invariants as a test. |

Files 1, 3 and 4 are in [`proposed-control-changes.patch`](proposed-control-changes.patch). File 2
is not (it pins every tracked file and is regenerated by the script); its digest is in
[`dry-run.json`](dry-run.json) under `proposal`.

No workflow, ruleset, required check or bypass setting is changed. No authority code, Lean theorem,
production path or historical integration note (`docs/integration/2026-11-05/*.md`, which are
controls of the retained-source gate and describe V22 as it was) is touched.

## Dry run

[`dry-run.json`](dry-run.json). The script builds the control commit twice from the same source
commit: the **proposal** with the proposed tag name `pcs-source-intake/core-claimcheck-v1-20261114`
(no ref is created), and the **dry run** with the placeholder tag name
`pcs-source-intake/DRY-RUN-core-claimcheck-not-a-real-tag`, committed in a throw-away worktree with
a local placeholder tag. It checks that the two differ only in the tag name and in the digests that
follow from it. On the dry-run control commit, unmodified:

* `reconcile --require-committed` passes (72 PRs);
* `check_reconciled_prs.py --core` passes;
* `research/integration_v2/test_reconcile.py` passes, with its proposed successor (75 tests);
* `scripts/test_reconciled_prs.py` passes (13 tests), including the squash of the whole current tree
  onto the protected baseline, checked by both gates in an isolated repository;
* the gate on the protected V22 commit itself still passes.

Rejected, as they must be (each alteration made on top of the control commit): an unlisted extra
file; an edited admitted file; an edited successor manifest; an edited predecessor manifest (V22); an
edited frozen benchmark result; an edited existing production file (`pcs/__init__.py`); a gate
control file edited after the control commit and left uncommitted; the retained-source entry
retargeted and committed; the retained tag pointing at another commit. Since 2026-11-19 the dry run
also rejects the tag pointing at the other design's commit (same tree) and the tag deleted.

**Not rejected, by the gate's design:** the same gate control file edited **and committed**. The
manifest gate treats its own sources as trusted configuration, and the retained-source gate lists
them as controls. So a committed edit to `research/integration_v2/reconcile.py` or
`test_reconcile.py` passes both gates (`h1b/h1b-adversarial.json`, test 9). Review of the control
commit's diff, the pre-merge gate-definition check, or G1 is what catches it.

The placeholder tag and the worktree are deleted at the end. Nothing was pushed.

## Why the evidence names an earlier commit

The manifest pins every tracked file, including the evidence files themselves, so evidence about
commit *H* cannot be inside *H*. The committed evidence is therefore generated at a source commit
*S* and committed in a following commit that changes only the evidence files (`dry-run.json`,
`ADMISSION_CENSUS.json`, the patch, `ADMISSION_AUDIT.json`). When the script runs at a later commit
it checks that chain and reports it under `evidence_committed_in_this_tree`. The numbers for the
exact head of the pull request (manifest digest, retained commit) are reported in the pull request
description and must be regenerated by the owner at the commit actually admitted.

## What the owner would do, if the answer is yes

1. Review the census, the audit, the attribution index, the security-review package and this
   proposal.
2. Fix the commit to admit, `H` (the PR head at that time), and check the committed evidence:
   `python -m research.claimcheck_v1_1.governance.check_admission_consistency` must report
   `consistent: true` (same commit everywhere, census = the added files with their identities,
   the patch yields the proposed digests, the retained commit is reproducible, and only evidence
   changed after the commit the evidence describes).
3. At `H`, run `python -m research.claimcheck_v1_1.governance.prepare_core_admission --out <dir>
   --pytest-python <python with pytest> --emit <dir2>`. It must report `all_as_expected: true`, and
   `<dir2>` then holds the four control files. Their digests, the V23 digest and the retained commit
   must equal those in the pull request description for `H`.
4. Create the retained commit exactly as recorded (`proposed_retained_source_commit` in
   `<dir>/dry-run.json`; its id must equal `commit` there). With the fixed identity
   `GIT_AUTHOR_NAME="PCS admission dry run" GIT_AUTHOR_EMAIL=dry-run@example.invalid
   GIT_COMMITTER_NAME="PCS admission dry run" GIT_COMMITTER_EMAIL=dry-run@example.invalid
   GIT_AUTHOR_DATE=2026-11-14T00:00:00Z GIT_COMMITTER_DATE=2026-11-14T00:00:00Z`:
   * **H1-b (proposed):** first the snapshot,
     `S=$(git commit-tree "H^{tree}" -p bc78660b5fac857fce3873eb6cda0445d1903da1 -m "ClaimCheck admitted source snapshot (proposed): the exact tree of reviewed source commit <H>, on protected main bc78660b5fac857fce3873eb6cda0445d1903da1. Clean history: no commit of the source branch is an ancestor.")`,
     then
     `git commit-tree "H^{tree}" -p "$S" -p 0b521f39af99f5856b69dfcc25bc274ec9dc804a -m "Retained qualified source: previous intake plus ClaimCheck sidecar (proposed; clean history; tree identical to reviewed source commit <H>)"`,
     where `<H>` is `H`'s full 40-hex ID. `S` must equal `snapshot.commit` in the dry run.
   * **H1-a (fallback):** `git commit-tree "H^{tree}" -p H -p 0b521f39af99f5856b69dfcc25bc274ec9dc804a -m "Retained qualified source: previous intake plus ClaimCheck sidecar (proposed; tree identical to the source commit)"`.

   Then `git tag -a pcs-source-intake/core-claimcheck-v1-20261114 <that commit>` and push the tag. The
   identity, date and messages are part of the commit id, which `check_reconciled_prs.py` names and
   V23 pins; to use others, change them in the script and regenerate. This is the step that cannot
   be done from this session and should not be.
5. On top of `H`, commit the four files from `<dir2>` as one separate, reviewed control commit.
   `source-policy` and `verified-public-integration` should then pass.
6. After merging, add `claimcheck-required` to the required checks (`REQUIRED_CHECKS.md`).

If the answer is no, nothing needs undoing: the branch contains no protected change.
