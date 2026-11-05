import PCSForgeRefinement.Syntax

/-! Test adapter only. Error categories match the existing reference abstractions:
formatted mismatch payloads and duplicate parameter names are deliberately not compared. -/
namespace PCSRuntimeDifferential
open PCSForgeRefinement

def normalizeValue : Value → String
  | .bool b => "ok:bool:" ++ toString b
  | .bitvec w b => "ok:bv:" ++ toString w.bits ++ ":" ++ toString b

def normalizeEval : Except EvalError Value → String
  | .ok v => normalizeValue v
  | .error (.undefinedVar n) => "error:undefined:" ++ n
  | .error (.runtime m) => "error:runtime:" ++ m
  | .error (.inputMismatch n) => "error:input:" ++ n
  | .error (.arity e g) => "error:arity:" ++ toString e ++ ":" ++ toString g

def normalizeCheck : Except TypeError Unit → String
  | .ok _ => "ok"
  | .error (.duplicateParam _) => "error:duplicate"
  | .error (.undefinedVar n) => "error:undefined:" ++ n
  | .error .mismatch => "error:mismatch"
  | .error .badOperands => "error:operands"

end PCSRuntimeDifferential
