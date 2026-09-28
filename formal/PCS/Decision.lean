import PCS.Core

namespace PCS.Decision

/-- Boolean check for a single computational evidence object.
    Operational replay establishes the evidence outcome before this layer runs. -/
def computationalEvidenceAccepts (c : Claim) (e : Evidence) : Bool :=
  if c.kind = ClaimKind.computational then
    if e.kind = EvidenceKind.computationalTest then
      if e.outcome = Outcome.pass then
        if e.id ∈ c.requiredEvidence then
          if e.predicate = c.predicate then true else false
        else false
      else false
    else false
  else false

/-- A successful Boolean evidence decision plus explicit context/membership
    constructs the logical assurance judgment. -/
theorem computationalEvidenceAccepts_sound
    {Γ : List Assumption} {c : Claim} {es : List Evidence} {e : Evidence}
    (member : e ∈ es)
    (context : ContextCovers Γ c)
    (h : computationalEvidenceAccepts c e = true) :
    Assures Γ AssuranceLevel.computational c es := by
  simp [computationalEvidenceAccepts] at h
  rcases h with ⟨claimKind, evidenceKind, passed, required, predicate⟩
  exact Assures.computational e member context claimKind evidenceKind passed ⟨required, predicate⟩

def formalEvidenceAccepts (c : Claim) (e : Evidence) : Bool :=
  if c.kind = ClaimKind.formal then
    if e.kind = EvidenceKind.formalProof then
      if e.outcome = Outcome.pass then
        if e.id ∈ c.requiredEvidence then
          if e.predicate = c.predicate then true else false
        else false
      else false
    else false
  else false

theorem formalEvidenceAccepts_sound
    {Γ : List Assumption} {c : Claim} {es : List Evidence} {e : Evidence}
    (member : e ∈ es)
    (context : ContextCovers Γ c)
    (h : formalEvidenceAccepts c e = true) :
    Assures Γ AssuranceLevel.formal c es := by
  simp [formalEvidenceAccepts] at h
  rcases h with ⟨claimKind, evidenceKind, passed, required, predicate⟩
  exact Assures.formal e member context claimKind evidenceKind passed ⟨required, predicate⟩

end PCS.Decision
