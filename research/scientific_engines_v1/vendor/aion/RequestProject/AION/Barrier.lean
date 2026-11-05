module

public import RequestProject.AION.Core

/-!
# Barrier (supersolution) upper bounds and Lyapunov-certified lower bounds

* `hitProb_le_of_supersolution` : a nonnegative function `g` with `g ≥ 1` on `B`
  and `L g ≤ 0` off `A ∪ B` dominates the hitting probability **everywhere**.
  No integrability, boundedness, nonexplosion or optional-stopping side condition
  is needed: the proof works with the monotone first-step iterates `hitN`, which is
  where unbounded barriers usually cause trouble in the process-level argument.

* `le_hitProb_of_subsolution` : a function `f` bounded above, with `f ≤ 1` on `B`,
  `f ≤ 0` off `D ∪ B`, and `L f ≥ 0` on a region `D` (disjoint from `A ∪ B`),
  is a lower bound **provided** the chain leaves `D` almost surely, which is
  certified by a Foster–Lyapunov function `V ≥ 0` with `L V ≤ -(total rate)` on `D`.
  Without the escape certificate the statement is false (a closed cycle inside `D`
  supports `f ≡ 1`), see `docs/NEGATIVE_RESULTS.md`.

* `expectedJumps_le` / `expectedTime_le` : Foster–Lyapunov bounds on the mean number
  of jumps / mean time spent in `D` before leaving it.
-/

@[expose] public section

open scoped BigOperators
open Classical

namespace AION
namespace JumpModel

variable {S : Type*} {ι : Type*} [Fintype ι] {M : JumpModel S ι}

lemma flux_le_of_gen_nonpos {g : S → ℝ} {x : S} (h : M.gen g x ≤ 0) :
    M.flux g x ≤ M.totalRate x * g x := by
  rw [gen_eq_flux_sub] at h; linarith

lemma flux_ge_of_gen_nonneg {g : S → ℝ} {x : S} (h : 0 ≤ M.gen g x) :
    M.totalRate x * g x ≤ M.flux g x := by
  rw [gen_eq_flux_sub] at h; linarith

/-! ## Upper bounds -/

/-- Finite-step version of the barrier theorem. -/
theorem hitN_le_of_supersolution {A B : Set S} {g : S → ℝ}
    (hg0 : ∀ x, 0 ≤ g x) (hgB : ∀ x ∈ B, 1 ≤ g x)
    (hgen : ∀ x, x ∉ A → x ∉ B → M.gen g x ≤ 0) :
    ∀ n x, M.hitN A B n x ≤ g x
  | 0, x => by
      simp only [hitN]; split_ifs with h
      · exact hgB x h
      · exact hg0 x
  | n + 1, x => by
      simp only [hitN]
      split_ifs with h1 h2 h3
      · exact hgB x h1
      · exact hg0 x
      · exact hg0 x
      · have hpos : 0 < M.totalRate x := lt_of_le_of_ne (M.totalRate_nonneg x) (Ne.symm h3)
        rw [div_le_iff₀ hpos]
        calc M.flux (M.hitN A B n) x ≤ M.flux g x :=
              M.flux_mono (hitN_le_of_supersolution hg0 hgB hgen n) x
          _ ≤ M.totalRate x * g x := flux_le_of_gen_nonpos (hgen x h2 h1)
          _ = g x * M.totalRate x := by ring

/-- **Barrier theorem.**  `P_x(reach B before A) ≤ g x` for every state `x`. -/
theorem hitProb_le_of_supersolution {A B : Set S} {g : S → ℝ}
    (hg0 : ∀ x, 0 ≤ g x) (hgB : ∀ x ∈ B, 1 ≤ g x)
    (hgen : ∀ x, x ∉ A → x ∉ B → M.gen g x ≤ 0) (x : S) :
    M.hitProb A B x ≤ g x :=
  hitProb_le_of_forall (fun n => hitN_le_of_supersolution hg0 hgB hgen n x)

/-! ## Survival in a region and Lyapunov escape certificates -/

variable (M) in
/-- Probability that the jump chain stays in `D` for the first `n` jumps
(i.e. occupies `D` at times `0,…,n`). -/
noncomputable def survN (D : Set S) : ℕ → S → ℝ
  | 0, x => if x ∈ D then 1 else 0
  | n + 1, x => if x ∈ D then M.flux (survN D n) x / M.totalRate x else 0

