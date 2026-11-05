import PCSRuntimeRefinement.JsIntervention
import PCSRuntimeRefinement.Mono

/-!
# Runtime correspondence: certificates, every-budget correspondence and result semantics

* `PyCert` / `JsCert` — a source-extraction certificate: the exact source file lines, a line
  window, and a concrete syntax tree.  The checker accepts iff the tree renders to exactly
  that window, passes the precedence (and, for JS, scope) discipline, and extraction succeeds.
  `source_extraction_certificate_sound` states what acceptance guarantees;
  `interventionPyCert` / `interventionJsCert` are accepted (checked by the kernel), and their
  extracted programs are `Py.bellmanCore` / `Js.bellmanCore`.
* Unsupported constructs are rejected by extraction (`py_unsupported_call_rejected`,
  `js_unsupported_call_rejected`, …).
* `runtime_result_semantics` — for **every** fuel budget, the Python and the JavaScript runs
  on a valid task either both report the explicit unresolved outcome or return the same
  cells/choices lists, and every returned cell means: global minimum objective, exact number
  of optimal assignments, mandatory/possible flip masks; `None`/`null` means infeasible.
-/

namespace PCSRuntimeRefinement

open PCSDD PCSOmega
open PCSRuntimeRefinement.PyBellman (encRaw encCell encChoice encNode)

/-! ## Source-extraction certificates -/

structure PyCert where
  file : List String
  start : Nat
  len : Nat
  tree : Py.PFun

def PyCert.check (c : PyCert) : Bool :=
  (c.file.drop c.start).take c.len == c.tree.render && c.tree.wf && c.tree.lower.isSome

structure JsCert where
  file : List String
  start : Nat
  len : Nat
  tree : Js.JFun

def JsCert.check (c : JsCert) : Bool :=
  (c.file.drop c.start).take c.len == c.tree.render && c.tree.wf && c.tree.scopeOK && c.tree.lower.isSome

/-- **`source_extraction_certificate_sound`.**  An accepted certificate binds an extracted
program to the exact source lines: the tree renders byte-for-byte to the certified window of
the uploaded file, its operator structure is unambiguous (and, for JS, block scoping is
shadow-free), and the executable program is the extraction of that very tree. -/
theorem source_extraction_certificate_sound :
    (∀ c : PyCert, c.check = true →
      (c.file.drop c.start).take c.len = c.tree.render ∧ c.tree.wf = true ∧ ∃ f, c.tree.lower = some f) ∧
    (∀ c : JsCert, c.check = true →
      (c.file.drop c.start).take c.len = c.tree.render ∧ c.tree.wf = true ∧ c.tree.scopeOK = true ∧
        ∃ f, c.tree.lower = some f) := by
  refine ⟨fun c h => ?_, fun c h => ?_⟩
  · simp only [PyCert.check, Bool.and_eq_true, beq_iff_eq, Option.isSome_iff_exists] at h
    exact ⟨h.1.1, h.1.2, h.2⟩
  · simp only [JsCert.check, Bool.and_eq_true, beq_iff_eq, Option.isSome_iff_exists] at h
    exact ⟨h.1.1.1, h.1.1.2, h.1.2, h.2⟩

/-- The certificate for `bellman` in `pcs/experimental/intervention.py` (lines 33–62). -/
def interventionPyCert : PyCert := ⟨Py.interventionPy, 32, 30, Py.bellmanCST⟩

/-- The certificate for `bellman` in website `public/intervention-core.mjs` (lines 14–27). -/
def interventionJsCert : JsCert := ⟨Js.interventionJs, 13, 14, Js.bellmanCST⟩

theorem interventionPyCert_accepted : interventionPyCert.check = true := by decide +kernel

theorem interventionJsCert_accepted : interventionJsCert.check = true := by decide +kernel

theorem interventionPyCert_program : interventionPyCert.tree.lower = some Py.bellmanCore :=
  Py.python_bellman_lowers

theorem interventionJsCert_program : interventionJsCert.tree.lower = some Js.bellmanCore :=
  Js.javascript_bellman_lowers

/-! ## Unsupported constructs are rejected -/

theorem py_unsupported_call_rejected (f : String) (args : List Py.PE) (hf : f ≠ "list") :
    (Py.PE.call f args).lower = none := by
  unfold Py.PE.lower; split <;> simp_all

theorem py_unsupported_generator_rejected (f : String) (elt : Py.PE) (tgt : List String) (it : Py.PE)
    (hf : f ≠ "min") : (Py.PE.genCall f elt tgt it).lower = none := by
  unfold Py.PE.lower; split <;> simp_all

theorem js_bare_arrow_rejected (pat : List String) (body : Js.JE) : (Js.JE.arrow pat body).lower = none := by
  simp [Js.JE.lower]

theorem js_bare_spread_rejected (e : Js.JE) : (Js.JE.spread e).lower = none := by
  simp [Js.JE.lower]

