import PCSEpistemic.Judgment

/-
Compositional stratified assurance with meet stratum and residual union.
-/

namespace PCSEpistemic

def asAssumption (c : Claim) : Assumption where
  id := c.id
  statement := "supported claim " ++ c.id ++ " at stratum"

def mergeAssumptions (Γ₁ Γ₂ : List Assumption) : List Assumption :=
  Γ₁ ++ Γ₂

def mergeEvidence (E₁ E₂ : List Evidence) : List Evidence :=
  E₁ ++ E₂

def mergeResiduals (R₁ R₂ : List Residual) : List Residual :=
  R₁ ++ R₂.filter (fun r => !(R₁.any (fun x => x.id == r.id)))

theorem mem_mergeEvidence_right
    {E₁ E₂ : List Evidence} {e : Evidence} (h : e ∈ E₂) :
    e ∈ mergeEvidence E₁ E₂ := by
  simp [mergeEvidence, h]

theorem compose_preserves_downstream
    {Γ₁ Γ₂ : List Assumption} {s₂ : Stratum}
    {c₁ c₂ : Claim} {E₁ E₂ : List Evidence}
    (h₂ : Assures (Γ₂ ++ [asAssumption c₁]) s₂ c₂ E₂) :
    Assures (mergeAssumptions Γ₁ Γ₂ ++ [asAssumption c₁]) s₂ c₂
      (mergeEvidence E₁ E₂) := by
  cases h₂ with
  | support e member context claimStratum discharge passed bound =>
      refine Assures.support e (mem_mergeEvidence_right member) ?_ claimStratum
        discharge passed bound
      intro aid haid
      obtain ⟨a, ha, hid⟩ := context aid haid
      refine ⟨a, ?_, hid⟩
      simp [mergeAssumptions] at ha ⊢
      exact Or.inr ha

theorem compose_meet_le_left (s₁ s₂ : Stratum) : Stratum.meet s₁ s₂ ≤ s₁ :=
  Stratum.meet_le_left s₁ s₂

theorem compose_meet_le_right (s₁ s₂ : Stratum) : Stratum.meet s₁ s₂ ≤ s₂ :=
  Stratum.meet_le_right s₁ s₂

def composedResiduals (c₂ : Claim) (s₁ s₂ : Stratum)
    (R₁ R₂ : List Residual) : List Residual :=
  mergeResiduals (mergeResiduals R₁ R₂) (impliedResiduals c₂ (Stratum.meet s₁ s₂))

structure StratifiedCertificate where
  assumptions : List Assumption
  claim : Claim
  evidence : List Evidence
  stratum : Stratum
  residuals : List Residual
  deriving DecidableEq, Repr

def composeCertificates (a b : StratifiedCertificate) : Option StratifiedCertificate :=
  if b.assumptions.any (fun x => x.id == a.claim.id) then
    -- Keep `asAssumption(a.claim)` in the merged context so downstream claim
    -- coverage remains exact after composition.
    some {
      assumptions := mergeAssumptions (mergeAssumptions a.assumptions [asAssumption a.claim])
        (b.assumptions.filter (fun x => x.id != a.claim.id))
      claim := { b.claim with stratum := Stratum.meet a.stratum b.stratum }
      evidence := mergeEvidence a.evidence b.evidence
      stratum := Stratum.meet a.stratum b.stratum
      residuals := composedResiduals b.claim a.stratum b.stratum a.residuals b.residuals
    }
  else
    none

theorem composeCertificates_meet
    {a b c : StratifiedCertificate}
    (h : composeCertificates a b = some c) :
    c.stratum = Stratum.meet a.stratum b.stratum := by
  unfold composeCertificates at h
  by_cases hCite : b.assumptions.any (fun x => x.id == a.claim.id) = true
  · simp [hCite] at h
    cases h
    rfl
  · simp [hCite] at h

end PCSEpistemic
