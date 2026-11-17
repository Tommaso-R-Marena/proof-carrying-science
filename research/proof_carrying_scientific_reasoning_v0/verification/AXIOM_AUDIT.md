# Axiom audit (Phase II)

From `lake build` `#print axioms` (Lean 4.28.0):

- Core checker theorems use only **`propext`** (and occasionally `Quot.sound` for list lemmas).
- **`sorryAx` absent** for `checkCertificate_sound`, `checkCertificate_implies_entails`, `hyp_not_math_established`, `meet_comm`.
- No custom axioms declared in this package.
