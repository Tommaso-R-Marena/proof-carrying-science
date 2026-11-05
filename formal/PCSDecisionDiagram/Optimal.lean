import PCSDecisionDiagram.Bellman

/-!
# Total-assignment meaning of a Bellman cell

* `objective P a = Σ i, if a i ≠ baseline i then cost i else 0` (`objL_zero`).
* `Feasible n ns P u a` — `a` has length `n`, the diagram root `u` is true at `a`, and every
  locked variable keeps its baseline value.  The baseline itself may be infeasible.
* `Optimal` — feasible and of minimum objective among **all** feasible total assignments.
* `flips P a i` — variable `i` differs from the baseline in `a`.

`bellman_correct` (strictly positive costs, valid diagram):
1. `cellRec u = none` iff no feasible total assignment respecting the locks exists;
2. the reported cost is attained by a feasible assignment and is globally minimum;
3. the reported count is the length of a duplicate-free list of exactly the optimal total
   assignments (so skipped variables add no extra assignments);
4. mandatory bit `i` iff **every optimal** assignment flips `i`; possible bit `i` iff **some
   optimal** assignment flips `i`.

`bellman_bounds`: count ≤ 2^n, masks < 2^n, mandatory ⊆ possible, locked variables never
appear in either mask, and cost ≤ n·B whenever every cost is at most `B`.
-/

namespace PCSDD

open PCSOmega

variable {n : Nat} {ns : Nodes} {P : Prices}

/-- The intervention objective of a total assignment. -/
def objective (P : Prices) (a : List Bool) : Nat :=
  ((List.range a.length).map (fun i => if a.getD i false = P.base i then 0 else P.cost i)).sum

/-- Variable `i` is flipped by `a`. -/
def flips (P : Prices) (a : List Bool) (i : Nat) : Bool :=
  decide (i < a.length) && (a.getD i false != P.base i)

/-- Feasible total assignment: diagram true and locks respected. -/
def Feasible (n : Nat) (ns : Nodes) (P : Prices) (u : Nat) (a : List Bool) : Prop :=
  a.length = n ∧ evalD ns (envOf a) u = true ∧ ∀ i < n, P.lock i = true → a.getD i false = P.base i

/-- Optimal total assignment. -/
def Optimal (n : Nat) (ns : Nodes) (P : Prices) (u : Nat) (a : List Bool) : Prop :=
  Feasible n ns P u a ∧ ∀ b, Feasible n ns P u b → objective P a ≤ objective P b

theorem objL_eq : ∀ (k : Nat) (s : List Bool), objL P k s =
    ((List.range s.length).map (fun i => if s.getD i false = P.base (k + i) then 0 else P.cost (k + i))).sum
  | _, [] => rfl
  | k, x :: t => by
      rw [objL, objL_eq (k + 1) t, List.length_cons, List.range_succ_eq_map, List.map_cons,
        List.sum_cons, List.map_map]
      have : (List.map (fun i => if t.getD i false = P.base (k + 1 + i) then 0 else P.cost (k + 1 + i))
          (List.range t.length)) = List.map ((fun i => if (x :: t).getD i false = P.base (k + i) then 0
            else P.cost (k + i)) ∘ Nat.succ) (List.range t.length) := by
        apply List.map_congr_left
        intro i _
        simp only [Function.comp, List.getD_cons_succ]
        rw [show k + 1 + i = k + i.succ by omega]
      rw [← this]
      simp only [List.getD_cons_zero, Nat.add_zero, Prices.flipC]
      omega

theorem objL_zero (a : List Bool) : objL P 0 a = objective P a := by
  rw [objL_eq]; simp [objective]

