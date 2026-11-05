import Lean.Data.Json
import PCSConditionalRuntime.JsRun
/-! Independent runtime comparison (a test, not a proof): runs the *extracted*
`checkConditional` of the current `conditional-core.mjs` on the tasks/limits in a JSON file produced
by the real Node implementation and prints the read-back receipts as JSON lines.  `digest` is
replaced by the constant `"DIGEST"` on both sides; `validateConditional`, `exact` and `integer` are
the identity (the tasks were produced by the real `conditionalFromText`, which calls the real
`validateConditional`, and the limits are valid).
Usage: `runtime_tests/conditional_js/run.sh SEED COUNT` -/
open PCSCR PCSCR.Js PCSCR.Py Lean

partial def ofJson : Json → T
  | .null => .null
  | .bool b => .bool b
  | .num n => .int n.mantissa
  | .str s => .str s
  | .arr xs => .arr (xs.toList.map ofJson)
  | j@(.obj _) => match j.getObjVal? "__obj__" with
    | .ok (.arr kvs) => .obj (kvs.toList.filterMap fun
        | .arr #[.str k, v] => some (k, ofJson v)
        | _ => none)
    | _ => .null

def ext : Ext := fun f args h => match f, args with
  | "digest", [_] => .ok (.str "DIGEST") h
  | "validateConditional", [v] => .ok v h
  | "exact", [v, _] => .ok v h
  | "integer", [v, _, _] => .ok v h
  | _, _ => .exc (.builtin "NameError") h

def main (args : List String) : IO Unit := do
  let raw ← IO.FS.readFile args.head!
  let j ← IO.ofExcept (Json.parse raw)
  let cases ← IO.ofExcept (j.getObjValAs? (Array Json) "cases")
  for c in cases do
    let t ← IO.ofExcept (c.getObjVal? "task")
    let lim ← IO.ofExcept (c.getObjVal? "limits")
    match jsRunCheck ext 5000 (ofJson t) (ofJson lim) with
    | .ok v h => match rb h v with
      | some r => IO.println (tToJson r)
      | none => IO.println "\"READBACK-FAIL\""
    | .exc e _ => IO.println s!"\"EXC {repr e}\""
    | .fuel => IO.println "\"FUEL\""
