import PCSDecisionDiagram
/-!
NEGATIVE CONTROL (outside every library and the production import graph).
Weighted `A ∨ B`, baseline false/false, costs 3/1.  The true minimum is 1 (flip `B`).
Intended result: compilation FAILS.  The planner output is first computed by kernel-checked
`decide +kernel` (minimum 1, mandatory flip `B`); the claimed minimum 0 and the claimed mandatory
flip of `A` are then rejected by `decide` as false propositions.
-/
open PCSOmega PCSDD
def A : BForm 2 := .atom ⟨0, by decide⟩
def B : BForm 2 := .atom ⟨1, by decide⟩
def wAB : ITask 2 := ⟨⟨.or A B, .ff, []⟩, [false, false], [3, 1], []⟩
def minOf (t : ITask 2) : Option Nat :=
  match plan t DEFAULT_LIMITS with
  | .ok r => r.minimumCost
  | .error _ => none
def mandOf (t : ITask 2) : Option (List Nat) :=
  match plan t DEFAULT_LIMITS with
  | .ok r => r.mandatory
  | .error _ => none
/-- The computed values (true, kernel-checked). -/
theorem wAB_min : minOf wAB = some 1 := by decide +kernel
theorem wAB_mand : mandOf wAB = some [1] := by decide +kernel

/-- FALSE claim: minimum 0.  Rejected: `decide` proves `some 1 = some 0` false. -/
theorem false_weighted_minimum : minOf wAB = some 0 := by
  rw [wAB_min]; decide

/-- FALSE claim: flipping `A` is mandatory.  Rejected: `decide` proves `some [1] = some [0]` false. -/
theorem false_mandatory_flip : mandOf wAB = some [0] := by
  rw [wAB_mand]; decide
