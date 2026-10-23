module

public import RequestProject.AION.Composition

/-!
# Negative results and obstructions (machine-checked)

1. `escape_certificate_necessary` : the lower-bound theorem is **false** without the
   Lyapunov escape certificate: a two-state cycle supports the subsolution `f ≡ 1`
   while the hitting probability is `0`.
2. `gen_mul` / `leibniz_fails` : the generator is not a derivation.  The exact product
   rule has the cross term `∑_r rate_r Δ_r f Δ_r g` ("carré du champ"), which does not
   vanish when a reaction changes several modules at once; a concrete instance shows
   the naive Leibniz rule fails.
3. `mm1_hits_surely` : **infinite-horizon rarity is not safety.**  For the M/M/1-type
   chain (arrivals `λ`, services `μ > λ`) whose stationary tail `P(X ≥ N) = (λ/μ)^N` is
   astronomically small, the level `N` is nevertheless reached with probability one
   from every state.  Hence no barrier certificate with value `< 1` can exist, and any
   claim of permanent safety would be false.
-/

@[expose] public section

open scoped BigOperators

namespace AION.NegativeResults

open AION AION.JumpModel

/-- Deterministic two-cycle on `Bool`. -/
noncomputable def cycle : JumpModel Bool Unit where
  rate _ _ := 1
  rate_nonneg _ _ := zero_le_one
  next _ b := !b

/-- Without an escape certificate, a subsolution need not be a lower bound. -/
theorem escape_certificate_necessary :
    ∃ (M : JumpModel Bool Unit) (A B D : Set Bool) (f : Bool → ℝ) (C : ℝ),
      (∀ x ∈ D, x ∉ B) ∧ (∀ x ∈ D, x ∉ A) ∧ (∀ x ∈ D, 0 < M.totalRate x) ∧
      (∀ x, f x ≤ C) ∧ (∀ x ∈ B, f x ≤ 1) ∧ (∀ x, x ∉ D → x ∉ B → f x ≤ 0) ∧
      (∀ x ∈ D, 0 ≤ M.gen f x) ∧ ¬ (∀ x, f x ≤ M.hitProb A B x) := by
  refine ⟨cycle, ∅, ∅, Set.univ, fun _ => 1, 1, ?_, ?_, ?_, ?_, ?_, ?_, ?_, ?_⟩
  · intro x _; exact Set.notMem_empty x
  · intro x _; exact Set.notMem_empty x
  · intro x _; simp [totalRate, cycle]
  · intro x; exact le_rfl
  · intro x hx; exact absurd hx (Set.notMem_empty x)
  · intro x hx; exact absurd (Set.mem_univ x) hx
  · intro x _; simp [gen]
  · intro h
    have := h true
    rw [hitProb_empty] at this
    norm_num at this

variable {S : Type*} {ι : Type*} [Fintype ι]

/-- Exact product rule for the generator (with the cross term). -/
theorem gen_mul (M : JumpModel S ι) (f g : S → ℝ) (x : S) :
    M.gen (fun y => f y * g y) x =
      f x * M.gen g x + g x * M.gen f x +
        ∑ r, M.rate r x * ((f (M.next r x) - f x) * (g (M.next r x) - g x)) := by
  simp only [gen, Finset.mul_sum, ← Finset.sum_add_distrib]
  exact Finset.sum_congr rfl (fun r _ => by ring)

/-- One reaction moving two modules at once. -/
noncomputable def joint : JumpModel (ℤ × ℤ) Unit where
  rate _ _ := 1
  rate_nonneg _ _ := zero_le_one
  next _ p := (p.1 + 1, p.2 + 1)

/-- The naive Leibniz rule fails for joint reactions. -/
theorem leibniz_fails :
    joint.gen (fun p => (p.1 : ℝ) * p.2) (0, 0) ≠
      ((0 : ℤ) : ℝ) * joint.gen (fun p => (p.2 : ℝ)) (0, 0) +
        ((0 : ℤ) : ℝ) * joint.gen (fun p => (p.1 : ℝ)) (0, 0) := by
  simp [gen, joint]

/-- M/M/1-type chain on `ℕ`: arrivals at rate `λ`, services at rate `μ` when `x ≥ 1`. -/
noncomputable def mm1 (lam mu : ℝ) (hl : 0 ≤ lam) (hm : 0 ≤ mu) : JumpModel ℕ (Fin 2) where
  rate r x := if r = 0 then lam else if 1 ≤ x then mu else 0
  rate_nonneg r x := by split_ifs <;> first | exact hl | exact hm | exact le_rfl
  next r x := if r = 0 then x + 1 else x - 1

