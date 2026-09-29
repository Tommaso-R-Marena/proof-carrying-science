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

> **The PCS assurance decision and normalized-state soundness layer is machine-checked in Lean 4.28.0.**

Do not state that the complete PCS product is formally verified end-to-end.

## Remaining formal boundary

Still open:

- raw PCS JSON/ZIP bytes -> parsed/schema-valid Lean-level representation;
- executable Python parser/replay/refinement -> `Normalized.DecisionInput`;
- Python implementation refinement to the Lean decision function beyond frozen cross-language decision vectors;
- formal real-analysis/numerical semantics for PK exponential/Emax evaluation;
- empirical adequacy, clinical validity, or regulatory acceptance of scientific models.

The next major theorem program is the serialized-package/executable-refinement bridge:

```text
raw package
   ↓
strict parse + schema + artifact/replay checks
   ↓
Normalized.DecisionInput
   ↓
machine-checked decision soundness
   ↓
Γ ; E ⊢ C @ L
```

## Reproduction gate

From repository root:

```bash
./scripts/verify_lean.sh
```

The script now uses token-safe grep patterns and rejects placeholders plus project-level `axiom`, `unsafe`, `implemented_by`, `extern`, and `native_decide` declarations.
