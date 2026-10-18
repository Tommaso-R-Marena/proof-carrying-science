import PCSEpistemic.Stratum

/-
Stratified assurance judgment. Evidence must discharge the claim stratum,
PASS, and be predicate-bound. Residuals record what remains OPEN.
-/

namespace PCSEpistemic

inductive Outcome where
  | pass
  | fail
  | unverified
  deriving DecidableEq, Repr

structure Assumption where
  id : String
  statement : String := ""
  deriving DecidableEq, Repr

structure Evidence where
  id : String
  stratum : Stratum
  outcome : Outcome
  predicate : String
  artifactIds : List String := []
  deriving DecidableEq, Repr

structure Claim where
  id : String
  stratum : Stratum
  predicate : String
  requiredEvidence : List String := []
  assumptions : List String := []
  deriving DecidableEq, Repr

structure Residual where
  id : String
  stratum : Stratum
  reason : String
  deriving DecidableEq, Repr

def ContextCovers (Γ : List Assumption) (c : Claim) : Prop :=
  ∀ aid, aid ∈ c.assumptions → ∃ a, a ∈ Γ ∧ a.id = aid

def BoundTo (e : Evidence) (c : Claim) : Prop :=
  e.id ∈ c.requiredEvidence ∧ e.predicate = c.predicate

inductive Assures : List Assumption → Stratum → Claim → List Evidence → Prop
  | support {Γ : List Assumption} {s : Stratum} {c : Claim} {es : List Evidence}
      (e : Evidence)
      (member : e ∈ es)
      (context : ContextCovers Γ c)
      (claimStratum : c.stratum = s)
      (discharge : Stratum.canDischarge e.stratum c.stratum = true)
      (passed : e.outcome = Outcome.pass)
      (bound : BoundTo e c) :
      Assures Γ s c es

theorem assures_context
    {Γ : List Assumption} {s : Stratum} {c : Claim} {es : List Evidence}
    (h : Assures Γ s c es) : ContextCovers Γ c := by
  cases h with
  | support _ _ context _ _ _ _ => exact context

theorem assures_claim_stratum
    {Γ : List Assumption} {s : Stratum} {c : Claim} {es : List Evidence}
    (h : Assures Γ s c es) : c.stratum = s := by
  cases h with
  | support _ _ _ claimStratum _ _ _ => exact claimStratum

theorem assures_has_passing_discharge
    {Γ : List Assumption} {s : Stratum} {c : Claim} {es : List Evidence}
    (h : Assures Γ s c es) :
    ∃ e, e ∈ es ∧ e.outcome = Outcome.pass ∧
      Stratum.canDischarge e.stratum c.stratum = true ∧ BoundTo e c := by
  cases h with
  | support e member _ _ discharge passed bound =>
      exact ⟨e, member, passed, discharge, bound⟩

theorem computational_cannot_assure_empirical
    {Γ : List Assumption} {c : Claim} {es : List Evidence}
    (_hc : c.stratum = Stratum.empirical)
    (hE : ∀ e ∈ es, e.stratum = Stratum.computational) :
    ¬ Assures Γ Stratum.empirical c es := by
  intro h
  cases h with
  | support e member _ claimStratum discharge _ _ =>
      have he : e.stratum = Stratum.computational := hE e member
      have hdis :
          Stratum.canDischarge Stratum.computational Stratum.empirical = true := by
        simpa [he, claimStratum, _hc] using discharge
      have hfalse :
          Stratum.canDischarge Stratum.computational Stratum.empirical = false := by
        decide
      exact Bool.noConfusion (hdis.symm.trans hfalse)

