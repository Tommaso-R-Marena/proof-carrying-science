# Required checks for ClaimCheck (owner decision C2): recommendation

**A recommendation. No ruleset, required check, workflow trigger of an existing gate, or bypass
setting has been changed.** Rulesets are repository settings only the owner can change, and the tools
available to this work cannot read them. The "documented" state below is what the repositories' own
documents record; confirm it in **Settings → Rules → Rulesets** before acting.

## What was checked

| | How | Result |
| --- | --- | --- |
| workflow triggers and job names, both repositories | parsed every workflow on the draft PR heads | inventory below |
| the names GitHub actually reports | check runs on core PR 212 (head `c526d05c`) and site PR 149 (head `272579f`) | names equal the job names; matrix jobs carry their parameters, e.g. `portability-ubuntu-24.04-py3.13` |
| the live rulesets | not readable here | **owner to confirm** |

Documented required checks: core `verified-public-integration` (strict aggregate) and `source-policy`
(`docs/HOSTED_CONTRIBUTION_CI.md`, 2026-10-09); site `site-full-gate`
(`docs/HOSTED_CI_REPLACEMENT.md` on the site, 2026-10-17). Older documents name Cloudflare and CircleCI
contexts that were later retired; they should not be re-added.

Two GitHub behaviours decide everything here (GitHub documentation, "Troubleshooting required status
checks"): a **workflow** skipped by a path or branch filter reports nothing, so a check required from
it stays *pending* and blocks every pull request that does not touch those paths; a **job** skipped by
its `if:` condition reports *success*, so a required job that is skipped passes the requirement.

## Core repository

### What exists

| Workflow | Runs on pull requests | Jobs (= check names) | Notes |
| --- | --- | --- | --- |
| `pcs-public-full-verification.yml` | every PR to `main` | `source-policy`, `core-full-gate`, `real-analysis-bridge`, `certiforge-integration`, `portability-*`, `lean-learning-loop`, `independent-pilot-cleanroom`, `verified-public-integration` | `verified-public-integration` runs with `always()` and fails unless every prerequisite **succeeded** (skipped, cancelled or missing fail it): the right kind of required check |
| `pcs-ci.yml`, `pcs-required-self-hosted.yml` | every PR to `main` | `repository-integrity`, `python-assurance`, `lean-kernel`, `v06-byte-contract`, `verified-integration`, `required-gate` | **every job is skipped on every pull request** (they run only for non-PR events in a private repository with a self-hosted runner) |
| `pcs-claimcheck-v1.yml` (added by this branch) | every PR (since commit `99637e67`) | `changes`, `offline-and-kernel`, `meaning-theorems`, `claimcheck-required` | see below |

### Finding: requirements that a skipped job would satisfy

On PR 212 the six jobs of `pcs-ci.yml` and `pcs-required-self-hosted.yml` report **skipped**. If any of
`repository-integrity`, `python-assurance`, `lean-kernel`, `v06-byte-contract`, `verified-integration`
or `required-gate` is a required check, it is satisfied on every pull request without anything having
run. The documented required checks do not include them; please confirm that the live ruleset does
not either. Separately, `core-full-gate` and three other jobs have `needs: source-policy` without
`always()`: when `source-policy` fails they are skipped, so they must never be required on their own.
`verified-public-integration` is safe because it rejects skipped prerequisites. And if the repository
were made private, every job of `pcs-public-full-verification.yml` would be skipped (they require a
public repository), so a required `verified-public-integration` would pass vacuously: re-examine the
ruleset before any visibility change.

### The ClaimCheck checks, and why only one should be required

Until commit `99637e67` the ClaimCheck workflow ran only on pull requests that touched its paths. Its
jobs could not be required: every other pull request would have waited for them forever. The
workflow now runs on every pull request:

* `changes` (seconds) decides whether the pull request touched `research/claimcheck_v1/`,
  `research/claimcheck_v1_1/`, the Lean bootstrap `scripts/activate_lean_428.sh` (which ClaimCheck
  runs and which the old path filter missed) or the workflow itself. It diffs GitHub's merge commit
  against its first parent with renames disabled, so a file moved out of ClaimCheck still counts, and
  it fails (it does not guess) if the checked-out commit is not that merge;
* `offline-and-kernel` and `meaning-theorems` run only when `changes` says so;
* `claimcheck-required` always runs and fails unless `changes` succeeded and, when a ClaimCheck path
  changed, both jobs succeeded.

Tested by `research/claimcheck_v1_1/governance/test_required_check.py`, which runs the two shell steps
verbatim: 13 change scenarios on real Git merge commits (documentation only, production code only, a
look-alike directory `claimcheck_v1_10/`, each ClaimCheck root, a new file, the Lean bootstrap, the
workflow, a deletion, a rename out of the tree, an empty pull request, a non-merge checkout, a manual
run), and all 192 combinations of job results for the aggregate, of which exactly the 17 intended
ones pass. The positive path also runs live on PR 212.

Actions in this workflow are now pinned to the commits the repository's other workflows use, and the
checkout does not keep credentials.

**Recommendation (core):** add exactly **`claimcheck-required`** (GitHub Actions) to the required
checks of the `main` ruleset, after the source admission (C1) is merged. Do not require
`offline-and-kernel` or `meaning-theorems` directly: they are skipped (= passing) on unrelated pull
requests by design, and the aggregate already requires them when they matter. Keep
`verified-public-integration` and `source-policy` as they are. Adding `claimcheck-required` cannot
leave a pull request pending (it runs on every pull request) and weakens nothing (it only adds a
condition).

A required check from a workflow in the pull request cannot stop a pull request that edits that
workflow. Here that is covered by the source admission: the V23 manifest pins the workflow's bytes,
so an edited workflow fails `source-policy` until the owner admits it.

If PR 216 is admitted, its `proofs-and-refinement` job has the same path-filter problem; give it the
same aggregate before requiring it (not done: that PR stays separate until decided).

## Website repository

| Workflow | Runs on pull requests | Jobs | Notes |
| --- | --- | --- | --- |
| `site-public-verification.yml` | every PR to `main` | `site-full-gate` and its prerequisites | `site-full-gate` runs `bash scripts/cloudflare_build.sh`, which runs `npm run ci:zero-minutes`, the complete website gate |
| `claim-check.yml` | PRs touching 10 ClaimCheck paths | `claim-check-page` | path-filtered: **must not be required as it is** |
| `site-check.yml`, `open-pr-reconciliation.yml`, `countermodel-lean.yml`, `site-contract.yml` | every PR | `site-check`, `original-pr-ancestry-and-production-preservation`, `countermodel-lean-kernel`, `site-contract` | unchanged |

**Recommendation (site):** no new required check. Proposed patch 03 (decision D3) appends
`npm run test:claim-check` to `ci:zero-minutes`, so ClaimCheck's mandatory tests (served runner
digest, catalog, withdrawn receipts refused, local-run labels, receipt rules) run inside
`site-full-gate`, which is already required and runs on every pull request. That adds no pending
check and changes no ruleset. `claim-check-page` (the browser journey with the real Lean kernel)
stays a supplementary, path-scoped check; if the owner wants it required too, give it the same
change-detection aggregate as the core workflow first.

