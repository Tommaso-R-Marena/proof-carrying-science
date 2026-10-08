> **Live status correction (2026-10-08):** GitHub ruleset `Protect PCS main` (ID 24471337) was inspected through the GitHub API. It **already requires** `Workers Builds: pcs-core-ci-only` (Cloudflare Workers and Pages integration ID 85455), not the legacy CircleCI no-op. The CircleCI compatibility context remains present but is not currently the required check. A separate `Workers Builds: pcs-core-ci-gate` check was observed running against PR #74 commit `037c47a2`; the required `pcs-core-ci-only` build was queued. Do not confuse the two check names or treat a green result from one as satisfying the other. Historical migration steps below record earlier states and should not override this checked live state. See issue #75 and `docs/PUBLIC_RELEASE_EXECUTION_2026-10-08.md`.

# Private PCS core CI: Cloudflare Workers Builds and fail-closed merge policy

**Scope:** This is CI verification infrastructure, not a scientific assurance theorem. As of 2026-10-06, GitHub Actions hosted minutes and CircleCI credits are unavailable for the private core repository. Do **not** remove protected-branch requirements just because an alternative job was configured.

## Actual configured build service

The separate, non-serving Cloudflare Worker `pcs-core-ci-gate` is GitHub-connected to `Tommaso-R-Marena/proof-carrying-science`. It does not deploy the PCS research core or touch the website production Worker: its deploy command only writes a CI-only message.

The Build command is an exact-commit, fail-closed chain: install PCS Python `[dev]` dependencies, audit Git repository integrity and executable modes, install elan and build the **pinned** `formal/` Lean authority via `scripts/verify_lean.sh`, run full pytest, and run frozen/adversarial campaigns. **Lean must be built before pytest** because v0.6 tests invoke its executable authority. The independent Cloudflare result appears as a GitHub check named **`Workers Builds: pcs-core-ci-gate`** when the build is associated with a commit.

Both the main and non-main core build triggers pin `PYTHON_VERSION=3.12` and `NODE_VERSION=22`, so the protected-branch candidate gate and post-merge main verification use the same runtime versions rather than silently testing different Python interpreters.

Cloudflare's free build minutes (currently 3,000/month, one concurrent job, 20-minute job timeout) are separate from GitHub-hosted Actions minutes. All queued/running/cancelled build states are **not** passed checks. Only a completed successful exact-SHA run is admissible engineering evidence. The free quota is finite, not free unlimited compute.

## IMPORTANT: protect the existing merge gate

The active GitHub ruleset `Protect PCS main` (ID `24471337`) still names the legacy CircleCI App status `ci/circleci: repository-integrity`. The repository now emits that exact context through a documented **zero-credit CircleCI no-op compatibility job** so the stale rule does not deadlock every PR; that status is not assurance evidence and must never be presented as such. The real engineering gate is the exact-head `Workers Builds: pcs-core-ci-only` / `Workers Builds: pcs-core-ci-gate` result. The GitHub ruleset should be migrated to the Cloudflare Workers and Pages check as soon as repository settings are changed; the connected GitHub tool available here cannot mutate rulesets. Do not use force-push or admin bypass to evade the real Cloudflare gate.

For an audited migration, the owner must:
1. Obtain a **completed green** Cloudflare full-Python/Lean result for the exact candidate PR head and verify it actually ran the tests, not a no-op.
2. Obtain a **red** result on a deliberately malformed disposable PR proving the verifier fails closed; inspect build logs and check identities.
3. In GitHub **Settings → Rules → Rulesets → Protect PCS main**, add `Workers Builds: pcs-core-ci-gate` as a required status from the **Cloudflare Workers and Pages** GitHub App while retaining CircleCI.
4. Verify the new check blocks known-bad PRs and permits known-good PRs; then remove the exhausted `ci/circleci: repository-integrity` requirement from that same ruleset, preserving mandatory PRs, signed/reviewed merge policy and strict update requirements.
5. Re-run on the new head SHA of every PR after bringing it up to date with main. For code changing semantics, obtain independent reviewer confirmation appropriate to its threat model.

This ruleset migration is still the desired end state, but the current repository uses the legacy CircleCI context only as a documented zero-credit compatibility bridge. Until the GitHub ruleset can be edited, merge decisions must require an independently inspected **green full Cloudflare build on the exact candidate head**; the compatibility status alone is never sufficient assurance.

## Security constraints

The configured Cloudflare Builds service uses a build token previously configured for the website because this integration cannot create a separate new user-scoped build token. It should be **replaced with a dedicated least-privilege token before accepting any untrusted contributors/forks**. Do not put credentials or owner secrets into builds. Cloudflare source builds execute repository code (including pip build hooks); they are not a safe sandbox for adversarial PRs with an account-wide deploy credential. Keep core private, run only explicitly trusted owner-originated branches for now, and disable automatic untrusted previews until proper credential isolation exists.

Do not conflate a Cloudflare success check with a Lean theorem, and do not claim universal AI safety or that all runtime and observation trust boundaries have disappeared.

## Other PR relationships

- #68 supplies optional self-hosted Linux/WSL verification; it uses custom runner label `pcs-lean-ci`, is disabled until the runner is registered, and also must build Lean *before* pytest.
- #62 adds contribution gates, #63 adds exact promotion gates; neither grants scientific acceptance without checker-reviewed certificates.
- #58 and #60 both include `.github/workflows/pcs-required-self-hosted.yml` and documentation, so reconcile these overlapping workflow files in the chosen merge order.
- #66 stays fail-closed until its P0 unknown `check_spec.type` repair is formalized and independently verified.
