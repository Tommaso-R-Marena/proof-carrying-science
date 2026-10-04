# Repository Integrity and Branch Reconciliation Policy

## Purpose

PCS makes unusually strong claims about reproducibility, proof checking, exact bytes, and explicit trust boundaries. The repository that implements those claims must itself be managed with the same discipline.

This policy defines the repository-level invariants that future developers, AI agents, proof assistants, and maintainers must preserve. It covers source bytes, Git metadata, branch lineage, CI evidence, formal-verification claims, and the handling of superseded work.

The dated audit that motivated this policy is recorded in `docs/BRANCH_RECONCILIATION_2026-10-04.md`.

## Source of truth

`main` is the only authoritative integration branch.

A feature branch, proof-search branch, Aristotle handoff, CI probe, or historical release branch is never authoritative merely because it is newer, has more commits, or appears "ahead" of `main`.

A branch may be treated as current only when all of the following are true:

1. its intended changes have an open integration PR, or the branch is explicitly named as active in current project documentation;
2. its base relationship to current `main` is understood;
3. its CI evidence applies to the exact head commit being discussed;
4. any superseded predecessor is identified;
5. no post-merge commits are being silently treated as though they were part of an earlier merged PR.

## Repository integrity is more than file contents

Git metadata is part of the executable system.

In particular:

- executable bits are semantically relevant for directly invoked scripts;
- line endings can affect shell entrypoints and frozen byte contracts;
- path case and Unicode-normalization collisions can break cross-platform checkouts;
- branch ancestry can be misleading after squash merges;
- a green historical CI run does not establish that current `main` is green;
- documentation that says "PASS" is not evidence unless it names or points to an exact tested commit.

The mandatory automated gate is:

```bash
python scripts/check_repository_integrity.py
```

It checks required governance files, shell-script Git modes, LF line endings, direct verification entrypoints, cross-platform path collisions, and synchronized Lean toolchain pins.

Every release gate also runs this check.

For repository settings/branch protection, treat the CircleCI status `ci/circleci: repository-integrity` as a required merge check. If automatic GitHub Actions triggers are re-enabled, the GitHub `repository-integrity` job should also remain a prerequisite for the other PCS CI jobs.

### Branch-protection enforcement status

As of 2026-10-04, GitHub reports `main` as protected by the active repository ruleset `Protect PCS main`.

The ruleset:
- targets the default branch;
- blocks deletion and non-fast-forward updates;
- requires changes through pull requests;
- requires review-thread resolution;
- requires `ci/circleci: repository-integrity`;
- requires the branch to be up to date before merge;
- requires linear history;
- has no bypass actors.

Enforcement was tested with temporary PR #56, which deliberately removed the required shell LF rule from `.gitattributes`. The repository-integrity check failed, and GitHub rejected a merge attempt with a ruleset violation naming the failing required status check. PR #56 was then closed without merge and its test branch was reset to `main`.

Issue #54 records the configuration and verification evidence and may be closed as completed.

## Shell-script rules

Every tracked `.sh` file must:

- be committed with mode `100755`;
- begin with a shebang;
- use LF rather than CRLF line endings.

For Windows development, do not assume that filesystem permissions reflect the Git index. Use:

```bash
git update-index --chmod=+x scripts/example.sh
git ls-files --stage scripts/example.sh
```

The second command must show `100755`.

`.gitattributes` pins shell files to LF endings. Do not remove that rule without an explicit repository-integrity PR.

## Branch lifecycle

Use these conceptual states when reasoning about branches:

- **ACTIVE** — current work with an open integration path.
- **MERGED** — intended work reached `main`; the branch must not receive additional work under the old PR.
- **SUPERSEDED** — replaced by a later implementation or PR.
- **ARCHIVAL** — intentionally preserved research/proof history; not a merge candidate.
- **DIAGNOSTIC** — temporary CI or investigation work; reset/delete after the investigation.
- **RECONCILIATION CANDIDATE** — potentially unique work that has not yet been shown to be present or superseded on `main`.

