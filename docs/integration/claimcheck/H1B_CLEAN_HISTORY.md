# H1-b: a retained-source commit without the development history

**Status (2026-11-19).** Designed, implemented in the admission tooling, and tested in throw-away
worktrees. **Not applied:** no retained commit, tag, control commit or ruleset was created or changed.
The design is the proposed answer to owner decision H1; H1-a (the original design) stays available
as a fallback. Approving C1 with either design remains a separate owner decision.

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

## 6. Results

Filled from `h1b/h1b-adversarial.json` when the run completes.
