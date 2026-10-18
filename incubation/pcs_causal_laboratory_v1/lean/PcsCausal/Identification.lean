/-
Identification criterion scaffolding.

Full backdoor soundness for structural causal models relative to Mathlib
probability is a staged obligation. This file records the adjustment formula
as a definitional target and proves only graph-side lemmas imported elsewhere.
-/
import PcsCausal.Graph

namespace PcsCausal

/-- Adjustment formula claim payload (semantic hook for future soundness proof). -/
structure BackdoorClaim where
  treatment : Vertex
  outcome : Vertex
  adjustment : Finset Vertex
  /-- Graphical side condition obligation (checked in Python; formalized incrementally). -/
  graphical_ok : Prop

/-- Positivity obligation: the observational conditional must be defined. -/
structure PositivityObligation (Z : Type*) where
  support : Z → Prop
  positive : ∀ z, support z → True

/-- Documentation: the classical backdoor display formula (not a theorem yet). -/
def backdoorFormulaString (X Y : String) (Z : List String) : String :=
  if Z.isEmpty then
    s!"P({Y}|do({X}=x)) = P({Y}|{X}=x)"
  else
    s!"P({Y}|do({X}=x)) = Σ_z P({Y}|{X}=x,Z=z) P(Z=z)"

/-!
BLOCKER (recorded): theorem `backdoor_soundness` connecting
`BackdoorClaim.graphical_ok` + SCM semantics + positivity to equality of
interventional and adjustment functionals remains open in Lean.

Python exact finite checks in `tests/test_scm_intervention.py` provide
independent computational evidence for supported binary models.
-/

end PcsCausal
