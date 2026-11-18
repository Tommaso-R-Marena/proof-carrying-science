import ScientificReasoning.Derivations

/-!
# Soundness and authority preservation
-/

namespace ScientificReasoning

theorem derives_sound
    (Γ : Context) (S : Support) (a : Authority) (φ : Formula)
    (h : Derives Γ S a φ) :
    Entails Γ φ := by
  induction h with
  | hyp p hp =>
      intro σ hsat
      exact hsat p hp
  | andI S T a b φ ψ hφ hψ ihφ ihψ =>
      intro σ hsat
      have h1 := ihφ σ hsat
      have h2 := ihψ σ hsat
      simp [Formula.eval, h1, h2]
  | andE1 S a φ ψ hand ih =>
      intro σ hsat
      have h := ih σ hsat
      simp [Formula.eval] at h
      exact h.1
  | andE2 S a φ ψ hand ih =>
      intro σ hsat
      have h := ih σ hsat
      simp [Formula.eval] at h
      exact h.2

theorem derives_support_in_context
    (Γ : Context) (S : Support) (a : Authority) (φ : Formula)
    (h : Derives Γ S a φ) :
    Support.subsetOf S Γ.ids := by
  induction h with
  | hyp p hp =>
      intro i hi
      simp at hi
      subst hi
      exact List.mem_map.2 ⟨p, hp, rfl⟩
  | andI S T a b φ ψ hφ hψ ihφ ihψ =>
      intro i hi
      cases List.mem_append.1 hi with
      | inl hS => exact ihφ i hS
      | inr hT => exact ihψ i hT
  | andE1 S a φ ψ hand ih => exact ih
  | andE2 S a φ ψ hand ih => exact ih

theorem andI_authority_meet (a b : Authority) :
    (Authority.meet a b).rank ≤ a.rank ∧ (Authority.meet a b).rank ≤ b.rank :=
  ⟨meet_le_left a b, meet_le_right a b⟩

theorem derives_hyp_authority
    (Γ : Context) (p : Premise) (hp : p ∈ Γ.premises) :
    Derives Γ [p.id] p.authority p.formula :=
  Derives.hyp Γ p hp

theorem no_escalation_by_meet (a b : Authority) :
    (Authority.meet a b).rank ≤ a.rank ∧
    (Authority.meet a b).rank ≤ b.rank ∧
    ¬ ((a = Authority.empiricalAsserted ∨ a = Authority.assumption) ∧
        Authority.meet a Authority.mathVerified = Authority.mathVerified) := by
  refine ⟨meet_le_left a b, meet_le_right a b, ?_⟩
  intro ⟨h, hm⟩
  exact meet_empirical_not_math a h hm

end ScientificReasoning

#print axioms ScientificReasoning.derives_sound
#print axioms ScientificReasoning.derives_support_in_context
#print axioms ScientificReasoning.andI_authority_meet
#print axioms ScientificReasoning.no_escalation_by_meet
#print axioms ScientificReasoning.meet_empirical_not_math