lemma survN_nonneg (D : Set S) : ∀ n x, 0 ≤ M.survN D n x
  | 0, x => by unfold survN; split_ifs <;> norm_num
  | n + 1, x => by
      unfold survN; split_ifs
      · exact div_nonneg (M.flux_nonneg (survN_nonneg D n) x) (M.totalRate_nonneg x)
      · exact le_rfl

lemma survN_le_one (D : Set S) (hD : ∀ x ∈ D, 0 < M.totalRate x) : ∀ n x, M.survN D n x ≤ 1
  | 0, x => by unfold survN; split_ifs <;> norm_num
  | n + 1, x => by
      unfold survN; split_ifs with h
      · rw [div_le_one (hD x h)]
        calc M.flux (M.survN D n) x ≤ M.flux (fun _ => (1:ℝ)) x :=
              M.flux_mono (survN_le_one D hD n) x
          _ = M.totalRate x := by rw [flux_const]; ring
      · norm_num

lemma survN_succ_le (D : Set S) (hD : ∀ x ∈ D, 0 < M.totalRate x) :
    ∀ n x, M.survN D (n + 1) x ≤ M.survN D n x
  | 0, x => by
      have := survN_le_one D hD 1 x
      simp only [survN] at this ⊢
      split_ifs with h
      · simpa [h] using this
      · exact le_rfl
  | n + 1, x => by
      rw [survN, survN]; split_ifs with h
      · exact div_le_div_of_nonneg_right (M.flux_mono (survN_succ_le D hD n) x) (hD x h).le
      · exact le_rfl

lemma flux_finset_sum (s : Finset ℕ) (F : ℕ → S → ℝ) (x : S) :
    M.flux (fun y => ∑ k ∈ s, F k y) x = ∑ k ∈ s, M.flux (F k) x := by
  simp only [flux, Finset.mul_sum]; exact Finset.sum_comm

