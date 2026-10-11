import PCSDecisionDiagram.Pass

/-!
# Executable diagram validator

`validB n ns` checks every node (variable in range, children precede the parent, children
differ, variables strictly increase along both edges) and uniqueness of every triple.
`validB_iff` proves it decides `Valid n ns` exactly, so invalid ordering, out-of-range or
forward child identifiers, redundant nodes and duplicate triples are all rejected.

`bellmanChecked` is a guarded entry point for an externally supplied diagram: it rejects an
invalid table, an out-of-range root and any non-positive cost before running the pass;
`bellmanChecked_ok` transfers the full single-pass contract to every accepted input.
-/

namespace PCSDD

instance (n : Nat) (ns : Nodes) (i : Nat) (nd : Node) : Decidable (NodeOK n ns i nd) := by
  unfold NodeOK; exact inferInstance

/-- Executable local node check. -/
def nodeOKB (n : Nat) (ns : Nodes) (i : Nat) : Bool :=
  match ns[i]? with
  | some nd => decide (NodeOK n ns i nd)
  | none => false

/-- Executable uniqueness check. -/
def uniqB (ns : Nodes) : Bool :=
  (List.range ns.size).all fun i => (List.range ns.size).all fun j => i == j || ns[i]? != ns[j]?

/-- Executable validator. -/
def validB (n : Nat) (ns : Nodes) : Bool :=
  (List.range ns.size).all (nodeOKB n ns) && uniqB ns

theorem validB_iff (n : Nat) (ns : Nodes) : validB n ns = true ↔ Valid n ns := by
  simp only [validB, uniqB, nodeOKB, Bool.and_eq_true, List.all_eq_true, List.mem_range,
    Bool.or_eq_true, beq_iff_eq, bne_iff_ne, ne_eq]
  constructor
  · rintro ⟨h1, h2⟩
    refine ⟨fun i hi => ?_, fun i j hi hj e => ?_⟩
    · have := h1 i hi
      rw [Array.getElem?_eq_getElem hi] at this
      simpa using this
    · rcases h2 i hi j hj with h | h
      · exact h
      · rw [Array.getElem?_eq_getElem hi, Array.getElem?_eq_getElem hj, e] at h
        exact absurd rfl h
  · rintro ⟨h1, h2⟩
    refine ⟨fun i hi => ?_, fun i hi j hj => ?_⟩
    · rw [Array.getElem?_eq_getElem hi]; simpa using h1 i hi
    · by_cases e : i = j
      · exact Or.inl e
      · right
        rw [Array.getElem?_eq_getElem hi, Array.getElem?_eq_getElem hj]
        intro h
        exact e (h2 i j hi hj (Option.some.inj h))

/-- Guarded Bellman entry point for an externally supplied diagram. -/
def bellmanChecked (n : Nat) (ns : Nodes) (P : Prices) (root : Nat) :
    Except String (Option Cell × PassSt) :=
  if validB n ns = false then .error "invalid ordered diagram" else
  if ns.size + 2 ≤ root then .error "root identifier out of range" else
  if (List.range n).all (fun k => decide (0 < P.cost k)) = false then .error "costs must be positive" else
  let st := bellmanPass ns P
  .ok (st.cells.getD root none, st)

theorem bellmanChecked_ok {n : Nat} {ns : Nodes} {P : Prices} {root : Nat} {oc : Option Cell}
    {st : PassSt} (h : bellmanChecked n ns P root = .ok (oc, st)) :
    Valid n ns ∧ root < ns.size + 2 ∧ (∀ k < n, 0 < P.cost k) ∧ oc = cellRec ns P root ∧
      PassInv ns P ns.size st := by
  unfold bellmanChecked at h
  split at h
  · cases h
  rename_i hv
  split at h
  · cases h
  rename_i hr
  split at h
  · cases h
  rename_i hc
  cases h
  have hv' : Valid n ns := (validB_iff n ns).1 (by simpa using hv)
  have hc' : ∀ k < n, 0 < P.cost k := by
    intro k hk
    cases hb : (List.range n).all (fun k => decide (0 < P.cost k))
    · exact absurd hb hc
    · simp only [List.all_eq_true, List.mem_range, decide_eq_true_eq] at hb
      exact hb k hk
  have I := bellmanPass_spec (P := P) hv'
  refine ⟨hv', by omega, hc', ?_, I⟩
  rw [Array.getD_eq_getD_getElem?, I.cells root (by omega)]; rfl

end PCSDD
