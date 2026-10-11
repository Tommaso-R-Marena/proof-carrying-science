import PCSRuntimeRefinement.Summary

/-!
# Runtime controls (kernel-checked executions of the extracted programs)

* a full run of both extracted planners on a two-variable task with a cost tie: identical
  cells, the tie is counted (`count = 2`), `False` wins the recorded choice;
* **Bool versus integer confusion**: a baseline written as the integer `0` instead of `False`
  is *silently accepted* by the Python semantics (`False == 0`) but changes the JavaScript
  result (`false !== 0`) — both validators therefore reject non-Boolean baselines;
* **resource exhaustion** is the explicit unresolved outcome `fuel`, never a value;
* a dangling child identifier raises `IndexError` in Python, while JavaScript reads
  `undefined` and fails later with a type error — an error path, not a result.
-/

namespace PCSRuntimeRefinement.RuntimeControls

open PCSRuntimeRefinement

/-- Nodes: `2 = (var 1, low 0, high 1)`, `3 = (var 0, low 2, high 1)`. -/
def nodesV : Val := .list [.list [.int 1, .int 0, .int 1], .list [.int 0, .int 2, .int 1]]
def namesV : Val := .list [.str "a", .str "b"]
def baselineV : Val := .obj [("a", .bool false), ("b", .bool false)]
def costsV : Val := .obj [("a", .int 3), ("b", .int 3)]
def tV (bl : Val) : Val := .obj [("problem", .obj [("variables", namesV)]), ("baseline", bl),
  ("costs", costsV), ("locked", .list [])]

def expectedCells : Val := .list [.none, .list [.int 0, .int 1, .int 0, .int 0],
  .list [.int 3, .int 1, .int 2, .int 2], .list [.int 3, .int 2, .int 0, .int 3]]
def expectedChoices : Val := .list [.none, .none, .bool true, .bool false]

theorem python_run : callFn .py 200 Py.bellmanCore [nodesV, namesV, baselineV, costsV, .list []] =
    .ok (.tuple [expectedCells, expectedChoices]) := by rfl

theorem javascript_run : callFn .js 200 Js.bellmanCore [nodesV, tV baselineV] =
    .ok (.obj [("cells", expectedCells), ("choices", expectedChoices)]) := by rfl

/-- Integer baseline `0`: Python computes the same answer as for `False` … -/
theorem python_int_baseline_same :
    callFn .py 200 Py.bellmanCore [nodesV, namesV, .obj [("a", .int 0), ("b", .bool false)], costsV, .list []] =
      .ok (.tuple [expectedCells, expectedChoices]) := by rfl

/-- … while JavaScript's strict comparison treats every value of `a` as a flip. -/
theorem javascript_int_baseline_differs :
    callFn .js 200 Js.bellmanCore [nodesV, tV (.obj [("a", .int 0), ("b", .bool false)])] =
      .ok (.obj [("cells", .list [.none, .list [.int 0, .int 1, .int 0, .int 0],
          .list [.int 3, .int 1, .int 2, .int 2], .list [.int 3, .int 1, .int 1, .int 1]]),
        ("choices", .list [.none, .none, .bool true, .bool true])]) := by rfl

/-- Too small a budget is the explicit unresolved outcome. -/
theorem python_exhaustion : callFn .py 6 Py.bellmanCore [nodesV, namesV, baselineV, costsV, .list []] = .fuel := by
  rfl

theorem javascript_exhaustion : callFn .js 6 Js.bellmanCore [nodesV, tV baselineV] = .fuel := by rfl

/-- A dangling child (`5`) is an error path in both languages. -/
def badNodes : Val := .list [.list [.int 0, .int 0, .int 5]]

theorem python_dangling_child :
    callFn .py 200 Py.bellmanCore [badNodes, namesV, baselineV, costsV, .list []] = .exc .indexError := by rfl

theorem javascript_dangling_child :
    callFn .js 200 Js.bellmanCore [badNodes, tV baselineV] = .exc .typeError := by rfl

end PCSRuntimeRefinement.RuntimeControls
