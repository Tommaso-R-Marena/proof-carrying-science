# Ready-to-run Aristotle project prompt

PCS is pinned to:

```text
leanprover/lean4:v4.28.0
```

This matches the most recent directly observed Aristotle backend default located during the 2026-09-28 audit. If Aristotle itself rewrites the project to a newer toolchain, preserve the output header and report the new version so PCS can be repinned deliberately.

## Recommended first run

From the repository root, submit the `formal/` project to Aristotle with instructions equivalent to:

```text
Work only inside this Lean project.

Target Lean 4.28.0.

First run lake build and repair any elaboration/compatibility errors in the existing no-sorry PCS core without weakening the intended assurance semantics.

Then solve every sorry in:
  Aristotle/Normalization.lean
  Aristotle/DecisionExtraction.lean
  Aristotle/SerializedBridge.lean

Preserve theorem statements unless they are actually ill-typed. If you believe a theorem is false, do not weaken it silently: explain the counterexample or missing precondition and make the smallest semantically justified correction.

Do not introduce:
  axiom declarations,
  admit,
  sorry,
  unsafe proof shortcuts,
  or new nonstandard axioms.

The intended logical judgment is:
  Γ ; E ⊢ C @ L
represented by Assures Γ L C E.

Important semantic rule:
a computational claim may be supported by either computationalTest evidence or stronger formalProof evidence.

Keep scientific replay/domain-checker soundness separate from the pure decision theorem. The decision theorem may assume RequiredEvidenceBound and ContextCovers.

After solving the files, run:
  lake build

and audit:
  grep -R --line-number --fixed-strings 'sorry' PCS.lean PCS Aristotle

Return all modified Lean files plus the exact Lean version and build result.
```

## Suggested CLI shape

Current Aristotle SDK documentation supports project-based submission. A typical invocation is:

```bash
aristotle submit "Use ARISTOTLE_PROJECT_PROMPT.md as the proof instructions and close all designated sorries without new axioms." \
  --project-dir ./formal \
  --wait
```

If your installed Aristotle CLI exposes different flags, use its project submission mode and the same prompt content.

## What to send back

The useful handoff is:

1. Aristotle-modified Lean files;
2. generated output header/toolchain version;
3. full `lake build` result;
4. any theorem Aristotle reports as false or under-specified;
5. `#print axioms` output for the principal soundness theorems if available.

Do not mark the PCS formal kernel machine-checked until the returned project independently builds under the recorded toolchain.


## Dependency order

1. Make the clean PCS library compile under Lean 4.28.0.
2. Solve `Aristotle/Normalization.lean`.
3. Solve `Aristotle/DecisionExtraction.lean`.
4. Solve `Aristotle/SerializedBridge.lean` using the previous direct soundness theorems.
5. Re-run `lake build` and the no-sorry audit.

`PCS.Normalized.DecisionInput` intentionally begins after raw JSON parsing/schema validation/evidence replay. Do not claim a raw-byte-to-Lean theorem merely from the normalized bridge.


## Final acceptance contract

Before returning the project, read and satisfy `ARISTOTLE_FINAL_ACCEPTANCE.md`.
Treat it as the final build/no-placeholder/axiom-audit checklist.
