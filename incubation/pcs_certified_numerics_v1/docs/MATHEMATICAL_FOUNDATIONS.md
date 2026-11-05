# Mathematical foundations

- Base quantities: `ℕ`, `ℤ`, `ℚ`, with intended `ℝ` semantics via Mathlib for future bridges.
- Closed rational intervals `[lo,hi]` with `lo≤hi`, plus explicit `∅`.
- Membership: `x ∈ [lo,hi] ↔ lo≤x≤hi` (exact on `ℚ`).
- Enclosure: computed set `E` is sound for `f` on `D` if `f(D) ⊆ E` under stated domain hypotheses.
- Partial operations return tagged `EnclStatus` (never numeric sentinels).
