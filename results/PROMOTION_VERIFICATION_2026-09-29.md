# Promotion verification — 2026-09-29

Run ID: `b3559078-9af6-4b88-8916-4044a408ce46`

## Verdict

**PASS — promoted PCS proof set is machine-checked and ready for merge.**

The verification-only Aristotle run changed no Lean sources, theorem statements, lakefile, or toolchain and searched for no new proofs.

## Build

- Toolchain: `leanprover/lean4:v4.28.0`
- `lean --version`: Lean 4.28.0, commit `7e01a1bf5c70`
- `lake build` from `formal/`: exit code 0
- Build result: `Build completed successfully (14 jobs).`
- No build warnings or errors.
- `scripts/verify_lean.sh`: exit code 0 in the returned verification environment.

## Placeholder and declaration audit

Independent searches performed by the verification run found:

- no `sorry`;
- no `admit`;
- no `axiom` declarations;
- no `unsafe` declarations;
- no `implemented_by`;
- no `extern`;
- no `native_decide`.

A compiled-declaration scan covered all 641 declarations from the `PCS.*` modules and found:

- 0 axioms;
- 0 unsafe declarations;
- 0 declarations containing `sorry`.

There is no `Aristotle` Lean library or namespace in the production-shaped project.

## Promoted theorem axiom audit

The eight promoted soundness theorems report:

```text
PCS.DecisionExtraction.decideClaim_computational_sound  depends on axioms: [propext, Classical.choice, Quot.sound]
PCS.DecisionExtraction.decideClaim_formal_sound         depends on axioms: [propext, Classical.choice, Quot.sound]
PCS.DecisionExtraction.decideClaim_empirical_sound      depends on axioms: [propext, Classical.choice, Quot.sound]
PCS.DecisionExtraction.decideClaim_mixed_sound          depends on axioms: [propext, Classical.choice, Quot.sound]
PCS.SerializedBridge.normalized_computational_sound     depends on axioms: [propext, Classical.choice, Quot.sound]
PCS.SerializedBridge.normalized_formal_sound            depends on axioms: [propext, Classical.choice, Quot.sound]
PCS.SerializedBridge.normalized_empirical_sound         depends on axioms: [propext, Classical.choice, Quot.sound]
PCS.SerializedBridge.normalized_mixed_sound             depends on axioms: [propext, Classical.choice, Quot.sound]
```

Across all 38 audited theorems, dependencies are limited to Lean's standard `propext`, `Classical.choice`, and `Quot.sound`; several audited theorems depend on none.

No `sorryAx` or PCS-specific axiom appears.

## Verification-script issue found

The pre-verification branch version of `scripts/verify_lean.sh` used:

```bash
'\\b(sorry|admit)\\b'
```

inside single quotes, causing GNU grep to search for literal backslash characters rather than the intended word boundary. Its successful exit therefore did not establish the placeholder result by itself.

The verification run independently performed correct searches and a compiled declaration scan, establishing the result above.

The repository script has subsequently been corrected to avoid ambiguous word-boundary escaping altogether and now uses identifier-token matching plus an explicit forbidden-declaration gate.

## Scope

This verification establishes the production-shaped PCS decision and normalized-state proof layer under Lean 4.28.0.

It does **not** establish end-to-end correctness from raw serialized PCS package bytes through Python parsing/replay into `Normalized.DecisionInput`, nor does it establish empirical or clinical adequacy of scientific models.
