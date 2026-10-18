# Formal theorem inventory (PcsNext isolated workspace)

Toolchain: `leanprover/lean4:v4.28.0`  
Build: `cd incubation/pcs_next_v1/formal && lake build` (12 jobs)

| Theorem | Module | Statement (informal) | Scope |
|---|---|---|---|
| `exists_ne_forall` | `PcsNext.ClaimIR` | Existential quantifier is not universal | Expr encoding |
| `neg_neg_preserves_exists` | `PcsNext.ClaimIR` | Double-negation wrapper is not itself existential | Expr encoding |
| `approx_not_necessarily_eq` | `PcsNext.Approx` | approx(1,2,1) holds while equality fails | Nat example |
| `improvesOn_not_ge` | `PcsNext.ScalarGuard` | Strict loss improvement contradicts ≥ | Scalar models |
| `preservesWithin_nil/cons` | `PcsNext.ScalarGuard` | Finite-domain preservation constructors | List domains |
| `preserves_same_model_zero_bound` | `PcsNext.ScalarGuard` | Identical models preserve with bound 0 | Finite domains |
| `proxyTerm_nonneg` / `proxyTerm_mono_dose` | `PcsNext.Bateman` | Nat proxy term nonnegative and monotone in dose | Nat arithmetic proxy — not IEEE Bateman |
| `trapAUC_nonneg` | `PcsNext.NCA` | Discrete Nat trapezoid AUC nonnegative | Nat samples; not float runtime |
| `convert_mL_per_min_one` / `mL_per_min_not_identity_scale` | `PcsNext.Units` | 1 mL/min → (3,50) L/h; scale ≠ identity | Nat conversion factor |
| `transfer_preserves_total` | `PcsNext.Conservation` | Two-cell transfer preserves total mass | Nat amounts |
| `rate_le_vmax` / `rate_km_zero_of_pos_conc` | `PcsNext.MM` | MM proxy ≤ vmax; km=0 ⇒ rate=vmax | Nat division proxy |
| `effect_ge_e0` / `effect_le_e0_add_emax` | `PcsNext.Emax` | Emax proxy bounded in [e0, e0+emax] | Nat division proxy |

Audit: no `sorry`, `admit`, `axiom`, `unsafe`, `implemented_by` in `PcsNext/`.

These theorems do **not** prove OS correctness, clinical validity, IEEE float semantics, or general intelligence.
