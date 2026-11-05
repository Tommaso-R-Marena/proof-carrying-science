module

public import RequestProject.AION.Composition

/-!
# Mass-action chemical reaction networks and exponential tail barriers

* `MACRN d n` : a mass-action network with `d` species and `n` reactions, exact
  rational rate constants, input/output stoichiometry.  Its propensity is
  `k_r ∏_i x_i (x_i-1) ⋯ (x_i - α_ri + 1)` (falling factorials), and
  `toJump` is the corresponding jump model on `ℕ^d`.
* `next_add_inp` : whenever a reaction has positive propensity, the truncated
  natural-number update `x - α + β` is the exact stoichiometric update.
* `gen_expBar` : for the exponential barrier `e(x) = ∏ ρ_i^{x_i}` the generator
  factorises exactly as `L(C·e)(x) = C·e(x)·P(x)` with the *drift polynomial*
  `P(x) = ∑_r k_r (∏_i ρ_i^{β_ri-α_ri} - 1) ∏_i (x_i)_{α_ri}`.  This holds for
  reactions that change several species at once (no Leibniz approximation).
* `cellCheck_sound` : an exact, finitely checkable certificate that `P ≤ 0` on the
  whole infinite orthant cell `{x | x ≥ m}`: expand `P` in the falling-factorial
  basis after the shift `x = m + t` (falling-factorial Vandermonde identity; all
  shift coefficients are nonnegative) and require every combined coefficient to be
  `≤ 0`.  Falling-factorial basis functions are `≥ 0` on `ℕ^d`.
-/

@[expose] public section

open scoped BigOperators
open Classical

namespace AION

open Nat in
/-- Falling-factorial Vandermonde identity. -/
theorem descFactorial_add_vandermonde (a b n : ℕ) :
    (a + b).descFactorial n =
      ∑ k ∈ Finset.range (n + 1), n.choose k * a.descFactorial (n - k) * b.descFactorial k := by
  rw [Nat.descFactorial_eq_factorial_mul_choose, Nat.add_choose_eq, Finset.mul_sum,
    Finset.Nat.sum_antidiagonal_eq_sum_range_succ (fun i j => n ! * (a.choose i * b.choose j))]
  rw [← Finset.sum_range_reflect]
  apply Finset.sum_congr rfl
  intro k hk
  have hk' : k ≤ n := Nat.lt_succ_iff.mp (Finset.mem_range.mp hk)
  simp only [Nat.descFactorial_eq_factorial_mul_choose]
  have h1 : n + 1 - 1 - k = n - k := by omega
  have h2 : n - (n - k) = k := by omega
  rw [h1, h2]
  have := Nat.choose_mul_factorial_mul_factorial hk'
  calc n ! * (a.choose (n - k) * b.choose k)
      = (n.choose k * k ! * (n - k)!) * (a.choose (n - k) * b.choose k) := by rw [this]
    _ = _ := by ring

/-- A mass-action reaction network with `d` species and `n` reactions. -/
structure MACRN (d n : ℕ) where
  inp : Fin n → Fin d → ℕ
  out : Fin n → Fin d → ℕ
  k : Fin n → ℚ
  k_nonneg : ∀ r, 0 ≤ k r

namespace MACRN

variable {d n : ℕ} (N : MACRN d n)

/-- Mass-action propensity (exact rational). -/
def prop (r : Fin n) (x : Fin d → ℕ) : ℚ :=
  N.k r * ∏ i, ((x i).descFactorial (N.inp r i) : ℚ)

/-- State update `x - α_r + β_r` (exact whenever the propensity is positive). -/
def next (r : Fin n) (x : Fin d → ℕ) : Fin d → ℕ := fun i => x i - N.inp r i + N.out r i

lemma prop_nonneg (r : Fin n) (x : Fin d → ℕ) : 0 ≤ N.prop r x :=
  mul_nonneg (N.k_nonneg r) (Finset.prod_nonneg (fun _ _ => Nat.cast_nonneg _))

/-- The jump model (continuous-time Markov chain) of the network. -/
noncomputable def toJump : JumpModel (Fin d → ℕ) (Fin n) where
  rate r x := (N.prop r x : ℝ)
  rate_nonneg r x := by exact_mod_cast N.prop_nonneg r x
  next := N.next

/-- A reaction with nonzero propensity has all its reactants present. -/
lemma inp_le_of_prop_ne_zero {r : Fin n} {x : Fin d → ℕ} (h : N.prop r x ≠ 0) (i : Fin d) :
    N.inp r i ≤ x i := by
  by_contra hlt
  push_neg at hlt
  apply h
  unfold prop
  rw [Finset.prod_eq_zero (Finset.mem_univ i)]
  · simp
  · simp [Nat.descFactorial_eq_zero_iff_lt.mpr hlt]

