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
`hydrophobic_score`, `trace_invariant`; `executableTypes_eq`) are now rejected, even when the
claim does not depend on that evidence. A new type is supported only by registering a
certified checker for it.

Unchanged: golden ACCEPT (both modes), tampered `REJECT:package`, insider `REJECT:replay`.

## 3. Kernel-checked theorems (no `sorry`, no `native_decide`)

All of these are about the actual pure decision functions, for **all** archive bytes,
transcripts, keys and fingerprint pins. Files: `PCS/V2/ExecutableFailClosed.lean`,
`PCS/V2/FailClosedProofs.lean`, `PCS/V2/GoldenCx/Counterexample.lean`,
`PCS/V2/Golden/FailClosedFixtures.lean`, `PCS/V2/Golden/Acceptance.lean`.

### Rejection
```lean
theorem executableAuthority_rejects_unregistered_type {raw es inp c m}
    (hz : decodeZip raw = some es) (hi : fromArchiveEntries es = some inp)
    (hc : verifyCertBytes inp.certificateBytes = some c) (hm : decodeCertModel c = some m)
    {e : CertEvidence} (he : e ∈ m.evidence)
    (hty : ∀ ty ∈ executableTypes, checkTypeOf e.json ≠ some ty)
    (t : AuthorityTranscript) (T : TrustAnchor) : executableAuthority t T raw ≠ "ACCEPT"
```
The same holds for `executableAuthorityEntries_rejects_unregistered_type` (directory mode), for
`zipModeOutput_rejects_unregistered_type` and `dirModeOutput_rejects_unregistered_type` (CLI:
every transcript file, key string, pin), and for `certifiedPCS_rejects_unregistered_type`
(package level). The hypotheses only describe how the input bytes parse; none of them mentions
signatures, outcomes, claims or the transcript.

`executableAuthority_rejects_false_supported_ai_claim` (and the `Entries` form): if a
supported claim decodes to a trace claim and some trace of it is unsafe in every delivered
file the artifact points to, the verdict is not ACCEPT, for every transcript and anchor.

Concrete fixtures: `cx_rejected`, `cx_entries_rejected`, `cx_cli_rejected`,
`cx_certifiedPCS_none`, and `cx_signed_but_rejected` (package-valid **and** accepted by the
legacy authority **and** rejected by the executable). Also
`m7/m7b/m7c/m15_rejected_zip` and `_rejected_entries`, which hold for every signature
pair, transcript and trust anchor.

### Acceptance
* `executableAuthority_evidence_certified`: on ACCEPT, every evidence item has a registered
  type. Some certified checker `k` handles its request, the executable's own executor returns
  exactly `k.run`, and a recorded PASS carries `k.Holds`.
* `executableAuthority_supported_claims_sound`: on ACCEPT, every supported claim decoding as
  an AI-safety claim satisfies `aiDomain.Holds r.table`, and every one decoding as a biology
  claim satisfies `bioDomain.Holds r.table`. This uses **no** externally supplied graph, no
  `NoForgery`, and no transcript assumption.
* `acceptPCSStrictWith_fallback_irrelevant` / `acceptArchiveStrictWith_fallback_irrelevant`:
  the strict verdict is identical for every fallback executor. In particular the
  transcript-fallback form `certifiedAuthority` and the constant-FAIL form used by the binary
  agree, so the transcript cannot influence replay on any input.
* `executableAuthority_refines_certifiedAuthority` (and `Entries`): ACCEPT iff the certified
  strict authority returns a result (re-proved).
* Golden: `supportedEvidence_golden`, `claimsBound_golden`, `certifiedPCS_golden`,
  `certifiedAuthority_golden`, `aiSafetyGoldenArchive_accepts`,
  `aiSafetyGoldenArchive_entries_accepts` (golden still ACCEPT, kernel-checked).

### Legacy analysis objects (kept, not run by the binary)
* `legacyAuthority_cx`: the old transcript-fallback authority `acceptArchiveWithCheckers`
  accepts the counterexample bytes.
