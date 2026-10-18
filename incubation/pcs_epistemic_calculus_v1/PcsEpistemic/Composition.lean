import PcsEpistemic.Assures

/-!
# Certificate composition

Founding target (FORMAL_SEMANTICS_DRAFT §6), realized for finite evidence bags
when the left bag is disjoint from the downstream claim's required identifiers.
-/
set_option autoImplicit false

namespace PcsEpistemic

def Context.union (Γ1 Γ2 : Context) : Context :=
  ⟨Γ1.assumptions ++ Γ2.assumptions⟩

def Context.withClaim (Γ : Context) (cid : Nat) : Context :=
  ⟨Γ.assumptions ++ [{ id := cid, openStatus := false }]⟩

/-- Lookup is stable under left-extension when the sought id is absent on the left. -/
theorem findEvidence_append_right
    (E1 E2 : List EvidenceRecord) (eid : Nat)
    (hmiss : findEvidence E1 eid = none) :
    findEvidence (E1 ++ E2) eid = findEvidence E2 eid := by
  unfold findEvidence at *
  simp [List.find?_append, hmiss]

/-- Support is preserved when prepending an evidence bag that does not mention
    any required identifier of the claim. -/
theorem supports_prepend_disjoint
    (claim : ClaimNode) (E1 E2 : List EvidenceRecord)
    (h2 : supportsClaim claim E2 = true)
    (hdisj : ∀ eid ∈ claim.requiredEvidence, findEvidence E1 eid = none) :
    supportsClaim claim (E1 ++ E2) = true := by
  simp only [supportsClaim, List.all_eq_true] at h2 ⊢
  intro eid heid
  have hx := h2 eid heid
  have hmiss := hdisj eid heid
  rw [findEvidence_append_right E1 E2 eid hmiss]
  exact hx

/-- Composition of graded assurance along a pipeline. -/
theorem compose_assures
    {Γ1 Γ2 : Context} {L1 L2 : EvidenceClass}
    {c1 c2 : ClaimNode}
    {E1 E2 : List EvidenceRecord}
    (_h1 : Assures Γ1 L1 c1 E1)
    (h2 : Assures (Γ2.withClaim c1.id) L2 c2 E2)
    (hdisj : ∀ eid ∈ c2.requiredEvidence, findEvidence E1 eid = none) :
    Assures (Γ1.union Γ2) L2 c2 (E1 ++ E2) := by
  refine ⟨h2.1, supports_prepend_disjoint c2 E1 E2 h2.2 hdisj⟩

/-- Independent support composition for dialectic merges. -/
theorem compose_independent_support
    (Γ1 Γ2 : Context) (L : EvidenceClass) (claim : ClaimNode)
    (E1 E2 : List EvidenceRecord)
    (h1 : Assures Γ1 L claim E1)
    (h2 : Assures Γ2 L claim E2)
    (hdisj : ∀ eid ∈ claim.requiredEvidence, findEvidence E1 eid = none) :
    Assures (Γ1.union Γ2) L claim (E1 ++ E2) := by
  refine ⟨h1.1, supports_prepend_disjoint claim E1 E2 h2.2 hdisj⟩

end PcsEpistemic
