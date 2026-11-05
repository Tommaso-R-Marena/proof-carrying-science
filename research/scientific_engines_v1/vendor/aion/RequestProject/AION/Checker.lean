module

public import RequestProject.AION.MassAction

/-!
# Executable certificate checker with machine-checked soundness

Target event: `B = {x | lvl ≤ x jB}` (copy number of species `jB` reaches `lvl`).
Taboo set (upper checker): `A = tabooA zero = {x | ∃ l, zero l ∧ x l = 0}` (some marked
species is extinct).  The lower checker accepts any executable taboo predicate.

## Upper certificates (finite core + infinite exponential tail)

`g(x) = 1` on `B`; `g(x) = T x` on the core box; `g(x) = C·∏ρ_i^{x_i}` outside the box.
`checkUpper` verifies, with exact rational arithmetic:
1. `lvl ≤ box jB`, `C > 0`, all `ρ_i ≥ 1`, `C·ρ_jB^lvl ≥ 1`;
2. `T ≥ 0` and `L g ≤ 0` at every core state not in `A ∪ B` (finite);
3. interface layer: `T x ≤ C·∏ρ_i^{x_i}` at core states within one jump of the tail;
4. for every species `j ≠ jB`, the falling-factorial cell certificate proving that
   the exponential drift polynomial is `≤ 0` on the infinite orthant cell
   `{x | x_j ≥ box j, x_l ≥ 1 for taboo species l}`.
`checkUpper_sound` : if the check returns `true`, then for **every** initial state,
`P_x(reach B before A) ≤ g x`.  No state outside the box is ever enumerated.

## Lower certificates (finite support + Lyapunov escape)

`f = 1` on `B`, `f = F` on core states not in `A`, `0` elsewhere; `V` on the box,
`0` elsewhere.  `checkLower` verifies at every core state with `F > 0` (not in
`A ∪ B`): positive total rate, `L f ≥ 0`, `L V ≤ -(total rate)`, and `V ≥ 0` on the box.
`checkLower_sound` : then `f x ≤ P_x(reach B before A)` for every `x`.
-/

@[expose] public section

open scoped BigOperators

namespace AION
namespace MACRN

variable {d n : ℕ} (N : MACRN d n)

/-- Core box `{x | ∀ i, x i < box i}` as a finset. -/
def boxFS (box : Fin d → ℕ) : Finset (Fin d → ℕ) :=
  Fintype.piFinset (fun i => Finset.range (box i))

lemma mem_boxFS {box : Fin d → ℕ} {x : Fin d → ℕ} : x ∈ boxFS box ↔ ∀ i, x i < box i := by
  simp [boxFS, Fintype.mem_piFinset]

/-! ## Upper certificates -/

/-- Taboo set "some marked species is extinct": `A = {x | ∃ l, zero l ∧ x l = 0}`. -/
def tabooA (zero : Fin d → Bool) (x : Fin d → ℕ) : Bool := decide (∃ l, zero l = true ∧ x l = 0)

/-- Upper (barrier) certificate data. -/
structure UpperCert (d : ℕ) where
  jB : Fin d
  lvl : ℕ
  zero : Fin d → Bool
  box : Fin d → ℕ
  T : (Fin d → ℕ) → ℚ
  C : ℚ
  ρ : Fin d → ℚ

/-- The glued barrier function of an upper certificate. -/
def UpperCert.g (c : UpperCert d) (x : Fin d → ℕ) : ℚ :=
  if c.lvl ≤ x c.jB then 1
  else if ∀ i, x i < c.box i then c.T x
  else c.C * expBar c.ρ x

/-- Largest reactant coefficient (maximal one-jump decrease of any species). -/
def maxInp : ℕ := Finset.univ.sup fun r => Finset.univ.sup fun i => N.inp r i

