/-!
Writ/9 independent abstract authority calculus.
This file does NOT prove correspondence to the Python/SQLite gateway,
cryptographic authenticity, host identity or external execution semantics.
-/
namespace Writ9

structure Scope where
  actions : List Nat
  clearance : Nat
  maxBytes : Nat
  quota : Nat

/-- A child does not receive broader authority than its parent. -/
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
  rcases h₁ with ⟨a₁, l₁, b₁, q₁⟩
  rcases h₂ with ⟨a₂, l₂, b₂, q₂⟩
  exact ⟨(fun x hx => a₂ x (a₁ x hx)),
         Nat.le_trans l₁ l₂, Nat.le_trans b₁ b₂, Nat.le_trans q₁ q₂⟩

theorem authorized_child_implies_parent {child parent : Scope}
    (h : Attenuates child parent) {a label bytes : Nat}
    (authorized : Allows child a label bytes) : Allows parent a label bytes := by
  rcases h with ⟨ha, hl, hb, _⟩
  rcases authorized with ⟨aok, lok, bok⟩
  exact ⟨ha a aok, Nat.le_trans lok hl, Nat.le_trans bok hb⟩

theorem three_hop_nonamplification {leaf mid root : Scope}
    (h₁ : Attenuates leaf mid) (h₂ : Attenuates mid root)
    {a label bytes : Nat} (ok : Allows leaf a label bytes) :
    Allows root a label bytes := by
  exact authorized_child_implies_parent (attenuation_transitive h₁ h₂) ok

end Writ9
