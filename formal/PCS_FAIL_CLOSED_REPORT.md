# PCS: fail-closed authority for unregistered check types

This report covers the change that makes `pcs-lean-authority` **fail closed**. Before the
change, an evidence item whose `check_spec.type` was not handled by a verified built-in or a
registered domain checker had its replay outcome taken from the transcript
(`observations.json`). A correctly signed archive whose AI-safety claim was false of its own
committed trace was therefore printed as `ACCEPT` (formerly `GoldenCx.cx_accepts`).

Recoverable checkpoint of the state before the change: git tag
`checkpoint-before-failclosed-unregistered-tags` and branch `checkpoint/pre-failclosed`
(commit `93e7d8b`).

## 1. What changed in the executable

The pure decision functions run by the binary (`executableAuthority` for `--zip`,
`executableAuthorityEntries` for directory mode, and the CLI wrappers `zipModeOutput` and
`dirModeOutput`) now evaluate the strict diagnostic `diagnosePCSStrictWith`
(`PCS/V2/FailClosedGate.lean`), with:

* replay executor `dispatch (builtinCheckers ++ certifiedRegistry) failClosedExec`. The
  fallback `failClosedExec` is the **constant `FAIL`**, so the transcript is never consulted
  for a replay outcome;
* a **check-type gate** `supportedEvidenceB`. *Every* evidence item of the certificate (not
  only the required ones) must be handled by a verified built-in or a registered checker. The
  gate runs **before** replay, so unsupported evidence is never replayed. Failure gives stage
  `unsupported_check_type`;
* a **claim-binding gate** `claimsBoundB productionBinders`. Every claim recorded at an
  assurance level (`supportive`: FORMALLY_PROVEN / COMPUTATIONALLY_SUPPORTED /
  EMPIRICALLY_SUPPORTED / MIXED_SUPPORTED) whose predicate decodes as an AI-safety trace claim
  or a biology residue-site claim must pass `domainAccepts` over a canonical obligation graph
  (`aiGraph` / `bioGraph`). That graph is built from the claim's **own required evidence**,
  checked by `checkGraph`. Failure gives stage `claim_binding`.

Stage order: `package` → `certificate_model` → `environment` → `workflow` → `artifact_table` →
**`unsupported_check_type`** → `replay` → `normalized_set` → `normalized` →
**`claim_binding`** → `transcript_binding` → `ACCEPT`.

The four layers stay separate, and each has its own theorem:

| layer | meaning | theorem |
|---|---|---|
| signature-valid / package-valid | both Ed25519 signatures, manifest and digests verify | `GoldenCx.cx_package_valid` (holds for the rejected counterexample) |
| computational verification | every evidence outcome comes from a certified checker | `executableAuthority_evidence_certified` |
| scientifically supported claim | supported AI/bio claims hold of the committed bytes | `executableAuthority_supported_claims_sound` |
| rejection | unregistered type, or false supported claim, gives no ACCEPT | `*_rejects_unregistered_type`, `*_rejects_false_supported_ai_claim` |

## 2. Inputs that now fail, and why

| input | old verdict | new verdict | reason |
|---|---|---|---|
| signed archive, evidence with unregistered type (e.g. `trace_invariant_v2`), transcript says PASS (`fixtures/ai_safety_counterexample`, campaign `m7`) | ACCEPT | `REJECT:unsupported_check_type` | check-type gate |
| same, but the trace is *safe* (`fixtures/failclosed_unknown_type_safe_trace`) | ACCEPT | `REJECT:unsupported_check_type` | gate is independent of outcome and truth |
| evidence with **no** `check_spec.type` (`fixtures/failclosed_missing_type`, `m7b`) | ACCEPT | `REJECT:unsupported_check_type` | missing type = unregistered |
| valid claim plus an extra **unrequired** evidence item of type `external_python` (`fixtures/failclosed_unrequired_unknown_evidence`, `m7c`) | ACCEPT | `REJECT:unsupported_check_type` | gate covers all evidence, not only required evidence |
| supported AI claim with budget 2 backed by registered `trace_invariant` evidence certifying budget 4; trace has 3 steps (`fixtures/failclosed_claim_binding_mismatch`, `m15`) | ACCEPT | `REJECT:claim_binding` | claim not bound by its own certified evidence |

Backward-compatibility loss: archives that use any check type outside the nine registered ones
(`reaction_balance`, `unit_compatible`, `csv_disjoint`, `pkpd_contract`,
`pkpd_reference_match`, `pkpd_peak_concentration_threshold`, `residue_bounds`,
`hydrophobic_score`, `trace_invariant`; `executableTypes_eq`) are nowM�^z�!j