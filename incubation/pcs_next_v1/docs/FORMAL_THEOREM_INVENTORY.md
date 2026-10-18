# Formal theorem inventory (PcsNext isolated workspace)

Toolchain: `leanprover/lean4:v4.28.0`  
Build: `cd incubation/pcs_next_v1/formal && lake build` (exit 0 on 2026-10-17)

| Theorem | Module | Statement (informal) | Scope |
|---|---|---|---|
| `exists_ne_forall` | `PcsNext.ClaimIR` | Existential quantifier is not universal | Expr encoding |
| `neg_neg_preserves_exists` | `PcsNext.ClaimIR` | Double-negation wrapper is not itself existential | Expr encoding |
| `approx_not_necessarily_eq` | `PcsNext.Approx` | approx(1,2,1) holds while equality fails | Nat example |
| `improvesOn_not_ge` | `PcsNext.ScalarGuard` | Strict loss improvement contradicts ≥ | Scalar models |
| `preservesWithin_nil/cons` | `PcsNext.ScalarGuard` | Finite-domain preservation constructors | List domains |
| `preserves_same_model_zero_bound` | `PcsNext.ScalarGuard` | Identical models preserve with bound 0 | Finite domains |

Audit: no `sorry`, `admit`, `axiom`, `unsafe`, `implemented_by`, `native_decide` in `PcsNext/`.

These theorems do **not** prove OS correctness, clinical validity, or general intelligence.

| `proxyTerm_nonneg` / `proxyTerm_mono_dose` | `PcsNext.Bateman` | Nat proxy term nonnegative and monotone in dose | Nat arithmetic proxy — not IEEE Bateman |
| `trapAUC_nonneg` | `PcsNext.NCA` | Discrete Nat trapezoid AUC nonnegative | Nat samples; not float runtime |
