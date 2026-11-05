import PCSForgeRefinement.Rewrite

/-!
# CertIR: implementation counterexamples, proposed patch and repaired theorems

## Counterexample 1 (type checker vs interpreter)

`certir::type_of` accepts *every* comparison operator on two booleans
(`(Ty::Bool, Ty::Bool) => Ok(Ty::Bool)`), while `certir_interpreter::eval_expr` only
implements `eq`/`ne` on booleans and returns `Runtime("bad bool cmp")` otherwise.  Hence

    fn p(a: bool, b: bool) -> bool { ult(a, b) }

passes `Program::check` but fails on *every* input (`typecheck_admits_failing_program`).

## Counterexample 2 (a "sound" rewrite changes behaviour)

Because of (1), the `and_zero` schema of `forgeopt-search` (`x & 0 ⇒ 0`) is not
behaviour-preserving for programs accepted by the original checker:

    fn p(a: bool, b: bool, u: u8) -> u8 { and(select(ult(a, b), u, u), u8(0)) }   // always errors
    fn q(a: bool, b: bool, u: u8) -> u8 { u8(0) }                                // returns 0

(`and_zero_unsound_under_original_checker`).

## Proposed patch (`crates/certir/src/lib.rs`, `type_of`, `Expr::Cmp` arm)

```diff
-        Expr::Cmp { lhs, rhs, .. } => {
+        Expr::Cmp { op, lhs, rhs } => {
             let tl = type_of(env, lhs)?;
             let tr = type_of(env, rhs)?;
             match (tl, tr) {
                 (Ty::BitVec(w1), Ty::BitVec(w2)) if w1 == w2 => Ok(Ty::Bool),
-                (Ty::Bool, Ty::Bool) => Ok(Ty::Bool),
+                (Ty::Bool, Ty::Bool) if matches!(op, CmpOp::Eq | CmpOp::Ne) => Ok(Ty::Bool),
                 _ => Err(TypeError::BadOperands),
             }
         }
```

The repaired checker is `typeOfG true`; `type_safety` proves that well-typed programs never
fail at runtime, and all certificate theorems are stated for it.  Both counterexample programs
are rejected by the repaired checker.

## Counterexample 3 (non-canonical public `Value`s)

`Value::BitVec { width, bits }` has public fields; a non-canonical payload (`bits ≥ 2^w`) is
masked by arithmetic but returned unmasked by a variable, so `or(x, x) ⇒ x` changes the result
(`noncanonical_input_breaks_or_idempotent`).  The certificate theorems therefore quantify over
canonical inputs (`Value.WF`, exactly what `Value::bitvec` constructs).
-/

namespace PCSForgeRefinement.Counterexample

open PCSForgeRefinement

def boolParams : List Param := [⟨"a", .bool⟩, ⟨"b", .bool⟩]

/-- `fn p(a: bool, b: bool) -> bool { ult(a, b) }` -/
def cxP : Program := ⟨"p", boolParams, .cmp .ult (.var "a") (.var "b"), .bool⟩

theorem typecheck_admits_failing_program :
    cxP.checkG false = .ok () ∧
    (∀ a b : Bool, eval cxP [.bool a, .bool b] = .error (.runtime "bad bool cmp")) ∧
    cxP.checkG true = .error .badOperands := by
  refine ⟨by decide, fun a b => ?_, by decide⟩
  cases a <;> cases b <;> decide

def params3 : List Param := [⟨"a", .bool⟩, ⟨"b", .bool⟩, ⟨"u", .bv .u8⟩]

def andZeroP : Program :=
  ⟨"p", params3, .binop .and (.select (.cmp .ult (.var "a") (.var "b")) (.var "u") (.var "u"))
    (.constBv .u8 0), .bv .u8⟩

def andZeroQ : Program := ⟨"q", params3, .constBv .u8 0, .bv .u8⟩

theorem and_zero_unsound_under_original_checker :
    andZeroP.checkG false = .ok () ∧ andZeroQ.checkG false = .ok () ∧
    Rule.apply andZeroP.env .andZero andZeroP.body = some andZeroQ.body ∧
    (∀ a b : Bool, ∀ u < 256,
      eval andZeroP [.bool a, .bool b, .bitvec .u8 u] = .error (.runtime "bad bool cmp") ∧
      eval andZeroQ [.bool a, .bool b, .bitvec .u8 u] = .ok (.bitvec .u8 0)) ∧
    andZeroP.checkG true = .error .badOperands ∧
    checkCert ⟨andZeroP, andZeroQ, [⟨.andZero, []⟩], SEMANTICS, LIBRARY⟩ = false := by
  refine ⟨by decide, by decide, by decide, fun a b u _ => ?_, by decide, by decide⟩
  cases a <;> cases b <;> exact ⟨rfl, rfl⟩

/-- A non-canonical payload makes `or(x, x) ⇒ x` observable. -/
def orP : Program := ⟨"p", [⟨"x", .bv .u8⟩], .binop .or (.var "x") (.var "x"), .bv .u8⟩
def orQ : Program := ⟨"q", [⟨"x", .bv .u8⟩], .var "x", .bv .u8⟩

theorem noncanonical_input_breaks_or_idempotent :
    eval orP [.bitvec .u8 300] = .ok (.bitvec .u8 44) ∧
    eval orQ [.bitvec .u8 300] = .ok (.bitvec .u8 300) ∧
    ¬ (Value.bitvec .u8 300).WF := by
  refine ⟨by decide, by decide, by decide⟩

end PCSForgeRefinement.Counterexample
