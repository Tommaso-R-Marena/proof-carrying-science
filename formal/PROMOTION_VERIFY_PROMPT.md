# Promotion verification prompt

This is a verification-only pass. The substantive proofs were already closed in the
previous Aristotle run.

Work on the current project exactly as supplied.

1. Preserve `leanprover/lean4:v4.28.0` unless your runtime necessarily reports a
   different toolchain; if it does, report the exact version and do not silently
   rewrite theorem statements.
2. Run `lake build` from `formal/`.
3. Do not weaken, generalize, strengthen, rename, or otherwise change theorem
   statements unless the project is genuinely ill-typed. This pass is intended to
   verify namespace/module promotion only.
4. Run the equivalent of:
   `grep -R --line-number -E '\b(sorry|admit)\b' PCS.lean PCS`
   and confirm no placeholders remain.
5. Confirm there are no project-specific `axiom` or `unsafe` declarations.
6. Capture the `#print axioms` output emitted by `PCS/Audit.lean`.
7. Specifically confirm these promoted theorems compile:
   - `PCS.DecisionExtraction.decideClaim_computational_sound`
   - `PCS.DecisionExtraction.decideClaim_formal_sound`
   - `PCS.DecisionExtraction.decideClaim_empirical_sound`
   - `PCS.DecisionExtraction.decideClaim_mixed_sound`
   - `PCS.SerializedBridge.normalized_computational_sound`
   - `PCS.SerializedBridge.normalized_formal_sound`
   - `PCS.SerializedBridge.normalized_empirical_sound`
   - `PCS.SerializedBridge.normalized_mixed_sound`
8. Report exact build exit code, Lean version, placeholder audit, and axiom audit.

Do not reintroduce an `Aristotle` Lean library or namespace. The production-shaped
formal architecture intentionally contains only ordinary `PCS.*` modules.

If the build succeeds unchanged, state that the namespace-promoted proof set is
machine checked and ready for merge.