/-- Exactness of the stoichiometric update for enabled reactions (in `ℤ`). -/
lemma next_add_inp {r : Fin n} {x : Fin d → ℕ} (h : N.prop r x ≠ 0) (i : Fin d) :
    ((N.next r x i : ℕ) : ℤ) = x i + (N.out r i : ℤ) - N.inp r i := by
  have := N.inp_le_of_prop_ne_zero h i
  simp only [next]; push_cast [this]; ring

/-- Total rate (exact rational). -/
def totalQ (x : Fin d → ℕ) : ℚ := ∑ r, N.prop r x

/-- Generator on rational-valued functions (exact rational). -/
def genQ (g : (Fin d → ℕ) → ℚ) (x : Fin d → ℕ) : ℚ :=
  ∑ r, N.prop r x * (g (N.next r x) - g x)

lemma totalQ_cast (x : Fin d → ℕ) : ((N.totalQ x : ℚ) : ℝ) = N.toJump.totalRate x := by
  simp [totalQ, JumpModel.totalRate, toJump]

lemma genQ_cast (g : (Fin d → ℕ) → ℚ) (x : Fin d → ℕ) :
    ((N.genQ g x : ℚ) : ℝ) = N.toJump.gen (fun y => (g y : ℝ)) x := by
  simp [genQ, JumpModel.gen, toJump]

/-! ## Exponential barriers -/

/-- Exponential barrier `∏ ρ_i^{x_i}`. -/
def expBar (ρ : Fin d → ℚ) (x : Fin d → ℕ) : ℚ := ∏ i, ρ i ^ (x i)

/-- Multiplicative jump factor of reaction `r` minus one. -/
def jumpFactor (ρ : Fin d → ℚ) (r : Fin n) : ℚ :=
  (∏ i, ρ i ^ (N.out r i)) / (∏ i, ρ i ^ (N.inp r i)) - 1

/-- Drift polynomial value `P(x) = ∑_r k_r c_r ∏_i (x_i)_{α_ri}`. -/
def driftVal (ρ : Fin d → ℚ) (x : Fin d → ℕ) : ℚ :=
  ∑ r, N.k r * N.jumpFactor ρ r * ∏ i, ((x i).descFactorial (N.inp r i) : ℚ)

lemma expBar_pos {ρ : Fin d → ℚ} (hρ : ∀ i, 0 < ρ i) (x : Fin d → ℕ) : 0 < expBar ρ x :=
  Finset.prod_pos (fun i _ => pow_pos (hρ i) _)

