import PCSDecisionDiagram.Conditional

/-!
# Bellman cells and their exact semantic summary

A Bellman cell `[cost, count, mandatoryMask, possibleMask]` summarises a finite list of
candidates `(objective, flipMask)`.  `Summ l oc` states that `oc` is `none` iff `l` is empty,
and otherwise records the minimum objective, the number of minimal candidates, the bits set
in **every** minimal candidate (mandatory) and in **some** minimal candidate (possible).

* `Summ.unique` — a summary is uniquely determined by the candidate list.
* `Summ.append` — disjoint union of candidate lists is summarised by `comb`: smaller cost wins;
  at ties counts **add**, mandatory masks **intersect**, possible masks **unite**.
* `Summ.shift` — adding a flip cost `c` and flip bit-mask `m` to every candidate shifts the
  cell.
* `comb_shift_pos` — a strictly positive extra cost always loses (skipped-variable rule).
-/

namespace PCSDD

/-- A Bellman cell. -/
structure Cell where
  cost : Nat
  count : Nat
  mand : Nat
  poss : Nat
  deriving DecidableEq, Repr

/-- The terminal-`1` cell `[0, 1, 0, 0]`. -/
def Cell.one : Cell := ⟨0, 1, 0, 0⟩

/-- Combine two branch cells (the tie rule of `bellman`). -/
def comb : Option Cell → Option Cell → Option Cell
  | none, y => y
  | some a, none => some a
  | some a, some b =>
      if a.cost < b.cost then some a
      else if b.cost < a.cost then some b
      else some ⟨a.cost, a.count + b.count, a.mand &&& b.mand, a.poss ||| b.poss⟩

/-- Add cost `c` and flip mask `m`. -/
def shiftCell (c m : Nat) (x : Cell) : Cell := ⟨x.cost + c, x.count, x.mand ||| m, x.poss ||| m⟩

/-- Shift a candidate `(objective, flipMask)`. -/
def shiftP (c m : Nat) (p : Nat × Nat) : Nat × Nat := (p.1 + c, p.2 ||| m)

/-- Exact summary of a candidate list. -/
structure Summ (l : List (Nat × Nat)) (oc : Option Cell) : Prop where
  none_iff : oc = none ↔ l = []
  attained : ∀ c, oc = some c → ∃ x ∈ l, x.1 = c.cost
  minimal : ∀ c, oc = some c → ∀ x ∈ l, c.cost ≤ x.1
  count : ∀ c, oc = some c → c.count = (l.filter (fun x => x.1 == c.cost)).length
  mand : ∀ c, oc = some c → ∀ i, c.mand.testBit i = true ↔ ∀ x ∈ l, x.1 = c.cost → x.2.testBit i = true
  poss : ∀ c, oc = some c → ∀ i, c.poss.testBit i = true ↔ ∃ x ∈ l, x.1 = c.cost ∧ x.2.testBit i = true

theorem Summ.nil : Summ [] none := by
  refine ⟨by simp, ?_, ?_, ?_, ?_, ?_⟩ <;> intro c hc <;> cases hc

theorem Summ.single (c m : Nat) : Summ [(c, m)] (some ⟨c, 1, m, m⟩) := by
  refine ⟨by simp, ?_, ?_, ?_, ?_, ?_⟩ <;> intro x hx <;> cases hx
  · exact ⟨_, List.mem_singleton_self _, rfl⟩
  · intro y hy; simp at hy; subst hy; exact Nat.le_refl _
  · simp
  · intro i; simp
  · intro i; simp