/-- **Infinite-horizon rarity is not safety.**  For `0 < λ < μ` (positive recurrent,
stationary tail `(λ/μ)^N`), every level `N` is reached with probability one. -/
theorem mm1_hits_surely {lam mu : ℝ} (hl : 0 < lam) (hlm : lam < mu) (N : ℕ) (x : ℕ) :
    (mm1 lam mu hl.le (hl.le.trans hlm.le)).hitProb ∅ {y | N ≤ y} x = 1 := by
  set M := mm1 lam mu hl.le (hl.le.trans hlm.le) with hM
  set r : ℝ := mu / lam with hr
  have hr1 : 1 < r := by rw [hr, one_lt_div hl]; exact hlm
  have hmu : mu = lam * r := by rw [hr]; field_simp
  set β : ℝ := (lam + mu) / (mu - lam) with hβ
  have hβ0 : 0 ≤ β := div_nonneg (by linarith) (by linarith)
  set α : ℝ := (β + 1) / (r - 1) with hα
  have hα0 : 0 ≤ α := div_nonneg (by linarith) (by linarith)
  have hαr : α * (r - 1) = β + 1 := by rw [hα]; field_simp [show r - 1 ≠ 0 by linarith]
  have hβml : β * (mu - lam) = lam + mu := by
    rw [hβ]; field_simp [show mu - lam ≠ 0 by linarith]
  -- escape function
  set V : ℕ → ℝ := fun y => if y ≤ N then β * y + α * (r ^ N - r ^ y) else β * N with hV
  apply le_antisymm (hitProb_le_one _ _ _)
  refine le_hitProb_of_subsolution (M := M) (D := {y | y < N}) (f := fun _ => 1) (C := 1)
    (V := V) ?_ ?_ ?_ ?_ ?_ ?_ ?_ ?_ ?_ x
  · intro y hy; simp only [Set.mem_setOf_eq, not_le]; exact hy
  · intro y _; exact Set.notMem_empty y
  · intro y _
    simp only [hM, totalRate, mm1, Fin.sum_univ_two, Fin.isValue, if_true, one_ne_zero, if_false]
    split_ifs <;> linarith [hl]
  · intro y; exact le_rfl
  · intro y _; exact le_rfl
  · intro y hy hB
    simp only [Set.mem_setOf_eq, not_lt, not_le] at hy hB; omega
  · intro y _; simp [gen]
  · intro y
    simp only [hV]
    split_ifs with h
    · have : r ^ y ≤ r ^ N := pow_le_pow_right₀ hr1.le h
      have : (0 : ℝ) ≤ y := Nat.cast_nonneg y
      nlinarith
    · exact mul_nonneg hβ0 (Nat.cast_nonneg N)
  · intro y hy
    simp only [Set.mem_setOf_eq] at hy
    simp only [hM, gen, totalRate, mm1, Fin.sum_univ_two, Fin.isValue, if_true, one_ne_zero,
      if_false]
    have h1 : y + 1 ≤ N := hy
    have hVy : V y = β * y + α * (r ^ N - r ^ y) := by simp [hV, hy.le]
    have hVy1 : V (y + 1) = β * (y + 1 : ℕ) + α * (r ^ N - r ^ (y + 1)) := by simp [hV, h1]
    rw [hVy, hVy1]
    rcases Nat.eq_zero_or_pos y with h0 | hpos
    · subst h0
      simp only [show ¬ (1 ≤ (0 : ℕ)) by omega, if_false, zero_mul, add_zero, pow_zero, pow_one,
        Nat.cast_zero, Nat.cast_one, zero_add, mul_zero]
      have : lam * (β * 1 + α * (r ^ N - r) - α * (r ^ N - 1)) = -lam := by
        have : β * 1 + α * (r ^ N - r) - α * (r ^ N - 1) = β - α * (r - 1) := by ring
        rw [this, hαr]; ring
      linarith
    · have hle : 1 ≤ y := hpos
      simp only [hle, if_true]
      have hVy2 : V (y - 1) = β * (y - 1 : ℕ) + α * (r ^ N - r ^ (y - 1)) := by
        simp [hV, show y - 1 ≤ N by omega]
      rw [hVy2]
      obtain ⟨z, rfl⟩ : ∃ z, y = z + 1 := ⟨y - 1, by omega⟩
      simp only [Nat.add_sub_cancel]
      push_cast
      rw [hmu] at hβml ⊢
      have hrz : r ^ (z + 1 + 1) = r ^ z * r * r := by ring
      have hrz1 : r ^ (z + 1) = r ^ z * r := by ring
      rw [hrz, hrz1]
      nlinarith

end AION.NegativeResults
