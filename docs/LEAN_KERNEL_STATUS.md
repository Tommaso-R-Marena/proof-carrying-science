# Lean kernel status

## Current verdict

**ARISTOTLE RETURNED A CLEAN MACHINE-CHECKED PROOF SET; PCS-NAMESPACE PROMOTION AWAITS ONE FINAL REBUILD.**

Pinned toolchain: `leanprover/lean4:v4.28.0`.

On 2026-09-29, the frozen Aristotle handoff built successfully under Lean 4.28.0 with the designated normalization, decision-extraction, direct soundness, and normalized-state bridge proofs closed. The returned project reported:

- `lake build` exit code 0;
- 15 jobs built successfully;
- no `sorry` or `admit`;
- no `sorryAx`;
- no project-specific axioms;
- no theorem statement weakening or added preconditions.

The returned staged proof modules have now been promoted, without changing theorem statements or proof bodies, into:

- `PCS.Normalization`;
- `PCS.DecisionExtraction`;
- `PCS.SerializedBridge`.

The old `Aristotle/*` staging modules are removed on the promotion branch. Because this environment does not contain Lean, the namespace-promoted branch must receive one final independent `lake build` before merge.

## Machine-checked result already established in the returned project

The Aristotle-built project machine-checked the following substantive chain:

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

for computational, formal, empirical, and mixed accepted statuses.

The extraction layer proves that any accepted decision has passed the required-evidence guards and exposes evidence witnesses of the correct class. The normalized-state bridge then composes those theorems with the explicit context and semantic-binding fields carried by `Normalized.DecisionInput`.

## Standard Lean dependencies

The returned `#print axioms` audit reported only standard Lean foundations where used:

- no axioms for the basic PCS kernel/context/PKPD facts;
- `propext` for some Boolean-to-Proposition soundness helpers;
- `propext` and `Quot.sound` for refinement/list membership lemmas;
- `propext`, `Quot.sound`, and `Classical.choice` for the whole-claim extraction/soundness and normalized bridge.

No `sorryAx` and no PCS-specific axiom appeared.

## What is still open

The formal result is not yet end-to-end serialized-package verification. Still open:

- raw PCS JSON/ZIP bytes -> parsed/schema-valid Lean-level representation;
- executable Python parser/replay/refinement -> `Normalized.DecisionInput`;
- Python implementation refinement to the Lean decision function beyond frozen decision vectors;
- formal real-analysis/numerical semantics for PK exponential/Emax evaluation;
- empirical adequacy or clinical validity of any PK/PD model.

The correct current claim after the promotion branch independently rebuilds is:

> The PCS assurance decision and normalized-state soundness layer is machine-checked in Lean 4.28.0.

Do not claim that the complete Python product or scientific model validity is formally verified end-to-end.

## Final promotion reproduction

From the repository root on branch `formal/aristotle-proof-promotion-2026-09-29`:

```bash
./scripts/verify_lean.sh
```

A successful run is required before merging the promotion branch.