theorem Summ.unique {l : List (Nat × Nat)} {x y : Option Cell} (hx : Summ l x) (hy : Summ l y) :
    x = y := by
  cases x with
  | none => cases y with
    | none => rfl
    | some b => exact absurd (hy.none_iff.2 (hx.none_iff.1 rfl)) (by simp)
  | some a => cases y with
    | none => exact absurd (hx.none_iff.2 (hy.none_iff.1 rfl)) (by simp)
    | some b =>
      have hc : a.cost = b.cost := by
        obtain ⟨p, hp, hpe⟩ := hx.attained a rfl
        obtain ⟨q, hq, hqe⟩ := hy.attained b rfl
        have := hx.minimal a rfl q hq
        have := hy.minimal b rfl p hp
        omega
      have hn : a.count = b.count := by rw [hx.count a rfl, hy.count b rfl, hc]
      have hm : a.mand = b.mand := Nat.eq_of_testBit_eq fun i => by
        cases h1 : a.mand.testBit i <;> cases h2 : b.mand.testBit i <;> try rfl
        · have := (hy.mand b rfl i).1 h2; rw [← hc] at this
          rw [(hx.mand a rfl i).2 this] at h1; cases h1
        · have := (hx.mand a rfl i).1 h1; rw [hc] at this
          rw [(hy.mand b rfl i).2 this] at h2; cases h2
      have hp : a.poss = b.poss := Nat.eq_of_testBit_eq fun i => by
        cases h1 : a.poss.testBit i <;> cases h2 : b.poss.testBit i <;> try rfl
        · have := (hy.poss b rfl i).1 h2; rw [← hc] at this
          rw [(hx.poss a rfl i).2 this] at h1; cases h1
        · have := (hx.poss a rfl i).1 h1; rw [hc] at this
          rw [(hy.poss b rfl i).2 this] at h2; cases h2
      cases a; cases b; simp_all

theorem noneIff_of_some {A B : List (Nat × Nat)} {a c : Cell} (hA : Summ A (some a)) :
    (some c = none ↔ A ++ B = []) := by
  constructor
  · intro h; cases h
  · intro h
    have h1 : A = [] := (List.append_eq_nil_iff.1 h).1
    exact absurd (hA.none_iff.2 h1) (by simp)

/-- Strict-winner case of `Summ.append`. -/
theorem Summ.append_lt {A B : List (Nat × Nat)} {a b : Cell} (hA : Summ A (some a))
    (hB : Summ B (some b)) (hlt : a.cost < b.cost) : Summ (A ++ B) (some a) := by
  have noB : ∀ x ∈ B, x.1 ≠ a.cost := fun x hx h => by
    have := hB.minimal b rfl x hx; omega
  refine ⟨noneIff_of_some hA, ?_, ?_, ?_, ?_, ?_⟩ <;> intro c hc <;> cases hc
  · obtain ⟨x, hx, e⟩ := hA.attained a rfl; exact ⟨x, List.mem_append_left _ hx, e⟩
  · intro x hx
    rcases List.mem_append.1 hx with hx | hx
    · exact hA.minimal a rfl x hx
    · have := hB.minimal b rfl x hx; omega
  · rw [List.filter_append, List.length_append, hA.count a rfl]
    have : (B.filter (fun x => x.1 == a.cost)).length = 0 := by
      rw [List.length_eq_zero_iff, List.filter_eq_nil_iff]
      intro x hx; simpa using noB x hx
    omega
  · intro i; rw [hA.mand a rfl i]
    constructor
    · intro h x hx he
      rcases List.mem_append.1 hx with hx | hx
      · exact h x hx he
      · exact absurd he (noB x hx)
    · intro h x hx he; exact h x (List.mem_append_left _ hx) he
  · intro i; rw [hA.poss a rfl i]
    constructor
    · rintro ⟨x, hx, he, hb⟩; exact ⟨x, List.mem_append_left _ hx, he, hb⟩
    · rintro ⟨x, hx, he, hb⟩
      rcases List.mem_append.1 hx with hx | hx
      · exact ⟨x, hx, he, hb⟩
      · exact absurd he (noB x hx)

