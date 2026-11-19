# Independent review checklist: the protected changes C1 (core) and D1–D3 (website)

For a reviewer who has not worked on this branch. Every step is read-only. The admission dry run
creates a throw-away worktree and a local placeholder tag and deletes both. `git commit-tree` writes
an unreferenced object and no ref. Nothing here pushes, tags, merges or deploys. Record each result
in the sign-off table (section 6).

The questions this review must answer:

* **Manifest integrity:** does V23 admit exactly the reviewed files, and change nothing else?
* **Retained-source ancestry:** is the retained commit exactly the admitted tree, with the previous
  intake and every original PR head as ancestors?
* **Exact file digests:** do the control files and the manifest have exactly the recorded digests?
* **Tag security:** can a tag widen authority, and is the tag created and protected as intended?
* **Widening:** could any step admit more source than reviewed, or bind less than intended?

Prerequisites:

* fresh clones of both repositories with full history and tags;
* `git` and Python 3.12 or later (with `pytest`, for the dry run);
* Node 20 or later for D3;
* no credentials.

## 1. Fix what is reviewed

```bash
git -C proof-carrying-science fetch origin main tommaso-r-marena/festive-galileo-4a5m5k --tags
git -C proof-carrying-science-site fetch origin main tommaso-r-marena/festive-galileo-4a5m5k --tags
```

* **Core:** `H` = the PR 212 head named in its description, `S` = the source commit its evidence
  names.
* **Site:** `H_site = fc6c7a468f3a614c5126f65092aa5e2d7b817974`, the evidence commit, and
  `S_site = e0b9136cf7e8480cfcf55c9bfa86b9582f22e39e`, the source commit.

The values for an exact head cannot be stored inside that head. They are in the pull-request
descriptions. **If the owner applies D1 or D3, or any licensing decision L2(b) or L3, before
admission, `S` changes. Every value below must then be regenerated and this review repeated.**

## 2. C1: core source admission

| # | Check | Command (in `proof-carrying-science`, at `H`) | Pass when |
| --- | --- | --- | --- |
| C1.1 | The committed evidence is about one commit and only evidence changed after it | `python -m research.claimcheck_v1_1.governance.check_admission_consistency` | `consistent: true`, all 11 checks; note `source_commit` (= `S`) |
| C1.2 | The proposal regenerates at `H` | `python -m research.claimcheck_v1_1.governance.prepare_core_admission --out /tmp/c1 --pytest-python "$(command -v python)" --emit /tmp/c1-emit` | `all_as_expected: true` |
| C1.3 | **Manifest integrity**, by code separate from the generator | `python -m research.claimcheck_v1_1.governance.review_v23_manifest --emit /tmp/c1-emit --head H` | `consistent: true`; all 10 checks (see below) |
| C1.4 | **Exact digests** of the four control files | `sha256sum /tmp/c1-emit/docs/integration/2026-11-14/RECONCILIATION_V23.json /tmp/c1-emit/research/integration_v2/reconcile.py /tmp/c1-emit/research/integration_v2/test_reconcile.py /tmp/c1-emit/scripts/check_reconciled_prs.py` | each equals the PR description's value for `H` |
| C1.5 | The control files change only what they must | `git diff --no-index <(git show H:research/integration_v2/reconcile.py) /tmp/c1-emit/research/integration_v2/reconcile.py`, and the same for the other two files | as listed in "The expected hunks" below |
| C1.6 | **Retained-source ancestry** | the `commit-tree` commands in `ADMISSION_PROPOSAL.md`, step 4, with `H`, for the design you approve under H1 (H1-b: two commands); then the ancestry commands below | the printed ID equals `proposed_retained_source_commit.commit` in `/tmp/c1/dry-run.json` and the PR description; `/tmp/c1/dry-run.json` reports `retained_history_as_designed: true` |
| C1.7 | **Tag security, before creation** | `git ls-remote --tags origin 'refs/tags/pcs-source-intake/core-claimcheck-v1-20261114'` | prints nothing (the name is not squatted) |
| C1.8 | Negative controls | in `/tmp/c1/dry-run.json`: `negative_controls` | all nine `rejected: true`; `dry_run_tested_the_proposal.only_the_tag_name_and_its_consequent_digests_differ: true` |
| C1.9 | The protected suites pass with the successor | in `/tmp/c1/dry-run.json`: `gate_tests_on_the_successor`, `retained_source_gate_tests_on_the_successor` | 75 passed; OK (13 tests, including the whole-tree squash) |

