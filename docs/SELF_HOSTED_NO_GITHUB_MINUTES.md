# Zero GitHub-hosted-minute assurance CI (optional)

The protected `main` branch currently requires the CircleCI status context
`ci/circleci: repository-integrity`. That is a **separate GitHub ruleset**
configuration. Adding this workflow does not automatically replace or satisfy
that mandatory status check; disabling the CircleCI rule without replacing it
would weaken the project's integrity policy.

## What this adds

- `.github/workflows/pcs-selfhosted-zero-minutes.yml` runs only on a
  `self-hosted`, `linux`, `x64` runner with the extra label `pcs-lean-ci`.
- It is gated by `PCS_SELF_HOSTED_CI_ENABLED=true`; absent the variable,
  GitHub skips the job without scheduling any billable GitHub-hosted compute.
- Runs on pushes to `main` and manual dispatch, NOT external PR heads
  (which are unsafe to run on an owner-controlled workstation).
- `bash scripts/ci_selfhosted_zero_hosted_minutes.sh` also runs locally
  without GitHub Actions: repository-integrity check, Python pytest,
  adversarial campaigns, and the pinned Lean `lake build`/proof-source audit.
- Runs are subject to the uptime, RAM and storage of the owner machine.
  On 16 GB Windows hardware, use WSL2 Ubuntu and allow suitable swap/cache
  for the first Lean/Mathlib build. This workflow makes no claim of being a
  genuinely independent cross-machine test.

## One-time setup

1. In the private GitHub repo, open Settings → Actions → Runners → New
   self-hosted runner → Linux x64. Follow GitHub's live registration commands
   inside a dedicated, least-privileged WSL2 Ubuntu or VM environment.
   Registration tokens are sensitive; **never commit them**.
2. Label the runner `pcs-lean-ci`. Install Python 3, pip, venv, curl, git,
   `elan`, `lean`, and `lake`. The existing `lean-toolchain` pins Lean.
3. Ensure the runner does not contain browser sessions, personal keys, cloud
   secrets, or deploy credentials. Avoid running external PR code.
4. Only when the runner is online, configure repository variable
   `PCS_SELF_HOSTED_CI_ENABLED=true` under Settings → Secrets and variables
   → Actions → Variables.
5. For the current protected-main rule, replace the exhausted CircleCI
   required context with a genuinely executing, independently inspectable
   alternative **only after testing the replacement**. The specific rule
   is `Protect PCS main` / ruleset ID `24471337`.
   Consider keeping a separate integrity check available at PR-time;
   this push/manual self-hosted workflow alone is not a substitute for
   mandatory pre-merge validation.

GitHub's October 2026 documentation states that self-hosted Actions runner
usage is free; your computer's electricity/internet and any separately
metered storage/services are outside that claim.

The website has a separate fully automatic free-tier Cloudflare Workers Builds
pipeline. That pipeline does NOT validate this repository's Lean kernel.
