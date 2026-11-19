/-!
# Evolving Safety Gate (research only)

A fail-closed admission lattice over safety *mechanisms*. Mechanisms that factor
through the guarded tool channel alone are never admitted. Joint-channel
detectors, joint-detecting correcting guards, and ensemble probes (joint +
stealth note probes) are admissible. Evolution may only retain a successor that
dominates its parent on the formal detectability order — never by silently
falling back to channel-1-only scoring.

This file does not import production PCS authority and does not claim general
alignment, recursive self-improvement, or frontier-model guarantees.
-/
set_option autoImplicit false

namespace EvolvingSafetyGate

/-- Finite catalog of mechanism classes under study. -/
inductive Mechanism where
  | channel1Only
  | jointChannel
  | correctingGuard
  | jointDetectingGuard
  | ensembleProbe
  deriving DecidableEq, Repr, Inhabited

/-- Whether the mechanism can separate the constructive Assurance-Mirage pair. -/
def detectsConstructiveMirage : Mechanism → Bool
  | .channel1Only => false
  | .jointChannel => true
  | .correctingGuard => false
  | .jointDetectingGuard => true
  | .ensembleProbe => true

/-- Formal admission bit: must detect the constructive mirage. -/
def admissible (m : Mechanism) : Bool :=
  detectsConstructiveMirage m

theorem channel1_never_admissible : admissible .channel1Only = false := by
  decide

theorem correcting_alone_never_admissible : admissible .correctingGuard = false := by
  decide

theorem joint_channel_admissible : admissible .jointChannel = true := by
  decide

theorem joint_detecting_guard_admissible : admissible .jointDetectingGuard = true := by
  decide

theorem ensemble_probe_admissible : admissible .ensembleProbe = true := by
  decide

/-- Detectability order used as the formal fitness coordinate. -/
def detectRank : Mechanism → Nat
  | .channel1Only => 0
  | .correctingGuard => 0
  | .jointChannel => 1
  | .jointDetectingGuard => 2
  | .ensembleProbe => 3

/-- Strict formal domination bit. -/
def dominates (a b : Mechanism) : Bool :=
  decide (detectRank a > detectRank b)

theorem joint_detecting_dominates_channel1 :
    dominates .jointDetectingGuard .channel1Only = true := by
  decide

theorem joint_detecting_dominates_correcting :
    dominates .jointDetectingGuard .correctingGuard = true := by
  decide

theorem joint_channel_dominates_channel1 :
    dominates .jointChannel .channel1Only = true := by
  decide

theorem ensemble_dominates_joint_detecting :
    dominates .ensembleProbe .jointDetectingGuard = true := by
  decide

theorem ensemble_dominates_channel1 :
    dominates .ensembleProbe .channel1Only = true := by
  decide

/-- Evolution may retain `succ` over `parent` only if it dominates. -/
def retainable (parent succ : Mechanism) : Bool :=
  dominates succ parent

theorem retain_joint_over_channel1 :
    retainable .channel1Only .jointDetectingGuard = true := by
  decide

theorem retain_ensemble_over_joint :
    retainable .jointDetectingGuard .ensembleProbe = true := by
  decide

/-- Channel-1 successors of an admissible parent are never retainable. -/
theorem never_retain_channel1_over_joint (parent : Mechanism)
    (h : admissible parent = true) :
    retainable parent .channel1Only = false := by
  cases parent <;> simp [retainable, dominates, detectRank, admissible,
    detectsConstructiveMirage] at h ⊢

/-- Admissible mechanisms are exactly those with positive detect rank. -/
theorem admissible_iff_pos_rank (m : Mechanism) :
    admissible m = decide (detectRank m > 0) := by
  cases m <;> decide

/-- Evolution invariant: retained champion stays admissible. -/
theorem retained_stays_admissible (parent succ : Mechanism)
    (hP : admissible parent = true) (hR : retainable parent succ = true) :
    admissible succ = true := by
  cases parent <;> cases succ <;>
    simp [retainable, dominates, detectRank, admissible, detectsConstructiveMirage] at hP hR ⊢

/-- Fail-closed envelope: non-admissible mechanisms never dominate admissible ones. -/
theorem nonadmissible_never_dominates_admissible (a b : Mechanism)
    (hA : admissible a = false) (hB : admissible b = true) :
    dominates a b = false := by
  cases a <;> cases b <;>
    simp [dominates, detectRank, admissible, detectsConstructiveMirage] at hA hB ⊢

/-- Finite catalog completeness for the five reviewed classes. -/
theorem catalog_exhaustive (m : Mechanism) :
    m = .channel1Only ∨ m = .jointChannel ∨
    m = .correctingGuard ∨ m = .jointDetectingGuard ∨
    m = .ensembleProbe := by
  cases m <;> simp

end EvolvingSafetyGate
