import PCS.V2.ProofGatedNoForget

/-!
# Exact worst-case absolute error on a bounded integer interval

For one-input integer ReLU networks `f` (candidate or incumbent) and `t` (target), both
`WideNet`s of arbitrary width and arbitrary parameter size, and integers `L ≤ U`, this
module computes

  `E_[L,U](f,t) = max_{x ∈ [L,U] ∩ ℤ} |f x - t x|`

**exactly**, without enumerating the interval.

Method (all steps are proved):
* the potential bend points of `f` and `t` are the finite list
  `kinks (f.hidden ++ t.hidden)` of `ProofGatedNoForget` (three integers around each
  real breakpoint `-b/w`, none for `w = 0`);
* the probe set is `L`, `U` and the bend points that lie in `[L,U]` (`probes`); its size is
  at most `2 + 3·(width f + width t)`, independent of `U - L`;
* between two consecutive probes the error function `gap f t` has zero second difference,
  hence is affine (`affine_of_secondDiff`), hence its absolute value is bounded by its
  values at the two probes (`abs_le_endpoints`);
* the checker `maxAbsErr` is the maximum of `|gap f t|` over the probes.

Main results (no hypotheses beyond `L ≤ U` where an interval must be nonempty):
* `errAt_le_maxAbsErr` and `maxAbsErr_attained`: `maxAbsErr` is exactly the maximum;
* `maxAbsErr_le_iff`: the bound check `maxAbsErr ≤ B` is sound and complete;
* `findErrViolation_sound` / `findErrViolation_complete`: a concrete integer witness in
  `[L,U]` is returned exactly when the bound is violated;
* `robustB_iff`: the robustness check "the candidate's worst-case error does not exceed
  the incumbent's" is equivalent to "every error bound valid for the incumbent on `[L,U]`
  is valid for the candidate";
* the general certificate theorem `probe_dominates` holds for **any** function
  `g : Int → Int` and **any** list `K` outside of which `g` has zero second difference.

The unified gate (corpus progress + all-integer no-forgetting + bounded-region
robustness) and its chain theorems are in `ProofGatedStrongGate`.
-/

namespace PCS.V2.ProofGatedRobust

open PCS.V2.ProofGatedSelfImprovement (relu)
open PCS.V2.ProofGatedWide
open PCS.V2.ProofGatedNoForget

/-! ## Affine pieces: the absolute value is maximised at an endpoint -/

/-- On an affine piece the value at an interior point lies between the endpoint values,
so its absolute value is at most the larger endpoint absolute value. -/
theorem abs_le_endpoints (g : Int → Int) (l r x : Int)
    (hsd : ∀ z, l < z → z < r → SecondDiffZero g z) (hl : l < x) (hr : x < r) :
    (g x).natAbs ≤ max (g l).natAbs (g r).natAbs := by
  have hx := affine_of_secondDiff g l r l x hsd (Int.le_refl l) (by omega)
    (by omega) (by omega)
  have hrr := affine_of_secondDiff g l r l r hsd (Int.le_refl l) (by omega)
    (by omega) (Int.le_refl r)
  generalize g (l + 1) - g l = s at hx hrr
  rcases Int.le_total 0 s with hs | hs
  · have h1 : 0 ≤ (x - l) * s := Int.mul_nonneg (by omega) hs
    have h2 : (x - l) * s ≤ (r - l) * s := Int.mul_le_mul_of_nonneg_right (by omega) hs
    omega
  · have h1 : (x - l) * s ≤ 0 := Int.mul_nonpos_of_nonneg_of_nonpos (by omega) hs
    have h2 : (r - l) * s ≤ (x - l) * s := Int.mul_le_mul_of_nonpos_right (by omega) hs
    omega

/-! ## Probes -/

/-- Membership in the closed integer interval `[L,U]`. -/
def inIv (L U x : Int) : Bool := decide (L ≤ x ∧ x ≤ U)

theorem inIv_iff (L U x : Int) : inIv L U x = true ↔ L ≤ x ∧ x ≤ U := by
  simp [inIv]

/-- The probe points of an interval for a list `K` of potential bend points. -/
def probes (K : List Int) (L U : Int) : List Int := L :: U :: K.filter (inIv L U)

theorem probes_in_interval (K : List Int) (L U : Int) (hLU : L ≤ U) :
    ∀ p ∈ probes K L U, L ≤ p ∧ p ≤ U := by
  intro p hp
  simp only [probes, List.mem_cons, List.mem_filter] at hp
  rcases hp with rfl | rfl | ⟨_, hp⟩
  · omega
  · omega
  · exact (inIv_iff L U p).mp hp

theorem probes_length (K : List Int) (L U : Int) : (probes K L U).length ≤ K.length + 2 := by
  simp only [probes, List.length_cons]
  have := List.length_filter_le (inIv L U) K
  omega

/-- **General probe theorem (certificate form).** If `g` has zero second difference at
every point of `(L,U)` outside the list `K`, then for every `x ∈ [L,U]` some probe
dominates `|g x|`. This holds for any function `g`, not only for networks. -/
theorem probe_dominates (g : Int → Int) (K : List Int) (L U : Int)
    (hK : ∀ z, L < z → z < U → z ∉ K → SecondDiffZero g z)
    (x : Int) (hxL : L ≤ x) (hxU : x ≤ U) :
    ∃ p ∈ probes K L U, (g x).natAbs ≤ (g p).natAbs := by
  by_cases hxP : x ∈ probes K L U
  · exact ⟨x, hxP, Nat.le_refl _⟩
  have hLx : L < x := by
    have : x ≠ L := fun h => hxP (by simp [probes, h])
    omega
  have hxU' : x < U := by
    have : x ≠ U := fun h => hxP (by simp [probes, h])
    omega
  have hLU : L ≤ U := by omega
  obtain ⟨l, hl, hlx, hmax⟩ :=
    exists_max_below (probes K L U) x ⟨L, by simp [probes], hLx⟩
  obtain ⟨r, hr, hxr, hmin⟩ :=
    exists_min_above (probes K L U) x ⟨U, by simp [probes], hxU'⟩
  have hlI := probes_in_interval K L U hLU l hl
  have hrI := probes_in_interval K L U hLU r hr
  have hsd : ∀ z, l < z → z < r → SecondDiffZero g z := by
    intro z hz1 hz2
    have hzP : z ∉ probes K L U := by
      intro hzP
      by_cases hzx : z < x
      · have := hmax z hzP hzx; omega
      · by_cases hzx' : z = x
        · exact hxP (hzx' ▸ hzP)
        · have := hmin z hzP (by omega); omega
    apply hK z (by omega) (by omega)
    intro hzK
    exact hzP (by
      simp only [probes, List.mem_cons, List.mem_filter]
      exact Or.inr (Or.inr ⟨hzK, (inIv_iff L U z).mpr ⟨by omega, by omega⟩⟩))
  have := abs_le_endpoints g l r x hsd hlx hxr
  rcases Nat.le_total (g l).natAbs (g r).natAbs with h | h
  · exact ⟨r, hr, by omega⟩
  · exact ⟨l, hl, by omega⟩

/-! ## Maximum over a list -/

/-- Maximum of a natural-valued function over a list (`0` for the empty list). -/
def maxOver (e : Int → Nat) : List Int → Nat
  | [] => 0
  | x :: xs => max (e x) (maxOver e xs)

theorem le_maxOver (e : Int → Nat) (xs : List Int) (x : Int) (hx : x ∈ xs) :
    e x ≤ maxOver e xs := by
  induction xs with
  | nil => simp at hx
  | cons y ys ih =>
    simp only [List.mem_cons] at hx
    simp only [maxOver]
    rcases hx with rfl | hx
    · omega
    · have := ih hx; omega

theorem maxOver_attained (e : Int → Nat) (y : Int) (ys : List Int) :
    ∃ x ∈ y :: ys, e x = maxOver e (y :: ys) := by
  induction ys generalizing y with
  | nil => exact ⟨y, by simp, by simp [maxOver]⟩
  | cons z zs ih =>
    obtain ⟨x, hx, hex⟩ := ih z
    by_cases h : maxOver e (z :: zs) ≤ e y
    · exact ⟨y, by simp, by simp only [maxOver] at h ⊢; omega⟩
    · refine ⟨x, List.mem_cons_of_mem _ hx, ?_⟩
      rw [hex]
      show maxOver e (z :: zs) = max (e y) (maxOver e (z :: zs))
      omega

theorem maxOver_le_iff (e : Int → Nat) (xs : List Int) (B : Nat) :
    maxOver e xs ≤ B ↔ ∀ x ∈ xs, e x ≤ B := by
  induction xs with
  | nil => simp [maxOver]
  | cons y ys ih =>
    simp only [maxOver, List.mem_cons, forall_eq_or_imp]
    rw [← ih]
    omega

/-! ## The exact worst-case error checker for networks -/

/-- Absolute prediction error of `f` against the target network `t` at `x`. -/
def errAt (f t : WideNet) (x : Int) : Nat := (predict f x - predict t x).natAbs

/-- Potential bend points of `f - t`. -/
def errKinks (f t : WideNet) : List Int := kinks (f.hidden ++ t.hidden)

/-- Probe points of `f - t` on `[L,U]`. -/
def errProbes (f t : WideNet) (L U : Int) : List Int := probes (errKinks f t) L U

/-- **The checker.** Exact `max_{x ∈ [L,U]} |f x - t x|`, or `0` if `L > U`. -/
def maxAbsErr (f t : WideNet) (L U : Int) : Nat :=
  if L ≤ U then maxOver (errAt f t) (errProbes f t L U) else 0

/-- The number of network evaluations made by the checker. -/
theorem errProbes_length (f t : WideNet) (L U : Int) :
    (errProbes f t L U).length ≤ 3 * (width f + width t) + 2 := by
  have h := probes_length (errKinks f t) L U
  have hk : (errKinks f t).length ≤ 3 * (f.hidden ++ t.hidden).length := by
    unfold errKinks kinks
    generalize f.hidden ++ t.hidden = l
    induction l with
    | nil => simp
    | cons u us ih =>
      simp only [List.flatMap_cons, List.length_append, List.length_cons]
      have : (unitKinks u).length ≤ 3 := by unfold unitKinks; split <;> simp
      omega
  simp only [List.length_append] at hk
  unfold errProbes width
  omega

theorem errAt_secondDiff (f t : WideNet) (z : Int) (hz : z ∉ errKinks f t) :
    SecondDiffZero (fun x => predict f x - predict t x) z := by
  simp only [errKinks, kinks, List.flatMap_append, List.mem_append, not_or] at hz
  exact secondDiff_sub (predict_secondDiff f z hz.1) (predict_secondDiff t z hz.2)

theorem errAt_le_probe (f t : WideNet) (L U x : Int) (hxL : L ≤ x) (hxU : x ≤ U) :
    ∃ p ∈ errProbes f t L U, errAt f t x ≤ errAt f t p :=
  probe_dominates (fun x => predict f x - predict t x) (errKinks f t) L U
    (fun z _ _ hz => errAt_secondDiff f t z hz) x hxL hxU

/-- **Upper bound.** The checker bounds the error at every integer of `[L,U]`. -/
theorem errAt_le_maxAbsErr (f t : WideNet) (L U x : Int) (hxL : L ≤ x) (hxU : x ≤ U) :
    errAt f t x ≤ maxAbsErr f t L U := by
  obtain ⟨p, hp, hle⟩ := errAt_le_probe f t L U x hxL hxU
  unfold maxAbsErr
  rw [if_pos (by omega)]
  exact Nat.le_trans hle (le_maxOver _ _ p hp)

/-- **Attainment.** On a nonempty interval the checker's value is attained at an integer
of `[L,U]`; together with `errAt_le_maxAbsErr` it is exactly the maximum. -/
theorem maxAbsErr_attained (f t : WideNet) (L U : Int) (hLU : L ≤ U) :
    ∃ x, L ≤ x ∧ x ≤ U ∧ errAt f t x = maxAbsErr f t L U := by
  obtain ⟨x, hx, hex⟩ := maxOver_attained (errAt f t) L
    (U :: (errKinks f t).filter (inIv L U))
  have hI := probes_in_interval (errKinks f t) L U hLU x hx
  refine ⟨x, hI.1, hI.2, ?_⟩
  unfold maxAbsErr
  rw [if_pos hLU]
  exact hex

/-- **Exactness**, stated as a single theorem. -/
theorem maxAbsErr_isMax (f t : WideNet) (L U : Int) (hLU : L ≤ U) :
    (∀ x, L ≤ x → x ≤ U → errAt f t x ≤ maxAbsErr f t L U) ∧
      ∃ x, L ≤ x ∧ x ≤ U ∧ errAt f t x = maxAbsErr f t L U :=
  ⟨fun x h1 h2 => errAt_le_maxAbsErr f t L U x h1 h2, maxAbsErr_attained f t L U hLU⟩

/-- The semantic statement "`B` bounds the error of `f` on `[L,U]`". -/
def ErrBound (f t : WideNet) (L U : Int) (B : Nat) : Prop :=
  ∀ x, L ≤ x → x ≤ U → errAt f t x ≤ B

/-- **Sound and complete bound check.** -/
theorem maxAbsErr_le_iff (f t : WideNet) (L U : Int) (B : Nat) :
    maxAbsErr f t L U ≤ B ↔ ErrBound f t L U B := by
  constructor
  · intro h x h1 h2
    exact Nat.le_trans (errAt_le_maxAbsErr f t L U x h1 h2) h
  · intro h
    by_cases hLU : L ≤ U
    · obtain ⟨x, h1, h2, hx⟩ := maxAbsErr_attained f t L U hLU
      rw [← hx]
      exact h x h1 h2
    · simp [maxAbsErr, hLU]

/-- Executable bound check. -/
def checkErrBound (f t : WideNet) (L U : Int) (B : Nat) : Bool :=
  decide (maxAbsErr f t L U ≤ B)

theorem checkErrBound_iff (f t : WideNet) (L U : Int) (B : Nat) :
    checkErrBound f t L U B = true ↔ ErrBound f t L U B := by
  simp [checkErrBound, maxAbsErr_le_iff]

/-! ## Witnesses for violated bounds -/

/-- Returns an integer of `[L,U]` at which the error exceeds `B`, if there is one. -/
def findErrViolation (f t : WideNet) (L U : Int) (B : Nat) : Option Int :=
  if L ≤ U then (errProbes f t L U).find? (fun x => decide (B < errAt f t x)) else none

/-- **Witness soundness.** -/
theorem findErrViolation_sound (f t : WideNet) (L U : Int) (B : Nat) (x : Int)
    (h : findErrViolation f t L U B = some x) :
    L ≤ x ∧ x ≤ U ∧ B < errAt f t x := by
  unfold findErrViolation at h
  split at h
  · rename_i hLU
    have hmem := List.mem_of_find?_eq_some h
    have hp := List.find?_some h
    have := probes_in_interval _ L U hLU x hmem
    exact ⟨this.1, this.2, by simpa using hp⟩
  · simp at h

/-- **Witness completeness.** If the bound is violated anywhere in `[L,U]`, a witness is
returned. -/
theorem findErrViolation_complete (f t : WideNet) (L U : Int) (B : Nat)
    (h : ∃ x, L ≤ x ∧ x ≤ U ∧ B < errAt f t x) :
    ∃ x, findErrViolation f t L U B = some x := by
  obtain ⟨x, h1, h2, h3⟩ := h
  obtain ⟨p, hp, hle⟩ := errAt_le_probe f t L U x h1 h2
  cases hf : findErrViolation f t L U B with
  | some y => exact ⟨y, rfl⟩
  | none =>
    unfold findErrViolation at hf
    rw [if_pos (by omega)] at hf
    have := List.find?_eq_none.mp hf p hp
    simp at this
    omega

theorem findErrViolation_none_iff (f t : WideNet) (L U : Int) (B : Nat) :
    findErrViolation f t L U B = none ↔ ErrBound f t L U B := by
  constructor
  · intro h x h1 h2
    apply Classical.byContradiction
    intro hx
    obtain ⟨y, hy⟩ := findErrViolation_complete f t L U B ⟨x, h1, h2, by omega⟩
    rw [h] at hy
    cases hy
  · intro h
    cases hf : findErrViolation f t L U B with
    | none => rfl
    | some x =>
      have := findErrViolation_sound f t L U B x hf
      have := h x this.1 this.2.1
      omega

/-! ## Bounded-region robustness: the worst-case error does not increase -/

/-- The candidate `m`'s worst-case error on `[L,U]` is at most the incumbent `a`'s. -/
def robustB (a m t : WideNet) (L U : Int) : Bool :=
  decide (maxAbsErr m t L U ≤ maxAbsErr a t L U)

/-- **Robustness check, semantic form.** The check succeeds exactly when every error bound
that holds for the incumbent on `[L,U]` also holds for the candidate. -/
theorem robustB_iff (a m t : WideNet) (L U : Int) :
    robustB a m t L U = true ↔
      ∀ B : Nat, ErrBound a t L U B → ErrBound m t L U B := by
  simp only [robustB, decide_eq_true_eq]
  constructor
  · intro h B hB
    rw [← maxAbsErr_le_iff] at hB ⊢
    omega
  · intro h
    have := h (maxAbsErr a t L U) ((maxAbsErr_le_iff a t L U _).mp (Nat.le_refl _))
    exact (maxAbsErr_le_iff m t L U _).mpr this

/-- Pointwise form: every error of the candidate in `[L,U]` is matched or exceeded by some
error of the incumbent in `[L,U]`. -/
theorem robustB_iff_pointwise (a m t : WideNet) (L U : Int) :
    robustB a m t L U = true ↔
      ∀ x, L ≤ x → x ≤ U → ∃ y, L ≤ y ∧ y ≤ U ∧ errAt m t x ≤ errAt a t y := by
  rw [robustB_iff]
  constructor
  · intro h x h1 h2
    obtain ⟨y, hy1, hy2, hy⟩ := maxAbsErr_attained a t L U (by omega)
    refine ⟨y, hy1, hy2, ?_⟩
    rw [hy]
    exact h _ (fun z hz1 hz2 => errAt_le_maxAbsErr a t L U z hz1 hz2) x h1 h2
  · intro h B hB x h1 h2
    obtain ⟨y, hy1, hy2, hy⟩ := h x h1 h2
    exact Nat.le_trans hy (hB y hy1 hy2)

/-- Witness for a robustness violation: an input whose candidate error exceeds the
incumbent's worst case. -/
def findRobustViolation (a m t : WideNet) (L U : Int) : Option Int :=
  findErrViolation m t L U (maxAbsErr a t L U)

theorem findRobustViolation_sound (a m t : WideNet) (L U x : Int)
    (h : findRobustViolation a m t L U = some x) :
    L ≤ x ∧ x ≤ U ∧ ∀ y, L ≤ y → y ≤ U → errAt a t y < errAt m t x := by
  obtain ⟨h1, h2, h3⟩ := findErrViolation_sound m t L U _ x h
  exact ⟨h1, h2, fun y hy1 hy2 => Nat.lt_of_le_of_lt (errAt_le_maxAbsErr a t L U y hy1 hy2) h3⟩

theorem findRobustViolation_none_iff (a m t : WideNet) (L U : Int) :
    findRobustViolation a m t L U = none ↔ robustB a m t L U = true := by
  unfold findRobustViolation
  rw [findErrViolation_none_iff, ← maxAbsErr_le_iff]
  simp [robustB]

/-- **Representation independence.** The checker's value depends only on the functions
computed on `[L,U]`, not on how the networks are written (unit order, dead units, split
units, …), although the probe lists may differ. -/
theorem maxAbsErr_congr {f f' t t' : WideNet} {L U : Int}
    (hf : ∀ x, L ≤ x → x ≤ U → predict f x = predict f' x)
    (ht : ∀ x, L ≤ x → x ≤ U → predict t x = predict t' x) :
    maxAbsErr f t L U = maxAbsErr f' t' L U := by
  have e : ∀ x, L ≤ x → x ≤ U → errAt f t x = errAt f' t' x := by
    intro x h1 h2; simp only [errAt, hf x h1 h2, ht x h1 h2]
  apply Nat.le_antisymm
  · rw [maxAbsErr_le_iff]
    intro x h1 h2
    rw [e x h1 h2]
    exact errAt_le_maxAbsErr f' t' L U x h1 h2
  · rw [maxAbsErr_le_iff]
    intro x h1 h2
    rw [← e x h1 h2]
    exact errAt_le_maxAbsErr f t L U x h1 h2

/-- Robustness is transitive. -/
theorem robustB_trans {a b c t : WideNet} {L U : Int} (h1 : robustB a b t L U = true)
    (h2 : robustB b c t L U = true) : robustB a c t L U = true := by
  simp only [robustB, decide_eq_true_eq] at *
  omega

end PCS.V2.ProofGatedRobust
