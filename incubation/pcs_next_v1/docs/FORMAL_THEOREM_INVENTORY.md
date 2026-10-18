# Formal theorem inventory (PcsNext isolated workspace)

Toolchain: `leanprover/lean4:v4.28.0`  
Build: `cd incubation/pcs_next_v1/formal && lake build` (13 jobs)

| Theorem | Module | Statement (informal) | Scope |
|---|---|---|---|
| `exists_ne_forall` | `PcsNext.ClaimIR` | Existential ≠ universal | Expr encoding |
| `neg_neg_preserves_exists` | `PcsNext.ClaimIR` | ¬¬ does not change exists head | Expr encoding |
| `and_preserves_exists_left` | `PcsNext.ClaimIR` | ∧ wrapper is not exists-headed | Expr encoding |
| `association_ne_causal` | `PcsNext.ClaimIR` | association tag ≠ causal tag | EvidenceKind |
| `causal_over_association_detected` | `PcsNext.ClaimIR` | nested causal∘association flagged | Detector hook |
| `approx_not_necessarily_eq` | `PcsNext.Approx` | approx(1,2,1) ⇏ equality | Nat example |
| `improvesOn_not_ge` / `preservesWithin_*` | `PcsNext.ScalarGuard` | Finite-domain improvement/preservation | Scalar models |
| `proxyTerm_nonneg` / `proxyTerm_mono_dose` | `PcsNext.Bateman` | Nat proxy nonnegative / mono in dose | Nat proxy |
| `trapAUC_nonneg` | `PcsNext.NCA` | Discrete trapezoid AUC ≥ 0 | Nat samples |
| `convert_mL_per_min_*` | `PcsNext.Units` | mL/min → L/h factor 3/50 | Nat conversion |
| `transfer_preserves_total` | `PcsNext.Conservation` | Two-cell transfer preserves mass | Nat amounts |
| `rate_le_vmax` / `rate_km_zero_of_pos_conc` | `PcsNext.MM` | MM proxy ≤ vmax | Nat division |
| `effect_ge_e0` / `effect_le_e0_add_emax` | `PcsNext.Emax` | Emax proxy in [e0, e0+emax] | Nat division |
| `concProxy_scale` / `scale_two_ne_one` | `PcsNext.Homogeneity` | Dose scale tracks concentration proxy | Nat mul |

Audit: no `sorry`, `admit`, `axiom`, `unsafe`, `implemented_by` in `PcsNext/`.

These theorems do **not** prove OS correctness, clinical validity, IEEE float semantics, or general intelligence.
