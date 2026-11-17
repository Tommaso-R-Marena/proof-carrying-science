import PCSIncremental.Graph

/-!
# Dependency reachability and acyclicity
-/
namespace PCSIncremental

/-- One-step dependency: `next` lists `prior` among its dependencies. -/
def dependsOn (g : Graph) (next prior : NodeId) : Prop :=
  ∃ n ∈ g.nodes, n.id = next ∧ prior ∈ n.deps

/-- Downstream affect relation: changing `root` can affect `leaf`. -/
inductive Downstream : Graph → NodeId → NodeId → Prop
  | refl (g : Graph) (root : NodeId) : Downstream g root root
  | cons {g : Graph} {root mid leaf : NodeId} :
      Downstream g root mid →
      dependsOn g leaf mid →
      Downstream g root leaf

/-- A retained id-set is upward-closed (contains all dependents of its members). -/
def upwardClosed (g : Graph) (S : List NodeId) : Prop :=
  ∀ prior ∈ S, ∀ next, dependsOn g next prior → next ∈ S

theorem upwardClosed_contains_downstream
    (g : Graph) (S : List NodeId) (hclosed : upwardClosed g S)
    (root leaf : NodeId) (hroot : root ∈ S) (hpath : Downstream g root leaf) :
    leaf ∈ S := by
  induction hpath with
  | refl => exact hroot
  | cons _ hdep ih => exact hclosed _ ih _ hdep

/-- Immediate predecessors of a node. -/
def predecessors (g : Graph) (id : NodeId) : List NodeId :=
  match g.find? id with
  | some n => n.deps
  | none => []

/-- Acyclicity via an explicit topological ranking. -/
structure TopoRank (g : Graph) where
  rank : NodeId → Nat
  respects : ∀ n ∈ g.nodes, ∀ d ∈ n.deps, rank d < rank n.id

def Acyclic (g : Graph) : Prop := Nonempty (TopoRank g)

theorem acyclic_deps_lower_rank (g : Graph) (tr : TopoRank g)
    (n : Node) (hn : n ∈ g.nodes) (d : NodeId) (hd : d ∈ n.deps) :
    tr.rank d < tr.rank n.id :=
  tr.respects n hn d hd

/-- No self-dependency edge when a topo rank exists. -/
theorem acyclic_no_self_dep (g : Graph) (tr : TopoRank g)
    (n : Node) (hn : n ∈ g.nodes) : n.id ∉ n.deps := by
  intro h
  have := tr.respects n hn n.id h
  exact Nat.lt_irrefl _ this

/-- Downstream steps strictly increase rank along edges. -/
theorem dependsOn_rank_lt (g : Graph) (tr : TopoRank g)
    {next prior : NodeId} (h : dependsOn g next prior) :
    tr.rank prior < tr.rank next := by
  rcases h with ⟨n, hn, hid, hdep⟩
  have := tr.respects n hn prior hdep
  simpa [hid] using this

end PCSIncremental
