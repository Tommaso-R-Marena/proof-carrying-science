# Lean kernel status

## Current verdict

**MACHINE-CHECKED PASS — PCS DECISION AND NORMALIZED-STATE SOUNDNESS LAYER.**

Pinned toolchain: `leanprover/lean4:v4.28.0`.

The production-shaped PCS formal library was independently rebuilt on 2026-09-29 in verification-only mode. No Lean source, theorem statement, lakefile, or toolchain change was required.

Verified result:

- `lake build` exit code 0;
- 14 jobs built successfully;
- Lean 4.28.0, commit `7e01a1bf5c70`;
- no `sorry` or `admit`;
- no project `axiom`, `unsafe`, `implemented_by`, `extern`, or `native_decide` declaration;
- compiled scan of 641 `PCS.*` declarations found no axiom, unsafe declaration, or `sorry`;
- no `Aristotle` Lean library or namespace remains;
- no theorem statement weakening or extra precondition was introduced.

The promoted proof modules are ordinary PCS modules:

- `PCS.Normalization`;
- `PCS.DecisionExtraction`;
- `PCS.SerializedBridge`.

## Machine-checked theorem chain

The current verified layer establishes, for computational, formal, empirical, and mixed accepted statuses:

```text
normalized/replayed evidence
        +
ContextCovers Γ c
        +
RequiredEvidenceBound c es
        +
decideClaim c es = accepted(L)
        ↓
Assures Γ L c es
```

The extraction layer proves that accepted decisions have passed the required-evidence guards and contain witnesses of the required evidence class. The normalized-state bridge composes those results with explicit context and semantic binding carried by `Normalized.DecisionInput`.

## Axiom audit

The promoted direct soundness and normalized bridge theorems depend only on Lean's standard:

- `propext`;
- `Classical.choice`;
- `Quot.sound`.

Across all 38 audited theorems, no `sorryAx` or PCS-specific axiom appears; several audited theorems depend on no axioms at all.

See:

`results/PROMOTION_VERIFICATION_2026-09-29.md`

## Correct public claim

The precise current statement is:

> **The exact PCS v0.6/v2 package/archive assurance layer is machine-checked in Lean 4.28.0. For the Lean-authoritative path on canonical archives, the only remaining hypothesis is Ed25519 unforgeability for the trust anchor (`PCS.V2.Frontier.pcs_frontier_archive_acceptance_sound`). SHA-256 is proved equal to an independent FIPS 180-4 specification; `reaction_balance`, `unit_compatible`, `csv_disjoint`, `pkpd_contract` and `pkpd_reference_match` are replayed by proved Lean checkers inside the authority, and a PK/PD PASS has a proved real-valued meaning (`PCSReal.PKPD.pcs_pkpd_reference_match_real`).**

Still not claimed: an RFC 8032 proof of the Lean Ed25519 verifier, Ed25519 unforgeability,
SHA-512 specification equivalence, a verified workflow front end or environment capture
beyond `EnvFacts`, verification of external validators, or any empirical/clinical adequacy.
See `formal/PCS_FRONTIER_FORMALIZATION_REPORT.md`.

Do not state that every production/runtime/cryptographic component is unconditionally formally verified end-to-end.

## Remaining formal boundary

> Superseded in part by the frontier passes — see `formal/PCS_FRONTIER_FORMALIZATION_REPORT.md`
> §3–§4 for the current list. The items below are the baseline boundary; SHA-256, the
> `unit_compatible`/`csv_disjoint`/PK/PD replays and the canonical-ZIP decoder are now
> proved, and capture/workflow are narrowed.

The representation bridge is now integrated. The remaining named boundaries are:

- authoritative production validity is now gated on compiled Lean acceptance; the whole-Python-semantics equivalence problem is therefore avoided rather than claimed proved. The remaining operational bridge is the faithful handoff from Python ZIP decoding/materialization/process invocation to the exact member bytes Lean checks;
- raw ZIP bytes -> semantic archive members (`ZipDecoderFaithful`);
- environment-capture rules -> `Describes` (`CaptureSound`);
- replay faithfulness for `unit_compatible`, `csv_disjoint`, PK/PD checks, and external validators;
- independent SHA-256 and Ed25519 specification-equivalence proofs;
- Ed25519 unforgeability for the trusted key;
- formal numerical semantics for the floating-point PK/PD path;
- empirical adequacy, clinical validity, or regulatory acceptance of scientific models.

The current high-assurance chain is:

```text
raw archive bytes
   ↓ Python ZIP decoder                 explicit contract
decoded archive members
   ↓ exact isolated handoff to Lean    production gate; invocation/materialization TCB
   ↓ archive partition / signed set    machine-checked
canonical certificate/package/index
   ↓ hashes + signatures + replay      machine-checked wiring;
                                       explicit crypto/replay contracts where noted
normalized v0.6/v2 decisions
   ↓
ScientificAssurance / scoped Assures   machine-checked
```

The production gate also emits the SHA-256 of the authority executable and the
canonical observation transcript into the verification result/receipt. A missing,
crashing, malformed, or rejecting authority cannot yield authoritative PCS validity.

For the exact theorem statements and TCB inventory, see `formal/PCS_FULL_FORMALIZATION_REPORT.md`.

## Reproduction gate

From repository root:

```bash
./scripts/verify_lean.sh
./scripts/verify_lean_real.sh   # Mathlib real-analysis bridge (PK/PD real-valued theorem)
```

The script now uses token-safe grep patterns and rejects placeholders plus project-level `axiom`, `unsafe`, `implemented_by`, `extern`, and `native_decide` declarations.
