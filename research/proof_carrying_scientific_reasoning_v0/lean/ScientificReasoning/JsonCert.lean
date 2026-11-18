import ScientificReasoning.Surface

/-!
# Post-parse JSON object graph → surface certificate

Typed certificate object after successful `json.loads` (duplicate keys already
rejected by the parser hook). Closes the decoder gap at the object-graph layer.

**Externally trusted:** byte-string → this AST (`json.loads` / CPython).
-/

namespace ScientificReasoning

inductive JsonAuth where
  | disputed | hypothesis | empiricalAsserted | assumption | derived | mathVerified
  deriving Repr, DecidableEq, Inhabited

def JsonAuth.toAuthority : JsonAuth → Authority
  | .disputed => .disputed
  | .hypothesis => .hypothesis
  | .empiricalAsserted => .empiricalAsserted
  | .assumption => .assumption
  | .derived => .derived
  | .mathVerified => .mathVerified

inductive JsonFormula where
  | atom : Nat → JsonFormula
  | not : JsonFormula → JsonFormula
  | and : JsonFormula → JsonFormula → JsonFormula
  deriving Repr, DecidableEq, Inhabited

def JsonFormula.toFormula : JsonFormula → Formula
  | .atom i => .atom i
  | .not φ => .not φ.toFormula
  | .and φ ψ => .and φ.toFormula ψ.toFormula

def JsonFormula.depth : JsonFormula → Nat
  | .atom _ => 0
  | .not φ => φ.depth + 1
  | .and φ ψ => Nat.max φ.depth ψ.depth + 1

def maxFormulaDepth : Nat := 64

structure JsonPremise where
  id : Nat
  formula : JsonFormula
  declaredAuthority : JsonAuth
  deriving Repr, DecidableEq, Inhabited

inductive JsonRule where
  | hyp (premiseId : Nat)
  | andI (left right : Nat)
  | andE1 (src : Nat)
  | andE2 (src : Nat)
  deriving Repr, DecidableEq, Inhabited

def JsonRule.toStepSpec : JsonRule → StepSpec
  | .hyp p => .hyp p
  | .andI l r => .andI l r
  | .andE1 s => .andE1 s
  | .andE2 s => .andE2 s

structure JsonStep where
  id : Nat
  rule : JsonRule
  claimedFormula : Option JsonFormula := none
  claimedSupport : Option (List Nat) := none
  claimedAuthority : Option JsonAuth := none
  claimedMathEstablished : Option Bool := none
  deriving Repr, DecidableEq, Inhabited

structure JsonCertificate where
  schemaVersion : Nat
  premises : List JsonPremise
  steps : List JsonStep
  conclusionStep : Nat
  claimedConclusion : Option JsonFormula := none
  claimedFinalSupport : Option (List Nat) := none
  claimedFinalAuthority : Option JsonAuth := none
  unknownTopKeys : List String := []
  deriving Repr, DecidableEq, Inhabited

def formulasDepthOk : List JsonPremise → Bool
  | [] => true
  | p :: rest => decide (p.formula.depth ≤ maxFormulaDepth) && formulasDepthOk rest

def decodePremise (p : JsonPremise) : Premise :=
  { id := p.id
    formula := p.formula.toFormula
    authority := p.declaredAuthority.toAuthority }

def decodeStep (s : JsonStep) : SurfaceStep :=
  { id := s.id
    spec := s.rule.toStepSpec
    claimedFormula := s.claimedFormula.map (·.toFormula)
    claimedSupport := s.claimedSupport
    claimedAuthority := s.claimedAuthority.map (·.toAuthority)
    claimedMathEstablished := s.claimedMathEstablished }

def decodeJsonCert (c : JsonCertificate) : Option SurfaceCertificate :=
  if !(c.unknownTopKeys = []) then none
  else if !(formulasDepthOk c.premises = true) then none
  else
    some {
      schemaVersion := c.schemaVersion
      premises := c.premises.map decodePremise
      steps := c.steps.map decodeStep
      conclusionStep := c.conclusionStep
      claimedConclusion := c.claimedConclusion.map (·.toFormula)
      claimedFinalSupport := c.claimedFinalSupport
      claimedFinalAuthority := c.claimedFinalAuthority.map (·.toAuthority)
    }

