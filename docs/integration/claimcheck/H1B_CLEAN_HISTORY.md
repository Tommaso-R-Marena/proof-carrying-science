# H1-b: a retained-source commit without the development history

**Status (2026-11-19; retained 2026-11-21).** Designed, implemented in the admission tooling, and
tested in throw-away worktrees. **Not applied:** no retained commit, tag, control commit or ruleset
was created or changed. The design is the proposed answer to owner decision H1. H1-a (the original
design) stays available as a fallback. Approving C1 with either design remains a separate owner
decision.

**Owner decision (2026-11-22): H1-b confirmed** for both retained-source tags: C1's, and R1's later
V24 (section 4). No permanent retained-source tag may reference the original model-response
development history. R1's V24 dry run must show what C1's does: no response commit and no withheld
blob reachable from the retained commit.
It is compatible with G2 (`G2_IMPORT_ISOLATION.md`). G2's workflow edit is one reviewed file in the
admitted tree, and the add-only checks allow exactly that change.

**What H1-b does not do.** It does not remove the original model responses from GitHub. Pull request
212 and pull request 216 keep the commits that added them reachable (GitHub keeps
`refs/pull/<n>/head`), and so do existing clones. H1-b only avoids adding one more, protected,
reference to that history: the retained-source tag.

## 1. The change

Only how the proposed retained commit is built (`prepare_core_admission.retained_commit`):

| | H1-a (original) | H1-b (proposed) |
| --- | --- | --- |
| commands | `R = commit-tree T -p H -p 0b521f39` | `S = commit-tree T -p bc78660b`, then `R = commit-tree T -p S -p 0b521f39` |
| tree of `R` | `T`, the tree of the reviewed source commit `H` | `T` (and `S` has `T` too) |
| first parent | `H`, whose ancestors are the whole ClaimCheck branch | `S`, a snapshot whose only parent is protected `main` (`bc78660b`, the commit the branch is based on) |
| second parent | the previous intake `0b521f39` | the same |
| identity, date, message | fixed | fixed; `S`'s message names `H` |

In words: `S` is exactly what a squash merge of the branch onto `main` produces, and `R` joins it to
the chain of earlier intakes. Everything else in C1 is unchanged: the proposed tag name, the four
control files and the patch. The only difference is the 40-hex commit ID inside
`scripts/check_reconciled_prs.py`, and the V23 and `reconcile.py` digests that follow from it.

Tooling: `prepare_core_admission --history clean` (the default) or `--history development` (H1-a);
`check_admission_consistency` rebuilds whichever design the dry run records; `prepare_c2b` builds
C1 the same way. `retained_history.py` measures what a candidate retained commit keeps reachable.

## 2. Why the gate accepts it, and what binds it

`scripts/check_reconciled_prs.py` (not changed) checks, for the core:

* the tag resolves to the commit ID compiled into the gate (`INTAKES`);
* the registry's protected `main` (`f20f3cab`) and the original PR heads (196: `8ba61c3a…`,
  197: `7c119370…`) are ancestors of that commit;
* its tree, minus control files, equals the pull request's tree, minus control files;
* the working tree is clean.

It never requires the ClaimCheck branch head to be an ancestor: the registry
(`docs/reconciliation/OPEN_PRS.json`, digest-pinned) lists only the pull requests open on 2026-11-05.
So the gate accepts both designs. **What makes one design binding is the commit ID the owner pins.**
A commit ID fixes the commit's parents. Once `INTAKES` names `R`, V23 pins `INTAKES` by bytes, and
`reconcile.py` pins V23's digest, the design cannot change without a new reviewed control commit.
Before pinning, the reviewer checks the construction:

* `check_admission_consistency` rebuilds `R` from `H` and compares the commit IDs;
* the dry run reports tree equality, the required ancestors, and that nothing of the source branch
  and no withheld response is reachable (`retained_history_review`).

## 3. What changes in meaning

