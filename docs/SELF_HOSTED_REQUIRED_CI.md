# Zero-Credit Required CI — Self-Hosted GitHub Actions

PCS must not make protected-main availability depend on a third-party monthly credit balance.

CircleCI remains useful for broader restoration, ABI, Lean, and release campaigns when credits are available. The minimal **required merge gate** can run on a repository-level GitHub Actions self-hosted Linux runner at no GitHub Actions minute charge.

## Why this exists

CircleCI Free blocks personal/private builds when available credits reach zero until the monthly refill. A required CircleCI status can therefore leave otherwise reviewable PRs permanently pending.

The self-hosted gate is intentionally smaller than the full evidence campaign. It runs:

- repository-integrity policy;
- Python compilation;
- pinned Lean authority compilation and formal source hygiene before verifier-dependent tests;
- existing signing-key custody tests;
- v0.6 provenance integration tests when present;
- pilot key-lifecycle/closeout tests when present.

Expensive cross-platform restoration, formal campaigns, and release evidence remain separate checks.

## Runner isolation

Use a dedicated Linux environment, preferably a dedicated WSL distribution, VM, or spare machine. Do not run the PCS runner under an account containing unrelated secrets.

The workflow has only `contents: read` GitHub token permissions and does not request repository secrets.

A self-hosted runner executes repository code. Only enable it for this private/trusted repository and do not expose it to arbitrary untrusted fork PRs.

## One-time runner setup

In GitHub:

1. Repository → **Settings → Actions → Runners**.
2. Choose **New self-hosted runner**.
3. Choose **Linux / x64**.
4. In the dedicated Linux/WSL environment, execute the download and configuration commands GitHub displays.
5. During configuration, add the custom label:

   `pcs-lean-ci`

   If using the command directly, GitHub's generated `config.sh` command can be extended with `--labels pcs-lean-ci`.
6. Start the runner with the command GitHub provides (normally `./run.sh`). For durable use, install it as a service only after the one-off validation succeeds.

The workflow requires all four labels:

`self-hosted`, `linux`, `x64`, `pcs-lean-ci`.

## Required status migration

After the first successful run appears on a PR, change the protected-main ruleset:

- remove `ci/circleci: repository-integrity` as the required merge status while CircleCI has no execution credits;
- require the GitHub Actions check rendered for:

  **PCS Required Self-Hosted / required-gate**

Do not remove the pull-request requirement, deletion protection, linear-history rule, or force-push protection.

When CircleCI credits return, its broader jobs may run as supplemental evidence. There is no need to make a credit-metered status the single mandatory merge dependency again.

## Current recovery order

1. Bring one `pcs-lean-ci` runner online.
2. Let PR #58 and PR #60 execute the self-hosted gate.
3. Require `PCS Required Self-Hosted / required-gate` in the main ruleset.
4. Merge #58 first if green.
5. Update #60 onto the resulting `main`, rerun the gate, and merge if green.
6. Keep CircleCI jobs informational until credits refill.

## Trust boundary

A self-hosted green check means the checked repository revision passed the specified local gate on that runner.

It does not prove:

- the runner operating system is uncompromised;
- hardware identity;
- cross-host reproducibility;
- Lean/kernel correctness beyond checks actually executed;
- scientific adequacy of a claim.

Those remain separate PCS evidence/trust questions.
