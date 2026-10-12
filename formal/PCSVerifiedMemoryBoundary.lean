import Std

/-! A typed reference contract for verified rule reuse and cost-based ranking.
This does not assert that the Python implementation refines these definitions.
-/

namespace PCSVerifiedMemoryBoundary

structure CheckedRule where
  statement : Prop
  evidence : statement

def Holds (rules : List CheckedRule) : Prop :=
  ∀ rule, rule ∈ rules → rule.statement

theorem checked_memory_holds (rules : List CheckedRule) : Holds rules := by
  intro rule _
  exact rule.evidence

-- A planner may depend on any previously checked library. Its result must
-- still prove the same immutable goal, with no additional assumptions.
def CheckedSearch (rules : List CheckedRule) (goal : Prop) : Prop :=
  Holds rules → goal

theorem reuse_preserves_original_goal (rules : List CheckedRule) (goal : Prop)
    (proof : CheckedSearch rules goal) : goal :=
  proof (checked_memory_holds rules)

structure Receipt (goal : Prop) where
  evidence : goal
  executionAttempts : Nat

def accept (goal : Prop) (_ranking : List Int)
    (checked : Option (Receipt goal)) : Option (Receipt goal) := checked

theorem ranking_cannot_authorize (goal : Prop) (ranking : List Int) :
    accept goal ranking none = none := rfl

theorem changed_ranking_preserves_checked_goal (goal : Prop)
    (a b : List Int) (checked : Option (Receipt goal)) :
    accept goal a checked = accept goal b checked := rfl

theorem accepted_goal_is_true (goal : Prop) (ranking : List Int)
    (checked : Option (Receipt goal)) (receipt : Receipt goal)
    (_accepted : accept goal ranking checked = some receipt) : goal := receipt.evidence

-- Count attempts before considering success/failure; rejected checker calls
-- cannot disappear from the measured cost used by a learning policy.
def attemptCost (outcomes : List Bool) : Nat := outcomes.length

theorem failed_attempt_increases_cost (outcomes : List Bool) :
    attemptCost (false :: outcomes) = attemptCost outcomes + 1 := by
  simp [attemptCost]

#print axioms checked_memory_holds
#print axioms reuse_preserves_original_goal
#print axioms ranking_cannot_authorize
#print axioms changed_ranking_preserves_checked_goal
#print axioms accepted_goal_is_true
#print axioms failed_attempt_increases_cost
end PCSVerifiedMemoryBoundary