**What C1.3 checks:**

* **V23 itself:**
  * format v23;
  * the predecessor is V22 at `bc78660b`, with SHA-256 `28cc42a6…ce83`;
  * the PR census, superseded PRs, workflow adaptations, predecessor tree, parent heads and
    protected-main fields are unchanged.
* **Against V22:**
  * no V22 entry is removed;
  * exactly one V22 entry changes: `scripts/check_reconciled_prs.py`;
  * every added entry is under `research/claimcheck_v1/`, `research/claimcheck_v1_1/`,
    `docs/integration/claimcheck/` or `.github/workflows/pcs-claimcheck-v1.yml`, with mode 100644.
    The one exception is V22 itself, now pinned as an ordinary file.
* **Against `H`:**
  * every entry equals the blob at `H`, except the gate script the control commit replaces and the
    gate's one pinned test repair (`research/scientific_receiver_v1/tests/test_host.py`, manifest
    `46916b52…`, accepted successor `1952bd78…`, rule `RECEIVER_CLEANUP_*` in `reconcile.py`);
  * no file at `H` is missing from V23 except the control paths.
* **Control paths:** V23 is a control path and V22 is not.

**The expected hunks (C1.5):**

* `reconcile.py`: the manifest path, the manifest digest (`MANIFEST_SHA256`), acceptance of format
  v23 as current, and the relation-scope label. No change to the gate's logic.
* `test_reconcile.py`: the existing test "V22 keeps the V21 intake manifest" reads V22 by path. One
  test is added, `test_v23_keeps_v22_and_only_adds_the_claimcheck_sidecar`. No existing assertion is
  removed or weakened.
* `check_reconciled_prs.py`: the core entry of `INTAKES` names the new retained commit and tag, and
  `CONTROLS` names V23 instead of V22. The site entry, the tag check and every other line are
  unchanged.

**Ancestry commands (C1.6).** Let `R` be the printed retained commit. Each of the following must
succeed:

* `git rev-parse R^{tree}` equals `git rev-parse H^{tree}`;
* `git rev-parse R^2` is `0b521f39af99f5856b69dfcc25bc274ec9dc804a`;
* `git merge-base --is-ancestor bc78660b5fac857fce3873eb6cda0445d1903da1 R`;
* for each head of PRs 196 and 197 in `docs/reconciliation/OPEN_PRS.json`:
  `git merge-base --is-ancestor <head> R`;
* **H1-b:** with `S = R^1`:
  * `git rev-parse S^{tree}` equals `H^{tree}`;
  * `git rev-list --parents -n 1 S` lists exactly one parent, `bc78660b5fac857fce3873eb6cda0445d1903da1`;
  * `git merge-base --is-ancestor H R` **fails**;
  * `git rev-list R --not bc78660b5fac857fce3873eb6cda0445d1903da1 0b521f39af99f5856b69dfcc25bc274ec9dc804a`
    prints exactly `R` and `S`;
  * none of the three commits that added the recorded responses is an ancestor:
    `git merge-base --is-ancestor <c> R` fails for `f17649ca`, `dbe31d72` and `87900a17`;
  * no withheld response is reachable. In Python:
    `retained_history.reach(".", R, [bc78660b…, 0b521f39…], retained_history.withheld_blobs(".", search_from="H"))`
    reports `withheld_blobs_reachable: []`;
* **H1-a:** `git rev-parse R^1` is `H`.

**Widening review (C1).** Each item must be answered "no", with the reason.

