# Public release execution record — 2026-10-08

**DECISION: HOLD. This document does not authorize changing the existing core repository to public.**

This checklist supplements `docs/PUBLIC_RELEASE_GATE.md` and is organized around verifiable release evidence, not assumptions that the current technical work is finished.

## Recommended publication boundary (proposal, not adopted legal terms)

A credible default is an **Apache-2.0 genuinely open reference verifier, certificate formats, Claim IR, Lean proof sources, and independent reproduction utilities**. Sell managed hosting, support, enterprise access controls, integration engineering, and *separately authored/licensed* domain packs where contributor/IP rights allow. A published Apache-2.0 file remains commercially usable under that license; saying “open-core” does not retroactively reserve commercial rights.

**Approval needed from the owner and qualified legal/IP reviewer.** Record authorship, institutional and third-party rights, existing recipients, publication priority, patent-sensitive work, and the boundaries of code excluded from any public distribution. Do not assert a CLA or assignment retroactively. A DCO sign-off is a provenance statement, not a transfer of university/collaborator rights.

## Release gates

| Gate | Present status | Evidence required to mark PASS |
|---|---|---|
| Apache-2.0/open-commercial boundary (#11) | OPEN | Dated founder decision, counsel review if needed, complete SPDX/license inventory and permission to distribute every incorporated file |
| Publication firewall | OPEN | Author/institution/collaborator clearance for relevant unpublished AI-safety, PK/PD, biochemistry and other constituent results |
| Source/history disclosure | OPEN | Full refs/PR history/archive/log scan, manual review, credential rotation where indicated; signed-off inventory |
| Shared Cloudflare CI credential (#75) | OPEN | Dedicated least-privilege build token or Cloudflare non-main builds disabled before untrusted public PRs; test no website deployment capability |
| Soundness PR #74 / issue #67 | OPEN | Complete Lean kernel + binary ZIP/dir fixtures + Python/adversarial exact SHA, independently reviewed and merged |
| Genuine protected-main CI (#75) | PARTIAL | GitHub currently requires Cloudflare `pcs-core-ci-only`; confirm it actually executes and passes the full suite on the exact SHA, and run known-bad enforcement test |
| Public Actions PR #76 | STAGED | Public standard-hosted full gate tested on actual PR merge commit, no secrets, fork safety, correct timeout and logs |
| Public contributor policies | PARTIAL | SECURITY, conduct, contribution/DCO, vulnerability handling, release processes reviewed and merged |
| Release evidence and non-claims | OPEN | Tagged candidate, bounded theorem inventory, trust boundary, signed SHA-bound run evidence, reviewer reproduction on a second environment |
| Founder authorization | OPEN | Record exact SHA + date + APPROVE; then execute deliberate GitHub visibility action, never indirectly as CI workaround |

## Auditing the *entire* repository history before visibility conversion

1. Make a **fresh trusted local clone**, including branches and tags; fetch pull request heads too (review access and rate limits apply). A default shallow clone or default-branch-only code search is insufficient.
2. Run `python scripts/public_release_history_audit.py --json audit-summary.json` from the clone; review every suspicious blob by hash/path privately. This is a heuristic first pass, NOT full secret validation or proof of no disclosure.
3. Use an independent, trusted history-aware secret scanner (for example gitleaks) and manually inspect CI run logs, artifacts, GitHub Releases, GitHub issue/PR text, binary artifacts, and any confidential past branches. Be mindful that scanners can miss private data unrelated to tokens.
4. Inspect licenses and source provenance file by file, including generated, vendored, AI-assisted, and third-party contributions; record rights for historical versions that will become public.
5. Rotate/revoke leaked credentials **before** visibility changes. Deleting from current `main` does not erase earlier Git objects, forks, logs or downloaded archives.
6. Have an independent reviewer sign off the complete disclosure/rights register. If full history cannot be cleared, **publish a clean, rights-cleared new public repository from an audited snapshot**, rather than flipping the old repository.

## CI cutover procedure

1. Keep the current trusted private CI while issue #67 / PR #74 is unresolved; do not count CircleCI's `ci/circleci: repository-integrity` zero-credit no-op as passing assurance.
2. Fix the shared Cloudflare build token. Stop automatic GitHub-connected Cloudflare builds of untrusted fork/PR source until the builder can run without credentials that can touch production.
3. Inspect PR #76, and test the same full suite on the **proposed merge commit** rather than just the unmerged PR head. Public hosted workflows must have only `contents: read` and no deployment secrets.
4. After legal/security clearance and an explicit repository public-release decision, enable standard GitHub-hosted CI, run one known-good full pass and one deliberately failing PR, and require `PCS Public Full Verification / core-full-gate` in the `Protect PCS main` GitHub ruleset.
5. The inspected current GitHub ruleset already requires `Workers Builds: pcs-core-ci-only` rather than the legacy CircleCI no-op. Ensure that exact required Cloudflare check really executes and is green; if migrating to public GitHub Actions, require the verified new check **before** retiring Cloudflare. Preserve reviews, conversation resolution, signed release policy and no-bypass controls.
6. Freeze/review/tag the tested commit and publish bounded release notes. Monitor security, fork CI spend/abuse and contributor submissions without granting untrusted jobs secrets.

## What was actually checked on 2026-10-08

- The core and website GitHub repos are **both private**.
- Core `main` declares Apache-2.0 in `LICENSE` and `pyproject.toml`.
- Existing core release gate is HOLD; upstream academic/IP ownership has not been independently cleared.
- Live GitHub ruleset `Protect PCS main` ID 24471337 currently requires `Workers Builds: pcs-core-ci-only` (Cloudflare App 85455), not CircleCI. PR #74's separate `pcs-core-ci-gate` build was observed actively running; these check identities must not be conflated.
- Default-branch source search returned no literal `CLOUDFLARE_API_TOKEN` or `client_secret` matches, **not** a full-history all-secret scan. A current-tree filename audit found 459 tracked blobs, including public-source Iris/Indometh validation CSV fixtures; see `docs/PUBLIC_RELEASE_RIGHTS_LEDGER.md` for rights and attribution checks.
- Core PR #74 remained a draft requiring exact-SHA verification; PR #76 contains a public-only CI workflow but has not demonstrated a public full build.
- The Cloudflare CI trigger uses a build token also named for the website; shared credential scope must be audited/isolated. There is no current evidence that a public fork build can be trusted with it.
- No repository visibility change, credential rotation, legal approval, or release tag is asserted here.

**Stopping rule:** Any unknown on licensing, secrecy, scientific integrity, or untrusted CI access means STOP rather than “probably safe.”

## Preparation staged in draft PR #77

Full Apache-2.0 LICENSE text, NOTICE, SECURITY.md, CODE_OF_CONDUCT.md, proposed DCO guidance, local history preflight plus tests, this release ledger, `docs/PUBLIC_RELEASE_RIGHTS_LEDGER.md`, and reviewer quickstart are staged but not merged or validated on this exact branch. Public visibility remains HOLD.