lemma inp_le_maxInp (r : Fin n) (i : Fin d) : N.inp r i ≤ N.maxInp :=
  le_trans (Finset.le_sup (f := fun i => N.inp r i) (Finset.mem_univ i))
    (Finset.le_sup (f := fun r => Finset.univ.sup fun i => N.inp r i) (Finset.mem_univ r))

/-- Corner of the tail cell attached to species `j`. -/
def UpperCert.corner (c : UpperCert d) (j : Fin d) : Fin d → ℕ :=
  fun i => if i = j then c.box j else if c.zero i then 1 else 0

/-- The executable upper-certificate checker (taboo set `tabooA c.zero`). -/
def checkUpper (c : UpperCert d) : Bool :=
  let A := tabooA c.zero
  decide (c.lvl ≤ c.box c.jB) && decide (0 < c.C) &&
  decide (∀ i, 1 ≤ c.ρ i) && decide (1 ≤ c.C * c.ρ c.jB ^ c.lvl) &&
  decide (∀ x ∈ boxFS c.box, 0 ≤ c.T x ∧
      (A x = false → ¬ c.lvl ≤ x c.jB → N.genQ c.g x ≤ 0) ∧
      ((∃ i, i ≠ c.jB ∧ c.box i ≤ x i + N.maxInp) → ¬ c.lvl ≤ x c.jB →
        c.T x ≤ c.C * expBar c.ρ x)) &&
  decide (∀ j, j = c.jB ∨ N.cellCheck c.ρ (c.corner j) = true)

