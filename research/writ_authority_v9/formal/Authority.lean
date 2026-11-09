import Std

/-!
Writ/9 independent abstract authority calculus.

The theorems concern *this definition only*, not Python gateway refinement,
credential authenticity, host isolation, or real-world effects.
-/
namespace Writ9

structure Scope where
  actions : List Nat
  clearance : Nat
  maxBytes : Nat
  quota : Nat

def Attenuates (child parent : Scope) : Prop :=
  (∀ a, a ∈ child.actions → a ∈ parent.actions) ∧
  child.clearance ≤ parent.clearance ∧
  child.maxBytes ≤ parent.maxBytes ∧
  child.quota ≤ parent.quota

def Allows (s : Scope) (action label bytes : Nat) : Prop :=
  action ∈ s.actions ∧ label ≤ s.clearance ∧ bytes ≤ s.maxBytes

theorem attenuation_reflexive (s : Scope) : Attenuates s s := by
  exact ⟨(fun _ h => h), Nat.le_refl _, Nat.le_refl _, Nat.le_refl _⟩

theorem attenuation_transitive {leaf mid root : Scope}
    (h₁ : Attenuates leaf mid) (h₂ : Attenuates mid root) :
    Attenuates leaf root := by
  exact ⟨(fun x hx => h₂.1 x (h₁.1 x hx)),
         Nat.le_trans h₁.2.1 h₂.2.1,
         Nat.le_trans h₁.2.2.1 h₂.2.2.1,
         Nat.le_trans h₁.2.2.2 h₂.2.2.2⟩

theorem authorized_child_implies_parent {child parent : Scope}
    (h : Attenuates child parent) {a label bytes : Nat}
    (authorized : Allows child a label bytes) : Allows parent a label bytes := by
  exact ⟨h.1 a authorized.1,
         Nat.le_trans authorized.2.1 h.2.1,
         Nat.le_trans authorized.2.2 h.2.2.1⟩

theorem three_hop_nonamplification {leaf mid root : Scope}
    (h₁ : Attenuates leaf mid) (h₂ : Attenuates mid root)
    {a label bytes : Nat} (ok : Allows leaf a label bytes) :
    Allows root a label bytes := by
  exact authorized_child_implies_parent (attenuation_transitive h₁ h₂) ok

end Writ9
