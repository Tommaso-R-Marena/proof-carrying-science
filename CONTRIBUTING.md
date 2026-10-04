# Contributing to Proof-Carrying Science

PCS treats repository history, CI evidence, and Git metadata as part of the assurance surface. Contributions therefore have stricter integration rules than a typical application repository.

Read `docs/REPOSITORY_INTEGRITY_POLICY.md` before modifying core verification, formalization, packaging, CI, or release infrastructure.

## Start from current main

Create new work from current `main`:

```bash
git fetch origin --prune
git switch main
git pull --ff-only
git switch -c <type>/<short-description>
```

Do not resume feature development on a branch whose PR has already merged or been superseded. If more work is needed, create a new branch and new PR from current `main`.

## Mandatory preflight

Before opening or updating a PR:

```bash
python scripts/check_repository_integrity.py
git diff --summary origin/main...HEAD
```

Inspect the second command for unexpected file-mode, rename, or path changes.

For branch-history investigations:

```bash
git fetch origin --prune
python scripts/audit_branch_reconciliation.py --base origin/main
```

Ahead/behind counts are diagnostic only. PCS uses squash merges, so graph divergence does not imply lost work.

## Shell scripts

Every tracked `.sh` file must be committed as `100755` and use LF endings.

On Windows, set the Git index bit explicitly:

```bash
git update-index --chmod=+x scripts/example.sh
git ls-files --stage scripts/example.sh
```

Do not rely on local filesystem permission behavior.

## Formal changes

For changes touching the production Lean root or Lean authority:

```bash
./scripts/verify_lean.sh
```

For changes touching the Mathlib real-analysis bridge:

```bash
./scripts/verify_lean_real.sh
```

A claim that a theorem or formal layer "passes" must name the exact commit and current gate evidence. Do not rely on an older status document after source or build configuration changes.

Never introduce `sorry`, `admit`, project `axiom`, `unsafe`, `implemented_by`, `extern`, or `native_decide` into the production formal root.

## Historical branches

Do not merge stale `formal/*`, `v06/*`, Aristotle, product, release, or diagnostic branches wholesale.

If an old branch may contain a useful residual change, identify the exact commit/hunk, compare it to current `main`, and port only the still-needed change onto a fresh branch.

See `docs/BRANCH_RECONCILIATION_2026-10-04.md` for the current audited baseline.

## CI and release infrastructure

Treat CI configuration and verification scripts as production code.

Temporary diagnostic jobs must be clearly identified and removed/reset after the investigation unless intentionally promoted into permanent policy.

The release gate runs repository-integrity checks. A release candidate with broken Git metadata is not acceptable merely because source files compile locally.

## Pull requests

Use the repository PR template. In particular, state:

- what changes;
- what does not change;
- whether a trust boundary or formal claim changes;
- which branches/PRs are superseded;
- exact validation performed;
- whether any Git metadata changed intentionally.

After a PR merges, do not add substantive commits to its old branch. Additional work requires a new PR.
