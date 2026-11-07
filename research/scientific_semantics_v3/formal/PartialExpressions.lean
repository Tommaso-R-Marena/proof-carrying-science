import Std

/-!
Partial rational expression semantics. Unlike Lean's total division operation,
division by zero is undefined. This file proves a structural division-to-inverse
rewrite preserves the whole partial evaluation, including undefined cases.
It proves no source-language interpretation, Python refinement or biology.
-/
namespace ScientificPartialExpressions

inductive Expr where
  | literal : Rat → Expr
  | symbol : String → Expr
  | add : Expr → Expr → Expr
  | mul : Expr → Expr → Expr
  | inv : Expr → Expr
  | div : Expr → Expr → Expr

def safeInv (x : Rat) : Option Rat := if x = 0 then none else some x⁻¹

def eval (env : String → Rat) : Expr → Option Rat
  | .literal x => some x
  | .symbol s => some (env s)
  | .add a b => match eval env a, eval env b with
    | some x, some y => some (x + y)
    | _, _ => none
  | .mul a b => match eval env a, eval env b with
    | some x, some y => some (x * y)
    | _, _ => none
  | .inv a => match eval env a with
    | some x => safeInv x
    | none => none
  | .div a b => match eval env a, eval env b with
    | some x, some y => match safeInv y with
      | some z => some (x * z)
      | none => none
    | _, _ => none

def rewrite : Expr → Expr
  | .literal x => .literal x
  | .symbol s => .symbol s
  | .add a b => .add (rewrite a) (rewrite b)
  | .mul a b => .mul (rewrite a) (rewrite b)
  | .inv a => .inv (rewrite a)
  | .div a b => .mul (rewrite a) (.inv (rewrite b))

theorem division_to_inverse (env : String → Rat) (a b : Expr) :
    eval env (.div a b) = eval env (.mul a (.inv b)) := by
  cases ha : eval env a <;> cases hb : eval env b <;> simp [eval, ha, hb]
  case some.some x y => cases safeInv y <;> rfl

/-- This equality includes the exact undefined domain, not just common points. -/
theorem rewrite_preserves_partial_evaluation (env : String → Rat) (e : Expr) :
    eval env (rewrite e) = eval env e := by
  induction e with
  | literal x => rfl
  | symbol s => rfl
  | add a b ha hb => simp only [rewrite, eval, ha, hb]
  | mul a b ha hb => simp only [rewrite, eval, ha, hb]
  | inv a ha => simp only [rewrite, eval, ha]
  | div a b ha hb =>
      rw [rewrite, ← division_to_inverse]
      simp only [eval, ha, hb]

theorem rewrite_preserves_definedness (env : String → Rat) (e : Expr) :
    (eval env (rewrite e)).isSome = (eval env e).isSome := by
  rw [rewrite_preserves_partial_evaluation]

theorem self_division_under_nonzero (env : String → Rat) (s : String)
    (nonzero : env s ≠ 0) : eval env (.div (.symbol s) (.symbol s)) = some 1 := by
  simp [eval, safeInv, nonzero, Rat.mul_inv_cancel (env s) nonzero]

theorem self_division_undefined_at_zero (env : String → Rat) (s : String)
    (zero : env s = 0) : eval env (.div (.symbol s) (.symbol s)) = none := by
  simp [eval, safeInv, zero]

/-- Algebraic cancellation x/x→1 is not an unconditional partial rewrite. -/
theorem cancellation_changes_domain :
    eval (fun _ => 0) (.div (.symbol "x") (.symbol "x")) ≠
      eval (fun _ => 0) (.literal 1) := by
  simp [eval, safeInv]

#print axioms division_to_inverse
#print axioms rewrite_preserves_partial_evaluation
#print axioms rewrite_preserves_definedness
#print axioms self_division_under_nonzero
#print axioms self_division_undefined_at_zero
#print axioms cancellation_changes_domain

end ScientificPartialExpressions
