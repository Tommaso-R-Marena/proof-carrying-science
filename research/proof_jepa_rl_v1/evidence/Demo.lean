import Lean

theorem proof_jepa_demo : ∀ (A : Prop) (B : Prop), ((A ∧ B) → A) := by
  intro h0
  intro h1
  intro h2
  exact h2.1

#print axioms proof_jepa_demo
