import tools.RuntimeCheckedBoundary
import tools.RuntimeValueType

/-! Exact source-bound continuation of `eval`, after input binding. This adds the
missing output-type check and `?` propagation. Input binding and compiler correctness
remain outside this extraction. Derived enum equality follows its standard structural
semantics; the actual derive annotations and variant declarations are bound below. -/
namespace PCSRuntimeOutputBoundaryV3
open PCSForgeRefinement PCSForgeRefinement.Rust PCSRuntimeCheckedBoundary
set_option maxRecDepth 4096

inductive Place where
  | variable (name : String)
  | field (receiver : Place) (name : String)
  | borrow (receiver : Place)

def Place.toks : Place → List String
  | .variable name => [name]
  | .field receiver name => receiver.toks ++ [".", name]
  | .borrow receiver => "&" :: receiver.toks

structure OutputContinuation where
  binding : String
  callee : String
  store : Place
  body : Place
  actualType : RExpr
  expectedType : Place
  rejection : RExpr
  result : RExpr

def OutputContinuation.toks (fn : OutputContinuation) : List String :=
  ["let", fn.binding, "=", fn.callee, "("] ++ fn.store.toks ++ [","] ++ fn.body.toks ++
  [")", "?", ";", "if"] ++ fn.actualType.toks ++ ["!="] ++ fn.expectedType.toks ++
  ["{", "return"] ++ fn.rejection.toks ++ [";", "}"] ++ fn.result.toks

def outputFn : OutputContinuation := {
  binding := "out", callee := "eval_expr_checked"
  store := .borrow (.variable "store")
  body := .borrow (.field (.variable "program") "body")
  actualType := .mcall (v "out") "ty" .nil
  expectedType := .field (.variable "program") "ret_ty"
  rejection := cl ["Err"] [cl ["EvalError", "Runtime"]
    [.mcall (.str "return type mismatch") "into" .nil]]
  result := cl ["Ok"] [v "out"] }

def derivePrefix : List String :=
  ["#", "[", "derive", "(", "Clone", ",", "Copy", ",", "Debug", ",", "PartialEq", ",",
   "Eq", ",", "Hash", ",", "Serialize", ",", "Deserialize", ")", "]",
   "#", "[", "serde", "(", "rename_all", "=", "\"lowercase\"", ")", "]"]

def widthDeclaration : List String := derivePrefix ++
  ["pub", "enum", "Width", "{", "U8", ",", "U16", ",", "U32", ",", "U64", ",", "}"]

def typeDeclaration : List String := derivePrefix ++
  ["pub", "enum", "Ty", "{", "Bool", ",", "BitVec", "(", "Width", ")", ",", "}"]

def outputSource : List String := source_lines% "../source_reference/certiforge/runtime-v3/eval-output.rs.txt"
def widthSource : List String := source_lines% "../source_reference/certiforge/runtime-v3/width-equality.rs.txt"
def typeSource : List String := source_lines% "../source_reference/certiforge/runtime-v3/type-equality.rs.txt"

theorem output_boundary_source_bound :
    lexLines outputSource = outputFn.toks ∧ lexLines widthSource = widthDeclaration ∧
      lexLines typeSource = typeDeclaration := by decide +kernel

def supportedWidth : RV → Bool
  | .ctor "Width" "U8" [] | .ctor "Width" "U16" [] | .ctor "Width" "U32" [] |
    .ctor "Width" "U64" [] => true
  | _ => false

/-- Structural equality of the actual derived `Ty` enum. Unsupported representations
are not converted into a Boolean answer. Width fields use the existing unit-enum
equality semantics. -/
def derivedTypeEq : RV → RV → Option Bool
  | .ctor "Ty" "Bool" [], .ctor "Ty" "Bool" [] => some true
  | .ctor "Ty" "Bool" [], .ctor "Ty" "BitVec" [w] => if supportedWidth w then some false else none
  | .ctor "Ty" "BitVec" [w], .ctor "Ty" "Bool" [] => if supportedWidth w then some false else none
  | .ctor "Ty" "BitVec" [a], .ctor "Ty" "BitVec" [b] =>
    if supportedWidth a && supportedWidth b then a.eqv b else none
  | _, _ => none

theorem derived_type_eq_exact (a b : Ty) :
    derivedTypeEq (encTy a) (encTy b) = some (decide (a = b)) := by
  cases a <;> cases b <;> try rfl
  case bool.bv w => cases w <;> rfl
  case bv.bool w => cases w <;> rfl
  case bv.bv w1 w2 => cases w1 <;> cases w2 <;> rfl

/-- The direct method dispatch uses the source-extracted Value::ty helper. Early
`return` is represented by `ret`; it is normalized only at the function boundary. -/
def finishValue (fn : OutputContinuation) (typeFuel : Nat) (expected : Ty) (value : RV) : Out :=
  match runFn [valueTyFn] typeFuel ["Value", "ty"] [value] with
  | some (.val actual) =>
    match derivedTypeEq actual (encTy expected) with
    | some true => evalE (runFn [] 1) [("out", value)] fn.result .val
    | some false => evalE (runFn [] 1) [("out", value)] fn.rejection .ret
    | none => .stuck "unsupported type equality"
  | some out => out
  | none => .stuck "missing Value::ty"