theorem testBit_maskL : ∀ (k : Nat) (s : List Bool) (i : Nat), (maskL P k s).testBit i =
    (decide (k ≤ i) && decide (i < k + s.length) && (s.getD (i - k) false != P.base i))
  | k, [], i => by simp [maskL]; omega
  | k, x :: t, i => by
      rw [maskL, Nat.testBit_or, testBit_maskL (k + 1) t i]
      simp only [Prices.flipM, List.length_cons]
      by_cases hik : i = k
      · subst hik
        by_cases hx : x = P.base i <;> simp [hx] <;> intro h <;> omega
      · have h2 : (if x = P.base k then 0 else 2 ^ k).testBit i = false := by
          split
          · simp
          · rw [Nat.testBit_two_pow]; simp; omega
        rw [h2, Bool.or_false]
        by_cases hki : k + 1 ≤ i
        · have : i - k = (i - (k + 1)) + 1 := by omega
          rw [this, List.getD_cons_succ]
          have e1 : decide (k + 1 ≤ i) = true := by simp [hki]
          have e2 : decide (k ≤ i) = true := by simp; omega
          have e3 : decide (i < k + 1 + t.length) = decide (i < k + (t.length + 1)) := by
            simp only [decide_eq_decide]; omega
          rw [e1, e2, e3]
        · simp only [show ¬ k + 1 ≤ i from hki, decide_false, Bool.false_and]
          simp only [show ¬ k ≤ i by omega, decide_false, Bool.false_and]

theorem maskL_zero_testBit (a : List Bool) (i : Nat) : (maskL P 0 a).testBit i = flips P a i := by
  rw [testBit_maskL]; simp [flips]

theorem locksB_iff : ∀ (k : Nat) (s : List Bool), locksB P k s = true ↔
    ∀ i < s.length, P.lock (k + i) = true → s.getD i false = P.base (k + i)
  | _, [] => by simp [locksB]
  | k, x :: t => by
      rw [locksB, Bool.and_eq_true, locksB_iff (k + 1) t]
      constructor
      · rintro ⟨h1, h2⟩ i hi hl
        cases i with
        | zero =>
            simp [Prices.lockOK] at h1
            simp at hl ⊢; rcases h1 with h | h
            · rw [h] at hl; cases hl
            · exact h
        | succ i =>
            simp only [List.getD_cons_succ]
            have := h2 i (by simp at hi; omega) (by rw [show k + 1 + i = k + (i + 1) by omega]; exact hl)
            rw [this, show k + 1 + i = k + (i + 1) by omega]
      · intro h
        refine ⟨?_, fun i hi hl => ?_⟩
        · simp only [Prices.lockOK, Bool.or_eq_true, Bool.not_eq_eq_eq_not, Bool.not_true,
            beq_iff_eq]
          cases hl : P.lock k
          · exact Or.inl rfl
          · exact Or.inr (by simpa using h 0 (by simp) (by simpa using hl))
        · have := h (i + 1) (by simp; omega) (by rw [show k + (i + 1) = k + 1 + i by omega]; exact hl)
          simpa [show k + (i + 1) = k + 1 + i by omega] using this

theorem feasL_zero_iff (u : Nat) (a : List Bool) :
    (a.length = n ∧ feasL ns P 0 u a = true) ↔ Feasible n ns P u a := by
  simp only [feasL, Bool.and_eq_true, envL_zero, locksB_iff, Nat.zero_add, Feasible]
  constructor
  · rintro ⟨hl, he, hk⟩; exact ⟨hl, he, fun i hi => hk i (by omega)⟩
  · rintro ⟨hl, he, hk⟩; exact ⟨hl, he, fun i hi => hk i (by omega)⟩

theorem mem_candL_zero {u : Nat} {p : Nat × Nat} :
    p ∈ candL n ns P 0 u ↔ ∃ a, Feasible n ns P u a ∧ objective P a = p.1 ∧ maskL P 0 a = p.2 := by
  rw [mem_candL]
  constructor
  · rintro ⟨a, hl, hf, h1, h2⟩
    exact ⟨a, (feasL_zero_iff u a).1 ⟨by simpa using hl, hf⟩, by rw [← objL_zero]; exact h1, h2⟩
  · rintro ⟨a, hf, h1, h2⟩
    have := (feasL_zero_iff u a).2 hf
    exact ⟨a, by simpa using this.1, this.2, by rw [objL_zero]; exact h1, h2⟩

/-- Total-level summary of the root cell. -/
theorem summ_root (hv : Valid n ns) (hpos : ∀ k < n, 0 < P.cost k) {u : Nat} (hu : u < ns.size + 2) :
    Summ (candL n ns P 0 u) (cellRec ns P u) :=
  summ_cellRec hv hpos (n - 0) 0 u rfl hu (Nat.zero_le _)

/-- The duplicate-free list of optimal total assignments for cost `c`. -/
def optList (n : Nat) (ns : Nodes) (P : Prices) (u c : Nat) : List (List Bool) :=
  ((allAsg n).filter (feasL ns P 0 u)).filter (fun a => objL P 0 a == c)

