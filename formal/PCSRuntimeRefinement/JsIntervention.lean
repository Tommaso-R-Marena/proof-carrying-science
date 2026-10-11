import PCSRuntimeRefinement.JsBellmanLoop
import PCSRuntimeRefinement.PyIntervention

/-!
# `javascript_intervention_refines_reference`

The commuting chain for the website planner's `bellman` (lines 14–27 of
`public/intervention-core.mjs`):

`source text →(javascript_bellman_source_bound, _wf, _scope, _lowers) extracted program
  →(JsBellman.bellman_exec) bellmanPass →(bellmanPass_spec) cellRec →(bellman_correct) meaning`.

JavaScript numbers: every intermediate value (costs `cell[0]+cost`, bits `2**v`, masks under
`|`/`&` after `ToInt32`, counts `cell[1]+=…`) is proved to stay exactly representable at the
validator's actual bounds (`n ≤ 24` variables, costs in `1..1000000`); the shared semantics
raises the explicit `inexact` outcome otherwise, so success certifies intermediate exactness.
-/

namespace PCSRuntimeRefinement.JsIntervention

open PCSRuntimeRefinement PCSRuntimeRefinement.JsBellman PCSDD PCSOmega
open PCSRuntimeRefinement.PyBellman (encRaw encCell encChoice encNode)
open PCSRuntimeRefinement.PyIntervention (lookupKey_zip getD_inj pyBaseline pyCosts pyLocked
  encPass pass_eq_rec)

/-- The task object `t` as the website receives it (the fields `bellman` reads). -/
def jsTask {n : Nat} (t : ITask n) (nms : List String) : Val :=
  .obj [("problem", .obj [("variables", .list (nms.map .str))]),
        ("baseline", pyBaseline t nms), ("costs", pyCosts t nms), ("locked", pyLocked t nms)]

/-- Encoding of a pass result as the returned object `{cells, choices}`. -/
def encPassJ (st : PassSt) : Val :=
  .obj [("cells", .list (st.cells.toList.map encCell)), ("choices", .list (st.choices.toList.map encChoice))]

theorem js_task_args {n : Nat} (t : ITask n) (nms : List String) (hnd : nms.Nodup) (hlen : nms.length = n)
    (hbl : t.baseline.length = n) (hcl : t.costs.length = n) (hlk : ∀ i ∈ t.locked, i < n) :
    ArgsJ t.prices n (jsTask t nms) (.list (nms.map .str)) := by
  refine ⟨nms, pyBaseline t nms, pyCosts t nms, pyLocked t nms, rfl, by omega, rfl, rfl, rfl,
    fun k hk => ⟨?_, ?_, ?_⟩⟩
  · show Res.ok ((lookupKey _ _).getD .undef) = _
    rw [lookupKey_zip nms _ hnd (by simp; omega) k (by omega)]
    simp [ITask.prices, List.getD_eq_getElem?_getD, hbl, hk]
  · show Res.ok ((lookupKey _ _).getD .undef) = _
    rw [lookupKey_zip nms _ hnd (by simp; omega) k (by omega)]
    simp [ITask.prices, List.getD_eq_getElem?_getD, show k < t.costs.length by omega]
  · show Res.ok _ = Res.ok _
    congr 1
    simp only [ITask.prices]
    apply Bool.eq_iff_iff.2
    rw [List.any_eq_true, List.contains_iff_mem]
    constructor
    · rintro ⟨x, hx, he⟩
      simp only [List.mem_map] at hx
      obtain ⟨j, hj, rfl⟩ := hx
      simp only [jsStrictEq, beq_iff_eq] at he
      have := getD_inj nms hnd k j (by omega) (by have := hlk j hj; omega) he
      exact this ▸ hj
    · intro hm
      exact ⟨_, List.mem_map.2 ⟨k, hm, rfl⟩, by simp [jsStrictEq]⟩

