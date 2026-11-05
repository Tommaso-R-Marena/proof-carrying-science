import PCS.Decision

namespace PCS.Refinement

open PCS.Decision

/-- Every required evidence object used by the decision layer is semantically
    bound to the same machine-readable predicate as the claim. -/
def RequiredEvidenceBound (c : Claim) (es : List Evidence) : Prop :=
  ∀ e, e ∈ requiredEvidenceFor c es → e.predicate = c.predicate

/-- All evidence selected as required for the claim has already been replayed
    and established as PASS by the operational checker layer. -/
def RequiredEvidencePasses (c : Claim) (es : List Evidence) : Prop :=
  ∀ e, e ∈ requiredEvidenceFor c es → e.outcome = Outcome.pass

/-- Membership in `requiredEvidenceFor` means both membership in the evidence
    list and explicit mention of the evidence ID by the claim. -/
theorem mem_requiredEvidenceFor_iff
    {c : Claim} {es : List Evidence} {e : Evidence} :
    e ∈ requiredEvidenceFor c es ↔
      e ∈ es ∧ e.id ∈ c.requiredEvidence := by
  simp [requiredEvidenceFor]

/-- A required evidence object satisfying the semantic-binding invariant is
    a `BoundTo` witness for the logical kernel. -/
theorem boundTo_of_required
    {c : Claim} {es : List Evidence} {e : Evidence}
    (binding : RequiredEvidenceBound c es)
    (member : e ∈ requiredEvidenceFor c es) :
    BoundTo e c := by
  constructor
  · exact (mem_requiredEvidenceFor_iff.mp member).2
  · exact binding e member

/-- Required evidence remains a member of the complete evidence list. -/
theorem member_of_required
    {c : Claim} {es : List Evidence} {e : Evidence}
    (member : e ∈ requiredEvidenceFor c es) :
    e ∈ es :=
  (mem_requiredEvidenceFor_iff.mp member).1

/-- Once a computational decision exposes a passing, semantically bound
    correctness witness, the witness constructs the trusted logical judgment.
    A formal proof is permitted as stronger-than-computational correctness
    evidence for a computational claim. -/
theorem computational_witness_sound
    {Γ : List Assumption} {c : Claim} {es : List Evidence} {e : Evidence}
    (context : ContextCovers Γ c)
    (claimKind : c.kind = ClaimKind.computational)
    (member : e ∈ requiredEvidenceFor c es)
    (evidenceKind :
      e.kind = EvidenceKind.computationalTest ∨
      e.kind = EvidenceKind.formalProof)
    (passed : e.outcome = Outcome.pass)
    (binding : RequiredEvidenceBound c es) :
    Assures Γ AssuranceLevel.computational c es := by
  exact Assures.computational
    e
    (member_of_required member)
    context
    claimKind
    evidenceKind
    passed
    (boundTo_of_required binding member)

/-- Formal-claim witness refinement. -/
theorem formal_witness_sound
    {Γ : List Assumption} {c : Claim} {es : List Evidence} {e : Evidence}
    (context : ContextCovers Γ c)
    (claimKind : c.kind = ClaimKind.formal)
    (member : e ∈ requiredEvidenceFor c es)
    (evidenceKind : e.kind = EvidenceKind.formalProof)
    (passed : e.outcome = Outcome.pass)
    (binding : RequiredEvidenceBound c es) :
    Assures Γ AssuranceLevel.formal c es := by
  exact Assures.formal
    e
    (member_of_required member)
    context
    claimKind
    evidenceKind
    passed
    (boundTo_of_required binding member)

/-- Empirical-claim witness refinement. -/
theorem empirical_witness_sound
    {Γ : List Assumption} {c : Claim} {es : List Evidence} {e : Evidence}
    (context : ContextCovers Γ c)
    (claimKind : c.kind = ClaimKind.empirical)
    (member : e ∈ requiredEvidenceFor c es)
    (evidenceKind :
      e.kind = EvidenceKind.empiricalValidation ∨
      e.kind = EvidenceKind.statisticalValidation)
    (passed : e.outcome = Outcome.pass)
    (binding : RequiredEvidenceBound c es) :
    Assures Γ AssuranceLevel.empirical c es := by
  exact Assures.empirical
    e
    (member_of_required member)
    context
    claimKind
    evidenceKind
    passed
    (boundTo_of_required binding member)

/-- Mixed assurance needs two distinct evidence roles: correctness and empirical
    adequacy/statistical validation. They need not be different values, although
    their required evidence kinds make them different in all ordinary cases. -/