theorem formal_cannot_assure_continuum
    {Γ : List Assumption} {c : Claim} {es : List Evidence}
    (_hc : c.stratum = Stratum.continuum)
    (hE : ∀ e ∈ es, e.stratum = Stratum.formal) :
    ¬ Assures Γ Stratum.continuum c es := by
  intro h
  cases h with
  | support e member _ claimStratum discharge _ _ =>
      have he : e.stratum = Stratum.formal := hE e member
      have hdis :
          Stratum.canDischarge Stratum.formal Stratum.continuum = true := by
        simpa [he, claimStratum, _hc] using discharge
      have hfalse :
          Stratum.canDischarge Stratum.formal Stratum.continuum = false := by
        decide
      exact Bool.noConfusion (hdis.symm.trans hfalse)

theorem continuum_cannot_assure_causal
    {Γ : List Assumption} {c : Claim} {es : List Evidence}
    (_hc : c.stratum = Stratum.causal)
    (hE : ∀ e ∈ es, e.stratum = Stratum.continuum) :
    ¬ Assures Γ Stratum.causal c es := by
  intro h
  cases h with
  | support e member _ claimStratum discharge _ _ =>
      have he : e.stratum = Stratum.continuum := hE e member
      have hdis :
          Stratum.canDischarge Stratum.continuum Stratum.causal = true := by
        simpa [he, claimStratum, _hc] using discharge
      have hfalse :
          Stratum.canDischarge Stratum.continuum Stratum.causal = false := by
        decide
      exact Bool.noConfusion (hdis.symm.trans hfalse)

def continuumResidual (claimId : String) : Residual where
  id := claimId ++ ":continuum-residual"
  stratum := .continuum
  reason :=
    "Discrete/formal matrix support does not discharge continuum accuracy; \
     residual truncation/refinement obligations remain OPEN."

def empiricalResidual (claimId : String) : Residual where
  id := claimId ++ ":empirical-residual"
  stratum := .empirical
  reason :=
    "Continuum residual bounds do not discharge empirical/statistical adequacy; \
     observational validation remains OPEN."

def causalResidual (claimId : String) : Residual where
  id := claimId ++ ":causal-residual"
  stratum := .causal
  reason :=
    "Empirical association does not discharge causal/external-world claims; \
     identification assumptions remain OPEN."

/-- Residuals implied by supporting a claim only up to stratum `s`. -/
def impliedResiduals (c : Claim) (s : Stratum) : List Residual :=
  match s with
  | .integrity | .computational | .formal =>
      [continuumResidual c.id, empiricalResidual c.id, causalResidual c.id]
  | .continuum =>
      [empiricalResidual c.id, causalResidual c.id]
  | .empirical =>
      [causalResidual c.id]
  | .causal =>
      []

theorem formal_support_keeps_continuum_residual (c : Claim) :
    continuumResidual c.id ∈ impliedResiduals c Stratum.formal := by
  simp [impliedResiduals]

theorem formal_support_keeps_empirical_residual (c : Claim) :
    empiricalResidual c.id ∈ impliedResiduals c Stratum.formal := by
  simp [impliedResiduals]

theorem continuum_support_keeps_empirical_residual (c : Claim) :
    empiricalResidual c.id ∈ impliedResiduals c Stratum.continuum := by
  simp [impliedResiduals]

theorem continuum_support_keeps_causal_residual (c : Claim) :
    causalResidual c.id ∈ impliedResiduals c Stratum.continuum := by
  simp [impliedResiduals]

def isForbiddenPromotion (e : Evidence) (c : Claim) : Bool :=
  Stratum.forbiddenPromotion e.stratum c.stratum

theorem forbidden_promotion_blocks_assures
    {Γ : List Assumption} {c : Claim} {es : List Evidence} {e : Evidence}
    (only : ∀ x ∈ es, x = e)
    (hforb : isForbiddenPromotion e c = true) :
    ¬ Assures Γ c.stratum c es := by
  intro h
  cases h with
  | support e' member' _ _ discharge _ _ =>
      have heq : e' = e := only e' member'
      subst heq
      have hblock := Stratum.forbidden_not_discharge hforb
      exact Bool.noConfusion (Eq.trans discharge.symm hblock)

end PCSEpistemic
