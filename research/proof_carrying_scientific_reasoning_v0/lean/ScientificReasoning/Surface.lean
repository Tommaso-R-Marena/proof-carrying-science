import ScientificReasoning.CheckCertificate
import ScientificReasoning.Belnap
import ScientificReasoning.Completeness

/-!
# Schema-v1 surface checker (Lean model of Python WF + claims)

Models the post-parse object graph validated by `check_certificate_v1.check`.
Does **not** model `json.loads` / CPython (irreducible runtime boundary).
-/

namespace ScientificReasoning

def maxPremises : Nat := 256
def maxSteps : Nat := 1024

structure SurfaceStep where
  id : Nat
  spec : StepSpec
  claimedFormula : Option Formula := none
  claimedSupport : Option Support := none
  claimedAuthority : Option Authority := none
  claimedMathEstablished : Option Bool := none
  deriving Repr, DecidableEq, Inhabited

structure SurfaceCertificate where
  schemaVersion : Nat
  premises : List Premise
  steps : List SurfaceStep
  conclusionStep : Nat
  claimedConclusion : Option Formula := none
  claimedFinalSupport : Option Support := none
  claimedFinalAuthority : Option Authority := none
  deriving Repr, DecidableEq, Inhabited

def SurfaceCertificate.erase (c : SurfaceCertificate) : StructuredCertificate :=
  { premises := c.premises
    steps := c.steps.map (·.spec)
    conclusionStep := c.conclusionStep }

def stepIdsOk : Nat → List SurfaceStep → Bool
  | _, [] => true
  | i, s :: rest => decide (s.id = i) && stepIdsOk (i + 1) rest

def optionEq {α} [DecidableEq α] : Option α → α → Bool
  | none, _ => true
  | some x, y => decide (x = y)

def claimsMatchStep (s : SurfaceStep) (j : VerifiedJudgment) : Bool :=
  optionEq s.claimedFormula j.formula &&
  optionEq s.claimedSupport j.support &&
  optionEq s.claimedAuthority j.assurance.declared &&
  !(s.claimedMathEstablished == some true)

def claimsMatchSteps : List SurfaceStep → List VerifiedJudgment → Bool
  | [], [] => true
  | s :: ss, j :: js => claimsMatchStep s j && claimsMatchSteps ss js
  | _, _ => false

def claimsMatchTop (c : SurfaceCertificate) (j : VerifiedJudgment) : Bool :=
  optionEq c.claimedConclusion j.formula &&
  optionEq c.claimedFinalSupport j.support &&
  optionEq c.claimedFinalAuthority j.assurance.declared &&
  !j.assurance.mathEstablished

def surfaceWF (c : SurfaceCertificate) : Bool :=
  (c.schemaVersion == 1) &&
  !c.steps.isEmpty &&
  decide (c.premises.length ≤ maxPremises) &&
  decide (c.steps.length ≤ maxSteps) &&
  uniquePremiseIds c.premises &&
  stepIdsOk 0 c.steps

def checkSurface (c : SurfaceCertificate) : Option VerifiedJudgment :=
  if surfaceWF c then
    match checkStepsLTR c.premises (c.steps.map (·.spec)) with
    | none => none
    | some js =>
        if claimsMatchSteps c.steps js then
          match Nat.decLt c.conclusionStep js.length with
          | isFalse _ => none
          | isTrue hlt =>
              let j := js[c.conclusionStep]'hlt
              if claimsMatchTop c j then some j else none
        else none
  else none