theorem Summ.perm_append {A B : List (Nat × Nat)} {oc : Option Cell} (h : Summ (A ++ B) oc) :
    Summ (B ++ A) oc := by
  have hm : ∀ x, x ∈ A ++ B ↔ x ∈ B ++ A := fun x => by simp [or_comm]
  refine ⟨?_, ?_, ?_, ?_, ?_, ?_⟩
  · rw [h.none_iff]; simp [and_comm]
  · intro c hc; obtain ⟨x, hx, e⟩ := h.attained c hc; exact ⟨x, (hm x).1 hx, e⟩
  · intro c hc x hx; exact h.minimal c hc x ((hm x).2 hx)
  · intro c hc; rw [h.count c hc]; simp [List.filter_append]; omega
  · intro c hc i; rw [h.mand c hc i]
    exact ⟨fun h x hx => h x ((hm x).2 hx), fun h x hx => h x ((hm x).1 hx)⟩
  · intro c hc i; rw [h.poss c hc i]
    exact ⟨fun ⟨x, hx, r⟩ => ⟨x, (hm x).1 hx, r⟩, fun ⟨x, hx, r⟩ => ⟨x, (hm x).2 hx, r⟩⟩

/-- **Disjoint union is summarised by `comb`** (tie: counts add, masks intersect / unite). -/
theorem Summ.append {A B : List (Nat × Nat)} {x y : Option Cell} (hA : Summ A x) (hB : Summ B y) :
    Summ (A ++ B) (comb x y) := by
  cases x with
  | none => have := hA.none_iff.1 rfl; subst this; simpa [comb] using hB
  | some a => cases y with
    | none => have := hB.none_iff.1 rfl; subst this; simpa [comb] using hA
    | some b =>
      simp only [comb]
      split
      · exact hA.append_lt hB (by assumption)
      · split
        · exact (hB.append_lt hA (by assumption)).perm_append
        · have hc : a.cost = b.cost := by omega
          refine ⟨noneIff_of_some hA, ?_, ?_, ?_, ?_, ?_⟩ <;> intro c hc' <;> cases hc'
          · obtain ⟨x, hx, e⟩ := hA.attained a rfl; exact ⟨x, List.mem_append_left _ hx, e⟩
          · intro x hx
            rcases List.mem_append.1 hx with hx | hx
            · exact hA.minimal a rfl x hx
            · have := hB.minimal b rfl x hx; simp only; omega
          · simp only
            rw [List.filter_append, List.length_append, hA.count a rfl, hB.count b rfl, hc]
          · intro i; simp only [Nat.testBit_and, Bool.and_eq_true]
            rw [hA.mand a rfl i, hB.mand b rfl i, hc]
            constructor
            · rintro ⟨h1, h2⟩ x hx he
              rcases List.mem_append.1 hx with hx | hx
              · exact h1 x hx (by omega)
              · exact h2 x hx he
            · intro h
              exact ⟨fun x hx he => h x (List.mem_append_left _ hx) (by omega),
                fun x hx he => h x (List.mem_append_right _ hx) he⟩
          · intro i; simp only [Nat.testBit_or, Bool.or_eq_true]
            rw [hA.poss a rfl i, hB.poss b rfl i, hc]
            constructor
            · rintro (⟨x, hx, he, hb⟩ | ⟨x, hx, he, hb⟩)
              · exact ⟨x, List.mem_append_left _ hx, by omega, hb⟩
              · exact ⟨x, List.mem_append_right _ hx, he, hb⟩
            · rintro ⟨x, hx, he, hb⟩
              rcases List.mem_append.1 hx with hx | hx
              · exact Or.inl ⟨x, hx, by omega, hb⟩
              · exact Or.inr ⟨x, hx, he, hb⟩

