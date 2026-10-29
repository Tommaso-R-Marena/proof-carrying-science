import PairGate
set_option autoImplicit false
namespace PCSPolicyVersioning
open PCSProgress PCSActionShield PCSTokenPolicyGate

/-- The modeled outcomes, safety labels, forbidden effects and goal meaning stay fixed. -/
abbrev Compatible (task candidate : Spec) : Prop :=
  candidate.base.safe = task.base.safe ∧ candidate.base.edges = task.base.edges ∧
  candidate.base.forbidden = task.base.forbidden ∧ candidate.goals = task.goals

/-- A policy update cannot replenish the protected remaining progress budget. -/
def updateOK (task candidate : Spec) (state budget : Nat) : Bool :=
  check candidate && decide (Compatible task candidate ∧ state ∈ region candidate ∧ rank candidate state ≤ budget)

theorem updateOK_sound {task candidate : Spec} {state budget : Nat}
    (h : updateOK task candidate state budget = true) :
    check candidate = true ∧ Compatible task candidate ∧
      state ∈ region candidate ∧ rank candidate state ≤ budget := by
  simpa [updateOK, and_assoc] using h

theorem update_available {task candidate : Spec} {state budget : Nat}
    (h : updateOK task candidate state budget = true) (hg : state ∉ task.goals)
    (a : PCSActionFormat.Action) :
    ∃ action, gate candidate state (PCSActionFormat.encodeTokens a) (PCSActionFormat.encode a) = .selected action := by
  obtain ⟨hc,compatible,hw,_⟩ := updateOK_sound h
  exact canonical_available hc hw (by simpa [compatible.2.2.2] using hg) a

theorem selected_checkpoint_decreases {task candidate : Spec} {state budget : Nat}
    (h : updateOK task candidate state budget = true) {tokens raw : List Nat} {e : Edge}
    (selected : gate candidate state tokens raw = .selected e.action)
    (edge : e ∈ task.base.edges) (source : e.source = state) :
    e.target ∈ task.base.safe ∧ rank candidate e.target + 1 ≤ budget := by
  obtain ⟨_,compatible,_,hb⟩ := updateOK_sound h
  have member : e ∈ candidate.base.edges := by simpa [compatible.2.1] using edge
  have progress := selected_all_outcomes selected member source rfl
  refine ⟨by simpa [compatible.1] using progress.2.1, ?_⟩
  have drop := progress.2.2.1
  omega

theorem successor_updateOK {task candidate : Spec} {state budget : Nat}
    (h : updateOK task candidate state budget = true) {tokens raw : List Nat} {e : Edge}
    (selected : gate candidate state tokens raw = .selected e.action)
    (edge : e ∈ task.base.edges) (source : e.source = state) :
    updateOK task candidate e.target (rank candidate e.target) = true := by
  obtain ⟨hc,compatible,_,_⟩ := updateOK_sound h
  have member : e ∈ candidate.base.edges := by simpa [compatible.2.1] using edge
  have progress := selected_all_outcomes selected member source rfl
  have facts : check candidate = true ∧ Compatible task candidate ∧
      e.target ∈ region candidate ∧ rank candidate e.target ≤ rank candidate e.target :=
    ⟨hc,compatible,progress.1,Nat.le_refl _⟩
  simpa [updateOK,and_assoc] using facts

/-- Every step may use a different checked policy, with one carried budget. -/
inductive VersionedRun (task : Spec) : Nat → Nat → Nat → Nat → Nat → Prop where
  | nil (state budget : Nat) (terminal : Spec)
      (valid : updateOK task terminal state budget = true) :
      VersionedRun task 0 state budget state budget
  | step {n state budget final remaining : Nat} (candidate : Spec)
      (tokens raw : List Nat) (e : Edge)
      (valid : updateOK task candidate state budget = true)
      (selected : gate candidate state tokens raw = .selected e.action)
      (source : e.source = state) (edge : e ∈ task.base.edges)
      (tail : VersionedRun task n e.target (rank candidate e.target) final remaining) :
      VersionedRun task (n+1) state budget final remaining

theorem versioned_safe_and_budget {task : Spec} {n state budget final remaining : Nat}
    (run : VersionedRun task n state budget final remaining)
    (hs : state ∈ task.base.safe) : final ∈ task.base.safe ∧ remaining + n ≤ budget := by
  induction run with
  | nil state budget terminal valid => exact ⟨hs,by omega⟩
  | @step n state budget final remaining candidate tokens raw e valid selected source edge tail ih =>
    obtain ⟨safe,drop⟩ := selected_checkpoint_decreases valid selected edge source
    obtain ⟨done,bound⟩ := ih safe
    exact ⟨done,by omega⟩

theorem versioned_length_bound {task : Spec} {n state budget final remaining : Nat}
    (run : VersionedRun task n state budget final remaining)
    (hs : state ∈ task.base.safe) : n ≤ budget := by
  have bound := (versioned_safe_and_budget run hs).2
  omega

theorem versioned_terminal_certificate {task : Spec} {n state budget final remaining : Nat}
    (run : VersionedRun task n state budget final remaining) :
    ∃ terminal, updateOK task terminal final remaining = true := by
  induction run with
  | nil state budget terminal valid => exact ⟨terminal,valid⟩
  | step candidate tokens raw e valid selected source edge tail ih => exact ih

