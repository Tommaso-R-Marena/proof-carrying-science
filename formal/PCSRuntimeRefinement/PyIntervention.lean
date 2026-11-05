import PCSRuntimeRefinement.PyBellmanLoop

/-!
# `python_intervention_refines_reference`

The commuting chain for the Python intervention planner's `bellman` (source lines 33–62 of
`pcs/experimental/intervention.py`):

`source text  →(python_bellman_source_bound, python_bellman_lowers)  extracted program
  →(bellman_exec)  Lean reference pass bellmanPass  →(bellmanPass_spec)  recursive cellRec
  →(bellman_correct)  minimum objective / optimal count / mandatory and possible masks`.

The task arguments are the actual Python objects of a validated `pcs-intervention-task-v1`
task: `names` a list of distinct strings, `baseline` / `costs` dictionaries keyed by those
names (in variable order), and `locked` the list of locked *names*.
-/

namespace PCSRuntimeRefinement.PyIntervention

open PCSRuntimeRefinement PCSRuntimeRefinement.PyBellman PCSDD PCSOmega

/-! ## Python objects of an intervention task -/

/-- `baseline` as a Python `dict` (`name → bool`). -/
def pyBaseline {n : Nat} (t : ITask n) (nms : List String) : Val :=
  .obj (nms.zip (t.baseline.map Val.bool))

/-- `costs` as a Python `dict` (`name → int`). -/
def pyCosts {n : Nat} (t : ITask n) (nms : List String) : Val :=
  .obj (nms.zip (t.costs.map (fun c : Nat => Val.int (Int.ofNat c))))

/-- `locked` as a Python `list` of names. -/
def pyLocked {n : Nat} (t : ITask n) (nms : List String) : Val :=
  .list (t.locked.map (fun i => Val.str (nms.getD i "")))

/-- The argument tuple `(nodes, names, baseline, costs, locked)`. -/
def pyArgs {n : Nat} (t : ITask n) (nms : List String) (ns : Nodes) : List Val :=
  [.list (ns.toList.map encNode), .list (nms.map .str), pyBaseline t nms, pyCosts t nms, pyLocked t nms]

/-- Encoding of a full pass result `(cells, choices)`. -/
def encPass (st : PassSt) : Val :=
  .tuple [.list (st.cells.toList.map encCell), .list (st.choices.toList.map encChoice)]

/-! ## List facts -/