def checkJsonCert (c : JsonCertificate) : Option VerifiedJudgment :=
  match decodeJsonCert c with
  | none => none
  | some sc => checkSurface sc

theorem checkJsonCert_implies_checkSurface
    (c : JsonCertificate) (j : VerifiedJudgment)
    (h : checkJsonCert c = some j) :
    ∃ sc, decodeJsonCert c = some sc ∧ checkSurface sc = some j := by
  simp [checkJsonCert] at h
  cases hd : decodeJsonCert c with
  | none => simp [hd] at h
  | some sc =>
      simp [hd] at h
      exact ⟨sc, rfl, h⟩

theorem checkJsonCert_sound
    (c : JsonCertificate) (j : VerifiedJudgment)
    (h : checkJsonCert c = some j) :
    ∃ sc, decodeJsonCert c = some sc ∧
      Derives sc.erase.toContext j.support j.assurance.declared j.formula := by
  obtain ⟨sc, hd, hs⟩ := checkJsonCert_implies_checkSurface c j h
  exact ⟨sc, hd, checkSurface_sound sc j hs⟩

theorem checkJsonCert_entails4
    (c : JsonCertificate) (j : VerifiedJudgment)
    (h : checkJsonCert c = some j) :
    ∃ sc, decodeJsonCert c = some sc ∧
      Belnap.Entails4 sc.erase.toContext j.formula := by
  obtain ⟨sc, hd, hs⟩ := checkJsonCert_implies_checkSurface c j h
  exact ⟨sc, hd, checkSurface_entails4 sc j hs⟩

theorem checkJsonCert_mathEstablished_false
    (c : JsonCertificate) (j : VerifiedJudgment)
    (h : checkJsonCert c = some j) :
    j.assurance.mathEstablished = false := by
  obtain ⟨sc, _, hs⟩ := checkJsonCert_implies_checkSurface c j h
  exact checkSurface_mathEstablished_false sc j hs

theorem checkJsonCert_implies_core
    (c : JsonCertificate) (j : VerifiedJudgment)
    (h : checkJsonCert c = some j) :
    ∃ sc, decodeJsonCert c = some sc ∧ checkCertificate sc.erase = some j := by
  obtain ⟨sc, hd, hs⟩ := checkJsonCert_implies_checkSurface c j h
  exact ⟨sc, hd, checkSurface_implies_checkCertificate sc j hs⟩

theorem checkJsonCert_rejects_unknown_keys
    (c : JsonCertificate) (hne : c.unknownTopKeys ≠ []) :
    checkJsonCert c = none := by
  have : decodeJsonCert c = none := by
    simp [decodeJsonCert, hne]
  simp [checkJsonCert, this]

theorem formulasDepthOk_false_of_mem
    (ps : List JsonPremise) (p : JsonPremise)
    (hp : p ∈ ps) (hd : maxFormulaDepth < p.formula.depth) :
    formulasDepthOk ps = false := by
  induction ps with
  | nil => cases hp
  | cons p0 rest ih =>
      cases hp with
      | head => simp [formulasDepthOk, Nat.not_le.mpr hd]
      | tail _ hp' =>
          cases h0 : decide (p0.formula.depth ≤ maxFormulaDepth) with
          | false => simp [formulasDepthOk, h0]
          | true => simp [formulasDepthOk, h0, ih hp']

theorem checkJsonCert_rejects_deep_formula
    (c : JsonCertificate) (p : JsonPremise)
    (hp : p ∈ c.premises) (hd : maxFormulaDepth < p.formula.depth)
    (hunk : c.unknownTopKeys = []) :
    checkJsonCert c = none := by
  have hfo := formulasDepthOk_false_of_mem c.premises p hp hd
  simp [checkJsonCert, decodeJsonCert, hunk, hfo]

/-- Attestation boundary: schema-v1 acceptance never yields mathEstablished. -/
theorem no_math_established_without_attestation
    (c : JsonCertificate) (j : VerifiedJudgment)
    (h : checkJsonCert c = some j) :
    j.assurance.mathEstablished = false :=
  checkJsonCert_mathEstablished_false c j h

end ScientificReasoning

#print axioms ScientificReasoning.checkJsonCert_sound
#print axioms ScientificReasoning.checkJsonCert_rejects_unknown_keys
#print axioms ScientificReasoning.checkJsonCert_rejects_deep_formula
#print axioms ScientificReasoning.no_math_established_without_attestation
