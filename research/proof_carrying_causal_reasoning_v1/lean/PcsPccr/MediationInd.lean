/-
Inductive mediation graph X → M → Y: empty adjustment is allowed; adjusting
for mediator M is forbidden by the descendant rule for total-effect queries.
-/
namespace PcsPccr.MediationInd

inductive Node where
  | X | M | Y
  deriving DecidableEq, Repr, Inhabited

def Parent : Node → Node → Prop
  | .X, .M => True
  | .M, .Y => True
  | _, _ => False

instance (a b : Node) : Decidable (Parent a b) := by
  cases a <;> cases b <;> simp [Parent] <;> infer_instance

inductive Descendant : Node → Node → Prop where
  | refl (a : Node) : Descendant a a
  | step {a b c : Node} : Descendant a b → Parent b c → Descendant a c

theorem parent_X_M : Parent .X .M := trivial
theorem parent_M_Y : Parent .M .Y := trivial

theorem descendant_X_M : Descendant .X .M :=
  .step (.refl .X) parent_X_M

theorem descendant_X_Y : Descendant .X .Y :=
  .step descendant_X_M parent_M_Y

def ProperDescendant (a b : Node) : Prop := Descendant a b ∧ a ≠ b

theorem proper_descendant_X_M : ProperDescendant .X .M :=
  ⟨descendant_X_M, by decide⟩

theorem proper_descendant_X_Y : ProperDescendant .X .Y :=
  ⟨descendant_X_Y, by decide⟩

def NoDescendantsOfTreatment (treatment : Node) (Z : List Node) : Prop :=
  ∀ z ∈ Z, ¬ ProperDescendant treatment z

theorem adjust_empty_ok : NoDescendantsOfTreatment .X [] := by
  intro z hz; cases hz

theorem adjust_M_forbidden : ¬ NoDescendantsOfTreatment .X [.M] := by
  intro h
  exact (h .M (List.Mem.head _)) proper_descendant_X_M

/-- No backdoor into X on this graph (X has no parents). -/
theorem X_has_no_parent {a : Node} (h : Parent a .X) : False := by
  cases a <;> simp [Parent] at h

/-- Vacuous backdoor criterion: empty set blocks all (i.e. zero) backdoors and
contains no descendants. -/
def SatisfiesBackdoor (Z : List Node) : Prop :=
  NoDescendantsOfTreatment .X Z

theorem empty_satisfies_backdoor : SatisfiesBackdoor [] := adjust_empty_ok

theorem M_fails_backdoor : ¬ SatisfiesBackdoor [.M] := adjust_M_forbidden

end PcsPccr.MediationInd