| Question | Why it should be "no" |
| --- | --- |
| Could the retained commit admit files that V23 does not list? | its tree is `H`'s tree (C1.6), and V23 pins every file at `H` (C1.3) |
| Could V23 admit a file outside the reviewed roots, or change an existing file? | C1.3; the only changed entry is the gate script, which the control commit replaces |
| Does the control commit change gate logic or a workflow? | C1.5: constants and one added test only; no workflow change |
| Could a tag admit anything? | no: the gate compares the tag's target with the commit ID compiled into it (`REQUIRED_CHECKS.md`, "Retained-source tags") |
| Does anything bind less than it appears to? | **yes, and it is documented**. On the core, the retained-source gate runs only when integration paths change (path-filtered workflow, not required). The binding control on every pull request is the V23 manifest, through `source-policy` and `verified-public-integration` (`REQUIRED_CHECKS.md`, "Which gates bind"; decision C2b) |
| Does the admitted tree contain material whose redistribution is not established? | **yes**: the recorded model outputs; decide L1 to L3 first (`MODEL_OUTPUT_LICENSING.md`) |
| Does the retained commit keep withheld material reachable? | **under H1-a, yes, as designed**: its first parent `H` reaches the three commits that added the recorded outputs (`f17649ca`, `dbe31d72`, `87900a17`), so the public tag keeps them reachable even after stubs and a squash merge. **Under H1-b, no**: the C1.6 commands show it. Neither design removes them from pull requests 212 and 216, or from clones (`H1B_CLEAN_HISTORY.md`) |
| Could H1-b let a different tree or history be pinned than the one reviewed? | no: the commit ID fixes tree and parents; `check_admission_consistency` rebuilds it from `H` and compares; the gate checks the same things under both designs, and a substituted commit, moved or deleted tag, or broken ancestry fails (`h1b/h1b-adversarial.json`) |
| Does V23's own text say anything the owner may not want permanent? | its `reviewer` field reads "PROPOSED by an AI assistant for the owner's review; not reviewed, not approved". Keep it as honest provenance, or change it in the generator and regenerate (which changes every digest) |

## 3. D1 to D3: website

In `proof-carrying-science-site`, at `H_site`:

| # | Check | Command | Pass when |
| --- | --- | --- | --- |
| D.0 | The records are consistent | `python3 scripts/check_claimcheck_proposals_consistency.py` | `consistent: true`, all 10 checks; `source_commit` = `S_site` |
| D.1 | Patch digests | `sha256sum docs/governance/claimcheck-proposals/0{1,2,3}-*.patch` | 01 `98218343…d398`; 02 `5948809b…1a5e`; 03 `53e96704…98fd1` |
| D1.1 | **D1** changes only the reading-help pin rule | read `01-reading-help-verifier.patch` (18 changed lines) | it compiles in one successor digest `9a114126…c2a5` for `docs/evidence/site-clarity-v2/reading-help-requalification.json`. It requires the successor's predecessor (`docs/evidence/site-clarity-v1/browser-qualifications.json`) to be unchanged, the successor to restate the historical pins exactly and to cover the same files, and every pinned file except `public/page-help-core.mjs` to keep its historical digest. The historical manifest is not edited |
| D1.2 | The successor record is the one pinned | `git show S_site:docs/evidence/site-clarity-v2/reading-help-requalification.json \| sha256sum` | `9a114126…c2a5` |
| D1.3 | Dry run 01 | in `01-reading-help-verifier.dry-run.json` | unpatched verifier fails 3 of 22 (the drift); patched passes 22 of 22; five alterations rejected |
| D2.1 | **D2** changes only the site intake and the `public/` anchor | read `02-reconciliation-gate.patch` (4 changed lines) | the site `INTAKES` entry becomes `('6c1ec33e51c3ead21fcaa07f368b7a1c791771dc','pcs-source-intake/site-claimcheck-v1-20261117')`; the `public/` rule compares with the retained commit instead of `main` |
| D2.2 | **Retained-source ancestry** | the reproduction below | the printed ID is `6c1ec33e…`; tree `1a2ab000ce15f14ad942240105a5efabda8a21e3` = `S_site^{tree}`; parents `S_site` and `d35e2b5e6b29e0a27dc0cb117986895fd58c1456`; every original site PR head (128–131, 145–147) is an ancestor |
| D2.3 | **Widening by the new `public/` anchor** | `git diff --name-status e8136625c463b271364b36b2b8ae76f8777f1967 S_site -- public` | exactly the reviewed page additions and the five modified public files (`check-my-files.html`, `llms.txt`, `page-help-core.mjs`, `runtime-connections.json`, `sitemap.xml`); after D2, `public/` can change only to the tree of a newly tagged retained commit |
| D2.4 | The census is exactly the change | in `02-site-admission-census.json` | 51 files: 45 added, 6 modified (the five above and `tests/science-clarity.test.mjs`, whose only change is the page count 75 to 76, every page still checked) |
| D2.5 | **Tag security, before creation** | `git ls-remote --tags origin 'refs/tags/pcs-source-intake/site-claimcheck-v1-20261117'` | prints nothing |
| D2.6 | Dry run 02 | in `02-reconciliation-gate.dry-run.json` | successor gate passes on 3,854 files; its own 13 tests pass; six alterations rejected, including `tag_points_at_another_commit` and `retained_commit_drops_original_pr_heads` |
| D3.1 | **D3** only adds the ClaimCheck tests to the complete gate | read `03-complete-gate.patch` (3 changed lines) | adds `test:claim-check` and appends it to `ci:zero-minutes`; nothing removed |
| D3.2 | Dry run 03 | in `03-complete-gate.dry-run.json` | the complete gate runs 15 ClaimCheck tests and fails on all eight alterations |