theorem mixed_witness_sound
    {Γ : List Assumption} {c : Claim} {es : List Evidence}
    {correctness empiricalEvidence : Evidence}
    (context : ContextCovers Γ c)
    (claimKind : c.kind = ClaimKind.mixed)
    (correctnessMember : correctness ∈ requiredEvidenceFor c es)
    (empiricalMember : empiricalEvidence ∈ requiredEvidenceFor c es)
    (correctnessKind : correctness.kind = EvidenceKind.formalProof)
    (empiricalKind :
      empiricalEvidence.kind = EvidenceKind.empiricalValidation ∨
      empiricalEvidence.kind = EvidenceKind.statisticalValidation)
    (correctnessPassed : correctness.outcome = Outcome.pass)
    (empiricalPassed : empiricalEvidence.outcome = Outcome.pass)
    (binding : RequiredEvidenceBound c es) :
    Assures Γ AssuranceLevel.mixed c es := by
  exact Assures.mixed
    correctness
    empiricalEvidence
    (member_of_required correctnessMember)
    (member_of_required empiricalMember)
    context
    claimKind
    correctnessKind
    empiricalKind
    correctnessPassed
    empiricalPassed
    (boundTo_of_required binding correctnessMember)
    (boundTo_of_required binding empiricalMember)

/-- Whole computational claim soundness once the decision extractor supplies
    one accepted correctness witness. -/
theorem computational_claim_sound
    {Γ : List Assumption} {c : Claim} {es : List Evidence}
    (context : ContextCovers Γ c)
    (claimKind : c.kind = ClaimKind.computational)
    (passes : RequiredEvidencePasses c es)
    (binding : RequiredEvidenceBound c es)
    (witness :
      ∃ e, e ∈ requiredEvidenceFor c es ∧
        (e.kind = EvidenceKind.computationalTest ∨
         e.kind = EvidenceKind.formalProof)) :
    Assures Γ AssuranceLevel.computational c es := by
  rcases witness with ⟨e, member, evidenceKind⟩
  exact computational_witness_sound
    context
    claimKind
    member
    evidenceKind
    (passes e member)
    binding

/-- Whole formal claim soundness once the decision extractor supplies one
    accepted formal-proof witness. -/
theorem formal_claim_sound
    {Γ : List Assumption} {c : Claim} {es : List Evidence}
    (context : ContextCovers Γ c)
    (claimKind : c.kind = ClaimKind.formal)
    (passes : RequiredEvidencePasses c es)
    (binding : RequiredEvidenceBound c es)
    (witness :
      ∃ e, e ∈ requiredEvidenceFor c es ∧
        e.kind = EvidenceKind.formalProof) :
    Assures Γ AssuranceLevel.formal c es := by
  rcases witness with ⟨e, member, evidenceKind⟩
  exact formal_witness_sound
    context
    claimKind
    member
    evidenceKind
    (passes e member)
    binding

/-- Whole empirical claim soundness once the decision extractor supplies one
    empirical/statistical validation witness. -/
theorem empirical_claim_sound
    {Γ : List Assumption} {c : Claim} {es : List Evidence}
    (context : ContextCovers Γ c)
    (claimKind : c.kind = ClaimKind.empirical)
    (passes : RequiredEvidencePasses c es)
    (binding : RequiredEvidenceBound c es)
    (witness :
      ∃ e, e ∈ requiredEvidenceFor c es ∧
        (e.kind = EvidenceKind.empiricalValidation ∨
         e.kind = EvidenceKind.statisticalValidation)) :
    Assures Γ AssuranceLevel.empirical c es := by
  rcases witness with ⟨e, member, evidenceKind⟩
  exact empirical_witness_sound
    context
    claimKind
    member
    evidenceKind
    (passes e member)
    binding

/-- Whole mixed claim soundness once the decision extractor supplies the two
    evidence roles required by the logical kernel. -/
theorem mixed_claim_sound
    {Γ : List Assumption} {c : Claim} {es : List Evidence}
    (context : ContextCovers Γ c)
    (claimKind : c.kind = ClaimKind.mixed)
    (passes : RequiredEvidencePasses c es)
    (binding : RequiredEvidenceBound c es)
    (correctnessWitness :
      ∃ e, e ∈ requiredEvidenceFor c es ∧
        e.kind = EvidenceKind.formalProof)
    (empiricalWitness :
      ∃ e, e ∈ requiredEvidenceFor c es ∧
        (e.kind = EvidenceKind.empiricalValidation ∨
         e.kind = EvidenceKind.statisticalValidation)) :
    Assures Γ AssuranceLevel.mixed c es := by
  rcases correctnessWitness with ⟨correctness, correctnessMember, correctnessKind⟩
  rcases empiricalWitness with ⟨empiricalEvidence, empiricalMember, empiricalKind⟩
  exact mixed_witness_sound
    context
    claimKind
    correctnessMember
    empiricalMember
    correctnessKind
    empiricalKind
    (passes correctness correctnessMember)
    (passes empiricalEvidence empiricalMember)
    binding

end PCS.Refinement