/-- **Soundness of the upper checker.** -/
theorem checkUpper_sound {c : UpperCert d}
    (hc : N.checkUpper c = true) (x : Fin d → ℕ) :
    N.toJump.hitProb {y | tabooA c.zero y = true} {y | c.lvl ≤ y c.jB} x ≤ (c.g x : ℝ) := by
  simp only [checkUpper, Bool.and_eq_true, decide_eq_true_eq] at hc
  obtain ⟨⟨⟨⟨⟨hbox, hC⟩, hρ⟩, hCB⟩, hcore⟩, hcell⟩ := hc
  have hρpos : ∀ i, 0 < c.ρ i := fun i => lt_of_lt_of_le one_pos (hρ i)
  have he1 : ∀ y : Fin d → ℕ, c.ρ c.jB ^ (y c.jB) ≤ expBar c.ρ y := by
    intro y
    unfold expBar
    rw [Fintype.prod_eq_mul_prod_compl c.jB]
    have : 1 ≤ ∏ i ∈ ({c.jB} : Finset (Fin d))ᶜ, c.ρ i ^ (y i) := by
      have := Finset.prod_le_prod (s := ({c.jB} : Finset (Fin d))ᶜ)
        (f := fun _ => (1:ℚ)) (g := fun i => c.ρ i ^ (y i))
        (fun _ _ => zero_le_one) (fun i _ => one_le_pow₀ (hρ i))
      simpa using this
    have h0 : 0 ≤ c.ρ c.jB ^ (y c.jB) := pow_nonneg (hρpos _).le _
    nlinarith
  have hB1 : ∀ y : Fin d → ℕ, c.lvl ≤ y c.jB → 1 ≤ c.C * expBar c.ρ y := by
    intro y h1
    calc (1 : ℚ) ≤ c.C * c.ρ c.jB ^ c.lvl := hCB
      _ ≤ c.C * c.ρ c.jB ^ (y c.jB) :=
          mul_le_mul_of_nonneg_left (pow_le_pow_right₀ (hρ _) h1) hC.le
      _ ≤ c.C * expBar c.ρ y := mul_le_mul_of_nonneg_left (he1 y) hC.le
  have hg0 : ∀ y, 0 ≤ c.g y := by
    intro y
    have hCe : 0 ≤ c.C * expBar c.ρ y := mul_nonneg hC.le (expBar_pos hρpos y).le
    unfold UpperCert.g
    split_ifs with h1 h2
    · norm_num
    · exact (hcore y (mem_boxFS.mpr h2)).1
    · exact hCe
  apply JumpModel.hitProb_le_of_supersolution
  · intro y; exact_mod_cast hg0 y
  · intro y hy
    simp only [Set.mem_setOf_eq] at hy
    simp [UpperCert.g, hy]
  · intro y hA hB
    simp only [Set.mem_setOf_eq, Bool.not_eq_true] at hA hB
    rw [← genQ_cast]
    by_cases hin : ∀ i, y i < c.box i
    · exact_mod_cast (hcore y (mem_boxFS.mpr hin)).2.1 hA hB
    · push_neg at hin
      obtain ⟨j, hj⟩ := hin
      have hjB : j ≠ c.jB := by
        rintro rfl; exact hB (le_trans hbox hj)
      have hcorner : ∀ i, c.corner j i ≤ y i := by
        intro i
        unfold UpperCert.corner
        split_ifs with h1 h2
        · subst h1; exact hj
        · have : ¬ (tabooA c.zero y = true) := by simpa using hA
          unfold tabooA at this
          simp only [decide_eq_true_eq, not_exists, not_and] at this
          have := this i h2; omega
        · exact Nat.zero_le _
      have hdrift := N.cellCheck_sound ((hcell j).resolve_left hjB) y hcorner
      have heq : c.g y = c.C * expBar c.ρ y := by
        simp only [UpperCert.g, hB, if_false]
        rw [if_neg (by push_neg; exact ⟨j, hj⟩)]
      have hle : ∀ r, N.toJump.rate r y ≠ 0 →
          c.g (N.next r y) ≤ c.C * expBar c.ρ (N.next r y) := by
        intro r hr
        have hr' : N.prop r y ≠ 0 := by
          intro h0; apply hr; simp [toJump, h0]
        set z := N.next r y with hz
        unfold UpperCert.g
        split_ifs with h1 h2
        · exact hB1 z h1
        · refine (hcore z (mem_boxFS.mpr h2)).2.2 ⟨j, hjB, ?_⟩ h1
          have hinp := N.inp_le_maxInp r j
          have : z j = y j - N.inp r j + N.out r j := rfl
          omega
        · exact le_rfl
      have h1 : N.genQ c.g y ≤ N.genQ (fun z => c.C * expBar c.ρ z) y := by
        have := JumpModel.gen_le_of_le_on_jumps (M := N.toJump) (g := fun z => (c.g z : ℝ))
          (φ := fun z => ((c.C * expBar c.ρ z : ℚ) : ℝ)) (x := y)
          (fun r hr => by
            simp only [toJump]
            exact_mod_cast hle r hr) (by simp only; exact_mod_cast heq)
        rw [← genQ_cast, ← genQ_cast] at this
        exact_mod_cast this
      rw [N.genQ_expBar hρpos] at h1
      have : c.C * expBar c.ρ y * N.driftVal c.ρ y ≤ 0 :=
        mul_nonpos_of_nonneg_of_nonpos (mul_nonneg hC.le (expBar_pos hρpos y).le) hdrift
      exact_mod_cast le_trans h1 this

/-! ## Lower certificates -/

/-- Lower (subsolution + escape) certificate data. -/
structure LowerCert (d : ℕ) where
  jB : Fin d
  lvl : ℕ
  box : Fin d → ℕ
  F : (Fin d → ℕ) → ℚ
  V : (Fin d → ℕ) → ℚ

/-- Lower-bound function. -/
def LowerCert.f (A : (Fin d → ℕ) → Bool) (c : LowerCert d) (x : Fin d → ℕ) : ℚ :=
  if c.lvl ≤ x c.jB then 1
  else if (∀ i, x i < c.box i) ∧ A x = false then c.F x else 0

/-- Escape (Lyapunov) function. -/
def LowerCert.Vf (c : LowerCert d) (x : Fin d → ℕ) : ℚ :=
  if ∀ i, x i < c.box i then c.V x else 0

