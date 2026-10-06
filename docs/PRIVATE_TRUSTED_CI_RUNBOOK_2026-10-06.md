# PCS private CI restoration without publicizing the research

**Current status: implementation prepared; runner not provisioned; branch protection unchanged.**

The core GitHub Actions workflow supports an optional repository Actions variable `PCS_TRUSTED_RUNNER`. When absent, jobs use GitHub-hosted `ubuntu-latest` as before. When set, it must name a **dedicated, sandboxed runner label** provisioned by the repository owner.

## Before providing any runner

1. Do not use your primary laptop, personal Windows installation, JHU/HPC infrastructure without authorization, or a normal Docker socket to execute arbitrary PR code. A self-hosted runner executes repository source and can leak its host, filesystem and network credentials if compromised.
2. Provision a disposable dedicated Linux VM or similarly strong isolated environment with an unprivileged user, no production secrets, no private SSH keys, no administrative cloud tokens, no privileged Docker socket or host file mounts, and restricted network egress. Patch host software and enable per-job reset/teardown.
3. Use the GitHub repository **Settings → Actions → Runners → New self-hosted runner** wizard; obtain a fresh short-lived registration token there. Never put tokens into code, CI logs or a support chat.
4. Register an **ephemeral** runner with a private label such as `pcs-private-ephemeral`. Enable automatic re-provisioning for each job (the workflow contains four independent checks plus the aggregate gate). Runner teardown and source cleanup are mandatory; one persistent runner that sequentially executes untrusted PRs is not equivalent isolation.
5. Set the repository Actions variable `PCS_TRUSTED_RUNNER` to `pcs-private-ephemeral` **only after** that isolation and provisioning are working. Never configure this label with a public/fork runner service or reuse it for private secrets.
6. This workflow fails closed for PRs whose `head.repo.full_name` differs from the protected repository. External forks need a separate explicitly approved strategy with untrusted code in disposable hosted environments. Do not use `pull_request_target` to build PR source.
7. The GitHub Actions token remains `contents: read` and `actions/checkout` uses `persist-credentials: false`. Never attach Cloudflare credentials or GitHub write tokens to the PR test environment.

## Reproducible command outside GitHub

From a **clean exact-SHA checkout** in a disposable Linux environment (Python ≥ 3.11; Python 3.12 recommended; Node.js 22; Lean/Lake pinned by `lean-toolchain`):

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[dev]'
python scripts/run_trusted_ci.py
```

The script executes Git integrity, the full Python suite, legacy and v0.6 adversarial campaigns, deterministic golden examples, certificate issuance and policy checks, default Lean target build and proof audit, v0.6 Python/Node byte contract, and (when available) Aristotle's golden-file literal checker. It fails on the first missing prerequisite or failed check; its `results/trusted-ci-diagnostic.json` is an **unsigned local diagnostic**, never a substitute for a GitHub-provided job status.

## Protected-branch cutover

1. Keep required `ci/circleci: repository-integrity` until `PCS CI / verified-integration` actually executes on an exact PR head, each dependent job reports success, and a deliberately failing PR is prevented from merging.
2. Set `PCS CI / verified-integration` as a required GitHub Actions check, in addition to the old required check, and demonstrate both positive and negative paths.
3. Only after the new gate is proven to enforce the same or stronger controls may the Owner deliberately retire the unavailable CircleCI context. Do not change rulesets to accept a manually asserted fake PASS.
4. Independently run domain-specific `PCS Submission Verification` and `PCS Promotion Verification` after core PRs #62/#63 have their workflows merged. Aggregate core CI is not a replacement for those per-PR, exact-byte checks.
5. Record exact commit hash, workflow-run URL, runner isolation specification, test steps, action conclusions and owner approval in the CI migration record.

## Blockers outside the repository

- Private hosted-runner usage remains unavailable while the allowance is exhausted. This code alone cannot provide execution capacity.
- GitHub rulesets and the repo Actions variable require an authorized owner to configure; they are deliberately **not** changed by this PR.
- No fresh Lean/Python assurance run on this PR has yet been observed. Until then, **do not merge formal or production-security claims into core main** under an assertion that CI passed.