def finishReference (expected : Ty) : Except EvalError Value → Except EvalError Value
  | .error err => .error err
  | .ok value => if value.ty = expected then .ok value else .error (.runtime "return type mismatch")

def runContinuation (checked : Out) (expected : Ty) (typeFuel : Nat) : Out :=
  match checked with
  | .val result => fixRet (qK result (finishValue outputFn typeFuel expected))
  | other => other

theorem continuation_exact (checked : Except EvalError Value) (expected : Ty) (extra : Nat) :
    runContinuation (.val (encRes checked)) expected (extra + 1) =
      .val (encRes (finishReference expected checked)) := by
  cases checked with
  | error err => rfl
  | ok value =>
    change fixRet (finishValue outputFn (extra + 1) expected (encVal value)) = _
    unfold finishValue
    rw [rust_value_ty]
    simp only [derived_type_eq_exact]
    by_cases h : value.ty = expected <;> simp [h, finishReference]
    all_goals rfl

/-- Composed coverage: the actual checked expression call, error propagation and
return-type guard. The supplied store is the result of the unextracted input phase. -/
theorem checked_output_continuation_refines (σ : Store) (e : Expr) (expected : Ty)
    (expressionExtra iteratorFuel typeExtra : Nat)
    (expressionBudget : depth e + 4 ≤ expressionExtra + 2)
    (iteratorBudget : σ.length ≤ iteratorFuel) :
    runContinuation (runChecked σ e (expressionExtra + 2) iteratorFuel) expected (typeExtra + 1) =
      .val (encRes (finishReference expected (checkedReference σ e))) := by
  rw [checked_wrapper_refines _ _ _ _ expressionBudget iteratorBudget, continuation_exact]

theorem output_acceptance_requires_declared_type (expected : Ty) (checked : Except EvalError Value)
    (value : Value) (accepted : finishReference expected checked = .ok value) :
    value.ty = expected := by
  cases checked with
  | error err => cases accepted
  | ok result =>
    by_cases h : result.ty = expected
    · simp only [finishReference, h, ↓reduceIte] at accepted
      cases accepted
      exact h
    · simp [finishReference, h] at accepted

theorem output_preserves_all_checked_errors (err : EvalError) (expected : Ty) (fuel : Nat) :
    runContinuation (.val (encRes (.error err))) expected fuel = .val (encRes (.error err)) := rfl

theorem output_preserves_resource_failure (why : String) (expected : Ty) (fuel : Nat) :
    runContinuation (.stuck why) expected fuel = .stuck why := rfl

theorem output_type_resource_failure (value : Value) (expected : Ty) :
    runContinuation (.val (encRes (.ok value))) expected 0 = .stuck "fuel" := by
  cases value <;> rfl

theorem output_certificate_preserves {c : Cert} (accepted : checkCert c = true)
    (δ : DStore) (typed : WTStore c.original.env δ) (f1 f2 iteratorFuel typeFuel : Nat)
    (candidateBudget : depth c.candidate.body + 4 ≤ f1 + 2)
    (originalBudget : depth c.original.body + 4 ≤ f2 + 2)
    (iteratorBudget : (PCSForgeRefinement.encStore δ).length ≤ iteratorFuel) :
    runContinuation (runChecked (PCSForgeRefinement.encStore δ) c.candidate.body (f1 + 2) iteratorFuel)
      c.candidate.retTy typeFuel =
    runContinuation (runChecked (PCSForgeRefinement.encStore δ) c.original.body (f2 + 2) iteratorFuel)
      c.original.retTy typeFuel := by
  obtain ⟨_, _, _, _, sameType, _⟩ := checkCert_spec accepted
  rw [sameType, checked_certificate_preserves accepted δ typed f1 f2 iteratorFuel
    candidateBudget originalBudget iteratorBudget]

end PCSRuntimeOutputBoundaryV3

#print axioms PCSRuntimeOutputBoundaryV3.output_boundary_source_bound
#print axioms PCSRuntimeOutputBoundaryV3.derived_type_eq_exact
#print axioms PCSRuntimeOutputBoundaryV3.continuation_exact
#print axioms PCSRuntimeOutputBoundaryV3.checked_output_continuation_refines
#print axioms PCSRuntimeOutputBoundaryV3.output_acceptance_requires_declared_type
#print axioms PCSRuntimeOutputBoundaryV3.output_preserves_all_checked_errors
#print axioms PCSRuntimeOutputBoundaryV3.output_preserves_resource_failure
#print axioms PCSRuntimeOutputBoundaryV3.output_type_resource_failure
#print axioms PCSRuntimeOutputBoundaryV3.output_certificate_preserves
