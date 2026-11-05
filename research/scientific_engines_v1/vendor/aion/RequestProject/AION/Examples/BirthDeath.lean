module

public import RequestProject.AION.Composition

/-!
# Example A: exact competing-boundary hitting probability of a linear birth–death chain

Reactions `X → 2X` (rate `λ x`) and `X → ∅` (rate `μ x`), countably infinite state
space `ℕ`.  For `0 < λ < μ` and every level `N ≥ 1`, the probability of reaching `N`
before extinction from `x ≤ N` is exactly

  `((μ/λ)^x - 1) / ((μ/λ)^N - 1)`

(the gambler's-ruin formula).  Both inequalities are obtained from the general
certificate theorems: the upper bound from the barrier theorem and the lower bound
from the Lyapunov-certified subsolution theorem (escape certificate `V(x) = c·x`).
The statement is symbolic in `λ, μ, N, x`; in particular it certifies probabilities
of order `(λ/μ)^{N-x}`, i.e. arbitrarily small, with relative error zero.
-/

@[expose] public section

open scoped BigOperators

namespace AION.Examples.BirthDeath

open AION AION.JumpModel

/-- The linear birth–death chain as a jump model on `ℕ`. -/
noncomputable def bd (lam mu : ℝ) (hl : 0 ≤ lam) (hm : 0 ≤ mu) : JumpModel ℕ (Fin 2) where
  rate r x := if r = 0 then lam * x else mu * x
  rate_nonneg r x := by
    split_ifs
    · exact mul_nonneg hl (Nat.cast_nonneg x)
    · exact mul_nonneg hm (Nat.cast_nonneg x)
  next r x := if r = 0 then x + 1 else x - 1

/-- Closed form `h(x) = (r^x - 1)/(r^N - 1)` with `r = μ/λ`. -/
noncomputable def hClosed (lam mu : ℝ) (N : ℕ) (x : ℕ) : ℝ :=
  ((mu / lam) ^ x - 1) / ((mu / lam) ^ N - 1)

variable {lam mu : ℝ} (hl : 0 < lam) (hlm : lam < mu)
include hl hlm

lemma r_gt_one : 1 < mu / lam := by rw [one_lt_div hl]; exact hlm

lemma gen_hClosed (N : ℕ) {x : ℕ} (hx : 1 ≤ x) :
    (bd lam mu hl.le (hl.le.trans hlm.le)).gen (hClosed lam mu N) x = 0 := by
  simp only [gen, Fin.sum_univ_two, bd, hClosed]
  simp only [Fin.isValue, if_true, one_ne_zero, if_false]
  obtain ⟨y, rfl⟩ : ∃ y, x = y + 1 := ⟨x - 1, by omega⟩
  simp only [Nat.add_sub_cancel]
  set r := mu / lam with hrdef
  have hmu : mu = lam * r := by rw [hrdef]; field_simp
  rw [hmu]
  ring

lemma hClosed_den_pos {N : ℕ} (hN : 1 ≤ N) : 0 < (mu / lam) ^ N - 1 := by
  have := one_lt_pow₀ (r_gt_one hl hlm) (by omega : N ≠ 0)
  linarith

lemma hClosed_nonneg {N : ℕ} (hN : 1 ≤ N) (x : ℕ) : 0 ≤ hClosed lam mu N x := by
  unfold hClosed
  apply div_nonneg _ (hClosed_den_pos hl hlm hN).le
  have := one_le_pow₀ (r_gt_one hl hlm).le (n := x)
  linarith

lemma hClosed_ge_one {N : ℕ} (hN : 1 ≤ N) {y : ℕ} (hy : N ≤ y) : 1 ≤ hClosed lam mu N y := by
  unfold hClosed
  rw [le_div_iff₀ (hClosed_den_pos hl hlm hN), one_mul]
  have := pow_le_pow_right₀ (r_gt_one hl hlm).le hy
  linarith

lemma hClosed_le_one {N : ℕ} (hN : 1 ≤ N) {y : ℕ} (hy : y ≤ N) : hClosed lam mu N y ≤ 1 := by
  unfold hClosed
  rw [div_le_iff₀ (hClosed_den_pos hl hlm hN), one_mul]
  have := pow_le_pow_right₀ (r_gt_one hl hlm).le hy
  linarith

lemma hClosed_self {N : ℕ} (hN : 1 ≤ N) : hClosed lam mu N N = 1 := by
  unfold hClosed; exact div_self (hClosed_den_pos hl hlm hN).ne'

/-- Upper bound from the barrier theorem (valid from every initial state). -/
theorem bd_upper {N : ℕ} (hN : 1 ≤ N) (x : ℕ) :
    (bd lam mu hl.le (hl.le.trans hlm.le)).hitProb {0} {y | N ≤ y} x ≤ hClosed lam mu N x := by
  apply hitProb_le_of_supersolution (hClosed_nonneg hl hlm hN)
  · intro y hy; exact hClosed_ge_one hl hlm hN hy
  · intro y hA _
    have : 1 ≤ y := by
      simp only [Set.mem_singleton_iff] at hA; omega
    rw [gen_hClosed hl hlm N this]

/-- Lower bound from the Lyapunov-certified subsolution theorem. -/
theorem bd_lower {N : ℕ} (hN : 1 ≤ N) {x : ℕ} (hx : x ≤ N) :
    hClosed lam mu N x ≤ (bd lam mu hl.le (hl.le.trans hlm.le)).hitProb {0} {y | N ≤ y} x := by
  set M := bd lam mu hl.le (hl.le.trans hlm.le) with hM
  set f : ℕ → ℝ := fun y => if N ≤ y then 1 else hClosed lam mu N y with hf
  set c : ℝ := (lam + mu) / (mu - lam) with hc
  have hml : 0 < mu - lam := by linarith
  have htot : ∀ y : ℕ, M.totalRate y = (lam + mu) * y := by
    intro y; simp [hM, totalRate, bd, Fin.sum_univ_two]; ring
  have hfx : f x = hClosed lam mu N x := by
    by_cases h : N ≤ x
    · have : x = N := le_antisymm hx h
      subst this; simp [hf, hClosed_self hl hlm hN]
    · simp [hf, h]
  rw [← hfx]
  refine le_hitProb_of_subsolution (M := M) (D := {y | 1 ≤ y ∧ y < N}) (C := 1)
    (V := fun y => c * y) ?_ ?_ ?_ ?_ ?_ ?_ ?_ ?_ ?_ x
  · intro y hy; simp only [Set.mem_setOf_eq, not_le]; exact hy.2
  · intro y hy; obtain ⟨h1, _⟩ := hy; simp only [Set.mem_singleton_iff]; omega
  · intro y hy; rw [htot]
    have : (1 : ℝ) ≤ y := by exact_mod_cast hy.1
    nlinarith
  · intro y; simp only [hf]; split_ifs with h
    · exact le_rfl
    · exact hClosed_le_one hl hlm hN (by omega)
  · intro y hy; simp [hf, show N ≤ y from hy]
  · intro y hyD hyB
    simp only [Set.mem_setOf_eq, not_and, not_lt, not_le] at hyD hyB
    have : y = 0 := by
      by_contra h0; have := hyD (by omega); omega
    subst this
    simp [hf, show ¬ N ≤ 0 by omega, hClosed]
  · intro y hy
    obtain ⟨h1, h2⟩ := hy
    have hgen := gen_hClosed hl hlm N h1
    have hfy : f y = hClosed lam mu N y := by simp [hf, show ¬ N ≤ y by omega]
    have hfy1 : f (y + 1) = hClosed lam mu N (y + 1) := by
      by_cases h : N ≤ y + 1
      · have : y + 1 = N := by omega
        rw [this]; simp [hf, hClosed_self hl hlm hN]
      · simp [hf, h]
    have hfy2 : f (y - 1) = hClosed lam mu N (y - 1) := by
      simp [hf, show ¬ N ≤ y - 1 by omega]
    have : M.gen f y = M.gen (hClosed lam mu N) y := by
      simp only [gen, Fin.sum_univ_two, hM, bd, Fin.isValue, if_true, one_ne_zero, if_false]
      rw [hfy, hfy1, hfy2]
    rw [this, hgen]
  · intro y
    have : 0 ≤ c := div_nonneg (by linarith) hml.le
    exact mul_nonneg this (Nat.cast_nonneg y)
  · intro y hy
    rw [htot]
    obtain ⟨h1, -⟩ := hy
    obtain ⟨z, rfl⟩ : ∃ z, y = z + 1 := ⟨y - 1, by omega⟩
    simp only [gen, Fin.sum_univ_two, hM, bd, Fin.isValue, if_true, one_ne_zero, if_false,
      Nat.add_sub_cancel]
    have hcm : c * (mu - lam) = lam + mu := by rw [hc]; field_simp
    push_cast
    nlinarith

/-- **Exact rare-event probability** (Example A), symbolic in all parameters. -/
theorem bd_exact {N : ℕ} (hN : 1 ≤ N) {x : ℕ} (hx : x ≤ N) :
    (bd lam mu hl.le (hl.le.trans hlm.le)).hitProb {0} {y | N ≤ y} x =
      ((mu / lam) ^ x - 1) / ((mu / lam) ^ N - 1) :=
  le_antisymm (bd_upper hl hlm hN x) (bd_lower hl hlm hN hx)

end AION.Examples.BirthDeath