Do not infer these states solely from ahead/behind counts.

### After a PR merges

Do not continue substantive development on the merged branch as though the new commits were included in the merged PR.

If additional work is needed:

1. start from current `main`;
2. create a new branch;
3. open a new PR;
4. reference the earlier PR where relevant.

If a post-merge commit already exists, it must be reviewed as a new change. Compare its content against current `main`; if the functionality is already present in evolved form, document that conclusion rather than merging the old branch.

### Squash merges

PCS commonly uses squash merges. Therefore Git graph divergence is not evidence that functionality is missing.

Before claiming that an "ahead" or "diverged" branch contains lost work, check:

1. the head SHA reviewed by the relevant PR;
2. the merged/squash commit on `main`;
3. the actual file/content delta;
4. whether later `main` commits implement an evolved version of the same change;
5. whether the branch received commits after its PR merged or closed.

The helper:

```bash
git fetch origin --prune
python scripts/audit_branch_reconciliation.py --base origin/main
```

reports graph shape, but its output is deliberately not a merge recommendation.

## Historical branches must not be merged wholesale

Old `formal/*`, `v06/*`, Aristotle handoff, release, and experiment branches often contain stacked development from before later integrations.

If a historical branch may contain valuable residual work:

1. identify the exact commit or hunk believed to be unique;
2. compare that content to current `main`;
3. port the smallest still-needed change onto a fresh branch from current `main`;
4. run current tests and trust-boundary audits;
5. open a new PR.

Never merge a large stale branch merely to make Git ahead/behind counts disappear.

## Formal-verification evidence rules

Claims such as "Lean passes", "machine checked", "no sorry", or "frontier theorem verified" must be attached to an exact repository state.

At minimum record:

- commit SHA;
- Lean toolchain version;
- the gate that was executed;
- whether the gate ran from a clean checkout;
- whether the production formal root or only a narrower target was built;
- any remaining trust assumptions.

A source document saying that a build passed is not a substitute for current CI.

For production formal work, run:

```bash
./scripts/verify_lean.sh
```

For the Mathlib real-analysis bridge, additionally run:

```bash
./scripts/verify_lean_real.sh
```

Do not weaken theorem statements, add proof escape hatches, or reinterpret an older green run as evidence for a changed commit.

## CI changes are production changes

CI configuration determines which evidence exists. Treat changes to `.circleci/config.yml`, workflow files, release gates, and verification scripts as production changes.

A CI-only change must explain:

- what evidence it adds/removes;
- which branches it runs on;
- whether it changes a required gate;
- whether it is temporary diagnostic instrumentation.

Temporary diagnostic jobs must not silently become permanent policy. Either remove them after the investigation or intentionally promote them with documentation.

## Documentation consistency

When a capability or proof status changes:

1. update the closest normative status document;
2. update any public claim that is no longer exact;
3. record the exact open boundary rather than saying "fully verified";
4. link superseded documents to the current source of truth.

When an incident reveals a new class of failure, add a machine regression check whenever technically possible.

## Merge checklist

Before merging any PCS change:

1. update from current `main`;
2. inspect `git diff --summary origin/main...HEAD` for unexpected mode or rename changes;
3. run `python scripts/check_repository_integrity.py`;
4. run the focused test suite for the change;
5. run formal gates when formal or authority paths are affected;
6. identify superseded branches/PRs in the PR description;
7. confirm documentation claims describe the exact tested state;
8. verify no intended change lives only in an already-merged branch;
9. preserve explicit trust boundaries and failure modes.

The PR template encodes these requirements.

## Incident rule

Repository-integrity failures are not "just CI" when they invalidate reproducibility evidence.

If a metadata, branch, CI, or packaging discrepancy is found:

1. identify the first affected commit;
2. determine whether source semantics actually changed;
3. reproduce the failure with the smallest independent check;
4. make the narrowest repair;
5. validate the exact production entrypoint;
6. record the incident and the preventive invariant;
7. reconcile any temporary branches created during diagnosis.

This is the process used for the 2026-10-04 executable-bit incident.
