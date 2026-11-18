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

def Formula.toJsonFormula : Formula → JsonFormula
  | .atom i => .atom i
  | .not φ => .not φ.toJsonFormula
  | .and φ ψ => .and φ.toJsonFormula ψ.toJsonFormula

theorem Formula.toJsonFormula_toFormula (φ : Formula) :
    φ.toJsonFormula.toFormula = φ := by
  induction φ with
  | atom i => rfl
  | not φ ih => simpa [Formula.toJsonFormula, JsonFormula.toFormula] using congrArg Formula.not ih
  | and φ ψ ihφ ihψ =>
      simp [Formula.toJsonFormula, JsonFormula.toFormula, ihφ, ihψ]

theorem JsonFormula.toFormula_toJsonFormula (φ : JsonFormula) :
    φ.toFormula.toJsonFormula = φ := by
  induction φ with
  | atom i => rfl
  | not φ ih => simpa [JsonFormula.toFormula, Formula.toJsonFormula] using congrArg JsonFormula.not ih
  | and φ ψ ihφ ihψ =>
      simp [JsonFormula.toFormula, Formula.toJsonFormula, ihφ, ihψ]

theorem JsonFormula.toFormula_injective {φ ψ : JsonFormula}
    (h : φ.toFormula = ψ.toFormula) : φ = ψ := by
  have := congrArg Formula.toJsonFormula h
  simpa [JsonFormula.toFormula_toJsonFormula] using this

def JsonFormula.depth : JsonFormula → Nat
  | .atom _ => 0
  | .not φ => φ.depth + 1
  | .and φ ψ => Nat.max φ.depth ψ.depth + 1

theorem JsonFormula.depth_eq_toFormula (φ : JsonFormula) :
    φ.depth = φ.toFormula.depth := by
  induction φ with
  | atom i => rfl
  | not φ ih => simp [JsonFormula.depth, JsonFormula.toFormula, Formula.depth, ih]
  | and φ ψ ihφ ihψ =>
      simp [JsonFormula.depth, JsonFormula.toFormula, Formula.depth, ihφ, ihψ]

def Authority.toJsonAuth : Authority → JsonAuth
  | .disputed => .disputed
  | .hypothesis => .hypothesis
  | .empiricalAsserted => .empiricalAsserted
  | .assumption => .assumption
  | .derived => .derived
  | .mathVerified => .mathVerified

theorem Authority.toJsonAuth_toAuthority (a : Authority) :
    a.toJsonAuth.toAuthority = a := by cases a <;> rfl

theorem JsonAuth.toAuthority_toJsonAuth (j : JsonAuth) :
    j.toAuthority.toJsonAuth = j := by cases j <;> rfl

theorem JsonAuth.toAuthority_surjective (a : Authority) :
    ∃ j : JsonAuth, j.toAuthority = a :=
  ⟨a.toJsonAuth, Authority.toJsonAuth_toAuthority a⟩

structure JsonPremise where
  id : Nat
  formula : JsonFormula
  declaredAuthority : JsonAuth
  unknownKeys : List String := []
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

theorem JsonRule.toStepSpec_injective {r₁ r₂ : JsonRule}
    (h : r₁.toStepSpec = r₂.toStepSpec) : r₁ = r₂ := by
  cases r₁ <;> cases r₂ <;> simp [JsonRule.toStepSpec] at h <;> simp [h]

structure JsonStep where
  id : Nat
  rule : JsonRule
  claimedFormula : Option JsonFormula := none
  claimedSupport : Option (List Nat) := none
  claimedAuthority : Option JsonAuth := none
  claimedMathEstablished : Option Bool := none
  unknownKeys : List String := []
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

def premisesKeysOk : List JsonPremise → Bool
  | [] => true
  | p :: rest => decide (p.unknownKeys = []) && premisesKeysOk rest

def stepsKeysOk : List JsonStep → Bool
  | [] => true
  | s :: rest => decide (s.unknownKeys = []) && stepsKeysOk rest

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
  else if !(premisesKeysOk c.premises = true) then none
  else if !(stepsKeysOk c.steps = true) then none
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

