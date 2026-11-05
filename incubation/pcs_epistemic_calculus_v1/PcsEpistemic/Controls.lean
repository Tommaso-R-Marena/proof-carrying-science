import PcsEpistemic.Dialectic
import PcsEpistemic.Laws

/-!
Executable kernel-checked controls for the epistemic calculus.
Prefer ordinary `decide` for Boolean finite checks.
-/
set_option autoImplicit false

namespace PcsEpistemic.Controls

open PcsEpistemic

def formalClaim : ClaimNode :=
  { id := 1, requiredClass := .formal, requiredEvidence := [10] }

def computationalClaim : ClaimNode :=
  { id := 2, requiredClass := .computational, requiredEvidence := [11] }

def emptyContext : Context := ⟨[]⟩

theorem control_no_computational_to_formal :
    EvidenceClass.computational.le .formal = false :=
  no_computational_to_formal

theorem control_formal_evidence_accepts :
    Assures emptyContext .formal formalClaim
      [{ id := 10, cls := .formal, accepted := true }] :=
  formal_evidence_assures_formal emptyContext formalClaim 10 rfl rfl

theorem control_computational_rejects_formal :
    ¬ Assures emptyContext .formal formalClaim
        [{ id := 10, cls := .computational, accepted := true }] :=
  computational_cannot_assure_formal emptyContext formalClaim 10 rfl rfl

theorem control_missing_evidence :
    ¬ Assures emptyContext .computational computationalClaim [] :=
  missing_evidence_blocks emptyContext computationalClaim 11 rfl

def sampleGraph : DepGraph :=
  { artifacts := [0, 1, 2]
    workflow := [
      { id := 100, inputs := [0], outputs := [1] },
      { id := 101, inputs := [1], outputs := [2] }]
    evidence := [
      { id := 10, cls := .computational, artifacts := [2], claims := [1] }]
    claims := [
      { id := 1, requiredClass := .computational, requiredEvidence := [10] }] }

theorem control_impact_reaches_claim :
    claimAffected (computeImpact sampleGraph [0]) 1 = true := by
  decide

theorem control_unrelated_declared_nonimpact :
    declaredNonImpact sampleGraph [0] 99 = true := by
  decide

def modelA : ModelCertificate :=
  { modelId := 1
    context := emptyContext
    claims := [formalClaim, computationalClaim]
    evidence := [
      { id := 10, cls := .formal, accepted := true },
      { id := 11, cls := .computational, accepted := true }] }

def modelB : ModelCertificate :=
  { modelId := 2
    context := emptyContext
    claims := [formalClaim, computationalClaim]
    evidence := [
      { id := 10, cls := .formal, accepted := true },
      { id := 11, cls := .computational, accepted := false }] }

def sampleEnsemble : Ensemble := ⟨[modelA, modelB]⟩

theorem control_agreement_contains_formal :
    formalClaim ∈ agreementCore sampleEnsemble [formalClaim, computationalClaim] := by
  decide

theorem control_dispute_contains_computational :
    computationalClaim ∈ disputeFrontier sampleEnsemble [formalClaim, computationalClaim] := by
  decide

theorem control_distinguishing_computational :
    Distinguishing sampleEnsemble computationalClaim := by
  unfold Distinguishing
  decide

theorem control_rejected_blocks_formal :
    ¬ Assures emptyContext .formal formalClaim
        [{ id := 10, cls := .formal, accepted := false }] :=
  rejected_evidence_blocks emptyContext formalClaim 10 .formal rfl rfl

theorem control_formal_covers_computational_claim :
    Assures emptyContext .computational computationalClaim
      [{ id := 11, cls := .formal, accepted := true }] :=
  formal_evidence_assures_computational emptyContext computationalClaim 11 rfl rfl

theorem control_empirical_rejects_formal :
    ¬ Assures emptyContext .formal formalClaim
        [{ id := 10, cls := .empirical, accepted := true }] :=
  empirical_cannot_assure_formal emptyContext formalClaim 10 rfl rfl

theorem control_agreement_dispute_disjoint :
    formalClaim ∉ disputeFrontier sampleEnsemble [formalClaim, computationalClaim] := by
  exact agreement_dispute_disjoint sampleEnsemble
    [formalClaim, computationalClaim] formalClaim
    (by decide)

theorem control_changed_artifact_in_impact :
    memNat (computeImpact sampleGraph [0]).affectedArtifacts 0 = true := by
  decide

theorem control_seed_reaches_processed :
    memNat (computeImpact sampleGraph [0]).affectedArtifacts 1 = true := by
  decide

theorem control_incomplete_never_endorses :
    ¬ NonImpact sampleGraph [0] 99 false :=
  incomplete_never_endorses sampleGraph [0] 99

theorem control_le_trans_formal_comp_prov :
    EvidenceClass.formal.le .provenance = true := by
  exact le_trans .formal .computational .provenance rfl rfl

theorem control_lattice_antisymm_comp :
    EvidenceClass.computational = EvidenceClass.computational :=
  le_antisymm .computational .computational rfl rfl

end PcsEpistemic.Controls