theorem checkSurface_implies_checkCertificate
    (c : SurfaceCertificate) (j : VerifiedJudgment)
    (h : checkSurface c = some j) :
    checkCertificate c.erase = some j := by
  simp [checkSurface] at h
  cases hwf : surfaceWF c with
  | false => simp [hwf] at h
  | true =>
      simp [hwf] at h
      cases hs : checkStepsLTR c.premises (c.steps.map (·.spec)) with
      | none => simp [hs] at h
      | some js =>
          simp [hs] at h
          cases hc : claimsMatchSteps c.steps js with
          | false => simp [hc] at h
          | true =>
              simp [hc] at h
              cases hlt : Nat.decLt c.conclusionStep js.length with
              | isFalse => simp [hlt] at h
              | isTrue ht =>
                  simp [hlt] at h
                  cases htop : claimsMatchTop c (js[c.conclusionStep]'ht) with
                  | false => simp [htop] at h
                  | true =>
                      simp [htop] at h
                      cases h
                      have hu : uniquePremiseIds c.premises = true := by
                        simp [surfaceWF, Bool.and_eq_true] at hwf
                        exact hwf.1.2
                      simp [checkCertificate, SurfaceCertificate.erase, decide_eq_true hu,
                        hs, hlt]

theorem checkSurface_sound
    (c : SurfaceCertificate) (j : VerifiedJudgment)
    (h : checkSurface c = some j) :
    Derives c.erase.toContext j.support j.assurance.declared j.formula :=
  checkCertificate_sound c.erase j (checkSurface_implies_checkCertificate c j h)

theorem checkSurface_entails4
    (c : SurfaceCertificate) (j : VerifiedJudgment)
    (h : checkSurface c = some j) :
    Belnap.Entails4 c.erase.toContext j.formula :=
  Belnap.checkCertificate_entails4 c.erase j (checkSurface_implies_checkCertificate c j h)

theorem checkSurface_mathEstablished_false
    (c : SurfaceCertificate) (j : VerifiedJudgment)
    (h : checkSurface c = some j) :
    j.assurance.mathEstablished = false :=
  checkCertificate_mathEstablished_false c.erase j
    (checkSurface_implies_checkCertificate c j h)

theorem checkSurface_requires_unique_ids
    (c : SurfaceCertificate) (j : VerifiedJudgment)
    (h : checkSurface c = some j) :
    uniquePremiseIds c.premises = true :=
  checkCertificate_requires_unique_ids c.erase j
    (checkSurface_implies_checkCertificate c j h)

theorem checkSurface_rejects_bad_schema
    (c : SurfaceCertificate) (hne : c.schemaVersion ≠ 1) :
    checkSurface c = none := by
  have : surfaceWF c = false := by
    simp [surfaceWF, beq_eq_false_iff_ne.2 hne]
  simp [checkSurface, this]

theorem checkSurface_rejects_empty_steps
    (c : SurfaceCertificate) (he : c.steps = []) :
    checkSurface c = none := by
  have : surfaceWF c = false := by
    simp [surfaceWF, he, List.isEmpty]
  simp [checkSurface, this]

theorem claimsMatchStep_rejects_math_true
    (s : SurfaceStep) (j : VerifiedJudgment)
    (h : s.claimedMathEstablished = some true) :
    claimsMatchStep s j = false := by
  simp [claimsMatchStep, h]

theorem hyp_mathVerified_not_established
    (ps : List Premise) (prior : List VerifiedJudgment) (pid : PropId)
    (p : Premise) (j : VerifiedJudgment)
    (hf : findPremise ps pid = some p)
    (ha : p.authority = Authority.mathVerified)
    (h : checkStep ps prior (.hyp pid) = some j) :
    j.assurance.declared = Authority.mathVerified ∧
      j.assurance.mathEstablished = false := by
  simp [checkStep, hf] at h
  cases h
  simp [Assurance.hypDeclared, ha]

def encodeSteps (off : Nat) : List StepSpec → List SurfaceStep
  | [] => []
  | st :: rest => { id := off, spec := st } :: encodeSteps (off + 1) rest

theorem encodeSteps_map_spec (off : Nat) (steps : List StepSpec) :
    (encodeSteps off steps).map (·.spec) = steps := by
  induction steps generalizing off with
  | nil => rfl
  | cons st rest ih => simp [encodeSteps, ih]

theorem encodeSteps_length (off : Nat) (steps : List StepSpec) :
    (encodeSteps off steps).length = steps.length := by
  induction steps generalizing off with
  | nil => rfl
  | cons _ rest ih => simp [encodeSteps, ih]

theorem stepIdsOk_encode (off : Nat) (steps : List StepSpec) :
    stepIdsOk off (encodeSteps off steps) = true := by
  induction steps generalizing off with
  | nil => rfl
  | cons st rest ih => simp [encodeSteps, stepIdsOk, ih]

theorem claimsMatchSteps_encode
    (off : Nat) (steps : List StepSpec) (js : List VerifiedJudgment)
    (hlen : (encodeSteps off steps).length = js.length) :
    claimsMatchSteps (encodeSteps off steps) js = true := by
  induction steps generalizing off js with
  | nil =>
      cases js with
      | nil => rfl
      | cons _ _ => simp [encodeSteps] at hlen
  | cons st rest ih =>
      cases js with
      | nil => simp [encodeSteps] at hlen
      | cons j0 js =>
          simp [encodeSteps, claimsMatchSteps, claimsMatchStep, optionEq] at hlen ⊢
          exact ih (off + 1) js (by simpa [encodeSteps_length] using hlen)

def StructuredCertificate.toSurface (c : StructuredCertificate) : SurfaceCertificate :=
  { schemaVersion := 1
    premises := c.premises
    steps := encodeSteps 0 c.steps
    conclusionStep := c.conclusionStep }

theorem checkCertificate_implies_checkSurface
    (c : StructuredCertificate) (j : VerifiedJudgment)
    (hne : c.steps ≠ [])
    (hprem : c.premises.length ≤ maxPremises)
    (hsteps : c.steps.length ≤ maxSteps)
    (h : checkCertificate c = some j) :
    checkSurface c.toSurface = some j := by
  have hu := checkCertificate_requires_unique_ids c j h
  have hmath := checkCertificate_mathEstablished_false c j h
  unfold checkCertificate at h
  simp [decide_eq_true hu] at h
  cases hs : checkStepsLTR c.premises c.steps with
  | none => simp [hs] at h
  | some js =>
      simp [hs] at h
      cases hlt : Nat.decLt c.conclusionStep js.length with
      | isFalse => simp [hlt] at h
      | isTrue ht =>
          simp [hlt] at h
          cases h
          have hlen := checkStepsLTR_length _ _ _ hs
          have hne' : ¬(encodeSteps 0 c.steps).isEmpty := by
            cases hsteps' : c.steps with
            | nil => exact (hne hsteps').elim
            | cons _ _ => simp [encodeSteps, List.isEmpty]
          have hwf : surfaceWF c.toSurface = true := by
            simp [surfaceWF, StructuredCertificate.toSurface, stepIdsOk_encode, hu,
              encodeSteps_length, hprem, hsteps, hne', beq_self_eq_true]
          have hmap := encodeSteps_map_spec 0 c.steps
          have hs' :
              checkStepsLTR c.toSurface.premises (c.toSurface.steps.map (·.spec)) = some js := by
            simpa [StructuredCertificate.toSurface, hmap] using hs
          have hclaims : claimsMatchSteps c.toSurface.steps js = true := by
            simpa [StructuredCertificate.toSurface] using
              claimsMatchSteps_encode 0 c.steps js (by simpa [encodeSteps_length, hlen])
          have htop : claimsMatchTop c.toSurface (js[c.conclusionStep]'ht) = true := by
            simp [claimsMatchTop, StructuredCertificate.toSurface, optionEq, hmath]
          have ht' : c.toSurface.conclusionStep < js.length := by
            simpa [StructuredCertificate.toSurface] using ht
          have hlt' : Nat.decLt c.toSurface.conclusionStep js.length = isTrue ht' :=
            Subsingleton.elim _ _
          simp only [checkSurface, hwf, hs', hclaims, hlt']
          simpa [StructuredCertificate.toSurface] using htop

theorem checkSurface_iff_checkCertificate
    (c : StructuredCertificate) (j : VerifiedJudgment)
    (hne : c.steps ≠ [])
    (hprem : c.premises.length ≤ maxPremises)
    (hsteps : c.steps.length ≤ maxSteps) :
    checkSurface c.toSurface = some j ↔ checkCertificate c = some j := by
  constructor
  · intro h
    have := checkSurface_implies_checkCertificate c.toSurface j h
    simpa [StructuredCertificate.toSurface, SurfaceCertificate.erase,
      encodeSteps_map_spec] using this
  · exact checkCertificate_implies_checkSurface c j hne hprem hsteps

end ScientificReasoning

#print axioms ScientificReasoning.checkSurface_implies_checkCertificate
#print axioms ScientificReasoning.checkSurface_sound
#print axioms ScientificReasoning.checkSurface_iff_checkCertificate
#print axioms ScientificReasoning.hyp_mathVerified_not_established
#print axioms ScientificReasoning.checkSurface_rejects_bad_schema