theorem getD_inj : ∀ (nms : List String), nms.Nodup → ∀ i j, i < nms.length → j < nms.length →
    nms.getD i "" = nms.getD j "" → i = j
  | [], _, _, _, hi, _, _ => absurd hi (by simp)
  | a :: nms, hnd, i, j, hi, hj, h => by
      have ha : a ∉ nms := (List.nodup_cons.1 hnd).1
      have hnd' := (List.nodup_cons.1 hnd).2
      cases i with
      | zero =>
          cases j with
          | zero => rfl
          | succ j =>
              simp only [List.getD_cons_zero, List.getD_cons_succ] at h
              have hj' : j < nms.length := by simp at hj; omega
              exact absurd (h ▸ (by simp [List.getD_eq_getElem?_getD, hj'] : nms.getD j "" ∈ nms)) ha
      | succ i =>
          cases j with
          | zero =>
              simp only [List.getD_cons_zero, List.getD_cons_succ] at h
              have hi' : i < nms.length := by simp at hi; omega
              exact absurd (h ▸ (by simp [List.getD_eq_getElem?_getD, hi'] : nms.getD i "" ∈ nms)) ha
          | succ j =>
              simp only [List.getD_cons_succ] at h
              have := getD_inj nms hnd' i j (by simp at hi; omega) (by simp at hj; omega) h
              omega

theorem lookupKey_zip : ∀ (nms : List String) (vs : List Val), nms.Nodup → nms.length = vs.length →
    ∀ k, k < nms.length → lookupKey (nms.zip vs) (nms.getD k "") = some (vs.getD k .none)
  | [], _, _, _, k, hk => absurd hk (by simp)
  | a :: nms, [], _, hl, _, _ => absurd hl (by simp)
  | a :: nms, b :: vs, hnd, hl, k, hk => by
      have ha : a ∉ nms := (List.nodup_cons.1 hnd).1
      cases k with
      | zero => simp [lookupKey]
      | succ k =>
          have hk' : k < nms.length := by simp at hk; omega
          have hne : (a == nms.getD k "") = false := by
            have hm : nms.getD k "" ∈ nms := by simp [List.getD_eq_getElem?_getD, hk']
            simp only [beq_eq_false_iff_ne]; intro h; exact ha (h ▸ hm)
          have ih := lookupKey_zip nms vs (List.nodup_cons.1 hnd).2 (by simpa using hl) k hk'
          unfold lookupKey at ih ⊢
          simp only [List.getD_cons_succ]
          rw [List.zip_cons_cons, List.find?_cons]
          dsimp only
          rw [hne]; exact ih

theorem pyEq_str (a b : String) : pyEq (.str a) (.str b) = (a == b) := rfl

/-- The Python objects of a task satisfy the argument contract `Args` of the extracted program. -/
theorem task_args {n : Nat} (t : ITask n) (nms : List String) (hnd : nms.Nodup) (hlen : nms.length = n)
    (hbl : t.baseline.length = n) (hcl : t.costs.length = n) (hlk : ∀ i ∈ t.locked, i < n) :
    Args t.prices n (.list (nms.map .str)) (pyBaseline t nms) (pyCosts t nms) (pyLocked t nms) := by
  refine ⟨nms, rfl, by omega, fun k hk => ⟨?_, ?_, ?_⟩⟩
  · show (match lookupKey _ _ with | some v => Res.ok v | none => Res.exc .keyError) = _
    rw [lookupKey_zip nms _ hnd (by simp; omega) k (by omega)]
    simp [ITask.prices, List.getD_eq_getElem?_getD, hbl, hk]
  · show (match lookupKey _ _ with | some v => Res.ok v | none => Res.exc .keyError) = _
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
      rw [pyEq_str, beq_iff_eq] at he
      have := getD_inj nms hnd k j (by omega) (by have := hlk j hj; omega) he
      exact this ▸ hj
    · intro hm
      exact ⟨_, List.mem_map.2 ⟨k, hm, rfl⟩, by rw [pyEq_str]; simp⟩

/-! ## The reference pass as the recursive specification -/

theorem toList_of_getElem? {α : Type} (arr : Array α) (m : Nat) (f : Nat → α) (hs : arr.size = m)
    (h : ∀ u < m, arr[u]? = some (f u)) : arr.toList = (List.range m).map f := by
  apply List.ext_getElem
  · simp [hs]
  · intro u h1 h2
    have hu : u < m := by simpa [hs] using h1
    have := h u hu
    simp only [Array.getElem?_eq_getElem (by omega : u < arr.size), Option.some.injEq] at this
    simp [this]

theorem pass_eq_rec {n : Nat} {ns : Nodes} {P : Prices} (hv : Valid n ns) :
    encPass (bellmanPass ns P) =
      .tuple [.list ((List.range (ns.size + 2)).map (fun u => encCell (cellRec ns P u))),
              .list ((List.range (ns.size + 2)).map (fun u => encChoice (choiceRec ns P u)))] := by
  have I := bellmanPass_spec (P := P) hv
  unfold encPass
  rw [toList_of_getElem? _ _ _ I.cells_size I.cells, toList_of_getElem? _ _ _ I.choices_size I.choices]
  simp [List.map_map, Function.comp_def]

/-- **`python_intervention_refines_reference`.**  For every valid diagram over `n` variables
and every task whose names are distinct and whose baseline / costs / locked lists are in range,
the source-extracted Python `bellman` terminates (for all sufficiently large fuel) with exactly
the encoding of the reference pass `bellmanPass`, which in turn lists, for every node
identifier `u`, the recursive cell `cellRec` and False-first choice `choiceRec`. -/
theorem python_intervention_refines_reference {n : Nat} (t : ITask n) (ns : Nodes) (nms : List String)
    (hv : Valid n ns) (hnd : nms.Nodup) (hlen : nms.length = n) (hbl : t.baseline.length = n)
    (hcl : t.costs.length = n) (hlk : ∀ i ∈ t.locked, i < n) :
    ∃ N, ∀ fuel, N ≤ fuel →
      callFn .py fuel Py.bellmanCore (pyArgs t nms ns) = .ok (encPass (bellmanPass ns t.prices)) ∧
      encPass (bellmanPass ns t.prices) =
        .tuple [.list ((List.range (ns.size + 2)).map (fun u => encCell (cellRec ns t.prices u))),
                .list ((List.range (ns.size + 2)).map (fun u => encChoice (choiceRec ns t.prices u)))] := by
  obtain ⟨N, hN⟩ := bellman_exec hv (task_args t nms hnd hlen hbl hcl hlk)
  exact ⟨N, fun fuel hf => ⟨hN fuel hf, pass_eq_rec hv⟩⟩

/-- **Semantic reading of the Python output.**  If the Python run returns its cells list and
the entry for node `u` is `[cost, count, mand, poss]`, then `cost` is the global minimum
intervention objective over the feasible total assignments of `u`, `count` is the exact number
of distinct optimal assignments, and `mand` / `poss` are exactly the flips common to all /
occurring in some optimal assignment; `None` means no feasible assignment. -/
theorem python_intervention_result_semantics {n : Nat} (t : ITask n) (ns : Nodes) (nms : List String)
    (hv : Valid n ns) (hnd : nms.Nodup) (hlen : nms.length = n) (hbl : t.baseline.length = n)
    (hcl : t.costs.length = n) (hlk : ∀ i ∈ t.locked, i < n) (hpos : ∀ k < n, 0 < t.prices.cost k)
    {u : Nat} (hu : u < ns.size + 2) :
    ∃ N, ∀ fuel, N ≤ fuel → ∃ cellsL choicesL : List Val,
      callFn .py fuel Py.bellmanCore (pyArgs t nms ns) = .ok (.tuple [.list cellsL, .list choicesL]) ∧
      (cellsL[u]? = some .none ↔ ∀ a, ¬ Feasible n ns t.prices u a) ∧
      ∀ c, cellsL[u]? = some (encRaw c) →
        (∃ a, Feasible n ns t.prices u a ∧ objective t.prices a = c.cost) ∧
        (∀ a, Feasible n ns t.prices u a → c.cost ≤ objective t.prices a) ∧
        c.count = (optList n ns t.prices u c.cost).length ∧
        (∀ i, c.mand.testBit i = true ↔ ∀ a, Optimal n ns t.prices u a → flips t.prices a i = true) ∧
        (∀ i, c.poss.testBit i = true ↔ ∃ a, Optimal n ns t.prices u a ∧ flips t.prices a i = true) := by
  obtain ⟨N, hN⟩ := python_intervention_refines_reference t ns nms hv hnd hlen hbl hcl hlk
  refine ⟨N, fun fuel hf => ?_⟩
  obtain ⟨h1, h2⟩ := hN fuel hf
  rw [h2] at h1
  refine ⟨_, _, h1, ?_, ?_⟩
  · have hc := (bellman_correct (P := t.prices) hv hpos hu).1
    rw [List.getElem?_map, List.getElem?_range hu]
    simp only [Option.map_some, Option.some.injEq]
    rw [← hc]
    cases cellRec ns t.prices u <;> simp [encCell, encRaw]
  · intro c hc
    rw [List.getElem?_map, List.getElem?_range hu] at hc
    simp only [Option.map_some, Option.some.injEq] at hc
    have hrec : cellRec ns t.prices u = some c := by
      cases hr : cellRec ns t.prices u with
      | none => rw [hr] at hc; simp [encCell, encRaw] at hc
      | some c' =>
          rw [hr] at hc
          simp only [encCell, encRaw, Val.list.injEq, List.cons.injEq, Val.int.injEq,
            Int.natCast_inj, and_true] at hc
          obtain ⟨a, b, d, e⟩ := hc
          cases c; cases c'; simp_all
    obtain ⟨hA, hB, -, ⟨-, -, hC⟩, hD, hE⟩ := (bellman_correct (P := t.prices) hv hpos hu).2 c hrec
    exact ⟨hA, hB, hC, hD, hE⟩

end PCSRuntimeRefinement.PyIntervention