**The D2 reproduction:**

```bash
GIT_AUTHOR_NAME="PCS retained source" GIT_AUTHOR_EMAIL=retained-source@example.invalid GIT_COMMITTER_NAME="PCS retained source" GIT_COMMITTER_EMAIL=retained-source@example.invalid GIT_AUTHOR_DATE=2026-11-17T00:00:00Z GIT_COMMITTER_DATE=2026-11-17T00:00:00Z git commit-tree "e0b9136cf7e8480cfcf55c9bfa86b9582f22e39e^{tree}" -p e0b9136cf7e8480cfcf55c9bfa86b9582f22e39e -p d35e2b5e6b29e0a27dc0cb117986895fd58c1456 -m "Retained qualified source: previous site intake plus the ClaimCheck page (proposed; tree identical to the source commit)"
```

**Widening review (site):**

* After D2, the deployed tree is anchored to the retained commit's `public/`, which is the
  reviewed census.
* The gate that enforces that anchor (`original-pr-ancestry-and-production-preservation`) is **not
  among the required checks** the owner confirmed. Unless D2b makes it required, the anchor is
  advisory.
* `site-full-gate` (required) enforces D1's pin and, after D3, the ClaimCheck tests.

## 4. Cross-repository consistency

* Each repository's `scripts/check_reconciled_prs.py` holds both repositories' `INTAKES` entries.
  C1 changes the core entry in the core copy, and D2 the site entry in the site copy.
* After both, each copy's entry for the other repository is stale but never used: the core
  workflow runs `--core` and the site workflow `--site`.
* Confirm both commands in `.github/workflows/model-assurance-studio-research.yml` (core) and
  `.github/workflows/open-pr-reconciliation.yml` (site).

## 5. What this review does not establish

It establishes neither the scientific correctness of ClaimCheck nor the correctness of the
admitted code. It also does not establish the licensing of the recorded model outputs; that is a
separate decision (L1 to L3). The code is covered by the security review (`SECURITY_REVIEW_C3_D4.md`)
and by the tests named in `OWNER_AUTHORIZATION.md`.

## 6. Sign-off

| Item | Reviewer | Date | Result (pass / fail and why) |
| --- | --- | --- | --- |
| C1.1–C1.9, widening review |  |  |  |
| D.0–D3.2, widening review |  |  |  |
| Cross-repository consistency |  |  |  |