/-- **`javascript_intervention_refines_reference`.**  For every valid diagram and every task
within the validator's bounds (`n ≤ 24`, costs `1..1000000`, distinct names, in-range lists),
the source-extracted website `bellman` returns, for all sufficiently large fuel, exactly the
encoding of `bellmanPass` — whose cells/choices are `cellRec`/`choiceRec` for every node —
and every intermediate JavaScript number is exactly representable. -/
theorem javascript_intervention_refines_reference {n : Nat} (t : ITask n) (ns : Nodes) (nms : List String)
    (hv : Valid n ns) (hnd : nms.Nodup) (hlen : nms.length = n) (hbl : t.baseline.length = n)
    (hcl : t.costs.length = n) (hlk : ∀ i ∈ t.locked, i < n) (hn : n ≤ 24)
    (hpos : ∀ k < n, 0 < t.prices.cost k) (hle : ∀ k, t.prices.cost k ≤ 1000000) :
    ∃ N, ∀ fuel, N ≤ fuel →
      callFn .js fuel Js.bellmanCore [.list (ns.toList.map encNode), jsTask t nms] =
        .ok (encPassJ (bellmanPass ns t.prices)) ∧
      encPassJ (bellmanPass ns t.prices) =
        .obj [("cells", .list ((List.range (ns.size + 2)).map (fun u => encCell (cellRec ns t.prices u)))),
              ("choices", .list ((List.range (ns.size + 2)).map (fun u => encChoice (choiceRec ns t.prices u))))] := by
  have hNB : ((n * 1000000 + 1000000 : Nat) : Int) ≤ MAX_SAFE := by
    have : n * 1000000 ≤ 24 * 1000000 := Nat.mul_le_mul_right _ hn
    unfold MAX_SAFE; omega
  obtain ⟨N, hN⟩ := JsBellman.bellman_exec hv hpos hle (by omega) hNB (pr := .obj [("variables", .list (nms.map .str))])
    rfl rfl (js_task_args t nms hnd hlen hbl hcl hlk)
  refine ⟨N, fun fuel hf => ⟨hN fuel hf, ?_⟩⟩
  have h := pass_eq_rec (P := t.prices) hv
  unfold encPass at h
  simp only [Val.tuple.injEq, List.cons.injEq, and_true] at h
  unfold encPassJ
  rw [h.1, h.2]

/-- **Cross-language agreement.**  On the same task, the Python and the JavaScript planners
return the same cells and choices (as a tuple, respectively as `{cells, choices}`). -/
theorem python_javascript_bellman_agree {n : Nat} (t : ITask n) (ns : Nodes) (nms : List String)
    (hv : Valid n ns) (hnd : nms.Nodup) (hlen : nms.length = n) (hbl : t.baseline.length = n)
    (hcl : t.costs.length = n) (hlk : ∀ i ∈ t.locked, i < n) (hn : n ≤ 24)
    (hpos : ∀ k < n, 0 < t.prices.cost k) (hle : ∀ k, t.prices.cost k ≤ 1000000) :
    ∃ N, ∀ fuel, N ≤ fuel → ∃ cellsV choicesV : Val,
      callFn .py fuel Py.bellmanCore (PyIntervention.pyArgs t nms ns) = .ok (.tuple [cellsV, choicesV]) ∧
      callFn .js fuel Js.bellmanCore [.list (ns.toList.map encNode), jsTask t nms] =
        .ok (.obj [("cells", cellsV), ("choices", choicesV)]) := by
  obtain ⟨N1, h1⟩ := PyIntervention.python_intervention_refines_reference t ns nms hv hnd hlen hbl hcl hlk
  obtain ⟨N2, h2⟩ := javascript_intervention_refines_reference t ns nms hv hnd hlen hbl hcl hlk hn hpos hle
  exact ⟨max N1 N2, fun fuel hf => ⟨_, _, (h1 fuel (by omega)).1, (h2 fuel (by omega)).1⟩⟩

end PCSRuntimeRefinement.JsIntervention
