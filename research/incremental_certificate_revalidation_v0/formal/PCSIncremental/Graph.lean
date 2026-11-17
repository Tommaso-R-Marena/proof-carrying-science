import Init

/-!
# Computation DAG model for incremental certificate revalidation

Exact equality is used throughout. Digests are not assumed collision-free.
No custom axioms. No `sorry`. No `admit`.
-/

namespace PCSIncremental

abbrev NodeId := Nat
abbrev OpId := Nat
abbrev PolicyId := Nat
abbrev VersionId := Nat
abbrev EvidenceId := Nat
abbrev Value := Nat
abbrev CertPayload := Nat

/-- A computation node in a finite DAG. -/
structure Node where
  id : NodeId
  op : OpId
  deps : List NodeId
  policy : PolicyId
  version : VersionId
  evidence : EvidenceId
  deriving Repr, DecidableEq, Inhabited

/-- Finite node list representing a computation graph. -/
structure Graph where
  nodes : List Node
  deriving Repr, DecidableEq, Inhabited

/-- Lookup a node by identifier. -/
def Graph.find? (g : Graph) (id : NodeId) : Option Node :=
  g.nodes.find? (fun n => decide (n.id = id))

/-- All node identifiers. -/
def Graph.ids (g : Graph) : List NodeId :=
  g.nodes.map (·.id)

/-- Unique identifiers (no duplicate ids). -/
def Graph.uniqueIds (g : Graph) : Prop :=
  ∀ n ∈ g.nodes, ∀ m ∈ g.nodes, n.id = m.id → n = m

/-- Every declared dependency exists as a node. -/
def Graph.depsExist (g : Graph) : Prop :=
  ∀ n ∈ g.nodes, ∀ d ∈ n.deps, ∃ m ∈ g.nodes, m.id = d

/-- Membership of a node id. -/
def Graph.hasId (g : Graph) (id : NodeId) : Prop :=
  ∃ n ∈ g.nodes, n.id = id

theorem find?_none_not_hasId (g : Graph) (id : NodeId)
    (h : g.find? id = none) : ¬ g.hasId id := by
  intro ⟨n, hn, hid⟩
  unfold Graph.find? at h
  have hp : (fun x : Node => decide (x.id = id)) n = true := by
    simp [hid]
  exact List.find?_eq_none.1 h n hn hp

theorem hasId_of_mem (g : Graph) (n : Node) (hn : n ∈ g.nodes) :
    g.hasId n.id :=
  ⟨n, hn, rfl⟩

/-- Structural well-formedness used by later modules (acyclicity separate). -/
structure WellFormedIds (g : Graph) : Prop where
  unique : g.uniqueIds
  deps : g.depsExist

theorem uniqueIds_of_wellFormed (g : Graph) (wf : WellFormedIds g) : g.uniqueIds :=
  wf.unique

theorem depsExist_of_wellFormed (g : Graph) (wf : WellFormedIds g) : g.depsExist :=
  wf.deps

end PCSIncremental
