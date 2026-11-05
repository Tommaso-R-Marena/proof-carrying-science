import PCSCompose.Levels

/-!
# Predictive obligations

A scientific theory may emit *predictive obligations*: claims that remain OPEN
until observational evidence is independently checked. Matching observations
yield Empirical support only — never Formal. Contradictory observations
falsify the obligation. This is the Popperian closure layer for HECK.
-/

namespace PCSCompose.Predictive

open PCSCompose.Levels

/-- Status of a predictive obligation. -/
inductive PredStatus where
  | open_
  | empiricallySupported
  | falsified
  deriving DecidableEq, Repr

/-- A bounded predictive obligation keyed by theory and prediction digest. -/
structure PredictiveObligation where
  id : Nat
  theoryId : Nat
  /-- Digested prediction key (exact SHA-256 digests live in the Python receiver). -/
  predictionKey : Nat
  status : PredStatus
  deriving DecidableEq, Repr

/-- Observation relative to a prediction key. -/
inductive Observation where
  | match_ (predictionKey : Nat)
  | contradict (predictionKey : Nat)
  | unrelated
  deriving DecidableEq, Repr

/-- Discharge rule: match → empirical support; contradict → falsified; else open. -/
def discharge (o : PredictiveObligation) (obs : Observation) : PredictiveObligation :=
  match obs with
  | .match_ k =>
      if k = o.predictionKey then { o with status := .empiricallySupported } else o
  | .contradict k =>
      if k = o.predictionKey then { o with status := .falsified } else o
  | .unrelated => o

/-- Matching observation never yields Formal; status is Empirical support. -/
theorem match_is_empirical (o : PredictiveObligation) :
    (discharge o (.match_ o.predictionKey)).status = .empiricallySupported := by
  simp [discharge]

/-- Contradiction falsifies. -/
theorem contradict_falsifies (o : PredictiveObligation) :
    (discharge o (.contradict o.predictionKey)).status = .falsified := by
  simp [discharge]

/-- Unrelated observation leaves status unchanged. -/
theorem unrelated_preserves (o : PredictiveObligation) :
    discharge o .unrelated = o := by
  simp [discharge]

/-- Wrong-key match does not discharge. -/
theorem wrong_key_match_preserves (o : PredictiveObligation) (k : Nat)
    (hne : k ≠ o.predictionKey) :
    discharge o (.match_ k) = o := by
  simp [discharge, hne]

/-- Wrong-key contradiction does not falsify. -/
theorem wrong_key_contradict_preserves (o : PredictiveObligation) (k : Nat)
    (hne : k ≠ o.predictionKey) :
    discharge o (.contradict k) = o := by
  simp [discharge, hne]

/-- Map predictive status to assurance level. -/
def PredStatus.toLevel : PredStatus → Level
  | .open_ => .open_
  | .empiricallySupported => .empirical
  | .falsified => .open_

/-- Falsified obligations never count as support. -/
def isSupport (o : PredictiveObligation) : Bool :=
  match o.status with
  | .empiricallySupported => true
  | .open_ | .falsified => false

theorem falsified_not_support (o : PredictiveObligation)
    (h : o.status = .falsified) : isSupport o = false := by
  simp [isSupport, h]

theorem open_not_support (o : PredictiveObligation)
    (h : o.status = .open_) : isSupport o = false := by
  simp [isSupport, h]

theorem empirical_is_support (o : PredictiveObligation)
    (h : o.status = .empiricallySupported) : isSupport o = true := by
  simp [isSupport, h]

/-- Falsification is sticky under subsequent matching. -/
def dischargeSticky (o : PredictiveObligation) (obs : Observation) : PredictiveObligation :=
  match o.status with
  | .falsified => o
  | _ => discharge o obs

theorem sticky_preserves_falsified (o : PredictiveObligation)
    (h : o.status = .falsified) (obs : Observation) :
    dischargeSticky o obs = o := by
  simp [dischargeSticky, h]

/-- Level of a discharged match is Empirical, never Formal. -/
theorem discharged_match_level_empirical (o : PredictiveObligation) :
    (discharge o (.match_ o.predictionKey)).status.toLevel = Level.empirical := by
  simp [discharge, PredStatus.toLevel]

theorem empirical_level_ne_formal :
    PredStatus.empiricallySupported.toLevel ≠ Level.formal := by
  decide

end PCSCompose.Predictive