/-- **Foster–Lyapunov mean-exit bound (jump count).**
If `V ≥ 0` and `L V ≤ -(total rate)` on `D`, the expected number of jumps made
while in `D`, `∑_{k<n} P(stay in D up to jump k)`, is at most `V x` for every `n`. -/
theorem expectedJumps_le (D : Set S) (hD : ∀ x ∈ D, 0 < M.totalRate x) {V : S → ℝ}
    (hV0 : ∀ x, 0 ≤ V x) (hV : ∀ x ∈ D, M.gen V x ≤ -M.totalRate x) :
    ∀ n x, ∑ k ∈ Finset.range n, M.survN D k x ≤ V x
  | 0, x => by simpa using hV0 x
  | n + 1, x => by
      rw [Finset.sum_range_succ']
      by_cases hx : x ∈ D
      · have hpos := hD x hx
        have hstep : ∀ k, M.survN D (k + 1) x = M.flux (M.survN D k) x / M.totalRate x := by
          intro k; simp [survN, hx]
        simp only [hstep]
        rw [← Finset.sum_div, ← flux_finset_sum]
        have h1 : M.flux (fun y => ∑ k ∈ Finset.range n, M.survN D k y) x ≤ M.flux V x :=
          M.flux_mono (fun y => expectedJumps_le D hD hV0 hV n y) x
        have h2 := hV x hx
        rw [gen_eq_flux_sub] at h2
        have h3 : M.survN D 0 x = 1 := by simp [survN, hx]
        rw [h3]
        have : M.flux (fun y => ∑ k ∈ Finset.range n, M.survN D k y) x / M.totalRate x
            ≤ V x - 1 := by
          rw [div_le_iff₀ hpos]; nlinarith
        linarith
      · have hz : ∀ k, M.survN D k x = 0 := by
          intro k; cases k <;> simp [survN, hx]
        simp [hz, hV0 x]

/-- Survival probability decays like `V / n`. -/
theorem survN_le_div (D : Set S) (hD : ∀ x ∈ D, 0 < M.totalRate x) {V : S → ℝ}
    (hV0 : ∀ x, 0 ≤ V x) (hV : ∀ x ∈ D, M.gen V x ≤ -M.totalRate x) (n : ℕ) (x : S) :
    (n : ℝ) * M.survN D n x ≤ V x := by
  have hanti : ∀ k ≤ n, M.survN D n x ≤ M.survN D k x := by
    intro k hk
    induction hk with
    | refl => exact le_rfl
    | step _ ih => exact le_trans (survN_succ_le D hD _ x) ih
  calc (n : ℝ) * M.survN D n x = ∑ k ∈ Finset.range n, M.survN D n x := by simp
    _ ≤ ∑ k ∈ Finset.range n, M.survN D k x :=
        Finset.sum_le_sum (fun k hk => hanti k (Finset.mem_range.mp hk).le)
    _ ≤ V x := expectedJumps_le D hD hV0 hV n x

/-! ## Lower bounds -/

/-- Key comparison: a subsolution is dominated by `hitN + C · survN`. -/
theorem sub_le_hitN_add_survN {A B D : Set S} {f : S → ℝ} {C : ℝ}
    (hDB : ∀ x ∈ D, x ∉ B) (hDA : ∀ x ∈ D, x ∉ A) (hD : ∀ x ∈ D, 0 < M.totalRate x)
    (hfC : ∀ x, f x ≤ C) (hfB : ∀ x ∈ B, f x ≤ 1) (hfout : ∀ x, x ∉ D → x ∉ B → f x ≤ 0)
    (hgen : ∀ x ∈ D, 0 ≤ M.gen f x) :
    ∀ n x, f x ≤ M.hitN A B n x + C * M.survN D n x
  | 0, x => by
      by_cases hB : x ∈ B
      · have : x ∉ D := fun h => hDB x h hB
        simp [hitN, survN, hB, this, hfB x hB]
      · by_cases hxD : x ∈ D
        · simp [hitN, survN, hB, hxD, hfC x]
        · simp [hitN, survN, hB, hxD, hfout x hxD hB]
  | n + 1, x => by
      by_cases hB : x ∈ B
      · have : x ∉ D := fun h => hDB x h hB
        simp [hitN, survN, hB, this, hfB x hB]
      · by_cases hxD : x ∈ D
        · have hpos := hD x hxD
          have hA := hDA x hxD
          have hne : M.totalRate x ≠ 0 := hpos.ne'
          simp only [hitN, survN, hB, hA, hne, hxD, if_false, if_true]
          have ih := sub_le_hitN_add_survN hDB hDA hD hfC hfB hfout hgen n
          have h1 : M.flux f x ≤ M.flux (M.hitN A B n) x + C * M.flux (M.survN D n) x := by
            rw [← flux_smul, ← flux_add]; exact M.flux_mono ih x
          have h2 := flux_ge_of_gen_nonneg (hgen x hxD)
          rw [mul_div_assoc', ← add_div, le_div_iff₀ hpos]
          nlinarith
        · have := hitN_nonneg (M := M) A B (n + 1) x
          simp only [survN, hxD, if_false, mul_zero, add_zero]
          linarith [hfout x hxD hB]

/-- **Lyapunov-certified subsolution lower bound.**
`f x ≤ P_x(reach B before A)` for every state `x`. -/
theorem le_hitProb_of_subsolution {A B D : Set S} {f V : S → ℝ} {C : ℝ}
    (hDB : ∀ x ∈ D, x ∉ B) (hDA : ∀ x ∈ D, x ∉ A) (hD : ∀ x ∈ D, 0 < M.totalRate x)
    (hfC : ∀ x, f x ≤ C) (hfB : ∀ x ∈ B, f x ≤ 1) (hfout : ∀ x, x ∉ D → x ∉ B → f x ≤ 0)
    (hgen : ∀ x ∈ D, 0 ≤ M.gen f x)
    (hV0 : ∀ x, 0 ≤ V x) (hV : ∀ x ∈ D, M.gen V x ≤ -M.totalRate x) (x : S) :
    f x ≤ M.hitProb A B x := by
  set C' := max C 0 with hC'
  have hfC' : ∀ y, f y ≤ C' := fun y => le_trans (hfC y) (le_max_left _ _)
  have hC'0 : 0 ≤ C' := le_max_right _ _
  have key : ∀ n : ℕ, f x ≤ M.hitProb A B x + C' * M.survN D n x := by
    intro n
    have := sub_le_hitN_add_survN hDB hDA hD hfC' hfB hfout hgen n x
    linarith [hitN_le_hitProb (M := M) A B n x]
  by_contra hlt
  push_neg at hlt
  set δ := f x - M.hitProb A B x with hδ
  have hδpos : 0 < δ := by linarith
  obtain ⟨n, hn⟩ := exists_nat_gt (C' * V x / δ)
  have hn' : C' * V x < n * δ := by rwa [div_lt_iff₀ hδpos] at hn
  have hs := survN_le_div D hD hV0 hV n x
  have hnpos : (0 : ℝ) < n := by
    have : 0 ≤ C' * V x := mul_nonneg hC'0 (hV0 x)
    by_contra h; push_neg at h; nlinarith
  have : C' * M.survN D n x < δ := by
    by_contra h; push_neg at h
    have : (n : ℝ) * δ ≤ n * (C' * M.survN D n x) := mul_le_mul_of_nonneg_left h hnpos.le
    nlinarith
  linarith [key n]

/-! ## Sandwich and relative error -/

/-- **Certified sandwich.** Combining both certificates gives `f x ≤ P ≤ g x`. -/
theorem sandwich {A B D : Set S} {f g V : S → ℝ} {C : ℝ}
    (hg0 : ∀ x, 0 ≤ g x) (hgB : ∀ x ∈ B, 1 ≤ g x)
    (hgen_up : ∀ x, x ∉ A → x ∉ B → M.gen g x ≤ 0)
    (hDB : ∀ x ∈ D, x ∉ B) (hDA : ∀ x ∈ D, x ∉ A) (hD : ∀ x ∈ D, 0 < M.totalRate x)
    (hfC : ∀ x, f x ≤ C) (hfB : ∀ x ∈ B, f x ≤ 1) (hfout : ∀ x, x ∉ D → x ∉ B → f x ≤ 0)
    (hgen_lo : ∀ x ∈ D, 0 ≤ M.gen f x)
    (hV0 : ∀ x, 0 ≤ V x) (hV : ∀ x ∈ D, M.gen V x ≤ -M.totalRate x) (x : S) :
    f x ≤ M.hitProb A B x ∧ M.hitProb A B x ≤ g x :=
  ⟨le_hitProb_of_subsolution hDB hDA hD hfC hfB hfout hgen_lo hV0 hV x,
   hitProb_le_of_supersolution hg0 hgB hgen_up x⟩

/-- Relative-error reading of a sandwich: if `0 < L ≤ p ≤ U ≤ (1+ε) L` then both
`U/p` and `p/L` are at most `1+ε`. -/
theorem relative_error_of_sandwich {L U p ε : ℝ} (hL : 0 < L) (hLp : L ≤ p) (hpU : p ≤ U)
    (hUL : U ≤ (1 + ε) * L) : U / p ≤ 1 + ε ∧ p / L ≤ 1 + ε := by
  have hp : 0 < p := lt_of_lt_of_le hL hLp
  have hε : 0 ≤ 1 + ε := by
    by_contra h; push_neg at h; nlinarith
  constructor
  · rw [div_le_iff₀ hp]; nlinarith
  · rw [div_le_iff₀ hL]; linarith

/-! ## Mean time spent in a region (continuous time) -/

variable (M) in
/-- Expected time spent in `D` during the first `n` jumps (holding time at `x` has
mean `1 / totalRate x`). -/
noncomputable def timeN (D : Set S) : ℕ → S → ℝ
  | 0, _ => 0
  | n + 1, x => if x ∈ D then (1 + M.flux (timeN D n) x) / M.totalRate x else 0

/-- **Foster–Lyapunov mean exit-time bound.** If `W ≥ 0` and `L W ≤ -1` on `D`
then the expected time spent in `D` (before leaving it, over any number of jumps)
is at most `W x`. -/
theorem expectedTime_le (D : Set S) (hD : ∀ x ∈ D, 0 < M.totalRate x) {W : S → ℝ}
    (hW0 : ∀ x, 0 ≤ W x) (hW : ∀ x ∈ D, M.gen W x ≤ -1) :
    ∀ n x, M.timeN D n x ≤ W x
  | 0, x => by simpa [timeN] using hW0 x
  | n + 1, x => by
      simp only [timeN]; split_ifs with hx
      · have hpos := hD x hx
        rw [div_le_iff₀ hpos]
        have h1 := M.flux_mono (expectedTime_le D hD hW0 hW n) x
        have h2 := hW x hx
        rw [gen_eq_flux_sub] at h2
        linarith
      · exact hW0 x

end JumpModel
end AION