/-- **Bellman correctness at the total-assignment level.** -/
theorem bellman_correct (hv : Valid n ns) (hpos : ∀ k < n, 0 < P.cost k) {u : Nat}
    (hu : u < ns.size + 2) :
    (cellRec ns P u = none ↔ ∀ a, ¬ Feasible n ns P u a) ∧
    ∀ c, cellRec ns P u = some c →
      (∃ a, Feasible n ns P u a ∧ objective P a = c.cost) ∧
      (∀ a, Feasible n ns P u a → c.cost ≤ objective P a) ∧
      (∀ a, Optimal n ns P u a ↔ Feasible n ns P u a ∧ objective P a = c.cost) ∧
      ((optList n ns P u c.cost).Nodup ∧
        (∀ a, a ∈ optList n ns P u c.cost ↔ Optimal n ns P u a) ∧
        c.count = (optList n ns P u c.cost).length) ∧
      (∀ i, c.mand.testBit i = true ↔ ∀ a, Optimal n ns P u a → flips P a i = true) ∧
      (∀ i, c.poss.testBit i = true ↔ ∃ a, Optimal n ns P u a ∧ flips P a i = true) := by
  have hS := summ_root (P := P) hv hpos hu
  refine ⟨?_, ?_⟩
  · rw [hS.none_iff]
    constructor
    · intro h a ha
      have : (objective P a, maskL P 0 a) ∈ candL n ns P 0 u := mem_candL_zero.2 ⟨a, ha, rfl, rfl⟩
      rw [h] at this; simp at this
    · intro h
      cases hc : candL n ns P 0 u with
      | nil => rfl
      | cons p l =>
          have : p ∈ candL n ns P 0 u := by rw [hc]; simp
          obtain ⟨a, ha, _⟩ := mem_candL_zero.1 this
          exact absurd ha (h a)
  · intro c hc
    have hatt : ∃ a, Feasible n ns P u a ∧ objective P a = c.cost := by
      obtain ⟨p, hp, he⟩ := hS.attained c hc
      obtain ⟨a, ha, h1, _⟩ := mem_candL_zero.1 hp
      exact ⟨a, ha, by rw [h1, he]⟩
    have hmin : ∀ a, Feasible n ns P u a → c.cost ≤ objective P a := fun a ha =>
      hS.minimal c hc (objective P a, maskL P 0 a) (mem_candL_zero.2 ⟨a, ha, rfl, rfl⟩)
    have hopt : ∀ a, Optimal n ns P u a ↔ Feasible n ns P u a ∧ objective P a = c.cost := by
      intro a
      constructor
      · rintro ⟨ha, hle⟩
        obtain ⟨b, hb, hbe⟩ := hatt
        exact ⟨ha, by have := hle b hb; have := hmin a ha; omega⟩
      · rintro ⟨ha, he⟩
        exact ⟨ha, fun b hb => by rw [he]; exact hmin b hb⟩
    have hmemL : ∀ a, a ∈ optList n ns P u c.cost ↔ Optimal n ns P u a := by
      intro a
      rw [hopt]
      simp only [optList, List.mem_filter, mem_allAsg, beq_iff_eq, objL_zero]
      constructor
      · rintro ⟨⟨hl, hf⟩, he⟩; exact ⟨(feasL_zero_iff u a).1 ⟨hl, hf⟩, he⟩
      · rintro ⟨ha, he⟩; have := (feasL_zero_iff u a).2 ha; exact ⟨⟨this.1, this.2⟩, he⟩
    refine ⟨hatt, hmin, hopt, ⟨?_, hmemL, ?_⟩, ?_, ?_⟩
    · exact ((nodup_allAsg n).filter _).filter _
    · rw [hS.count c hc]
      unfold candL optList
      rw [List.filter_map, List.length_map]
      rfl
    · intro i
      rw [hS.mand c hc i]
      constructor
      · intro h a ha
        rw [← maskL_zero_testBit]
        exact h (objective P a, maskL P 0 a) (mem_candL_zero.2 ⟨a, ((hopt a).1 ha).1, rfl, rfl⟩)
          ((hopt a).1 ha).2
      · intro h p hp he
        obtain ⟨a, ha, h1, h2⟩ := mem_candL_zero.1 hp
        rw [← h2, maskL_zero_testBit]
        exact h a ((hopt a).2 ⟨ha, by rw [h1, he]⟩)
    · intro i
      rw [hS.poss c hc i]
      constructor
      · rintro ⟨p, hp, he, hb⟩
        obtain ⟨a, ha, h1, h2⟩ := mem_candL_zero.1 hp
        rw [← h2, maskL_zero_testBit] at hb
        exact ⟨a, (hopt a).2 ⟨ha, by rw [h1, he]⟩, hb⟩
      · rintro ⟨a, ha, hb⟩
        refine ⟨(objective P a, maskL P 0 a), mem_candL_zero.2 ⟨a, ((hopt a).1 ha).1, rfl, rfl⟩,
          ((hopt a).1 ha).2, ?_⟩
        rw [maskL_zero_testBit]; exact hb

