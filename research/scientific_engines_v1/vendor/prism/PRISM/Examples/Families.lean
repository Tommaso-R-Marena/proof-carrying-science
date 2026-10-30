module

public import PRISM.Certificates.Checker

/-!
# Parameterized families and formal negative results

1. **Regulator-activity family (`orProblem n`)** — `2^n` models, `n` unit-cost
   single-regulator assays, query "is any regulator active?".  For *every* `n` the
   exact minimax cost is `n` (`or_value`).  The lower bound is certified by a
   symbolic adversary on a core of only `n + 1` models (`orLB_isAdversary`), and
   transferred to the `2^n`-model space by monotonicity (the optimality sandwich).
   (Mathematically this is the classical evasiveness of `OR_n` in decision-tree
   complexity; the point here is the machine-checked, enumeration-free certificate.)
2. **Pointer family (`ptrProblem n`)** — an adaptivity gap: an adaptive policy
   succeeds with worst-case cost `2` (`ptr_adaptive`), while every successful
   nonadaptive design costs at least `n + 1` (`ptr_nonadaptive`), for every `n ≥ 2`.
3. **Greedy trap (`trapP`)** — the one-step-optimal (minimum worst-case posterior
   width) first experiment is strictly suboptimal: every policy starting with it
   costs `≥ 5` while the exact optimum is `4` (`trap_greedy_suboptimal`,
   `trap_value`).
-/

@[expose] public section

namespace PRISM.Families

open Problem

/-! ## 1. Regulator-activity (OR) family -/

section OrFamily

variable (n : ℕ)

/-- `2^n` candidate regulator-activity patterns; assay `j` reveals regulator `j`;
query: `1` if some regulator is active, else `0`. -/
def orProblem : Problem (Fin n → Bool) (Fin n) Bool where
  obs m j := m j
  q m := if ∃ j, m j = true then 1 else 0
  cost _ := 1

/-- No regulator active. -/
def zeroModel : Fin n → Bool := fun _ => false

/-- Exactly regulator `i` active. -/
def unitModel (i : Fin n) : Fin n → Bool := fun j => decide (j = i)

/-- The `n + 1`-model adversarial core. -/
def orCore : Finset (Fin n → Bool) := insert (zeroModel n) (Finset.univ.image (unitModel n))

variable {n}

lemma unitModel_injective : Function.Injective (unitModel n) := by
  intro i j h
  have := congrFun h i
  simp [unitModel] at this
  exact this

lemma zero_ne_unit (i : Fin n) : zeroModel n ≠ unitModel n i := by
  intro h
  have := congrFun h i
  simp [zeroModel, unitModel] at this

lemma orCore_card : (orCore n).card = n + 1 := by
  rw [orCore, Finset.card_insert_of_notMem, Finset.card_image_of_injective _ unitModel_injective,
    Finset.card_univ, Fintype.card_fin]
  simp only [Finset.mem_image, Finset.mem_univ, true_and, not_exists]
  intro i h
  exact zero_ne_unit i h.symm

lemma mem_orCore {m : Fin n → Bool} :
    m ∈ orCore n ↔ m = zeroModel n ∨ ∃ i, m = unitModel n i := by
  simp only [orCore, Finset.mem_insert, Finset.mem_image, Finset.mem_univ, true_and]
  constructor
  · rintro (h | ⟨i, rfl⟩)
    · exact Or.inl h
    · exact Or.inr ⟨i, rfl⟩
  · rintro (h | ⟨i, rfl⟩)
    · exact Or.inl h
    · exact Or.inr ⟨i, rfl⟩

lemma zero_mem_orCore : zeroModel n ∈ orCore n := mem_orCore.2 (Or.inl rfl)

lemma orq_zero : (orProblem n).q (zeroModel n) = 0 := by simp [orProblem, zeroModel]

lemma orq_unit (i : Fin n) : (orProblem n).q (unitModel n i) = 1 := by
  simp only [orProblem, unitModel]
  rw [if_pos ⟨i, by simp⟩]

open Classical in
/-- The symbolic adversary: `|S| - 1` on sub-version-spaces of the core containing the
"no regulator active" model. -/
noncomputable def orLB (S : Finset (Fin n → Bool)) : ℚ≥0 :=
  if zeroModel n ∈ S ∧ S ⊆ orCore n then ((S.card - 1 : ℕ) : ℚ≥0) else 0

