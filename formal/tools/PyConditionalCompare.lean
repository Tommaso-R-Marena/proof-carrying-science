import Lean.Data.Json
import PCSConditionalRuntime.PyRun
/-! Independent runtime comparison (a test, not a proof): runs the *extracted* `check` of the
current `conditional.py` on the tasks/limits in a JSON file produced by the real CPython
implementation and prints the read-back receipts as JSON lines.  `digest` is replaced by the
constant `"DIGEST"` on both sides; `validate` is the identity (the tasks were produced by the
real `from_text`, which calls the real `validate`).
Usage: `runtime_tests/conditional_py/run.sh SEED COUNT` -/
open PCSCR PCSCR.Py Lean

partial def ofJson : Json → T
  | .null => .null
  | .bool b => .bool b
  | .num n => .int n.mantissa
  | .str s => .str s
  | .arr xs => .arr (xs.toList.map ofJson)
  | j@(.obj _) => match j.getObjVal? "__obj__" with
    -- `Lean.Json` objects are sorted maps; the CPython driver therefore encodes each dict as
    -- `{"__obj__": [[key, value], ...]}` to transmit its exact insertion order.
    | .ok (.arr kvs) => .obj (kvs.toList.filterMap fun
        | .arr #[.str k, v] => some (k, ofJson v)
        | _ => none)
    | _ => .null

def ext : Ext := fun f args h => match f, args with
  | "digest", [_] => .ok (.str "DIGEST") h
  | "validate", [v] => .ok v h
  | _, _ => .exc (.builtin "NameError") h

def main (args : List String) : IO Unit := do
  let raw ← IO.FS.readFile args.head!
  let j ← IO.ofExcept (Json.parse raw)
  let cases ← IO.ofExcept (j.getObjValAs? (Array Json) "cases")
  for c in cases do
    let t ← IO.ofExcept (c.getObjVal? "task")
    let lim ← IO.ofExcept (c.getObjVal? "limits")
    match pyRunCheck ext 5000 (ofJson t) (ofJson lim) with
    | .ok v h => match rb h v with
      | some r => IO.println (tToJson r)
      | none => IO.println "\"READBACK-FAIL\""
    | .exc e _ => IO.println s!"\"EXC {repr e}\""
    | .fuel => IO.println "\"FUEL\""