theorem premisesKeysOk_false_of_mem
    (ps : List JsonPremise) (p : JsonPremise)
    (hp : p ∈ ps) (hne : p.unknownKeys ≠ []) :
    premisesKeysOk ps = false := by
  induction ps with
  | nil => cases hp
  | cons p0 rest ih =>
      cases hp with
      | head => simp [premisesKeysOk, hne]
      | tail _ hp' =>
          cases h0 : decide (p0.unknownKeys = []) with
          | false => simp [premisesKeysOk, h0]
          | true => simp [premisesKeysOk, h0, ih hp']

theorem stepsKeysOk_false_of_mem
    (ss : List JsonStep) (s : JsonStep)
    (hs : s ∈ ss) (hne : s.unknownKeys ≠ []) :
    stepsKeysOk ss = false := by
  induction ss with
  | nil => cases hs
  | cons s0 rest ih =>
      cases hs with
      | head => simp [stepsKeysOk, hne]
      | tail _ hs' =>
          cases h0 : decide (s0.unknownKeys = []) with
          | false => simp [stepsKeysOk, h0]
          | true => simp [stepsKeysOk, h0, ih hs']

theorem checkJsonCert_rejects_unknown_premise_keys
    (c : JsonCertificate) (p : JsonPremise)
    (hp : p ∈ c.premises) (hne : p.unknownKeys ≠ [])
    (hunk : c.unknownTopKeys = []) :
    checkJsonCert c = none := by
  have hfo := premisesKeysOk_false_of_mem c.premises p hp hne
  simp [checkJsonCert, decodeJsonCert, hunk, hfo]

theorem checkJsonCert_rejects_unknown_step_keys
    (c : JsonCertificate) (s : JsonStep)
    (hs : s ∈ c.steps) (hne : s.unknownKeys ≠ [])
    (hunk : c.unknownTopKeys = [])
    (hpok : premisesKeysOk c.premises = true) :
    checkJsonCert c = none := by
  have hfo := stepsKeysOk_false_of_mem c.steps s hs hne
  simp [checkJsonCert, decodeJsonCert, hunk, hpok, hfo]

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

theorem decodeJsonCert_ok_of
    (c : JsonCertificate)
    (hunk : c.unknownTopKeys = [])
    (hpok : premisesKeysOk c.premises = true)
    (hsok : stepsKeysOk c.steps = true)
    (hdepth : formulasDepthOk c.premises = true) :
    decodeJsonCert c = some {
      schemaVersion := c.schemaVersion
      premises := c.premises.map decodePremise
      steps := c.steps.map decodeStep
      conclusionStep := c.conclusionStep
      claimedConclusion := c.claimedConclusion.map (·.toFormula)
      claimedFinalSupport := c.claimedFinalSupport
      claimedFinalAuthority := c.claimedFinalAuthority.map (·.toAuthority)
    } := by
  simp [decodeJsonCert, hunk, hpok, hsok, hdepth]

/-- Semantic triangle at the JSON-object layer. -/
theorem json_semantic_triangle
    (c : JsonCertificate) (j : VerifiedJudgment)
    (h : checkJsonCert c = some j) :
    (∃ sc, decodeJsonCert c = some sc ∧ checkCertificate sc.erase = some j) ∧
      j.assurance.mathEstablished = false ∧
      (∃ sc, decodeJsonCert c = some sc ∧
        Derives sc.erase.toContext j.support j.assurance.declared j.formula) :=
  ⟨checkJsonCert_implies_core c j h,
   checkJsonCert_mathEstablished_false c j h,
   checkJsonCert_sound c j h⟩

end ScientificReasoning

#print axioms ScientificReasoning.checkJsonCert_sound
#print axioms ScientificReasoning.checkJsonCert_rejects_unknown_keys
#print axioms ScientificReasoning.checkJsonCert_rejects_deep_formula
#print axioms ScientificReasoning.no_math_established_without_attestation
#print axioms ScientificReasoning.Formula.toJsonFormula_toFormula
#print axioms ScientificReasoning.JsonFormula.toFormula_toJsonFormula
#print axioms ScientificReasoning.json_semantic_triangle
#print axioms ScientificReasoning.JsonRule.toStepSpec_injective
#print axioms ScientificReasoning.checkJsonCert_rejects_unknown_premise_keys
#print axioms ScientificReasoning.checkJsonCert_rejects_unknown_step_keys