/-- A call of an arbitrary global function (e.g. `eval(x)`) is rejected. -/
theorem js_unsupported_call_rejected (g : String) (args : List Js.JE) :
    (Js.JE.call (.name g) args).lower = none := by
  simp [Js.JE.lower]

/-- Expression statements other than `x.push(e)` are rejected. -/
theorem js_unsupported_statement_rejected (g : String) (args : List Js.JE) :
    (Js.JS.expr (.call (.name g) args)).lower = none := by
  simp [Js.JS.lower]

/-! ## Every-budget correspondence and result semantics -/

/-- **`runtime_result_semantics`.**  For every valid task within the validator's bounds and
**every** fuel budget: the Python run and the JavaScript run each either report the explicit
unresolved outcome or return the reference cells/choices (the same lists in both languages),
and the entry of every node `u` means exactly what `bellman_correct` says. -/
theorem runtime_result_semantics {n : Nat} (t : ITask n) (ns : Nodes) (nms : List String)
    (hv : Valid n ns) (hnd : nms.Nodup) (hlen : nms.length = n) (hbl : t.baseline.length = n)
    (hcl : t.costs.length = n) (hlk : ∀ i ∈ t.locked, i < n) (hn : n ≤ 24)
    (hpos : ∀ k < n, 0 < t.prices.cost k) (hle : ∀ k, t.prices.cost k ≤ 1000000) :
    ∃ cellsL choicesL : List Val,
      (∀ fuel, callFn .py fuel Py.bellmanCore (PyIntervention.pyArgs t nms ns) = .fuel ∨
        callFn .py fuel Py.bellmanCore (PyIntervention.pyArgs t nms ns) = .ok (.tuple [.list cellsL, .list choicesL])) ∧
      (∀ fuel, callFn .js fuel Js.bellmanCore [.list (ns.toList.map encNode), JsIntervention.jsTask t nms] = .fuel ∨
        callFn .js fuel Js.bellmanCore [.list (ns.toList.map encNode), JsIntervention.jsTask t nms] =
          .ok (.obj [("cells", .list cellsL), ("choices", .list choicesL)])) ∧
      cellsL.length = ns.size + 2 ∧ choicesL.length = ns.size + 2 ∧
      ∀ u, u < ns.size + 2 →
        (cellsL[u]? = some .none ↔ ∀ a, ¬ Feasible n ns t.prices u a) ∧
        ∀ c, cellsL[u]? = some (encRaw c) →
          (∃ a, Feasible n ns t.prices u a ∧ objective t.prices a = c.cost) ∧
          (∀ a, Feasible n ns t.prices u a → c.cost ≤ objective t.prices a) ∧
          c.count = (optList n ns t.prices u c.cost).length ∧
          (∀ i, c.mand.testBit i = true ↔ ∀ a, Optimal n ns t.prices u a → flips t.prices a i = true) ∧
          (∀ i, c.poss.testBit i = true ↔ ∃ a, Optimal n ns t.prices u a ∧ flips t.prices a i = true) := by
  obtain ⟨N1, h1⟩ := PyIntervention.python_intervention_refines_reference t ns nms hv hnd hlen hbl hcl hlk
  obtain ⟨N2, h2⟩ := JsIntervention.javascript_intervention_refines_reference t ns nms hv hnd hlen hbl hcl hlk hn hpos hle
  have I := bellmanPass_spec (P := t.prices) hv
  refine ⟨(bellmanPass ns t.prices).cells.toList.map encCell,
    (bellmanPass ns t.prices).choices.toList.map encChoice, fun fuel => ?_, fun fuel => ?_,
    by simp [I.cells_size], by simp [I.choices_size], fun u hu => ?_⟩
  · have := callFn_fuel_or_eventual (r := .ok (PyIntervention.encPass (bellmanPass ns t.prices)))
      ⟨N1, fun f hf => (h1 f hf).1⟩ fuel
    rwa [PyIntervention.encPass] at this
  · have := callFn_fuel_or_eventual (r := .ok (JsIntervention.encPassJ (bellmanPass ns t.prices)))
      ⟨N2, fun f hf => (h2 f hf).1⟩ fuel
    rwa [JsIntervention.encPassJ] at this
  · obtain ⟨N3, h3⟩ := PyIntervention.python_intervention_result_semantics t ns nms hv hnd hlen hbl hcl hlk hpos hu
    obtain ⟨cellsL, choicesL, hrun, hsem⟩ := h3 (max N1 N3) (Nat.le_max_right _ _)
    have hrun' := (h1 (max N1 N3) (Nat.le_max_left _ _)).1
    rw [hrun, PyIntervention.encPass] at hrun'
    simp only [Res.ok.injEq, Val.tuple.injEq, List.cons.injEq, Val.list.injEq, and_true] at hrun'
    rw [← hrun'.1]
    exact hsem

end PCSRuntimeRefinement
