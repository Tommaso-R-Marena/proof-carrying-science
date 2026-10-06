# PCS CI provider migration — 2026-10-06

Status: **PREPARED, NOT CUT OVER**. GitHub Actions and CircleCI hosted minutes on private repos have reportedly been exhausted. A status stuck pending because a runner did not execute is **not** a pass.

## Current safety baseline
- `main` is protected by the **Protect PCS main** ruleset. It requires a PR, linear history, resolved review threads, and `ci/circleci: repository-integrity`, with no bypass actors.
- The GitHub Actions workflow `.github/workflows/pcs-ci.yml` now schedules read-only checks on PRs and main. It has one aggregate job named `verified-integration`, which fails if **any** prerequisite check is failed, cancelled, skipped, or unavailable.
- Required prereqs: repository-integrity (including Git modes), Python assurance/regression/adversarial/golden examples, Lean build + placeholder check, and frozen v0.6 cross-language byte contracts.
- These are **source and executable verification checks**, not formal assurance of external empirical truth.

## Cutover (only after real successful PR execution)
1. Confirm that the repository may be public **only after** completing `docs/PUBLIC_RELEASE_GATE.md`. If keeping private, supply a safely isolated runner or wait for credit reset. Do not use `pull_request_target` to execute untrusted PR code.
2. Create a disposable PR from current `main` and inspect **all** run steps, logs, build artifacts and their exact SHA. Ensure `PCS CI / verified-integration` is actually green. A no-run or runner-less check is **not** evidence.
3. Inspect `PCS CI / repository-integrity`, `PCS CI / python-assurance`, `PCS CI / lean-kernel`, and `PCS CI / v06-byte-contract` individually. Validate equivalence to the existing CircleCI gate and run optional restoration, signing/provenance, and specialized suites for relevant PRs.
4. Under GitHub **Settings → Rules → Rulesets → Protect PCS main**, add the GitHub required check (select `PCS CI / verified-integration` with **GitHub Actions** as the expected app). Keep the old CircleCI requirement initially.
5. Verify that an intentionally failing test branch is rejected by the new check; also confirm that a green test PR satisfies the new status. Only then remove the obsolete required `ci/circleci: repository-integrity` status. Preserve the PR/linear-history/conversation-resolution rules. Do not add bypass actors.
6. Keep exact-head revalidation in the PCS production promotion gateway. Domain-specific submission and promotion workflows require their **own** completed successful jobs; an aggregate core CI green does not replace them.
7. Restore scheduled maintenance and document the settings, exact job names, tests, head SHAs and approval in an audited issue.

**Important:** Changing a repo private→public has side effects. GitHub reports that push rulesets are disabled during such a change; re-check and re-enable effective protections before letting outside contributors submit.

## Open PR reconciliation (against 2026-10-06 main)
| PR | Scope / changed files | Decision until verified |
|---|---|---|
| #62 | 2 files: digest-bound submission verifier and read-only workflow | **Priority 1**. Required for core Commons submissions. Review and run PR-specific job before merge. |
| #63 | 2 files: exact archive-to-source production promotion verifier/workflow | **Priority 1** after #62. Requires fresh Lean/PCS and PR-diff checks; no bypass. |
| #61 | 5 files: Claim Invalidation v1 fixtures and reference checker | **Priority 2** after review of corpus and reference semantics. |
| #58 | 27 files, ~2,897 changed lines: SBOM and signed provenance, shared .circleci and workflow edits | **Priority 3**; large, independently review and rebase/consolidate. |
| #60 | 17 files, ~2,088 changed lines: pilot key custody/closeout, overlapping CI files with #58 | **Priority 3**; deduplicate shared CI edits and independently test key lifecycle. |

**No PR above is deemed test-passing merely because GitHub says `mergeable`.**
Main still carries historical formal, Lean and proof-translation features already integrated through squash merges; do not wholesale merge 50+ historical branches. Follow `docs/BRANCH_RECONCILIATION_2026-10-04.md` and perform targeted salvage only for demonstrated absent functionality.

### Current blocker
PRs #58, #60, #61, #62, and #63 have the current required `ci/circleci: repository-integrity` pending. Do **not** remove the requirement merely to get them merged. A change of CI provider is permissible only after independently executed equivalent verification.
