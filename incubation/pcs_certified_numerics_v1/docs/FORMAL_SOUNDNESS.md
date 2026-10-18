# Formal soundness

Lean library `CertNum` (Lean 4.28.0, Mathlib `v4.28.0`):

- `mem_neg`, `mem_add`, `mem_sub`, `mem_mul` — membership preservation for interval ops
- `mem_hull_left/right`, `mem_inter_of_mem`, `width_nonneg`
- **No `sorry` / `admit`** in the soundness modules that build

Build: `lake build` in this directory with `LAKE_CACHE_DIR` isolated.

Axiom audit: Mathlib classical foundations only; no project axioms.
