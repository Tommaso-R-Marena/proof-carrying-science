# PCS public-source and CI audit evidence — 2026-10-08

**RELEASE STATUS: HOLD.** This records completed investigative checks and the actual limits of the evidence; it is not a release authorization.

## Owner licensing choice

On 2026-10-08 the founder declared ownership of the original PCS intellectual property and selected Apache-2.0 for the open verification core. The applicable license text, NOTICE, open-core charter, contributor DCO proposal, source reviewer quickstart, security policy, and Code of Conduct are staged in draft release PR #77. This declaration is not an independent grant of rights to third-party data, external packages, trademarks, institutional material, or other contributors' work. See `docs/OPEN_SOURCE_CHARTER.md` and `docs/PUBLIC_RELEASE_RIGHTS_LEDGER.md`.

## Verified scope of Git metadata inspection

- GitHub repository refs API was paged twice and returned **123 refs** (2026-10-08).
- For each returned commit-type ref, the full *tip tree* was requested recursively; no truncated trees or fetching errors were reported.
- For these 123 tip trees, a **filename-only** heuristic matching `.env`, private-key file extensions, `.db`/`.sqlite`, credential-like names and similar markers found **zero** candidate paths.
- The current repository tree has source files, public-data validation fixtures, test and documentation assets. Separately, prior default-branch code search yielded no literal `CLOUDFLARE_API_TOKEN` or `client_secret` source hit.
- **NOT DONE:** scanning every historical blob including deleted files, scanning token-shaped strings in all source/blob bytes, historical logs and artifacts, independent gitleaks audit, attribution and input consent validation. A zero candidate *filename* count does NOT imply release safety.
- Run `scripts/public_release_history_audit.py` (PR #77) plus an independent secret scanner on a complete trusted clone of all refs, and review logs/artifacts before publishing.

## Cloudflare CI security status

- Core builds `pcs-core-ci-only` and `pcs-core-ci-gate` use a shared build token named `proof-carrying-science-site build token`; it has **not** been isolated.
- The core preview trigger still matches all branches except main as checked. A PATCH attempting to narrow it was rejected by Cloudflare with `12002: Invalid request body`; **no policy change** occurred.
- **Do not enable public untrusted PR access while this trigger can execute their source with the shared credential.**
- Complete full PR #74 verification or migrate to a verified independent full job; then disable/delete core-connected Cloudflare auto-build triggers and confirm the website's separate build remains functional.
- The connected GitHub actions available here do **not** include repository-visibility or ruleset mutation; these are explicit owner actions in GitHub settings.

## Verified formal-CI status

- PR #74 exact head `037c47a2e8c90cbef76093ec26b31b6ee7f088e0` remained a draft.
- Cloudflare `pcs-core-ci-gate` build `a4eabb9e-1195-48b9-bd25-f1e4eb2df12b` **terminated** after progressing to 162 of 193 Lean build jobs; it did not complete full Python/adversarial tests.
- Required `pcs-core-ci-only` build `dcf02622-a023-4014-b77c-e4c7984f9afe` was observed executing Lean build jobs, not yet PASS.
- GitHub `Protect PCS main` ruleset 24471337 currently requires `Workers Builds: pcs-core-ci-only`; the CircleCI legacy success is a no-op and NOT the required context.
- Draft public CI PR #76 adds a gated, **no-production-secrets** Linux full Lean+executable+Python+adversarial+cross-language byte-contract pipeline, four extra Windows/macOS/Linux Python portability test configurations, fail-closed `verified-public-integration` aggregate, main-only CodeQL Python/JS analysis, and Dependabot for Python and Actions updates. These have not yet run on public GitHub hosts.
- Standard public hosted minutes reduce billing/queue delays, but will **not** make invalid Lean source compile or prevent genuine memory exhaustion.

## Website exposure boundary

Separate website draft PR #81 prepares GitHub open-source verification links for research preview and architecture pages. **Do not deploy until the core repository is actually public.** Private contributor submissions, credentials, D1 production records, account state and admin authorization do not become public when PCS core source becomes open.

## Remaining owner actions

1. Complete third-party material/contractual rights review and sign exact release contents.
2. Run a complete history blob and logs audit in a trusted environment; revoke any exposed credentials.
3. Convert the existing core PR build away from Cloudflare shared website-token trust, or disconnect those core builds before accepting untrusted public PRs.
4. After the prior checks, change **core** repository visibility intentionally. Leave the website source private unless a separate disclosure/rights gate is approved.
5. Run full public CI on an exact PR merge commit and a known-bad negative PR; set that verified `PCS Public Full Verification / verified-public-integration` check as required, then retire the Cloudflare required status without weakening protections.
6. Independently review and merge PR #74, #76 and #77 as applicable. Publish an exact revision release with SHA-bound logs and bounded proof claims.