The retained-source mechanism was introduced to keep the *history* of qualified pull requests
reachable after squash merges ("exact qualified source histories, retained independently of linear
main history", comment in the gate). H1-b keeps that for the pull requests of 2026-11-05, through the
previous intake. For ClaimCheck it retains the reviewed **tree**, not the branch's **history**:

* the development commits are no longer reachable through a protected tag;
* their IDs stay recorded: in `S`'s message, in the dry-run evidence, and in pull request 212 on
  GitHub;
* while `H` exists anywhere, anyone can check that `S`'s tree equals `H`'s.

This is the cost of H1-b, and the reason it is your decision. No gate, pin or digest is weakened,
and no trust is added: the exact bytes are bound by the tree ID and by V23's SHA-256 of every file,
as under H1-a.

## 4. The website and V24

* **Website (D2).** Its retained commit has the same H1-a shape, but the website's history contains
  none of the 22 withheld responses. Checked 2026-11-19: 0 of the 22 blobs among the 12,285 objects
  reachable from every ref of the site clone. No change is proposed for D2. The site's examples
  carry derived readings attributed to the Nemotron arm, not raw responses
  (`MODEL_OUTPUT_LICENSING.md`, section 4).
* **V24 (R1).** The research branch (PR 216) merges the ClaimCheck branch, so its history contains
  the same commits, and its tree still contains all 45 responses. A V24 retained commit built the
  H1-a way would bring the development history back through a second tag. Two preconditions avoid
  that:
  * build V24 the H1-b way, on post-C1 `main`, with C1's retained commit as the previous intake;
  * make sure its tree carries the withholding stubs first, by merging the post-withholding
    ClaimCheck branch or `main` after C1.

  Test 12 below checks both.

## 5. Tests (owner's list of 2026-11-19)

`python -m research.claimcheck_v1_1.governance.h1b_adversarial --out docs/integration/claimcheck/h1b`
runs them in throw-away worktrees with a local placeholder tag. It runs the two unmodified gates
(the manifest gate `reconcile.py --require-committed` and `check_reconciled_prs.py --core`). Results:
[`h1b/h1b-adversarial.json`](h1b/h1b-adversarial.json); summary in section 6.

Fast unit tests of the construction: `research/claimcheck_v1_1/tests/test_retained_history.py`
(7 tests).

## 6. Results (2026-11-19; rerun 2026-11-24)

**Rerun on 2026-11-24 at the source commit named in `dry-run.json`.** That commit carries the committed
stubs (`bed63365`) and G2's files (`0f0fe031`, `8631e9c2`), so no withholding is simulated for the ClaimCheck branch.
Test 12 still simulates it for the research branch, which keeps the originals until R1. The results
are in `h1b/h1b-adversarial.json` and in the PR description. The table below is the run of
2026-11-19.

Run at `044d7ee2`, and again at `ad43f21c` after the independent review with the same results (`h1b/h1b-adversarial.json`, the later run; commit IDs differ with the head). The branch still holds the original responses (the
withholding waits for your archive, A1), so the tests ran on a throw-away commit with the stubs that
the governed tool writes, marked as a simulation. The H1-b retained commit there is `1b3e3967…`, on
snapshot `d11ebb31…`; the H1-a commit for the same tree is `52638462…`. Both are objects in a
throw-away worktree, with no ref.

**11 of the 12 tests pass. Test 9 fails, for a reason that predates H1-b.**

| # | Test | Result |
| --- | --- | --- |
| 1 | retained tree = reviewed tree | pass: the retained commit, the snapshot and the source have the same tree ID; `git diff` is empty |
| 2 | no file introduced or removed | pass: same census; the snapshot changes against `main` exactly what the branch changes |
| 3 | required ancestors | pass: the registry's `main` (`f20f3cab`), the heads of PRs 196 and 197 and the previous intake are ancestors; both gates pass on the control commit (72 PRs) |
| 4 | no ancestry to the response commits | pass: the H1-b commit reaches 2 commits beyond protected history (itself and the snapshot), none of the 3 response commits and none of the 22 withheld blobs. The H1-a commit, measured as the positive control, reaches all 3 commits and all 22 blobs |
| 5 | a changed file fails | pass: uncommitted, the manifest gate rejects it; committed, both gates reject it |
| 6 | a substituted retained commit fails | pass: a tag on the H1-a commit (same tree), or on a forged commit with the same tree and parents, is rejected by the retained-source gate. Retargeting the pinned entry as well is rejected by the manifest gate, which pins that entry's bytes; the retained-source gate alone would accept it, by design |
| 7 | a moved or deleted tag fails | pass: a tag moved to the source commit or to the snapshot, or deleted, is rejected |
| 8 | altered predecessor or broken ancestry | pass: a retained commit without the previous intake, or on a forged intake with the same tree and no history, is rejected (the PR 197 head is no longer an ancestor); an edited V22 is rejected |
| 9 | a changed protected control file fails | **fail.** Committed edits to the pinned control files (`check_reconciled_prs.py`, `test_reconciled_prs.py`, V23, V22, the required workflow) are rejected, and so are edits to `boundary.py` and `__init__.py` (by the retained-source gate). But a committed edit to `research/integration_v2/reconcile.py` or `test_reconcile.py` **passes both gates**. The manifest gate treats its own sources as "trusted checked-in configuration" (`reconcile.py`, `_snapshot`), and the retained-source gate lists the same files as controls. An uncommitted edit is rejected. The proposed guard G1 would flag all four files |
| 10 | same reviewed authority | pass: V23 under H1-b and under H1-a differ in exactly one of 10,087 entries (the gate script that names the commit); every other field is equal; `reconcile.py` differs only in the manifest digest |
| 11 | linear history | pass: a squash of the pull request onto protected `main` passes both gates; the retained commit and the snapshot are not on `main` |
| 12 | V24 | pass: a V24 retained commit built the H1-b way reaches none of the response commits or withheld blobs and keeps the whole intake chain. One built the H1-a way reaches all of them. The research branch's tree still holds all 22 withheld responses, so its withholding is a precondition |

**What test 9 means.** It is not a property of H1-b; the gates behave the same under H1-a. It is a
property of the protected gate as it stands. The code that checks every other file cannot check
itself, and the same two files are excluded by the second gate. So a pull request that edits those
files and commits the edit passes every gate. C1 and C2b each change `reconcile.py` and
`test_reconcile.py` by design, so their review is where this matters.

**The trust root is wider than these two files** (independent review, 2026-11-19, reproduced). Both
gates import standard-library modules (`json`, `argparse`, `hashlib`, `subprocess` and others) before
any check runs:

* the manifest gate runs as `python -m …` from the repository root, and the retained-source gate as
  `python scripts/…`;
* so a module the pull request adds, such as a `json.py` at the root or in `scripts/`, runs first;
  so would a new `research/__init__.py`;
* a harmless marker module placed there ran before either gate checked anything;
* the scripts that `source-policy` runs before the gate also come from the pull request (V23 pins
  them, but only the later gate checks that).

So a pull request can make both gates report success without touching any gate file. What catches
that:

* review;
* the pre-merge check, and G1, both extended on 2026-11-19 to the import paths (`REQUIRED_CHECKS.md`,
  "G1");
* C2b's child process, now in Python's isolated mode (`-I`);
* G2, now prepared and tested (`G2_IMPORT_ISOLATION.md`): the gates run first, with isolated
  imports. In its dry run, none of 19 working vectors ran.

None of these is applied.

**A precondition, and a merge rule.**

* H1-b keeps the withheld responses unreachable only after the withholding commit. Before it, the
  admitted tree itself carries them. The dry run then reports `all_as_expected: false`; no gate checks
  it.
* PR 216 holds the three response commits in its history and all 22 responses in its tree. A merge
  commit or rebase merge of PR 216 would put them into `main`'s history whatever C1 pins. **Squash-merge
  PR 216 only, and only after its tree carries the stubs.** The same holds for PR 212: squash-merge
  only.