## What to verify by hand in the rulesets

The tools used for this work list branches and say only whether one is protected: on 2026-11-18
core `main` (`bc78660b`) and site `main` (`e8136625`) were both reported protected. Please check in
**Settings → Rules → Rulesets** of each repository:

* **core `main`:** required checks include `verified-public-integration` and `source-policy`; none
  of `repository-integrity`, `python-assurance`, `lean-kernel`, `v06-byte-contract`,
  `verified-integration` or `required-gate` is required (they are skipped, i.e. passing, on every
  pull request); no retired Cloudflare or CircleCI context is required; pull requests, resolved
  conversations, linear history, no force-push or deletion; no bypass actor.
* **site `main`:** `site-full-gate` is required; `claim-check-page` is not (path-filtered); the same
  pull-request, linear-history and no-bypass settings.
* After C1: add `claimcheck-required` (GitHub Actions) to core `main`.
* Tags: whether a rule restricts who may create `pcs-source-intake/*` tags (the retained-source
  tags are owner-held).

## Consequences

| Decision | If approved | If not |
| --- | --- | --- |
| require `claimcheck-required` (core) | a ClaimCheck change cannot merge without both ClaimCheck jobs passing; unrelated pull requests are unaffected (one job of a few seconds) | ClaimCheck failures are visible but advisory, as today |
| apply patch 03 (site) | ClaimCheck's mandatory tests become part of the existing required website gate | the tests run only in the path-scoped `claim-check-page` job |
| confirm the core ruleset does not require the always-skipped jobs | removes a requirement that gives no protection on pull requests, if one exists | nothing changes |
