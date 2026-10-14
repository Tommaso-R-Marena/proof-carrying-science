import PCSConditionalRuntime.JsConditionalLowered
import PCSConditionalRuntime.PyRun

/-!
# Running the extracted `conditional-core.mjs`

* `jsProg` — the extracted program table (dialect `js`);
* module initialisation runs the extracted module-level statements (`TASK`, `RECEIPT`, `OPS`,
  `RESERVED`, the frozen `DEFAULT_LIMITS` object): `js_init_result` computes the globals
  `jsGlobals` and the heap `jsHeap0` by kernel evaluation;
* `jsRunCheck ext k task limits` allocates the task and the options object `{limits}` on that
  heap and runs the extracted `checkConditional(task, {limits})` with fuel `k`; `ext` gives the
  behaviour of the unextracted functions (`validateConditional`, and the imports `digest`,
  `exact`, `integer`).  `checkConditional` is `async`; its only `await`ed callee is `digest`,
  so the run returns the value the promise resolves to.
-/

namespace PCSCR.Js

open PCSCR PCSCR.Py

def jsProg : Prog := conditionalJsModule.prog

def jsCtx0 (ext : Ext) : Ctx := ⟨.js, jsProg, [], ext⟩

/-- Globals after running the module-level statements. -/
def jsGlobals : Env :=
  [("DEFAULT_LIMITS", .ref 2), ("RESERVED", .ref 1), ("OPS", .ref 0),
   ("RECEIPT", .str "pcs-conditional-boolean-receipt-v1"), ("TASK", .str "pcs-conditional-boolean-task-v1")]

def jsHeap0 : Heap :=
  [.list [.str "atom", .str "true", .str "false", .str "not", .str "and", .str "or", .str "implies"],
   .list [.str "AND", .str "OR", .str "NOT", .str "IMPLIES", .str "TRUE", .str "FALSE"],
   .dict [(.str "nodes", .int 4096), (.str "operations", .int 100000)]]

/-- Module initialisation (no calls: one level suffices, for every behaviour of the externs). -/
theorem js_init_result (ext : Ext) :
    execB (jsCtx0 ext) (interp (jsCtx0 ext) 1) [] [] js_init = .ok (.normal jsGlobals) jsHeap0 := by
  rfl

def jsCtx (ext : Ext) : Ctx := ⟨.js, jsProg, jsGlobals, ext⟩

/-- Run `checkConditional(task, {limits})` on freshly allocated JSON inputs. -/
def jsRunCheck (ext : Ext) (k : Nat) (task lim : T) : Out V :=
  let p := allocT jsHeap0 task
  let q := allocT p.2 (.obj [("limits", lim)])
  run (jsCtx ext) k "checkConditional" [p.1, q.1] q.2

end PCSCR.Js
