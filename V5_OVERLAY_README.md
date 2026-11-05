# PCS V5 independent integration overlay

This overlay is **not** a standalone repository and is **not** a proven deployable runtime.
It is intended to be applied to a fresh branch based on
`research/proof-gated-self-improvement-v1-20261016` and kept in a **draft** stacked PR.
The authority migration in `formal/PCS/V2/ProofGatedArtifacts.lean` is intentional.

Verified upstream release: `b5ec1c476666feb3b13d72f78227a87f688f5868e75cc87f8269e75e33015d79`
(the inner `dist/pcs_proof_gated_v5.tar.gz` of the user-provided outer attachment).
The upstream 472-file manifest is complete; do **not** copy the stale outer snapshot.

The overlay excludes four original modules which match the PR #117 Git blobs
exactly: ProofGatedMultilayer.lean, ProofGatedPromotion.lean, ProofGatedSelfImprovement.lean, ProofGatedSymbolic.lean.
The original modules intentionally modified by the V5 snapshot are:
ProofGatedArtifacts.lean, ProofGatedAudit.lean, ProofGatedInference.lean.
All remaining `ProofGated*.lean` modules are new additions to that branch.

## Apply safely

1. Create a new research branch from the exact PR #117 head; do not work in main.
2. Extract this zip into the **repository root** with overwrite only on that research branch.
3. Run `python research/proof-gated-self-improvement-v1/v5_fixture_differential.py`.
4. Run `source scripts/activate_lean_428.sh; cd formal; bash scripts/proof_gated_ci.sh`.
5. Run all existing PR #117 tests and real-Lean model promotions.
6. Verify CI (provided workflow `.github/workflows/pcs-proof-gated-v5-integration.yml`), then review the codec behavior migration and keep the PR draft.
7. Do not assume the Lean proofs establish OS, SHA-256, Python, file ownership, or production process isolation.

**Important:** the official inner `PROOF_GATED_MANIFEST.json` and `PROOF_GATED_SHA256SUMS`
are *not* included in this overlay. They describe Aristotle's standalone formal tree,
not the combined PCS repository; shipping them in the overlay would create misleading
attestations. The original source archive retains them for independent inspection.
This overlay has its **own** per-file SHA-256 manifest instead.

## Independent verification already performed

- Inner archive: 472/472 correct exact files, SHA-256 manifest 470/470 matches.
- PGSI1 reference fixture checks: 8,450 valid and 28 negative inputs.
- Exact worst-case error fixture checks: 311 cases.
- Three-way strong gate fixture checks: 11 cases.
- No new Lean kernel checks were run locally; GitHub Actions are required.
