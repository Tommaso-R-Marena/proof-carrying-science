# Aristotle semantic integration ledger

The supplied latest Aristotle archive is integrated into the PCS formal workspace.
See PUBLIC_INTEGRATION_2026-10-08.md and ARISTOTLE_SOURCE_IMPORT_MANIFEST.json
for source provenance, actual checks, scope and deployment assumptions.

V1/v2 provide canonical structured interpretation, explanations, bounded
countermodel/equivalence search and composition. V3 adds signed role-separated
receipts, elaboration/proof requirements, revocation, expiration and single-use
ledger semantics. Translation and strengthening have distinct outcomes. Actual
issuer tools check elaboration and replay declarations through the Lean kernel
before signing. These tools are not a sandbox for arbitrary Lean/meta code.

`pcs semantic-authority-v3 --help` documents the persistent PCS integration.
The host approves exact checker/configuration/ClaimIR-binding hashes; the existing
scoped SQLite store and host clock control the decision. Known public fixture
keys are rejected by default. Certification is reported only after COMMIT.
The v1 bridge remains stateless and nonproduction. Both interfaces always report
`pcs_scientific_authority: false`; they do not prove human intent or empirical truth.

Public CI builds the actual executable and runs all v1/v2/v3 fixture suites,
the v3 audit, imported Python tests, PCS tests and the 36-case compiled bridge.
Missing source fails closed. Skipped checks are not validation. Live website
submissions still require an isolated issuer service and protected role keys.
Machine-generated training fixtures do not establish independent human supervision
or held-out generalization.
