import PCSScientificReceiver.Types

/-!
Receiver-derived semantics for the restricted exact-rational A → B protocol.
The numerical expression is fixed by the receiver. No submitted equality, proof
flag, or executable expression participates in establishing its state meaning.
Physical scope means nonnegative finite states/firings only; no kinetic or
empirical interpretation follows.
-/
namespace PCSScientificReceiver

open CertNum CertNum.Expr CertNum.Certificate

/-- The only supported expression denotes the final A coordinate. -/
def coordinateName : String := "A_final"

def environment (c : Contract) : Env :=
  fun name => if name = coordinateName then some c.envValue else none

/-- Construct the variable certificate from received rational bounds. Reversed
bounds are separately rejected, including the empty-domain checker case. -/
def certificate (c : Contract) : IntervalEnclosureCert where
  expr := .var coordinateName
  arith := .var coordinateName
  box := [(coordinateName, Interval.mk' c.boxLo c.boxHi)]
  claimed := Interval.mk' c.lower c.upper

/-- Every actual state, including initial/final states, and every actual firing
is nonnegative. The finite index types enforce exact checking scope. -/
def PhysicalAdmissible (c : Contract) : Prop :=
  (∀ k : Fin (c.firings.length + 1),
    0 ≤ state c k.val 0 ∧ 0 ≤ state c k.val 1) ∧
  (∀ k : Fin c.firings.length, 0 ≤ c.firings[k.val])

instance (c : Contract) : Decidable (PhysicalAdmissible c) :=
  by unfold PhysicalAdmissible; infer_instance

/-- These are independent checks of bindings and input-domain conditions,
not a decision procedure for the final conservation/enclosure theorem. -/
def bindingChecks (c : Contract) : Bool :=
  decide (c.referenceStep = c.firings.length ∧
    c.declaredTotal = c.initialA + c.initialB ∧
    c.envValue = finalState c 0 ∧
    c.boxLo ≤ c.boxHi ∧ c.lower ≤ c.upper ∧
    c.boxLo ≤ c.envValue ∧ c.envValue ≤ c.boxHi)

def physicalChecks (c : Contract) : Bool :=
  if c.physical then decide (PhysicalAdmissible c) else true

/-- Receiving authority for typed contracts. Byte decoding adds canonicality;
all mathematical bindings are independently checked here. -/
def checkContract (c : Contract) : Bool :=
  bounded c && bindingChecks c &&
    checkIntervalEnclosure (certificate c) && physicalChecks c

structure Result where
  stepCount : Nat
  unitCode : Bool
  physical : Bool
  finalA : ℚ
  finalB : ℚ
  total : ℚ
  lowerA : ℚ
  upperA : ℚ
  lowerB : ℚ
  upperB : ℚ
  deriving DecidableEq, Repr

def resultOfContract (c : Contract) : Result where
  stepCount := c.firings.length
  unitCode := c.unitCode
  physical := c.physical
  finalA := finalState c 0
  finalB := finalState c 1
  total := c.declaredTotal
  lowerA := c.lower
  upperA := c.upper
  lowerB := c.declaredTotal - c.upper
  upperB := c.declaredTotal - c.lower

/-- Exact mathematical interpretation of the accepted typed data. The semantic
link is a conclusion, never a producer-supplied hypothesis. -/
structure ContractSound (c : Contract) : Prop where
  bounded : bounded c = true
  reference : c.referenceStep = c.firings.length
  totalBinding : c.declaredTotal = c.initialA + c.initialB
  environmentBinding : c.envValue = finalState c 0
  boxValid : c.boxLo ≤ c.boxHi
  claimValid : c.lower ≤ c.upper
  actualInBox : c.boxLo ≤ c.envValue ∧ c.envValue ≤ c.boxHi
  certificateAccepted : checkIntervalEnclosure (certificate c) = true
  expressionState : (certificate c).expr.eval (environment c) = some (finalState c 0)
  conservation : finalState c 0 + finalState c 1 = c.declaredTotal
  aEnclosed : c.lower ≤ finalState c 0 ∧ finalState c 0 ≤ c.upper
  bEnclosed : c.declaredTotal - c.upper ≤ finalState c 1 ∧
    finalState c 1 ≤ c.declaredTotal - c.lower
  physical : c.physical = true → PhysicalAdmissible c

/-- The receiver's fixed expression/environment is tied to the computed state
by the independently checked environment binding. -/
theorem expression_state_of_binding (c : Contract)
    (binding : c.envValue = finalState c 0) :
    (certificate c).expr.eval (environment c) = some (finalState c 0) := by
  simp [certificate, Expr.eval, environment, binding]

theorem environment_in_box (c : Contract)
    (lower : c.boxLo ≤ c.envValue) (upper : c.envValue ≤ c.boxHi) :
    EnvInBox (environment c) (toBox (certificate c).box) := by
  intro name x hx
  by_cases hname : name = coordinateName
  · subst name
    have hx' : c.envValue = x := by simpa [environment] using hx
    subst x
    simpa [certificate, toBox, lookupBox] using Interval.mem_mk'_of_le lower upper
  · simp [environment, hname] at hx

/-- Main typed receiving theorem. Conservation and complementary enclosure are
obtained from the existing CertNum/PCCA integration theorem, with its semantic
link discharged from receiving checks. -/
theorem checkContract_sound (c : Contract) (accepted : checkContract c = true) :
    ContractSound c := by
  simp only [checkContract, Bool.and_eq_true] at accepted
  obtain ⟨⟨⟨hb, hbindings⟩, hcert⟩, hphysical⟩ := accepted
  have bindings := of_decide_eq_true hbindings
  rcases bindings with ⟨href, htotal, henv, hbox, hclaim, hlo, hhi⟩
  have hlink := expression_state_of_binding c henv
  have hboxEnv := environment_in_box c hlo hhi
  have science := PCSIntegration.conserved_complement_enclosure
    (initial c) (schedule c) c.firings.length (certificate c) hcert
    (environment c) hboxEnv hlink
  have hconserve : finalState c 0 + finalState c 1 = c.declaredTotal := by
    simpa [finalState, state, initial, ← htotal] using science.1
  have ha : c.lower ≤ finalState c 0 ∧ finalState c 0 ≤ c.upper := by
    simpa [finalState, state, certificate, Interval.mk', hclaim, Interval.Mem]
      using science.2.1
  have hbnd : c.declaredTotal - c.upper ≤ finalState c 1 ∧
      finalState c 1 ≤ c.declaredTotal - c.lower := by
    constructor <;> linarith [ha.1, ha.2, hconserve]
  refine ⟨hb, href, htotal, henv, hbox, hclaim, ⟨hlo, hhi⟩,
    hcert, hlink, hconserve, ha, hbnd, ?_⟩
  intro hp
  simpa [physicalChecks, hp] using hphysical

/-- A physical-mode acceptance guarantees nonnegative species at every received
step, rather than merely at the final coordinate. -/
theorem physical_state_nonnegative (c : Contract)
    (accepted : checkContract c = true) (physical : c.physical = true)
    (k : Nat) (within : k ≤ c.firings.length) :
    0 ≤ state c k 0 ∧ 0 ≤ state c k 1 := by
  exact ((checkContract_sound c accepted).physical physical).1 ⟨k, by omega⟩

theorem physical_firing_nonnegative (c : Contract)
    (accepted : checkContract c = true) (physical : c.physical = true)
    (k : Fin c.firings.length) : 0 ≤ c.firings[k.val] :=
  ((checkContract_sound c accepted).physical physical).2 k

/-- Returned fields have the model interpretation and advertised bounds. -/
structure ResultSound (c : Contract) (r : Result) : Prop where
  source : r = resultOfContract c
  contract : ContractSound c
  stepBinding : r.stepCount = c.referenceStep
  stateA : r.finalA = finalState c 0
  stateB : r.finalB = finalState c 1
  conserved : r.finalA + r.finalB = r.total
  enclosedA : r.lowerA ≤ r.finalA ∧ r.finalA ≤ r.upperA
  enclosedB : r.lowerB ≤ r.finalB ∧ r.finalB ≤ r.upperB
  physical : r.physical = true → PhysicalAdmissible c

theorem resultOfContract_sound (c : Contract) (accepted : checkContract c = true) :
    ResultSound c (resultOfContract c) := by
  have h := checkContract_sound c accepted
  exact ⟨rfl, h, h.reference.symm, rfl, rfl, h.conservation,
    h.aEnclosed, h.bEnclosed, h.physical⟩

/-- Nontrivial accepted transition with a nonsingleton box and claimed interval.
The physical request is independently checked for both states and the firing. -/
def sampleContract : Contract where
  referenceStep := 1
  unitCode := true
  physical := true
  initialA := 1
  initialB := 0
  envValue := 2 / 3
  boxLo := 3 / 5
  boxHi := 7 / 10
  lower := 1 / 2
  upper := 3 / 4
  declaredTotal := 1
  firings := [1 / 3]

theorem sample_accepts : checkContract sampleContract = true  := by
  norm_num [checkContract, sampleContract, bounded, rationals, rationalBounded,
    maxOperand, maxSteps, bindingChecks, physicalChecks, PhysicalAdmissible,
    finalState, state, initial, schedule, PCCA.Stoich.evolve, PCCA.Stoich.fire,
    PCSIntegration.transfer, Fin.sum_univ_one, certificate, checkIntervalEnclosure,
    Expr.evalInterval, toBox, lookupBox, Enclosure.ok, Interval.mk',
    Fin.forall_fin_succ, coordinateName]

theorem sample_scientific_claim :
    ResultSound sampleContract (resultOfContract sampleContract) :=
  resultOfContract_sound sampleContract sample_accepts

/-- Altering the producer's final-value binding cannot preserve acceptance. -/
theorem sample_wrong_environment_rejects :
    checkContract { sampleContract with envValue := 0 } = false  := by
  norm_num [checkContract, sampleContract, bounded, rationals, rationalBounded,
    maxOperand, maxSteps, bindingChecks, physicalChecks, PhysicalAdmissible,
    finalState, state, initial, schedule, PCCA.Stoich.evolve, PCCA.Stoich.fire,
    PCSIntegration.transfer, Fin.sum_univ_one, certificate, checkIntervalEnclosure,
    Expr.evalInterval, toBox, lookupBox, Enclosure.ok, Interval.mk',
    Fin.forall_fin_succ, coordinateName]

/-- Conservation declarations are checked against the received initial data. -/
theorem sample_false_total_rejects :
    checkContract { sampleContract with declaredTotal := 2 } = false  := by
  norm_num [checkContract, sampleContract, bounded, rationals, rationalBounded,
    maxOperand, maxSteps, bindingChecks, physicalChecks, PhysicalAdmissible,
    finalState, state, initial, schedule, PCCA.Stoich.evolve, PCCA.Stoich.fire,
    PCSIntegration.transfer, Fin.sum_univ_one, certificate, checkIntervalEnclosure,
    Expr.evalInterval, toBox, lookupBox, Enclosure.ok, Interval.mk',
    Fin.forall_fin_succ, coordinateName]

/-- Empty-domain interval acceptance cannot bypass explicit endpoint checks. -/
theorem sample_reversed_box_rejects :
    checkContract { sampleContract with boxLo := 1, boxHi := 0 } = false  := by
  norm_num [checkContract, sampleContract, bounded, rationals, rationalBounded,
    maxOperand, maxSteps, bindingChecks, physicalChecks, PhysicalAdmissible,
    finalState, state, initial, schedule, PCCA.Stoich.evolve, PCCA.Stoich.fire,
    PCSIntegration.transfer, Fin.sum_univ_one, certificate, checkIntervalEnclosure,
    Expr.evalInterval, toBox, lookupBox, Enclosure.ok, Interval.mk',
    Fin.forall_fin_succ, coordinateName]

#print axioms sample_accepts
#print axioms sample_scientific_claim
#print axioms sample_wrong_environment_rejects
#print axioms sample_false_total_rejects
#print axioms sample_reversed_box_rejects
#print axioms checkContract_sound
#print axioms resultOfContract_sound
#print axioms physical_state_nonnegative
#print axioms physical_firing_nonnegative

end PCSScientificReceiver
