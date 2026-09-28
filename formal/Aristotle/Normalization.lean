import PCS.Refinement

namespace PCS.Aristotle.Normalization

open PCS.Decision
open PCS.Refinement

/-- Evidence IDs are unique in the normalized state handed to decideClaim. -/
def UniqueEvidenceIds (es : List Evidence) : Prop :=
  ∀ e₁ ∈ es, ∀ e₂ ∈ es, e₁.id = e₂.id → e₁ = e₂

/-- Every ID named by the claim is represented at most once in normalized evidence. -/
def RequiredIdsUnambiguous (c : Claim) (es : List Evidence) : Prop :=
  ∀ eid ∈ c.requiredEvidence, ∀ e₁ ∈ es, ∀ e₂ ∈ es,
    e₁.id = eid → e₂.id = eid → e₁ = e₂

theorem uniqueEvidenceIds_implies_required_unambiguous
    {c : Claim} {es : List Evidence}
    (h : UniqueEvidenceIds es) :
    RequiredIdsUnambiguous c es := by
  sorry

/-- If a normalized evidence object is selected by requiredEvidenceFor,
    its ID is explicitly required by the claim. -/
theorem selected_evidence_id_required
    {c : Claim} {es : List Evidence} {e : Evidence}
    (h : e ∈ requiredEvidenceFor c es) :
    e.id ∈ c.requiredEvidence := by
  sorry

/-- Every selected required evidence object is part of the original evidence list. -/
theorem selected_evidence_in_source
    {c : Claim} {es : List Evidence} {e : Evidence}
    (h : e ∈ requiredEvidenceFor c es) :
    e ∈ es := by
  sorry

/-- No missing required evidence means every required ID has a witness. -/
theorem no_missingRequiredEvidence_has_witness
    {c : Claim} {es : List Evidence}
    (h : missingRequiredEvidence c es = false) :
    ∀ eid ∈ c.requiredEvidence, ∃ e ∈ es, e.id = eid := by
  sorry

end PCS.Aristotle.Normalization
