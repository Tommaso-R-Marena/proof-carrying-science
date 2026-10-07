# PCS CI provider migration — 2026-10-07

Status: **CUT OVER TO CLOUDFLARE WORKERS BUILDS** for the private PCS core repository.

GitHub-hosted Actions minutes and CircleCI compute credits are not the core assurance path. A status that did not execute the repository-integrity + pinned Lean + full Python + adversarial gate is **not** evidence that a revision passed PCS engineering CI.

## Current assurance path

The GitHub-connected Cloudflare Worker build service `pcs-core-ci-gate` runs, fail-closed, on non-main owner branches. The main-side build service runs the same command after merge. Both pin `PYTHON_VERSION=3.12` and `NODE_VERSION=22`.

The full gate performs, in order:

1. install PCS `[dev]` dependencies;
2. run `scripts/check_repository_integrity.py`;
3. install the pinned Lean toolchain and run `scripts/verify_lean.sh`;
4. run the complete `pytest` suite;
5. run `scripts/adversarial_campaign.py`;
6. run `scripts/adversarial_v06_hardening.py`.

The core CI Workers do **not** deploy PCS. Their deploy command is a CI-only no-op message. Only a completed successful build for the exact candidate SHA is admissible engineering evidence.

## GitHub protection transition

The active `Protect PCS main` ruleset still requires the legacy CircleCI App status `ci/circleci: repository-integrity`. CircleCI now emits that context with a zero-credit `type: no-op` compatibility job solely to prevent the stale required context from deadlocking every PR. It is **not** an assurance result.

The real gate is the Cloudflare Workers and Pages check `Workers Builds: pcs-core-ci-gate`. The remaining account-level migration is:

1. in GitHub **Settings → Rules → Rulesets → Protect PCS main**, add `Workers Builds: pcs-core-ci-gate` from the **Cloudflare Workers and Pages** app as a required status;
2. confirm a known-bad disposable PR is blocked and a known-good exact-head PR is permitted;
3. remove the legacy `ci/circleci: repository-integrity` requirement;
4. retain PR-required, linear-history, conversation-resolution, and no-bypass protections.

The connected GitHub integration used for this migration can read but cannot mutate repository rulesets, so that settings change must be performed by a repository administrator.

## GitHub Actions and self-hosted runners

GitHub workflows remain in the repository for optional owner-controlled self-hosted execution. Automatic jobs are guarded by explicit repository variables and reject fork PR execution. If the variables/runners are absent, skipped jobs are expected and are **not** substitutes for the Cloudflare gate.

Do not re-enable GitHub-hosted compute merely to obtain a green badge while hosted minutes are exhausted.

## Integrated work

Core PR #72 consolidated the previously open provenance/SBOM, pilot key lifecycle and closeout, Commons contribution/promotion gates, CI migration, cross-project adapter, fail-closed checker authority, zero-minute runner, and ProofLab benchmark work into `main`.

PR #73 is the post-merge repair/validation pass for the fail-closed authority integration. It must not merge until the exact-head Cloudflare full gate is green. After merge, the new `main` SHA must also receive a green main-side Cloudflare full gate.

## Security boundary

Cloudflare source builds execute repository code. The current build integration uses an existing build token and therefore must be restricted to trusted owner-originated branches while the core repository is private. Before accepting untrusted contributors or forks into automatic builds, replace it with a dedicated least-privilege CI token or isolated runner architecture.

A green CI build is an engineering verification result, not a Lean theorem and not proof of external empirical truth.