theorem objective_le (B : Nat) (hB : ∀ i, P.cost i ≤ B) (a : List Bool) :
    objective P a ≤ a.length * B := by
  rw [← objL_zero]
  suffices ∀ k (s : List Bool), objL P k s ≤ s.length * B from this 0 a
  intro k s
  induction s generalizing k with
  | nil => simp [objL]
  | cons x t ih =>
      have := ih (k + 1)
      have h2 : P.flipC k x ≤ B := by
        unfold Prices.flipC; split
        · omega
        · exact hB k
      rw [objL, List.length_cons, Nat.succ_mul]; omega

/-- **Range bounds of a resolved root cell.** -/
theorem bellman_bounds (hv : Valid n ns) (hpos : ∀ k < n, 0 < P.cost k) {u : Nat}
    (hu : u < ns.size + 2) {c : Cell} (hc : cellRec ns P u = some c) :
    c.count ≤ 2 ^ n ∧ c.mand < 2 ^ n ∧ c.poss < 2 ^ n ∧
    (∀ i, c.mand.testBit i = true → c.poss.testBit i = true) ∧
    (∀ i, P.lock i = true → c.poss.testBit i = false ∧ c.mand.testBit i = false) ∧
    (∀ B, (∀ i, P.cost i ≤ B) → c.cost ≤ n * B) := by
  obtain ⟨_, h⟩ := bellman_correct (P := P) hv hpos hu
  obtain ⟨⟨a, ha, hae⟩, _, hopt, ⟨_, _, hcount⟩, hmand, hposs⟩ := h c hc
  have aopt : Optimal n ns P u a := (hopt a).2 ⟨ha, hae⟩
  have flip_lt : ∀ b i, Optimal n ns P u b → flips P b i = true → i < n := by
    intro b i hb hf
    simp only [flips, Bool.and_eq_true, decide_eq_true_eq] at hf
    have := hb.1.1; omega
  have mand_poss : ∀ i, c.mand.testBit i = true → c.poss.testBit i = true := fun i h =>
    (hposs i).2 ⟨a, aopt, (hmand i).1 h a aopt⟩
  have poss_lock : ∀ i, P.lock i = true → c.poss.testBit i = false := by
    intro i hl
    cases hb : c.poss.testBit i
    · rfl
    · obtain ⟨b, hbo, hf⟩ := (hposs i).1 hb
      have hi := flip_lt b i hbo hf
      have := hbo.1.2.2 i hi hl
      simp only [flips, this, bne_self_eq_false, Bool.and_false] at hf
      cases hf
  refine ⟨?_, ?_, ?_, mand_poss, fun i hl => ⟨poss_lock i hl, ?_⟩, ?_⟩
  · rw [hcount, ← length_allAsg n]
    exact Nat.le_trans (List.length_filter_le _ _) (List.length_filter_le _ _)
  · apply Nat.lt_pow_two_of_testBit
    intro i hi
    cases hb : c.mand.testBit i
    · rfl
    · have := flip_lt a i aopt ((hmand i).1 hb a aopt); omega
  · apply Nat.lt_pow_two_of_testBit
    intro i hi
    cases hb : c.poss.testBit i
    · rfl
    · obtain ⟨b, hbo, hf⟩ := (hposs i).1 hb
      have := flip_lt b i hbo hf; omega
  · cases hb : c.mand.testBit i
    · rfl
    · have := mand_poss i hb; rw [poss_lock i hl] at this; cases this
  · intro B hB
    rw [← hae, ← ha.1]; exact objective_le B hB a

end PCSDD
