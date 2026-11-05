import PCSCompose.Compose
import PCSCompose.Predictive

/-!
# Executable kernel controls for HECK

Finite deciding examples that must pass under `decide` / `decide`.
-/

namespace PCSCompose.Controls

open PCSCompose.Levels PCSCompose.Compose PCSCompose.Predictive

def formalAtom : EvidenceAtom :=
  { id := 1, level := .formal, supported := true, claimId := 10 }

def empiricalAtom : EvidenceAtom :=
  { id := 2, level := .empirical, supported := true, claimId := 20 }

def badAtom : EvidenceAtom :=
  { id := 3, level := .formal, supported := false, claimId := 30 }

def atoms : List EvidenceAtom := [formalAtom, empiricalAtom, badAtom]

/-- Positive: formal leaf meets formal requirement. -/
theorem good_formal_singleton :
    accept atoms { id := 100, requiredLevel := .formal, leafIds := [1] } = true := by
  decide

/-- Positive: empirical requirement met by empirical leaf. -/
theorem good_empirical_singleton :
    accept atoms { id := 101, requiredLevel := .empirical, leafIds := [2] } = true := by
  decide

/-- Heterogeneous compose: formal+empirical achieves empirical, accepts empirical req. -/
theorem good_heterogeneous_empirical_req :
    accept atoms { id := 102, requiredLevel := .empirical, leafIds := [1, 2] } = true := by
  decide

/-- Heterogeneous compose cannot satisfy Formal requirement. -/
theorem reject_heterogeneous_formal_req :
    accept atoms { id := 103, requiredLevel := .formal, leafIds := [1, 2] } = false := by
  decide

/-- Unsupported leaf rejects. -/
theorem reject_unsupported :
    accept atoms { id := 104, requiredLevel := .formal, leafIds := [3] } = false := by
  decide

/-- Missing leaf rejects. -/
theorem reject_missing :
    accept atoms { id := 105, requiredLevel := .formal, leafIds := [99] } = false := by
  decide

/-- Empty rejects. -/
theorem reject_empty :
    accept atoms { id := 106, requiredLevel := .formal, leafIds := [] } = false := by
  decide

/-- Empirical leaf cannot satisfy Formal requirement. -/
theorem reject_empirical_as_formal :
    accept atoms { id := 107, requiredLevel := .formal, leafIds := [2] } = false := by
  decide

/-- Achieved level of heterogeneous pair is empirical. -/
theorem achieved_heterogeneous_is_empirical :
    achievedLevel atoms { id := 108, requiredLevel := .empirical, leafIds := [1, 2] }
      = Level.empirical := by
  decide

def obl : PredictiveObligation :=
  { id := 1, theoryId := 7, predictionKey := 42, status := .open_ }

theorem predictive_match_supports :
    isSupport (discharge obl (.match_ 42)) = true := by
  decide

theorem predictive_contradict_falsifies :
    (discharge obl (.contradict 42)).status = .falsified := by
  decide

theorem predictive_match_not_formal :
    (discharge obl (.match_ 42)).status.toLevel ≠ Level.formal := by
  decide

theorem predictive_sticky_falsified :
    let f := discharge obl (.contradict 42)
    dischargeSticky f (.match_ 42) = f := by
  decide

theorem level_meet_laws :
    Level.empirical.meet Level.formal = Level.empirical ∧
    Level.computational.meet Level.empirical = Level.empirical ∧
    Level.provenance.meet Level.formal = Level.provenance := by
  decide

end PCSCompose.Controls
