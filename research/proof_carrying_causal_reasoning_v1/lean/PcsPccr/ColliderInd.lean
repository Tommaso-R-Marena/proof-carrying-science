/-
Inductive collider graph X → C ← Y.
-/
namespace PcsPccr.ColliderInd

inductive Node where
  | X | Y | C
  deriving DecidableEq, Repr, Inhabited

def Parent : Node → Node → Prop
  | .X, .C => True
  | .Y, .C => True
  | _, _ => False

instance (a b : Node) : Decidable (Parent a b) :=
  match a, b with
  | .X, .C | .Y, .C => isTrue trivial
  | .X, .X | .X, .Y | .Y, .Y | .Y, .X | .C, .C | .C, .X | .C, .Y =>
      isFalse (by intro h; exact False.elim h)

inductive Descendant : Node → Node → Prop where
  | refl : ∀ a, Descendant a a
  | step : ∀ {a b c}, Descendant a b → Parent b c → Descendant a c

theorem parent_X_C : Parent .X .C := trivial
theorem parent_Y_C : Parent .Y .C := trivial

theorem not_parent_X_Y : ¬ Parent .X .Y := by
  intro h; exact False.elim h

theorem no_parent_of_Y {a : Node} (h : Parent a .Y) : False := by
  cases a <;> exact False.elim h

/-- Y is not a descendant of X (no directed path). -/
theorem not_descendant_X_Y : ¬ Descendant .X .Y := by
  intro h
  -- `refl` impossible (X ≠ Y) and eliminated automatically.
  cases h with
  | step hab hbc => exact no_parent_of_Y hbc

theorem descendant_X_C : Descendant .X .C :=
  Descendant.step (Descendant.refl .X) parent_X_C

def ProperDescendant (a b : Node) : Prop := Descendant a b ∧ a ≠ b

theorem proper_descendant_X_C : ProperDescendant .X .C :=
  ⟨descendant_X_C, by decide⟩

def NoDescendantsOfTreatment (treatment : Node) (Zset : List Node) : Prop :=
  ∀ z ∈ Zset, ¬ ProperDescendant treatment z

theorem adjust_empty_ok : NoDescendantsOfTreatment .X [] := by
  intro z hz; cases hz

theorem adjust_C_forbidden : ¬ NoDescendantsOfTreatment .X [.C] := by
  intro h
  exact (h .C (List.Mem.head _)) proper_descendant_X_C

theorem C_is_collider : Parent .X .C ∧ Parent .Y .C :=
  ⟨parent_X_C, parent_Y_C⟩

end PcsPccr.ColliderInd