/-- **Shifting every candidate shifts the summary.** -/
theorem Summ.shift {l : List (Nat × Nat)} {x : Option Cell} (h : Summ l x) (c m : Nat) :
    Summ (l.map (shiftP c m)) (x.map (shiftCell c m)) := by
  refine ⟨?_, ?_, ?_, ?_, ?_, ?_⟩
  · cases x <;> simp [h.none_iff.symm]
  · intro d hd
    cases x with
    | none => cases hd
    | some a =>
      cases hd
      obtain ⟨p, hp, e⟩ := h.attained a rfl
      exact ⟨shiftP c m p, List.mem_map_of_mem hp, by simp [shiftP, shiftCell, e]⟩
  · intro d hd
    cases x with
    | none => cases hd
    | some a =>
      cases hd
      intro q hq
      simp only [List.mem_map] at hq
      obtain ⟨p, hp, rfl⟩ := hq
      have := h.minimal a rfl p hp
      simp [shiftP, shiftCell]; omega
  · intro d hd
    cases x with
    | none => cases hd
    | some a =>
      cases hd
      simp only [shiftCell]
      rw [h.count a rfl, List.filter_map, List.length_map]
      congr 1
      apply List.filter_congr
      intro p _
      show (p.1 == a.cost) = ((shiftP c m p).1 == a.cost + c)
      simp only [shiftP]; rw [Bool.eq_iff_iff]; simp only [beq_iff_eq]; omega
  · intro d hd i
    cases x with
    | none => cases hd
    | some a =>
      cases hd
      simp only [shiftCell, Nat.testBit_or, Bool.or_eq_true]
      rw [h.mand a rfl i]
      constructor
      · rintro (h1 | h1) q hq he
        · simp only [List.mem_map] at hq
          obtain ⟨p, hp, rfl⟩ := hq
          simp only [shiftP, Nat.testBit_or, Bool.or_eq_true] at he ⊢
          exact Or.inl (h1 p hp (by omega))
        · simp only [List.mem_map] at hq
          obtain ⟨p, hp, rfl⟩ := hq
          simp [shiftP, Nat.testBit_or, h1]
      · intro h1
        by_cases hm : m.testBit i = true
        · exact Or.inr hm
        · left
          intro p hp he
          have := h1 (shiftP c m p) (List.mem_map_of_mem hp) (by simp [shiftP, he])
          simp only [shiftP, Nat.testBit_or, Bool.or_eq_true] at this
          rcases this with h' | h'
          · exact h'
          · exact absurd h' hm
  · intro d hd i
    cases x with
    | none => cases hd
    | some a =>
      cases hd
      simp only [shiftCell, Nat.testBit_or, Bool.or_eq_true]
      rw [h.poss a rfl i]
      constructor
      · rintro (⟨p, hp, he, hb⟩ | h1)
        · exact ⟨shiftP c m p, List.mem_map_of_mem hp, by simp [shiftP, he],
            by simp [shiftP, Nat.testBit_or, hb]⟩
        · obtain ⟨p, hp, e⟩ := h.attained a rfl
          exact ⟨shiftP c m p, List.mem_map_of_mem hp, by simp [shiftP, e],
            by simp [shiftP, Nat.testBit_or, h1]⟩
      · rintro ⟨q, hq, he, hb⟩
        simp only [List.mem_map] at hq
        obtain ⟨p, hp, rfl⟩ := hq
        simp only [shiftP, Nat.testBit_or, Bool.or_eq_true] at he hb
        rcases hb with hb | hb
        · exact Or.inl ⟨p, hp, by omega, hb⟩
        · exact Or.inr hb

theorem shiftCell_zero (x : Cell) : shiftCell 0 0 x = x := by
  cases x; simp [shiftCell]

theorem shiftP_zero : shiftP 0 0 = id := by
  funext p; simp [shiftP]

/-- **Strictly positive extra cost always loses** (both argument orders). -/
theorem comb_shift_pos (x : Option Cell) {c : Nat} (hc : 0 < c) (m : Nat) :
    comb x (x.map (shiftCell c m)) = x ∧ comb (x.map (shiftCell c m)) x = x := by
  cases x with
  | none => exact ⟨rfl, rfl⟩
  | some a =>
    constructor
    · simp [comb, shiftCell]; omega
    · simp only [Option.map_some, comb, shiftCell]
      rw [if_neg (by omega), if_pos (by omega)]

end PCSDD
