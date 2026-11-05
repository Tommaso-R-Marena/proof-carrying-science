# Security and rights checkpoint — 2026-10-08

**Public follow-up, 2026-10-08:** The owner made all three repositories public and explicitly confirmed complete first-party ownership and publication authority. See PUBLIC_INTEGRATION_2026-10-08.md. Private-status/missing-owner-decision statements below are historical and superseded. Third-party license obligations and actual technical gates remain distinct.

Release state: **HOLD**. This document does not authorize visibility changes or certify ownership.

## Verified local work

All advertised heads, tags and PR-head refs were fetched. Gitleaks 8.24.3 was installed from the official archive with its published checksum and run over all reachable Git history with complete redaction. An independent history preflight inspected reachable Git objects and explicitly flagged undecoded binary content. Core had 6 Gitleaks candidates and 134 independent candidates (81 binary/unknown-encoding blobs and 53 private-key-header markers); website had 8 and 19 (1 binary and 18 markers); CertiForge had none from either method. Candidate categories include secret-rejection literals, synthetic fixtures and publicly served IndexNow ownership keys. Those observations are not a completed adjudication or evidence of credential revocation. Raw matches remain outside the source repositories.

REST inventories include every paginated PR, branch, issue/comment surface, workflow run, available artifact and release exposed by current permissions. Metadata scanning found zero Gitleaks candidates. At inventory time there were 1,347 core runs, 1,283 website runs, 7 CertiForge runs and 387 unexpired core artifacts totaling 3,256,879,455 bytes. Logs and artifact payload probes were blocked at `results-receiver.actions.githubusercontent.com` and `productionresultssa2.blob.core.windows.net`; these host additions are saved in the environment draft. Metadata coverage does not mean payload coverage. Review bodies, binary/encoded history, external CI/Cloudflare logs, caches and inaccessible deployment data remain unresolved disclosure surfaces.

Python's hash-pinned development/build dependency sets, the Node lockfile and the Rust lockfile were scanned with pip-audit, npm audit and cargo-audit respectively. No known advisory was reported at this run. Wrangler was updated to 4.149.0 to remove the inherited vulnerable sharp dependency. No scanner result establishes absence of undiscovered vulnerabilities.

Untrusted PR source can no longer run through the legacy self-hosted job conditions: these require a private repository, protected ref and a non-PR event. Public verification workflows use read-only permissions, immutable action revisions and credential-free checkout. Frozen dependency installation and a checksum-pinned Lean installer are implemented. Existing required Cloudflare checks have not been weakened. No remote workflow execution, token-scope isolation or provider rotation is asserted by source changes.

## Credentials and administration

All repositories are observed PRIVATE. GitHub metadata advertises admin/push permission, while Actions-administration, branch-protection detail and deployment operations have incomplete or denied access. The current core ruleset requires `Workers Builds: pcs-core-ci-only`; it has zero required approving reviews and no bypass actors. Website and CertiForge lack observed rulesets/protected branches. GitHub Actions secret metadata returned empty lists; this says nothing about Cloudflare Builds tokens, provider secrets, historical credentials or external secret stores.

The reported shared Cloudflare build-token risk remains OPEN. Provider access is not established, so no credential was revoked, rotated, scoped or tested invalid. Do not expose core PR builds to website/deploy privileges. Required owner action: identify the provider token, inspect effective scope, create separate least-privilege CI and deployment identities, rotate the old identity, update protected references and verify the old token is invalid. No secret values should be sent in chat.

## Rights and publication quarantine

Every source repository stays private while rights are unresolved. This is the publication quarantine; source is retained for review. The existing ledger's founder ownership assertion is historical repository evidence, not independent institutional/contributor clearance and not blanket clearance for CertiForge or website assets.

| Scope | Evidence prepared | Release decision |
|---|---|---|
| PCS Python, formal source, adapters and research prose | Exact ref inventory, commit provenance, Apache-2.0 metadata and NOTICE | OPEN: founder plus any university/employer/grant/collaborator or patent rights |
| CertiForge implementation, formal source and experiments | Separate private source, exact revisions, license declarations, no copied internals | OPEN: separate owner/institution and unpublished-research clearance; stays private |
| Website source, logo/figures and account/research backend | Apache-2.0 license intent, NOTICE, dependency declarations, privacy updates | OPEN: separate website publication decision and asset provenance |
| Iris/Indometh and other datasets | Existing source citations and derivative-source records | OPEN: exact redistribution and attribution obligations |
| Consented replays and learned model artifacts | Backend opt-in/replay/export/deletion controls and existing synthetic-model provenance | OPEN: per-artifact data/model rights and research-consent review; no private user data imported into this campaign |
| Third-party distributions | Per-repository declared-license manifests | OPEN: inspect actual redistributions and source/NOTICE obligations |

Apache-2.0 is the preferred licensing architecture, including website source intent; paid hosting, deployments, integrations and support remain possible. Adding a license is not a rights-holder certification. DCO guidance is prospective and makes no retroactive claim about existing contributors or AI output. No noncommercial restriction, nonprofit status or tax-deductibility is asserted.

Before publication, record affected commit/tree/blob identities, the actual rights holder, basis and scope of permission, any institutional or patent review, reviewer and date. Counsel/technology transfer must resolve ambiguous ownership. A founder's approval cannot substitute for another rights holder's permission. See PUBLIC_RELEASE_RIGHTS_LEDGER.md and the constituent/publication firewall documents.
