import PCS.Refinement

namespace PCS.Aristotle.DecisionExtraction

open PCS.Decision
open PCS.Refinement

/-
These are deliberately isolated Aristotle obligations. They are NOT imported by
PCS.lean until the sorries are replaced and Lean 4.28.0 accepts the file.

The intended proof strategy is case analysis on decideClaim in evaluation order.
Do not weaken theorem statements, add axioms, or use sorry in the returned proof.
-/

theorem decideClaim_computational_extract
    {c : Claim} {es : List Evidence}
    (h : decideClaim c es = DecisionStatus.computational) :
    c.kind = ClaimKind.computational ∧
    RequiredEvidencePasses c es ∧
    (∃ e, e ∈ requiredEvidenceFor c es ∧
      (e.kind = EvidenceKind.computationalTest ∨
       e.kind = EvidenceKind.formalProof)) := by
  sorry

theorem decideClaim_formal_extract
    {c : Claim} {es : List Evidence}
    (h : decideClaim c es = DecisionStatus.formal) :
    c.kind = ClaimKind.formal ∧
    RequiredEvidencePasses c es ∧
    (∃ e, e ∈ requiredEvidenceFor c es ∧
      e.kind = EvidenceKind.formalProof) := by
  sorry

theorem decideClaim_empirical_extract
    {c : Claim} {es : List Evidence}
    (h : decideClaim c es = DecisionStatus.empirical) :
    c.kind = ClaimKind.empirical ∧
    RequiredEvidencePasses c es ∧
    (∃ e, e ∈ requiredEvidenceFor c es ∧
      (e.kind = EvidenceKind.empiricalValidation ∨
       e.kind = EvidenceKind.statisticalValidation)) := by
  sorry

theorem decideClaim_mixed_extract
    {c : Claim} {es : List Evidence}
    (h : decideClaim c es = DecisionStatus.mixed) :
    c.kind = ClaimKind.mixed ∧
    RequiredEvidencePasses c es ∧
    (∃ correctness,
      correctness ∈ requiredEvidenceFor c es ∧
      correctness.kind = EvidenceKind.formalProof) ∧
    (∃ empiricalEvidence,
      empiricalEvidence ∈ requiredEvidenceFor c es ∧
      (empiricalEvidence.kind = EvidenceKind.empiricalValidation ∨
       empiricalEvidence.kind = EvidenceKind.statisticalValidation)) := by
  sorry

theorem decideClaim_computational_sound
    {Γ : List Assumption} {c : Claim} {es : List Evidence}
    (context : ContextCovers Γ c)
    (binding : RequiredEvidenceBound c es)
    (h : decideClaim c es = DecisionStatus.computational) :
    Assures Γ AssuranceLevel.computational c es := by
  rcases decideClaim_computational_extract h with
    ⟨claimKind, passes, witness⟩
  exact computational_claim_sound
    context claimKind passes binding witness

theorem decideClaim_formal_sound
    {Γ : List Assumption} {c : Claim} {es : List Evidence}
    (context : ContextCovers Γ c)
    (binding : RequiredEvidenceBound c es)
    (h : decideClaim c es = DecisionStatus.formal) :
    Assures Γ AssuranceLevel.formal c es := by
  rcases decideClaim_formal_extract h with
    ⟨claimKind, passes, witness⟩
  exact formal_claim_sound
    context claimKind passes binding witness

theorem decideClaim_empirical_sound
    {Γ : List Assumption} {c : Claim} {es : List Evidence}
    (context : ContextCovers Γ c)
    (binding : RequiredEvidenceBound c es)
    (h : decideClaim c es = DecisionStatus.empirical) :
    Assures Γ AssuranceLevel.empirical c es := by
  rcases decideClaim_empirical_extract h with
    ⟨claimKind, passes, witness⟩
  exact empirical_claim_sound
    context claimKind passes binding witness

theorem decideClaim_mixed_sound
    {Γ : List Assumption} {c : Claim} {es : List Evidence}
    (context : ContextCovers Γ c)
    (binding : RequiredEvidenceBound c es)
    (h : decideClaim c es = DecisionStatus.mixed) :
    Assures Γ AssuranceLevel.mixed c es := by
  rcases decideClaim_mixed_extract h with
    ⟨claimKind, passes, correctnessWitness, empiricalWitness⟩
  exact mixed_claim_sound
    context claimKind passes binding
    correctnessWitness empiricalWitness

end PCS.Aristotle.DecisionExtraction
