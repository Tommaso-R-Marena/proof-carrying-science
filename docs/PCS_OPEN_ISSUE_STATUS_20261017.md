# Open-issue and pull-request reconciliation — 2026-10-17

The inspected protected sources were core `68d8351a326565496908bf76c8a8daf082b94ff9`, website `a6a9a54bb8f2e8fb45f783a9df56929aca11a54b`, and CertiForge `c71e8575db2800b015a9d444f8ed572490f3a871`. This is a status reconciliation, not legal clearance, an external review, or a scientific acceptance record.

## Pull requests

Core dependency PRs #110–#114 update download-artifact to 8.0.2, upload-artifact to 7.0.2, lean-action to 1.6.2 and both CodeQL actions to 4.38.3. Their five patches are consolidated so matching CodeQL initialization and analysis revisions qualify together. Every action remains pinned to a complete commit SHA. Existing job identities, permissions, conditions, evidence uploads and protected verification obligations are preserved. Close the superseded PRs only after this combined change passes the required checks and merges.

Research PR #117 remains a draft. Its branch is independently evolving and is not part of this dependency update. Its finite-corpus improvement and out-of-corpus counterexample do not establish general self-improvement or production authority. Research results from that unmerged branch must not be presented as protected-main capabilities on the website. Independent review and the PR's documented trust-boundary gates remain outstanding.

There were no open CertiForge PRs/issues or website PRs at the initial audit.

## Every open issue

| Repository / issue | Existing implementation and current disposition | Remaining acceptance evidence |
| --- | --- | --- |
| Core #9, external-pilot operations | `SIGNING_KEY_CUSTODY.md`, `pilot_key_lifecycle.py`, `PILOT_CLOSEOUT.md` and `pilot_closeout.py` already implement public-key lifecycle records and hash-bound local retention/deletion. Retain these controls and their adversarial tests. | Actual custody/recovery drill and partner-specific retention execution; counsel-reviewed terms; entity/payment path; a genuine external workflow. Registry declarations are not proof of hardware custody or backup recovery. |
| Core #11, third-party and historical disclosure | Apache-2.0 first-party publication was already authorized. Keep dependency/license inventories, source attribution and the newly integrated CC BY 4.0 yacht data license. `public_release_history_audit.py` redacts heuristic findings and explicitly flags uninspected binaries. | Contributor/third-party rights adjudication, historical archive/log inspection and qualified legal review. A scanner pass cannot establish these. |
| Core #13, external design-partner workflow | Intake locks, typed packages, independent replay, reviewer policies and receipts are implemented. The archived yacht experiment is a developer-run research analysis, not an external partner exercise. | An actual external partner's prospectively frozen claims, delivery, second-environment reviewer replay and feedback. Do not substitute a synthetic partner or an agent-generated review. |
| Core #14, paid pilot | Existing technical delivery machinery and explicit limitations remain available. | #9, #11 and #13 evidence plus counsel-reviewed commercial scope and an established entity/payment route. No engagement or payment is fabricated by this release. |
| Website #93, legacy D1 ledger | The live schema can be inspected without replaying historical SQL. The ledger records actual 0024/0025 executions; unrecorded legacy schema is not relabeled as historical execution. Future-migration tooling belongs in the website repository. | A reviewed production data-effects baseline and demonstrated forward migration path preserving accounts, tasks, research and immutable audit state. Schema-only recovery is insufficient to close this issue. |
| Website #2, domain/governance | Public source visibility and the existing canonical Workers hostname are already explicit. Keep canonical, security, contact and indexing metadata consistent. | Owner domain/contact/branding decision, naming/trademark review and corresponding privacy/indexing review. No domain purchase or invented legal approval. |

All six issues retain their unmet acceptance criteria. Updating evidence and implementing available engineering work does not justify closing external or legal prerequisites. Website synchronization and deployment evidence are tracked separately in that repository and the integration PRs.
