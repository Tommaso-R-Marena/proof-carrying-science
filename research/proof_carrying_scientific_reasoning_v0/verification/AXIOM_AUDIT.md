# Axiom audit

From `lake build` `#print axioms` (Lean 4.28.0):

- **`sorryAx` absent** across all package theorems.
- Typical soundness theorems: **`propext`**, occasionally **`Quot.sound`** (list lemmas).
- **`meet_exhaustive` / `meet_assoc` / `meet_idem` / `meet_comm`:** no axioms.
- **`Classical.choice`** appears only on surface↔core **iff** theorems that equate two `Nat.decLt` proof packages (`checkSurface_iff_checkCertificate`, `checkCertificatePy_iff_core`). One-direction soundness (`checkSurface_implies_checkCertificate`) is choice-free.
- No custom axioms in this package.

## Irreducible (outside Lean)

Byte-string `json.loads` / CPython / OS I/O → typed `JsonCertificate`.
