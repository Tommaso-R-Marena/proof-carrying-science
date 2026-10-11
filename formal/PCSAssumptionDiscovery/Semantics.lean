import PCSDecisionDiagram

/-!
# Exact assumption discovery: independent semantics

A *finite abduction problem* over `m` world variables and a catalog of `k` named hypotheses:

* `ambient : BForm m` — the ambient assumptions `A`;
* `target : BForm m` — the target `T`;
* `catalog` — the hypotheses `H₀ … H_{k-1}` (index `i ≥ catalog.length` reads `TRUE`);
* `costs` — positive selection costs;
* `lockedIn` / `lockedOut` — selections forced on / off.

For a selector vector `y : List Bool` (length `k`):

* `Context p w y  :=  A(w) ∧ ∧ᵢ (yᵢ → Hᵢ(w))`
* `Consistent p y :=  ∃ w, Context p w y`
* `Sufficient p y :=  ∀ w, Context p w y → T(w)`
* `Feasible p y   :=  |y| = k ∧ Consistent ∧ Sufficient ∧ locks`
* `selCost p y    :=  Σᵢ (if yᵢ then costᵢ else 0)`
* `Optimal p y    :=  Feasible p y ∧ ∀ z, Feasible p z → cost y ≤ cost z`

All quantifiers range over *total world assignments of length `m`*.  Nothing in this file
refers to decision diagrams, Bellman tables or search; it is the independent mathematical
denotation against which the algorithms are proved.
-/

namespace PCSAssumptionDiscovery

open PCSOmega

/-- A finite abduction problem. -/
structure Problem (m k : Nat) where
  ambient : BForm m
  target : BForm m
  catalog : List (BForm m)
  costs : List Nat
  lockedIn : List Nat
  lockedOut : List Nat
  deriving DecidableEq, Repr

variable {m k : Nat}

namespace Problem

/-- Hypothesis `i` (out-of-range indices read `TRUE`). -/
def hyp (p : Problem m k) (i : Nat) : BForm m := p.catalog.getD i .tt

/-- Selection cost of hypothesis `i`. -/
def cost (p : Problem m k) (i : Nat) : Nat := p.costs.getD i 0

/-- Executable validity: `k` hypotheses, `k` positive costs, in-range locks. -/
def validB (p : Problem m k) : Bool :=
  (p.catalog.length == k) && (p.costs.length == k) && p.costs.all (fun c => decide (0 < c)) &&
    p.lockedIn.all (fun i => decide (i < k)) && p.lockedOut.all (fun i => decide (i < k))

theorem validB_pos {p : Problem m k} (h : p.validB = true) : ∀ i < k, 0 < p.cost i := by
  intro i hi
  simp only [validB, Bool.and_eq_true, beq_iff_eq, List.all_eq_true, decide_eq_true_eq] at h
  have hc := h.1.1.1.2
  have hpos := h.1.1.2
  have : i < p.costs.length := by omega
  simp only [cost, List.getD_eq_getElem?_getD, List.getElem?_eq_getElem this, Option.getD_some]
  exact hpos _ (List.getElem_mem this)

end Problem

/-- Selector `i` of `y`. -/
def sel (y : List Bool) (i : Nat) : Bool := y.getD i false

/-- The context of world `w` under selection `y`. -/
def Context (p : Problem m k) (w y : List Bool) : Prop :=
  p.ambient.eval (envOf w) = true ∧ ∀ i < k, sel y i = true → (p.hyp i).eval (envOf w) = true

/-- Some world of length `m` satisfies the context. -/
def Consistent (p : Problem m k) (y : List Bool) : Prop :=
  ∃ w, w.length = m ∧ Context p w y

/-- Every world of length `m` satisfying the context satisfies the target. -/
def Sufficient (p : Problem m k) (y : List Bool) : Prop :=
  ∀ w, w.length = m → Context p w y → p.target.eval (envOf w) = true

/-- Locked selections are respected. -/
def LocksOK (p : Problem m k) (y : List Bool) : Prop :=
  (∀ i ∈ p.lockedIn, sel y i = true) ∧ (∀ i ∈ p.lockedOut, sel y i = false)