/-- The symbolic adversary is a valid adversary certificate, for every `n`. -/
theorem orLB_isAdversary : (orProblem n).IsAdversary 0 orLB := by
  classical
  intro S
  by_cases h : zeroModel n ∈ S ∧ S ⊆ orCore n
  swap
  · left; simp [orLB, h]
  obtain ⟨hz, hsub⟩ := h
  by_cases hc : S.card ≤ 1
  · left
    simp only [orLB, hz, hsub, and_self, if_true]
    have : S.card - 1 = 0 := by omega
    simp [this]
  push_neg at hc
  right
  obtain ⟨m, hm, hmz⟩ := Finset.exists_mem_ne hc (zeroModel n)
  obtain ⟨i, rfl⟩ : ∃ i, m = unitModel n i := by
    rcases mem_orCore.1 (hsub hm) with h | h
    · exact absurd h hmz
    · exact h
  refine ⟨?_, fun j => ⟨false, (orProblem n).mem_outcomes.2 ⟨zeroModel n, hz, rfl⟩, ?_⟩⟩
  · have := (orProblem n).sub_le_width hm hz
    rw [orq_unit, orq_zero] at this
    linarith
  · set C := (orProblem n).cell S j false with hC
    have hzC : zeroModel n ∈ C := (orProblem n).mem_cell.2 ⟨hz, rfl⟩
    have hCsub : C ⊆ orCore n := ((orProblem n).cell_subset S j false).trans hsub
    have hcard : S.card ≤ C.card + 1 := by
      have hsplit := Finset.card_filter_add_card_filter_not
        (s := S) (fun m => (orProblem n).obs m j = false)
      have h2 : (S.filter (fun m => ¬ (orProblem n).obs m j = false)).card ≤ 1 := by
        apply Finset.card_le_one.2
        have key : ∀ a ∈ S.filter (fun m => ¬ (orProblem n).obs m j = false), a = unitModel n j := by
          intro a ha
          rw [Finset.mem_filter] at ha
          rcases mem_orCore.1 (hsub ha.1) with h | ⟨i', rfl⟩
          · subst h; exact absurd rfl ha.2
          · have : (unitModel n i') j = true := by simpa [orProblem] using ha.2
            simp only [unitModel, decide_eq_true_eq] at this
            rw [this]
        intro a ha b hb
        rw [key a ha, key b hb]
      have hCc : C.card = (S.filter (fun m => (orProblem n).obs m j = false)).card := rfl
      omega
    simp only [orLB, hz, hsub, hzC, hCsub, and_self, if_true]
    have : S.card - 1 ≤ 1 + (C.card - 1) := by omega
    have hcost : (orProblem n).cost j = 1 := rfl
    rw [hcost]
    exact_mod_cast this

lemma orLB_core : orLB (orCore n) = n := by
  classical
  simp [orLB, zero_mem_orCore, orCore_card]

lemma or_terminal_testAll (m : Fin n → Bool) :
    (orProblem n).terminal (Policy.testAll Finset.univ.toList) m Finset.univ = {m} := by
  rw [terminal_testAll]
  ext x
  simp only [Finset.mem_filter, Finset.mem_univ, Finset.mem_toList, true_imp_iff, true_and,
    Finset.mem_singleton]
  constructor
  · intro h; funext j; exact h j
  · rintro rfl _; rfl

/-- **Exact optimal cost of the regulator-activity family, for every `n`.**
Deciding whether any of `n` regulators is active with single-regulator assays has
exact minimax cost `n` over the `2^n`-model hypothesis space; the lower bound comes
from an `n + 1`-model core. -/
theorem or_value : (orProblem n).value 0 Finset.univ = ((n : ℚ≥0) : WithTop ℚ≥0) := by
  apply le_antisymm
  · apply (value_le_iff le_rfl).2
    refine ⟨Policy.testAll (O := Bool) Finset.univ.toList, ?_, ?_⟩
    · intro m _
      rw [or_terminal_testAll]
      simp [width]
    · intro m _
      rw [pathCost_testAll]
      simp [orProblem]
  · have h1 := adversary_le_value le_rfl orLB_isAdversary (orCore n)
    rw [orLB_core] at h1
    exact h1.trans (value_mono le_rfl (Finset.subset_univ _))

/-- The size comparison behind the certificate: the core has `n + 1` models while
the hypothesis space has `2^n`. -/
theorem or_sizes : (orCore n).card = n + 1 ∧ Fintype.card (Fin n → Bool) = 2 ^ n := by
  refine ⟨orCore_card, ?_⟩
  simp

end OrFamily

/-! ## 2. Pointer family: adaptivity gap -/

section Pointer

variable (n : ℕ)

/-- Model `(a, b)`: pointer `a` and bit vector `b`; query `b a`.  Experiment `none`
reads the pointer, `some i` reads bit `i`. -/
def ptrProblem : Problem (Fin n × (Fin n → Bool)) (Option (Fin n)) ℕ where
  obs m e := match e with
    | none => m.1.val
    | some i => if m.2 i then 1 else 0
  q m := if m.2 m.1 then 1 else 0
  cost _ := 1

/-- Read the pointer, then read the bit it points to. -/
def ptrPolicy : Policy (Option (Fin n)) ℕ :=
  .test none (fun o => if h : o < n then .test (some ⟨o, h⟩) (fun _ => .stop) else .stop)

variable {n}

/-- **Adaptive strategy**: succeeds exactly with worst-case cost `2`. -/
theorem ptr_adaptive :
    (ptrProblem n).Succeeds 0 (ptrPolicy n) Finset.univ ∧
      (ptrProblem n).CostLE (ptrPolicy n) Finset.univ 2 := by
  constructor
  · rintro ⟨a, b⟩ -
    have e1 : (ptrProblem n).obs (a, b) none = a.val := rfl
    simp only [ptrPolicy, terminal, e1, dif_pos a.isLt]
    rw [(ptrProblem n).width_le_iff le_rfl]
    have key : ∀ x ∈ (ptrProblem n).cell ((ptrProblem n).cell Finset.univ none a.val)
        (some ⟨a.val, a.isLt⟩) ((ptrProblem n).obs (a, b) (some ⟨a.val, a.isLt⟩)),
        (ptrProblem n).q x = (ptrProblem n).q (a, b) := by
      rintro ⟨x1, x2⟩ hx
      simp only [mem_cell, Finset.mem_univ, true_and] at hx
      obtain ⟨h1, h2⟩ := hx
      have hx1 : x1 = a := Fin.ext h1
      subst hx1
      have h2' : (if x2 ⟨x1.val, x1.isLt⟩ then (1 : ℕ) else 0) = if b ⟨x1.val, x1.isLt⟩ then 1 else 0 := h2
      have : x2 x1 = b x1 := by
        cases hx : x2 x1 <;> cases hb : b x1 <;> simp_all
      simp [ptrProblem, this]
    intro x hx y hy
    rw [key x hx, key y hy, sub_self]
  · rintro ⟨a, b⟩ -
    simp only [ptrPolicy, pathCost]
    have e1 : (ptrProblem n).obs (a, b) none = a.val := rfl
    rw [e1, dif_pos a.isLt]
    simp only [pathCost]
    have : (ptrProblem n).cost none = 1 := rfl
    have : (ptrProblem n).cost (some ⟨a.val, a.isLt⟩) = 1 := rfl
    simp_all
    norm_num

/-- **Nonadaptive lower bound**: for `n ≥ 2`, a nonadaptive design succeeds only if
it runs every one of the `n + 1` experiments, hence costs at least `n + 1` on every
model. -/
theorem ptr_nonadaptive (hn : 2 ≤ n) (l : List (Option (Fin n)))
    (hs : (ptrProblem n).Succeeds 0 (Policy.testAll l) Finset.univ) (m : Fin n × (Fin n → Bool)) :
    n + 1 ≤ (ptrProblem n).pathCost (Policy.testAll l) m := by
  have hall : ∀ e, e ∈ l := by
    intro e
    by_contra he
    cases e with
    | none =>
      let i0 : Fin n := ⟨0, by omega⟩
      let i1 : Fin n := ⟨1, by omega⟩
      let b : Fin n → Bool := fun i => decide (i = i0)
      refine testAll_fails (m₁ := (i0, b)) (m₂ := (i1, b)) (Finset.mem_univ _)
        (Finset.mem_univ _) ?_ ?_ hs
      · intro e he'
        cases e with
        | none => exact absurd he' he
        | some j => rfl
      · have : i1 ≠ i0 := by simp [i0, i1, Fin.ext_iff]
        simp [ptrProblem, b, this]
    | some i =>
      refine testAll_fails (m₁ := (i, fun j => decide (j = i))) (m₂ := (i, fun _ => false))
        (Finset.mem_univ _) (Finset.mem_univ _) ?_ ?_ hs
      · intro e he'
        cases e with
        | none => rfl
        | some j =>
          have hji : j ≠ i := fun h => he (h ▸ he')
          simp [ptrProblem, hji]
      · simp [ptrProblem]
  rw [pathCost_testAll]
  have hc : l.map (ptrProblem n).cost = l.map (fun _ => (1 : ℚ≥0)) := rfl
  rw [hc, List.map_const', List.sum_replicate, nsmul_eq_mul, mul_one]
  have : (Finset.univ : Finset (Option (Fin n))).card ≤ l.length :=
    (Finset.card_le_card fun e _ => List.mem_toFinset.2 (hall e)).trans (List.toFinset_card_le l)
  simp only [Finset.card_univ, Fintype.card_option, Fintype.card_fin] at this
  exact_mod_cast this

end Pointer

/-! ## 3. Greedy trap -/

section Greedy

/-- Four mechanisms, three binary assays with costs `2, 2, 1`. -/
def trapP : Problem (Fin 4) (Fin 3) (Fin 2) where
  obs := ![![0, 1, 0], ![0, 1, 1], ![1, 0, 0], ![1, 1, 0]]
  q := ![1, 0, 3, 1 / 2]
  cost := ![2, 2, 1]

/-- An optimal policy: assay 0, then assay 2 or assay 1. -/
def trapPolicy : Policy (Fin 3) (Fin 2) :=
  .test 0 ![.test 2 ![.stop, .stop], .test 1 ![.stop, .stop]]

/-- Exact-optimality certificate for `trapP`. -/
def trapCert : OptCert (Fin 4) (Fin 3) (Fin 2) where
  policy := trapPolicy
  bound := 4
  core := Finset.univ
  adversary := [(Finset.univ, 4), ({0, 2, 3}, 4), ({0, 3}, 2), ({2, 3}, 2), ({0, 1, 3}, 3), ({0, 1}, 1)]

theorem trapCert_ok : trapP.checkOptimal 0 Finset.univ trapCert = true := by decide +kernel

/-- The exact optimal value of the greedy-trap instance is `4`. -/
theorem trap_value : trapP.value 0 Finset.univ = 4 :=
  (checkOptimal_sound le_rfl trapCert_ok).2.2.2

/-- One-step greedy picks assay `1`: its worst posterior width is `1`, while assays
`0` and `2` each leave a posterior with width `5/2`. -/
theorem trap_greedy_choice :
    (∀ o ∈ trapP.outcomes Finset.univ 1, trapP.width (trapP.cell Finset.univ 1 o) ≤ 1) ∧
    (∃ o ∈ trapP.outcomes Finset.univ 0, trapP.width (trapP.cell Finset.univ 0 o) = 5 / 2) ∧
    (∃ o ∈ trapP.outcomes Finset.univ 2, trapP.width (trapP.cell Finset.univ 2 o) = 5 / 2) := by
  decide +kernel

/-- **Greedy is not globally optimal**: every successful policy whose first
experiment is the greedy choice costs at least `5 > 4 = value`. -/
theorem trap_greedy_suboptimal (f : Fin 2 → Policy (Fin 3) (Fin 2))
    (hs : trapP.Succeeds 0 (.test 1 f) Finset.univ) :
    5 ≤ trapP.worstCost (.test 1 f) Finset.univ := by
  have hA := checkAdversary_sound (P := trapP) (ε := 0) (cert := trapCert.adversary)
    (by decide +kernel)
  have h := adversary_test_bound le_rfl hA hs (costLE_worstCost _ _) (o := 1) (by decide +kernel)
  have hl : lbOf trapCert.adversary (trapP.cell Finset.univ 1 1) = 3 := by decide +kernel
  have hc : trapP.cost 1 = 2 := rfl
  rw [hl, hc] at h
  calc (5 : ℚ≥0) = 2 + 3 := by norm_num
    _ ≤ _ := h

end Greedy

end PRISM.Families
