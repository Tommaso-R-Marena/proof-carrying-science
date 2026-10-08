import Lean

/-!
# `kernel_rfl`: definitional equality checked by the trusted kernel only

`kernel_rfl` closes a goal `lhs = rhs` with `Eq.refl lhs`, but instead of asking the
elaborator's (`Meta`-level) unifier to check `lhs â‰¡ rhs` it adds the auxiliary lemma
`lhs = rhs := Eq.refl lhs` directly to the environment, so the check `lhs â‰¡ rhs` is
performed **by Lean's trusted kernel** (exactly as `decide +kernel` checks
`Decidable.decide p â‰¡ true`).  No axiom, `native_decide`, `ofReduceBool` or compiled code is
involved: if the kernel cannot establish the definitional equality, the tactic fails.

This is used for the compositional kernel evaluation of the golden fixture, where
the elaborator's unifier is far slower than the kernel and refuses to unfold
well-founded definitions, while `decide +kernel` would require a `DecidableEq`
instance for every intermediate structure.
-/

namespace PCS.V2.KernelRfl

open Lean Meta Elab Tactic

/-- Close `lhs = rhs` (or a closed `âˆ€ xs, lhs = rhs`) by kernel-checked `Eq.refl`. -/
elab "kernel_rfl" : tactic =>
  closeMainGoalUsing `kernel_rfl fun expectedType _ => do
    let expectedType := (â† instantiateMVars expectedType).cleanupAnnotations
    if expectedType.hasFVar || expectedType.hasMVar then
      throwError "kernel_rfl: goal must be closed (no local hypotheses or metavariables)"
    let pf â† forallTelescope expectedType fun xs body => do
      let some (_, lhtÑPÐ€L@öç¯…ªì