theorem versioned_completion_at_budget {task : Spec} {n state budget final remaining : Nat}
    (run : VersionedRun task n state budget final remaining)
    (hs : state ∈ task.base.safe) (used : n = budget) : final ∈ task.goals := by
  have bound := (versioned_safe_and_budget run hs).2
  have zero : remaining = 0 := by omega
  obtain ⟨terminal,valid⟩ := versioned_terminal_certificate run
  obtain ⟨hc,compatible,hw,hr⟩ := updateOK_sound valid
  have terminal_zero : rank terminal final = 0 := by omega
  have reached : final ∈ terminal.goals :=
    (((check_iff terminal).mp hc).1 final hw).2.1.mp terminal_zero
  simpa [compatible.2.2.2] using reached

namespace RankReset
/-- Action zero toggles safe non-goal states; action one reaches the goal. -/
def edges : List Edge := [⟨0,0,1⟩,⟨1,0,0⟩,⟨0,1,2⟩,⟨1,1,2⟩]
def policyA : Spec := ⟨⟨[0],[0,1,2],edges,[(0,0),(0,1),(1,1)],[]⟩,[2],[(0,2),(1,1),(2,0)]⟩
def policyB : Spec := ⟨⟨[0],[0,1,2],edges,[(0,1),(1,0),(1,1)],[]⟩,[2],[(0,1),(1,2),(2,0)]⟩
def task : Spec := policyA
def zeroAction : PCSActionFormat.Action := ⟨0,by decide⟩
def tokens : List Nat := PCSActionFormat.encodeTokens zeroAction
def raw : List Nat := PCSActionFormat.encode zeroAction

theorem policyA_checked : check policyA = true := by decide
theorem policyB_checked : check policyB = true := by decide

theorem stepA : check policyA = true ∧ Compatible task policyA ∧
    gate policyA 0 tokens raw = .selected 0 ∧ (⟨0,0,1⟩ : Edge) ∈ task.base.edges := by decide

theorem stepB : check policyB = true ∧ Compatible task policyB ∧
    gate policyB 1 tokens raw = .selected 0 ∧ (⟨1,0,0⟩ : Edge) ∈ task.base.edges := by decide

def rotatingState (n : Nat) : Nat := if n % 2 = 0 then 0 else 1
def rotatingPolicy (n : Nat) : Spec := if n % 2 = 0 then policyA else policyB

theorem every_rotating_step_locally_checked (n : Nat) :
    check (rotatingPolicy n) = true ∧ Compatible task (rotatingPolicy n) ∧
    gate (rotatingPolicy n) (rotatingState n) tokens raw = .selected 0 ∧
    (⟨rotatingState n,0,rotatingState (n+1)⟩ : Edge) ∈ task.base.edges := by
  rcases Nat.mod_two_eq_zero_or_one n with h | h
  · have next : (n+1)%2=1 := by omega
    simpa [rotatingState,rotatingPolicy,h,next] using stepA
  · have next : (n+1)%2=0 := by omega
    simpa [rotatingState,rotatingPolicy,h,next] using stepB

theorem rotating_never_goal (n : Nat) : rotatingState n ∉ task.goals := by
  unfold rotatingState
  split <;> decide

theorem rank_reset_refused : updateOK task policyB 1 (rank policyA 1) = false := by decide

theorem productive_update_allowed :
    updateOK task policyB 0 (rank policyA 0) = true ∧ rank policyB 0 < rank policyA 0 ∧
    gate policyB 0 tokens raw = .selected 1 := by decide

/-- A locally valid controller can move the goalpost; fixed task identity forbids it. -/
def shiftedGoal : Spec := ⟨⟨[0],[0,1,2],edges,[(0,0)],[]⟩,[1],[(0,1),(1,0)]⟩

theorem shifted_goal_locally_checked : check shiftedGoal = true := by decide

theorem shifted_goal_refused : updateOK task shiftedGoal 0 2 = false := by decide
end RankReset
end PCSPolicyVersioning

#print axioms PCSPolicyVersioning.updateOK_sound
#print axioms PCSPolicyVersioning.update_available
#print axioms PCSPolicyVersioning.selected_checkpoint_decreases
#print axioms PCSPolicyVersioning.successor_updateOK
#print axioms PCSPolicyVersioning.versioned_safe_and_budget
#print axioms PCSPolicyVersioning.versioned_length_bound
#print axioms PCSPolicyVersioning.versioned_terminal_certificate
#print axioms PCSPolicyVersioning.versioned_completion_at_budget
#print axioms PCSPolicyVersioning.RankReset.policyA_checked
#print axioms PCSPolicyVersioning.RankReset.policyB_checked
#print axioms PCSPolicyVersioning.RankReset.stepA
#print axioms PCSPolicyVersioning.RankReset.stepB
#print axioms PCSPolicyVersioning.RankReset.every_rotating_step_locally_checked
#print axioms PCSPolicyVersioning.RankReset.rotating_never_goal
#print axioms PCSPolicyVersioning.RankReset.rank_reset_refused
#print axioms PCSPolicyVersioning.RankReset.productive_update_allowed
#print axioms PCSPolicyVersioning.RankReset.shifted_goal_locally_checked
#print axioms PCSPolicyVersioning.RankReset.shifted_goal_refused