* `legacy_no_unconditional_claim_bridge`: for that legacy authority, no unconditional
  claim-level soundness statement holds.
* `executableAuthorityWith_nil` is now only one-directional (strict ACCEPT ⇒ old ACCEPT). The
  converse is false, and the counterexample is the witness. `executableAuthorityEntriesWith_nil`
  was removed.

## 4. Other fallback / default-accept paths investigated

* **Unrequired evidence**: previously ignored by claim decisions, so any type was allowed.
  It is now covered by the check-type gate (`m7c`).
* **Claim aggregation**: a claim's recorded status was accepted once its required evidence
  replayed, without checking that the evidence certifies *that* claim's proposition (wrong
  parameters, as in `m15`). This is now covered for AI/bio predicates by the claim-binding gate.
* **Directory vs ZIP mode**: both modes go through the same `diagnosePCSStrictWith`. The
  command-line directory-mode wrapper is connected to the decision function by
  `dirModeOutput_accept`.
* **Checker registry**: duplicate tags or shadowing a built-in were already fail-closed
  (`buildRegistry_dup_none`, `buildRegistry_builtin_none`). This is unchanged.

## 5. Remaining trust and limits (what is *not* proved)

* The compiled binary, the Lean compiler/runtime, ZIP/file IO and argument parsing are
  trusted. The fixture runs in `tools/run_fixture_tests.sh` are tests, not proofs.
* The transcript is still used for the **workflow** and **environment-capture** oracles and
  for the `transcript_binding` stage. It no longer affects replay outcomes.
* Claims whose predicates decode in neither registered domain (for example PK/PD, chemistry
  or opaque predicates) carry only the evidence-level guarantee: their evidence was certified
  and passed. No semantic claim-level statement is proved for them.
* Claims that are not supportive (rejected/unsupported statuses) are not bound. They assert
  nothing.
* The supported-claim theorems are statements about the committed artifact bytes. Transfer to
  the deployed external world still needs the separate hypotheses of
  `archive_external_world_transfer_sound`.
* The earlier generic theorems (`domain_adapter_sound`, `root_assurance_sound`,
  `untrusted_proposer_cannot_forge_assurance`, `pipeline_refines`, the frontier theorem) are
  unchanged and still proved.

## 6. Commands and results

```
lake build                                              # Build completed successfully (255 jobs)
lake env lean --run tools/WriteGeneralFixtures.lean     # writes archive.zip + package/ per fixture
bash tools/run_fixture_tests.sh                         # 14/14 ok, exit 0
lake env lean --run tools/CheckGoldenFileLiterals.lean  # OK (golden files match kernel literals)
rg -n "^\s*(axiom|unsafe|@\[extern|@\[implemented_by)|\bsorry\b|\badmit\b|native_decide" PCS PCSAuthority.lean tools
    # only comments and the pre-existing function `DistributedContributors.admit`
```
Axiom audit (`PCS/V2/FailClosedAudit.lean`, printed during `lake build`): every listed theorem
depends only on `propext`, `Classical.choice`, `Quot.sound`. There is no `sorryAx` and no
`Lean.ofReduceBool`.

`tools/run_fixture_tests.sh` output:
```
ok   ai_safety_golden [zip] ACCEPT
ok   ai_safety_golden [dir] ACCEPT
ok   ai_safety_tampered [zip] REJECT:package
ok   ai_safety_insider [zip] REJECT:replay
ok   ai_safety_counterexample [zip|dir] REJECT:unsupported_check_type
ok   failclosed_unknown_type_safe_trace [zip|dir] REJECT:unsupported_check_type
ok   failclosed_missing_type [zip|dir] REJECT:unsupported_check_type
ok   failclosed_unrequired_unknown_evidence [zip|dir] REJECT:unsupported_check_type
ok   failclosed_claim_binding_mismatch [zip|dir] REJECT:claim_binding
```
