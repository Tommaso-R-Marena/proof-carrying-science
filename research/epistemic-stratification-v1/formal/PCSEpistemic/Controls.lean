import PCSEpistemic.Composition
import PCSEpistemic.Invalidation

/-
Kernel controls for epistemic stratification. Research reference only.
-/

namespace PCSEpistemic.Controls

open PCSEpistemic

def Γ₀ : List Assumption := [{ id := "A_model", statement := "finite transport model" }]

def claimFormal : Claim where
  id := "C_discrete"
  stratum := .formal
  predicate := "amount-conserved"
  requiredEvidence := ["E_matrix"]
  assumptions := ["A_model"]

def claimEmpirical : Claim where
  id := "C_world"
  stratum := .empirical
  predicate := "amount-conserved"
  requiredEvidence := ["E_matrix"]
  assumptions := ["A_model"]

def claimContinuum : Claim where
  id := "C_continuum"
  stratum := .continuum
  predicate := "amount-conserved"
  requiredEvidence := ["E_matrix"]
  assumptions := ["A_model"]

def evidenceFormal : Evidence where
  id := "E_matrix"
  stratum := .formal
  outcome := .pass
  predicate := "amount-conserved"
  artifactIds := ["matrix.json"]

def evidenceComputational : Evidence where
  id := "E_matrix"
  stratum := .computational
  outcome := .pass
  predicate := "amount-conserved"
  artifactIds := ["matrix.json"]

theorem positive_formal_support :
    Assures Γ₀ Stratum.formal claimFormal [evidenceFormal] := by
  refine Assures.support evidenceFormal (by simp) ?_ rfl (by decide) rfl ?_
  · intro aid haid
    have : aid = "A_model" := by simpa [claimFormal] using haid
    subst this
    exact ⟨{ id := "A_model", statement := "finite transport model" }, by simp [Γ₀], rfl⟩
  · exact ⟨by decide, by decide⟩

theorem negative_computational_to_empirical :
    ¬ Assures Γ₀ Stratum.empirical claimEmpirical [evidenceComputational] := by
  exact computational_cannot_assure_empirical rfl (by
    intro e he
    simp at he
    subst he
    rfl)

theorem negative_formal_to_continuum :
    ¬ Assures Γ₀ Stratum.continuum claimContinuum [evidenceFormal] := by
  exact formal_cannot_assure_continuum rfl (by
    intro e he
    simp at he
    subst he
    rfl)

theorem residual_after_formal :
    continuumResidual claimFormal.id ∈ impliedResiduals claimFormal Stratum.formal :=
  formal_support_keeps_continuum_residual claimFormal

def upstream : StratifiedCertificate where
  assumptions := Γ₀
  claim := claimFormal
  evidence := [evidenceFormal]
  stratum := .formal
  residuals := impliedResiduals claimFormal .formal

def downstream : StratifiedCertificate where
  assumptions := Γ₀ ++ [asAssumption claimFormal]
  claim := {
    id := "C_pipeline"
    stratum := .computational
    predicate := "pipeline-ok"
    requiredEvidence := ["E_pipe"]
    assumptions := ["A_model", "C_discrete"]
  }
  evidence := [{
    id := "E_pipe"
    stratum := .computational
    outcome := .pass
    predicate := "pipeline-ok"
    artifactIds := ["pipe.json"]
  }]
  stratum := .computational
  residuals := []

theorem composition_meet_is_computational :
    ∃ c, composeCertificates upstream downstream = some c ∧
      c.stratum = Stratum.computational := by
  refine ⟨{
    assumptions := mergeAssumptions
      (mergeAssumptions upstream.assumptions [asAssumption upstream.claim])
      (downstream.assumptions.filter (fun x => x.id != upstream.claim.id))
    claim := { downstream.claim with stratum := Stratum.meet upstream.stratum downstream.stratum }
    evidence := mergeEvidence upstream.evidence downstream.evidence
    stratum := Stratum.meet upstream.stratum downstream.stratum
    residuals := composedResiduals downstream.claim upstream.stratum downstream.stratum
      upstream.residuals downstream.residuals
  }, ?_, rfl⟩
  simp [composeCertificates, upstream, downstream, asAssumption, claimFormal, Γ₀]

theorem invalidation_marks_matrix_claim :
    let inv := invalidate ["matrix.json"] [evidenceFormal] [claimFormal]
    "C_discrete" ∈ inv.affectedClaims ∧ "E_matrix" ∈ inv.affectedEvidence := by
  simp [invalidate, claimTouches, evidenceTouches, evidenceFormal, claimFormal]

end PCSEpistemic.Controls
