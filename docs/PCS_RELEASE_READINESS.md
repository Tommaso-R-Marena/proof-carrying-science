# PCS research-platform release readiness

This record separates local implementation, independent mathematical checking, protected provider CI and actual live deployment. It does not authorize release or scientific acceptance.

## Current source identity

Starting core: `e1067e406a1a1991497e7130e1f209239e5607cc`. Starting website: `1a351144cac080a990ab6f75fe8b57b476c3b08a`. CertiForge: `415a1de40eaeadc366ac2d824c05ee52bb2bd66e`. New local changes are not yet a protected immutable release. Exact feature commits, qualified CI revisions and deployed website/core bindings must be filled from provider-generated evidence after integration; historical starting SHA is not a claim that new features were deployed at that SHA.

## Verified and tested scope

Historical proof/search/model artifacts retain their original SHA-256 seals and limitations. Current formal audit evidence distinguishes cached default/extended Lean builds, freshly audited source windows, individual new source-correspondence proofs and bounded differential tests. A proof about a Lean reference model is never presented as Python or JavaScript refinement unless that actual correspondence is proved.

New qualification tooling binds source bytes, lockfiles, fixed commands and result logs. Missing required local gates, failed results and drift veto full local qualification. Independently rerunning its reviewed recipes establishes only local execution. Arbitrary caller JSON, self-reported neural metrics, forged log success strings and provider-status fields never supply production authority.

New workstream tests and experiment reports are reported independently. The Rust checked-entry guard preserves the exact extracted low-level eval_expr source and rejects noncanonical caller-built stores at the new boundary; CertiForge PR #3 passed the protected rust-and-lean gate and merged as `c71e8575db2800b015a9d444f8ed572490f3a871` with an identical tested tree and no new universal wrapper correspondence theorem is asserted. The expanded 1,618-case differential campaign is archival evidence at the original CertiForge revision, not post-guard release qualification. Synthetic contributor/account/D1/browser fixtures validate infrastructure only. They establish neither genuine human participation nor independent external researcher acceptance. Experimental policies have no signing authority and do not receive automatic promotion.

## Release vetoes and pending evidence

- Protected CI for release core fd4ddaf and website 72a47c9: **passed**, respectively runs 38312790669 and 38319164005. New continuation changes remain separately unqualified until their own gates pass.
- Cross-repository compatibility: **tested**, pinned CertiForge c71e857 and protected core fd4ddaf.
- Live deployment: Cloudflare build ed195caf-8037-40dc-a51c-5b4b06322b0b succeeded at 72a47c9; ten live asset hashes match, source-bound public proof and fresh local replay succeeded.
- Actual remote D1 reconciliation, backup restoration or destructive schema migration: **not performed**. The new job journal uses existing audit infrastructure and does not require a new D1 schema.
- Independent external scientific review: **not performed**.
- Complete transitive source/dataset/institutional rights clearance: **not inferred**. The technical rights inventory identifies evidence and unresolved questions; existing first-party licensing is preserved.
- Whole-runtime Python/JavaScript conditional refinement, full Rust top-level interpreter refinement and unrestricted English semantic fidelity: **open research obligations**.
- Demonstrated new held-out neural or RL improvement: only actual frozen experimental evidence may update this item; no advance superiority claim.

Any failed critical check vetoes release. Local dry-run success is not deployment success. An owner-controlled hosted qualification matrix remains distinct from ten public admissions; existing 2/IP/day and 12/global public quotas must not be bypassed.

## Financial, security and production boundaries

No paid resources or financial information are permitted. Existing public CI and local CPU are used with bounded budgets. Keys and personal data are excluded from public qualification artifacts. Privileged provider credentials remain outside untrusted proposal processes. No untrusted PR obtains production or training-service secrets. No branch protection is bypassed.

Model training may consume only explicitly authorized, independently checked data with its provenance and split retained. Withdrawal records quarantine descendants and state the limitations of already distributed offline exports or checkpoints. Signing-key custody and operational incident response remain separate owner-controlled responsibilities.

## Reproduction and evidence

See `PCS_RESEARCH_PLATFORM_TECHNICAL_REPORT.md`, the full 59-item ledger, and each workstream report. Run:

```bash
python -m pcs.release_qualification_v1 run --output /tmp/pcs-final-local-qualification
python -m pcs.release_qualification_v1 verify /tmp/pcs-final-local-qualification/qualification.json --replay-output /tmp/pcs-independent-local-qualification
```

These commands produce inspectable local evidence; they cannot authorize deployment. Final release evidence must identify exact tested source trees, all protected required checks, authorized merger identity, provider deployment identity and byte-bound live assets. Root integration updates the pending fields only after those results actually exist.