/-- The executable lower-certificate checker. -/
def checkLower (A : (Fin d → ℕ) → Bool) (c : LowerCert d) : Bool :=
  decide (∀ x ∈ boxFS c.box, 0 ≤ c.V x ∧
    (A x = false → ¬ c.lvl ≤ x c.jB → 0 < c.F x →
      0 < N.totalQ x ∧ 0 ≤ N.genQ (c.f A) x ∧ N.genQ c.Vf x ≤ -N.totalQ x))

/-- **Soundness of the lower checker.** -/
theorem checkLower_sound {A : (Fin d → ℕ) → Bool} {c : LowerCert d}
    (hc : N.checkLower A c = true) (x : Fin d → ℕ) :
    ((c.f A x : ℚ) : ℝ) ≤ N.toJump.hitProb {y | A y = true} {y | c.lvl ≤ y c.jB} x := by
  simp only [checkLower, decide_eq_true_eq] at hc
  set D : Set (Fin d → ℕ) :=
    {y | (∀ i, y i < c.box i) ∧ A y = false ∧ ¬ c.lvl ≤ y c.jB ∧ 0 < c.F y} with hD
  set Cb : ℚ := 1 + ∑ y ∈ boxFS c.box, |c.F y| with hCb
  have hsum0 : 0 ≤ ∑ y ∈ boxFS c.box, |c.F y| := Finset.sum_nonneg (fun _ _ => abs_nonneg _)
  refine JumpModel.le_hitProb_of_subsolution (M := N.toJump) (A := {y | A y = true})
    (B := {y | c.lvl ≤ y c.jB}) (f := fun y => ((c.f A y : ℚ) : ℝ)) (D := D) (C := (Cb : ℝ))
    (V := fun y => ((c.Vf y : ℚ) : ℝ)) ?_ ?_ ?_ ?_ ?_ ?_ ?_ ?_ ?_ x
  · intro y hy; exact hy.2.2.1
  · intro y hy; simp [hy.2.1]
  · intro y hy
    rw [← totalQ_cast]
    exact_mod_cast (hc y (mem_boxFS.mpr hy.1)).2 hy.2.1 hy.2.2.1 hy.2.2.2 |>.1
  · intro y
    have : c.f A y ≤ Cb := by
      unfold LowerCert.f
      split_ifs with h1 h2
      · linarith
      · have hmem : y ∈ boxFS c.box := mem_boxFS.mpr h2.1
        have : |c.F y| ≤ ∑ z ∈ boxFS c.box, |c.F z| :=
          Finset.single_le_sum (f := fun z => |c.F z|) (fun _ _ => abs_nonneg _) hmem
        linarith [le_abs_self (c.F y)]
      · linarith
    simp only; exact_mod_cast this
  · intro y hy
    simp only [Set.mem_setOf_eq] at hy
    simp [LowerCert.f, hy]
  · intro y hyD hyB
    simp only [Set.mem_setOf_eq] at hyB
    have : c.f A y ≤ 0 := by
      unfold LowerCert.f
      rw [if_neg hyB]
      split_ifs with h2
      · by_contra hpos; push_neg at hpos
        exact hyD ⟨h2.1, h2.2, hyB, hpos⟩
      · exact le_rfl
    simp only; exact_mod_cast this
  · intro y hy
    rw [← genQ_cast]
    exact_mod_cast ((hc y (mem_boxFS.mpr hy.1)).2 hy.2.1 hy.2.2.1 hy.2.2.2).2.1
  · intro y
    have : 0 ≤ c.Vf y := by
      unfold LowerCert.Vf
      split_ifs with h
      · exact (hc y (mem_boxFS.mpr h)).1
      · exact le_rfl
    simp only; exact_mod_cast this
  · intro y hy
    rw [← genQ_cast, ← totalQ_cast]
    exact_mod_cast ((hc y (mem_boxFS.mpr hy.1)).2 hy.2.1 hy.2.2.1 hy.2.2.2).2.2

end MACRN
end AION
