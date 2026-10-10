/-! Abstract learning boundary. These types do not establish Python refinement.
No theorem about model intelligence or English intent is asserted. -/
namespace PCSProofBoundary

structure Certificate (goal : Prop) : Type where
  evidence : goal

inductive Outcome (goal : Prop) : Type where
  | verified : Certificate goal → Outcome goal
  | unknown : Outcome goal
  | exhausted : Outcome goal
  | invalid : Outcome goal

def reward {goal : Prop} : Outcome goal → Nat
  | .verified _ => 1
  | _ => 0

def accept {goal : Prop} (_proposal : Bool) (checked : Option (Certificate goal)) : Outcome goal :=
  match checked with
  | some certificate => .verified certificate
  | none => .unknown

theorem certified_has_original_evidence {goal : Prop} (c : Certificate goal) : goal :=
  c.evidence

theorem proposal_cannot_supply_reward {goal : Prop} (proposal : Bool) :
    reward (accept (goal := goal) proposal none) = 0 := rfl

theorem success_reward_requires_original_goal {goal : Prop} (outcome : Outcome goal)
    (h : reward outcome = 1) : goal := by
  cases outcome with
  | verified c => exact c.evidence
  | unknown => contradiction
  | exhausted => contradiction
  | invalid => contradiction

theorem changed_premise_requires_new_evidence {A B : Prop} (old : Certificate A)
    (transfer : A → B) : B := transfer old.evidence

#print axioms certified_has_original_evidence
#print axioms proposal_cannot_supply_reward
#print axioms success_reward_requires_original_goal
#print axioms changed_premise_requires_new_evidence
end PCSProofBoundary
