import PCSConditionalRuntime.PyConditionalLowered
import PCSConditionalRuntime.Mono

/-!
# Running the extracted `conditional.py`

* `pyProg` — the extracted program table (names are resolved through it at run time);
* module initialisation runs the extracted module-level statements (`TASK`, `RECEIPT`, `OPS`,
  `RESERVED`, the `MAX_*` constants and the `DEFAULT_LIMITS` dictionary) once:
  `py_init_result` computes the resulting globals `pyGlobals` and heap `pyHeap0` by kernel
  evaluation;
* `pyRunCheck ext k task limits` allocates the two JSON inputs on that heap and runs the
  extracted `check(task, limits)` with fuel `k`; `ext` gives the behaviour of the unextracted
  functions `digest` and `validate`.
-/

namespace PCSCR.Py

open PCSCR

def pyProg : Prog := conditionalPyModule.prog

def pyCtx0 (ext : Ext) : Ctx := ⟨.py, pyProg, [], ext⟩

/-- Globals after running the module-level statements. -/
def pyGlobals : Env :=
  [("DEFAULT_LIMITS", .ref 0), ("MAX_DEPTH", .int 12), ("MAX_FORMULA_NODES", .int 128),
   ("MAX_VARIABLES", .int 24),
   ("RESERVED", .fset [.str "AND", .str "OR", .str "NOT", .str "IMPLIES", .str "TRUE", .str "FALSE"]),
   ("OPS", .fset [.str "atom", .str "true", .str "false", .str "not", .str "and", .str "or", .str "implies"]),
   ("RECEIPT", .str "pcs-conditional-boolean-receipt-v1"), ("TASK", .str "pcs-conditional-boolean-task-v1")]

def pyHeap0 : Heap := [.dict [(.str "nodes", .int 4096), (.str "operations", .int 100000)]]

/-- Module initialisation (no calls: one level suffices, for every behaviour of the externs). -/
theorem py_init_result (ext : Ext) :
    execB (pyCtx0 ext) (interp (pyCtx0 ext) 1) [] [] py_init = .ok (.normal pyGlobals) pyHeap0 := by
  rfl

def pyCtx (ext : Ext) : Ctx := ⟨.py, pyProg, pyGlobals, ext⟩

/-- Run `check(task, limits)` on freshly allocated JSON inputs. -/
def pyRunCheck (ext : Ext) (k : Nat) (task lim : T) : Out V :=
  let p := allocT pyHeap0 task
  let q := allocT p.2 lim
  run (pyCtx ext) k "check" [p.1, q.1] q.2

/-- Read back a returned value as a JSON tree. -/
def rb (h : Heap) (v : V) : Option T := readback (h.length + 1) h v

/-! ## JSON printing (for runtime comparisons only) -/

def jsonStr (s : String) : String := "\"" ++ s ++ "\""

partial def tToJson : T → String
  | .null => "null"
  | .bool b => if b then "true" else "false"
  | .int i => toString i
  | .str s => jsonStr s
  | .arr xs => "[" ++ ", ".intercalate (xs.map tToJson) ++ "]"
  | .obj kvs => "{" ++ ", ".intercalate (kvs.map fun (k, v) => jsonStr k ++ ": " ++ tToJson v) ++ "}"

end PCSCR.Py