/-- A satisfiable, sufficient selection respecting the locks. -/
def Feasible (p : Problem m k) (y : List Bool) : Prop :=
  y.length = k ∧ Consistent p y ∧ Sufficient p y ∧ LocksOK p y

/-- Total selection cost. -/
def selCost (p : Problem m k) (y : List Bool) : Nat :=
  ((List.range k).map (fun i => if sel y i then p.cost i else 0)).sum

/-- A globally minimum-cost feasible selection. -/
def Optimal (p : Problem m k) (y : List Bool) : Prop :=
  Feasible p y ∧ ∀ z, Feasible p z → selCost p y ≤ selCost p z

/-- The catalog-index set chosen by `y`. -/
def idxSet (k : Nat) (y : List Bool) : List Nat := (List.range k).filter (sel y)

/-- The ambient assumptions alone are satisfiable. -/
def AmbientConsistent (p : Problem m k) : Prop :=
  ∃ w, w.length = m ∧ p.ambient.eval (envOf w) = true

/-! ## Basic facts -/

/-- `map` preserves duplicate-freedom for functions injective on the list. -/
theorem nodup_map_of_injOn {α β : Type} {f : α → β} :
    ∀ {l : List α}, l.Nodup → (∀ x ∈ l, ∀ y ∈ l, f x = f y → x = y) → (l.map f).Nodup
  | [], _, _ => List.nodup_nil
  | a :: l, h, hi => by
      rw [List.nodup_cons] at h
      rw [List.map_cons, List.nodup_cons]
      refine ⟨fun hm => ?_, nodup_map_of_injOn h.2 fun x hx y hy => hi x (by simp [hx]) y (by simp [hy])⟩
      obtain ⟨b, hb, he⟩ := List.mem_map.1 hm
      have := hi b (by simp [hb]) a (by simp) he
      subst this; exact h.1 hb

theorem mem_idxSet {y : List Bool} {i : Nat} : i ∈ idxSet k y ↔ i < k ∧ sel y i = true := by
  simp [idxSet]

/-- Two length-`k` selectors with the same index set are equal (index sets are exact names
for explanations). -/
theorem idxSet_inj {y z : List Bool} (hy : y.length = k) (hz : z.length = k)
    (h : idxSet k y = idxSet k z) : y = z := by
  apply List.ext_getElem (by omega)
  intro i h1 h2
  have hi : i < k := by omega
  have e : sel y i = sel z i := by
    cases hyi : sel y i <;> cases hzi : sel z i
    · rfl
    · have : i ∈ idxSet k z := mem_idxSet.2 ⟨hi, hzi⟩
      rw [← h, mem_idxSet] at this; rw [hyi] at this; simp at this
    · have : i ∈ idxSet k y := mem_idxSet.2 ⟨hi, hyi⟩
      rw [h, mem_idxSet] at this; rw [hzi] at this; simp at this
    · rfl
  simpa [sel, List.getD_eq_getElem?_getD, h1, h2] using e

theorem Feasible.consistent_ambient {p : Problem m k} {y : List Bool} (h : Feasible p y) :
    AmbientConsistent p := by
  obtain ⟨_, ⟨w, hw, hc, _⟩, _⟩ := h
  exact ⟨w, hw, hc⟩

/-- Contexts shrink when more hypotheses are selected. -/
theorem Context.mono {p : Problem m k} {w y z : List Bool}
    (hsub : ∀ i < k, sel y i = true → sel z i = true) (h : Context p w z) : Context p w y :=
  ⟨h.1, fun i hi hy => h.2 i hi (hsub i hi hy)⟩

/-- An inconsistent selection makes every superset inconsistent. -/
theorem not_consistent_mono {p : Problem m k} {y z : List Bool}
    (hsub : ∀ i < k, sel y i = true → sel z i = true) (h : ¬ Consistent p y) :
    ¬ Consistent p z := fun ⟨w, hw, hc⟩ => h ⟨w, hw, hc.mono hsub⟩

/-- A sufficient selection stays sufficient when more hypotheses are selected. -/
theorem Sufficient.mono {p : Problem m k} {y z : List Bool}
    (hsub : ∀ i < k, sel y i = true → sel z i = true) (h : Sufficient p y) : Sufficient p z :=
  fun w hw hc => h w hw (hc.mono hsub)

end PCSAssumptionDiscovery