lemma expBar_next {ρ : Fin d → ℚ} (hρ : ∀ i, 0 < ρ i) {r : Fin n} {x : Fin d → ℕ}
    (h : N.prop r x ≠ 0) :
    expBar ρ (N.next r x) = expBar ρ x * (N.jumpFactor ρ r + 1) := by
  have hinp := N.inp_le_of_prop_ne_zero h
  have hden : (∏ i, ρ i ^ (N.inp r i)) ≠ 0 :=
    Finset.prod_ne_zero_iff.mpr (fun i _ => pow_ne_zero _ (hρ i).ne')
  rw [jumpFactor, sub_add_cancel, expBar, expBar, mul_div_assoc', eq_div_iff hden]
  rw [← Finset.prod_mul_distrib, ← Finset.prod_mul_distrib]
  refine Finset.prod_congr rfl (fun i _ => ?_)
  rw [← pow_add, ← pow_add]
  congr 1
  simp only [next]
  have := hinp i
  omega

/-- **Exact generator factorisation for exponential barriers.** -/
theorem genQ_expBar {ρ : Fin d → ℚ} (hρ : ∀ i, 0 < ρ i) (C : ℚ) (x : Fin d → ℕ) :
    N.genQ (fun y => C * expBar ρ y) x = C * expBar ρ x * N.driftVal ρ x := by
  unfold genQ driftVal
  rw [Finset.mul_sum]
  refine Finset.sum_congr rfl (fun r _ => ?_)
  by_cases h : N.prop r x = 0
  · rw [h, zero_mul]
    unfold prop at h
    rcases mul_eq_zero.mp h with h' | h'
    · rw [h']; ring
    · rw [h']; ring
  · show N.prop r x * (C * expBar ρ (N.next r x) - C * expBar ρ x) = _
    rw [N.expBar_next hρ h]
    unfold prop
    ring

/-! ## Falling-factorial cell certificates -/

/-- Falling-factorial basis function `∏_i (t_i)_{e_i}` (nonnegative on `ℕ^d`). -/
def ffBasis (e t : Fin d → ℕ) : ℚ := ∏ i, ((t i).descFactorial (e i) : ℚ)

lemma ffBasis_nonneg (e t : Fin d → ℕ) : 0 ≤ ffBasis e t :=
  Finset.prod_nonneg (fun _ _ => Nat.cast_nonneg _)

/-- Value of a sparse polynomial given in the falling-factorial basis. -/
def evalTerms (L : List ((Fin d → ℕ) × ℚ)) (t : Fin d → ℕ) : ℚ :=
  (L.map (fun p => p.2 * ffBasis p.1 t)).sum

/-- Shift coordinate `j` by `m` (falling-factorial Vandermonde expansion). -/
def shift1 (j : Fin d) (m : ℕ) (L : List ((Fin d → ℕ) × ℚ)) : List ((Fin d → ℕ) × ℚ) :=
  L.flatMap fun p =>
    (List.range (p.1 j + 1)).map fun kk =>
      (Function.update p.1 j kk,
        p.2 * ((p.1 j).choose kk : ℚ) * (m.descFactorial (p.1 j - kk) : ℚ))

lemma evalTerms_cons (q : (Fin d → ℕ) × ℚ) (L : List ((Fin d → ℕ) × ℚ)) (t : Fin d → ℕ) :
    evalTerms (q :: L) t = q.2 * ffBasis q.1 t + evalTerms L t := by
  simp [evalTerms]

lemma evalTerms_append (L₁ L₂ : List ((Fin d → ℕ) × ℚ)) (t : Fin d → ℕ) :
    evalTerms (L₁ ++ L₂) t = evalTerms L₁ t + evalTerms L₂ t := by
  simp [evalTerms]

theorem evalTerms_shift1 (j : Fin d) (m : ℕ) (L : List ((Fin d → ℕ) × ℚ)) (t : Fin d → ℕ) :
    evalTerms (shift1 j m L) t = evalTerms L (Function.update t j (t j + m)) := by
  induction L with
  | nil => simp [shift1, evalTerms]
  | cons q L ih =>
    rw [shift1, List.flatMap_cons, evalTerms_append, ← shift1, ih, evalTerms_cons]
    congr 1
    set t' := Function.update t j (t j + m)
    have hrest : ∀ kk, ffBasis (Function.update q.1 j kk) t =
        ((t j).descFactorial kk : ℚ) *
          ∏ i ∈ ({j} : Finset (Fin d))ᶜ, ((t i).descFactorial (q.1 i) : ℚ) := by
      intro kk
      unfold ffBasis
      rw [Fintype.prod_eq_mul_prod_compl j]
      congr 1
      · simp
      · refine Finset.prod_congr rfl (fun i hi => ?_)
        have hij : i ≠ j := by simpa using hi
        simp [Function.update_of_ne hij]
    have hmain : ffBasis q.1 t' = ((m + t j).descFactorial (q.1 j) : ℚ) *
          ∏ i ∈ ({j} : Finset (Fin d))ᶜ, ((t i).descFactorial (q.1 i) : ℚ) := by
      unfold ffBasis
      rw [Fintype.prod_eq_mul_prod_compl j]
      congr 1
      · simp [t', add_comm]
      · refine Finset.prod_congr rfl (fun i hi => ?_)
        have hij : i ≠ j := by simpa using hi
        simp [t', Function.update_of_ne hij]
    rw [hmain, descFactorial_add_vandermonde]
    push_cast
    rw [evalTerms, List.map_map]
    rw [show ∀ (f : ℕ → ℚ) (k : ℕ), ((List.range k).map f).sum = ∑ i ∈ Finset.range k, f i
      from fun f k => rfl]
    rw [Finset.sum_mul, Finset.mul_sum]
    refine Finset.sum_congr rfl (fun kk _ => ?_)
    simp only [Function.comp_apply]
    rw [hrest]
    ring

/-- Shift every coordinate in the list `js` by `m`. -/
def shiftList (m : Fin d → ℕ) : List (Fin d) → List ((Fin d → ℕ) × ℚ) → List ((Fin d → ℕ) × ℚ)
  | [], L => L
  | j :: js, L => shift1 j (m j) (shiftList m js L)

theorem evalTerms_shiftList (m : Fin d → ℕ) :
    ∀ (js : List (Fin d)), js.Nodup → ∀ (L : List ((Fin d → ℕ) × ℚ)) (t : Fin d → ℕ),
      evalTerms (shiftList m js L) t = evalTerms L (fun i => if i ∈ js then t i + m i else t i)
  | [], _, L, t => by simp [shiftList]
  | j :: js, hnd, L, t => by
      rw [shiftList, evalTerms_shift1, evalTerms_shiftList m js (List.nodup_cons.mp hnd).2]
      have hj : j ∉ js := (List.nodup_cons.mp hnd).1
      congr 1
      funext i
      by_cases hij : i = j
      · subst hij; simp [hj]
      · simp [hij]

/-- Shift all coordinates by `m`. -/
def shiftAll (m : Fin d → ℕ) (L : List ((Fin d → ℕ) × ℚ)) : List ((Fin d → ℕ) × ℚ) :=
  shiftList m (List.finRange d) L

theorem evalTerms_shiftAll (m : Fin d → ℕ) (L : List ((Fin d → ℕ) × ℚ)) (t : Fin d → ℕ) :
    evalTerms (shiftAll m L) t = evalTerms L (fun i => t i + m i) := by
  rw [shiftAll, evalTerms_shiftList m _ (List.nodup_finRange d)]
  simp

/-- The drift polynomial of the exponential barrier, in the falling-factorial basis. -/
def driftTerms (ρ : Fin d → ℚ) : List ((Fin d → ℕ) × ℚ) :=
  (List.finRange n).map fun r => (N.inp r, N.k r * N.jumpFactor ρ r)

lemma evalTerms_driftTerms (ρ : Fin d → ℚ) (x : Fin d → ℕ) :
    evalTerms (N.driftTerms ρ) x = N.driftVal ρ x := by
  rw [evalTerms, driftTerms, List.map_map]
  rfl

/-- Combined coefficient of a basis element in a term list. -/
def groupedCoeff (L : List ((Fin d → ℕ) × ℚ)) (e : Fin d → ℕ) : ℚ :=
  ((L.filter (fun q => q.1 = e)).map Prod.snd).sum

/-- The executable cell check: after shifting to the cell corner `m`, every combined
falling-factorial coefficient of the drift polynomial is `≤ 0`. -/
def cellCheck (ρ : Fin d → ℚ) (m : Fin d → ℕ) : Bool :=
  let L := shiftAll m (N.driftTerms ρ)
  L.all fun p => decide (groupedCoeff L p.1 ≤ 0)

lemma list_sum_eq_grouped (L : List ((Fin d → ℕ) × ℚ)) (b : (Fin d → ℕ) → ℚ) :
    (L.map (fun p => p.2 * b p.1)).sum =
      ∑ e ∈ (L.map Prod.fst).toFinset, groupedCoeff L e * b e := by
  induction L with
  | nil => simp
  | cons q L ih =>
    have hG : ∀ e, groupedCoeff (q :: L) e = (if q.1 = e then q.2 else 0) + groupedCoeff L e := by
      intro e; unfold groupedCoeff
      by_cases h : q.1 = e <;> simp [h]
    simp only [List.map_cons, List.sum_cons, List.toFinset_cons, hG, add_mul,
      Finset.sum_add_distrib, ih]
    rw [Finset.sum_insert_of_eq_zero_if_notMem (s := (L.map Prod.fst).toFinset)
      (f := fun e => groupedCoeff L e * b e)]
    · congr 1
      simp only [ite_mul, zero_mul]
      rw [Finset.sum_ite_eq]; simp
    · intro hq
      have : groupedCoeff L q.1 = 0 := by
        unfold groupedCoeff
        rw [List.filter_eq_nil_iff.mpr]
        · simp
        · intro p hp
          simp only [decide_eq_true_eq]
          intro he; apply hq
          rw [List.mem_toFinset, List.mem_map]; exact ⟨p, hp, he⟩
      simp [this]

lemma list_sum_nonpos_of_grouped (L : List ((Fin d → ℕ) × ℚ)) (b : (Fin d → ℕ) → ℚ)
    (hb : ∀ e, 0 ≤ b e) (h : ∀ p ∈ L, groupedCoeff L p.1 ≤ 0) :
    (L.map (fun p => p.2 * b p.1)).sum ≤ 0 := by
  rw [list_sum_eq_grouped]
  refine Finset.sum_nonpos (fun e he => ?_)
  rw [List.mem_toFinset, List.mem_map] at he
  obtain ⟨p, hp, rfl⟩ := he
  exact mul_nonpos_of_nonpos_of_nonneg (h p hp) (hb _)

/-- **Soundness of the cell check**: the drift polynomial is `≤ 0` on the entire
infinite orthant cell `{x | m ≤ x}`. -/
theorem cellCheck_sound {ρ : Fin d → ℚ} {m : Fin d → ℕ} (h : N.cellCheck ρ m = true)
    (x : Fin d → ℕ) (hx : ∀ i, m i ≤ x i) : N.driftVal ρ x ≤ 0 := by
  have hx' : x = fun i => (x i - m i) + m i := by
    funext i; have := hx i; omega
  rw [← evalTerms_driftTerms, hx', ← evalTerms_shiftAll]
  apply list_sum_nonpos_of_grouped (shiftAll m (N.driftTerms ρ)) _ (fun e => ffBasis_nonneg e _)
  intro p hp
  unfold cellCheck at h
  simpa using List.all_eq_true.mp h p hp

end MACRN
end AION
