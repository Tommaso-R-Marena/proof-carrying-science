/-
Copyright (c) 2026 Proof-Carrying Causality Laboratory.
Independent incubation formalization — not PCS production TCB.
-/
import Mathlib.Data.Finset.Basic
import Mathlib.Data.Fintype.Basic

namespace PcsCausal

/-- Finite named vertex identifiers. -/
abbrev Vertex := String

/-- Directed edge parent → child. -/
structure DirEdge where
  parent : Vertex
  child : Vertex
  deriving DecidableEq, Repr

/-- A finite directed graph given by vertex and edge finsets. -/
structure Digraph where
  vertices : Finset Vertex
  edges : Finset DirEdge
  edges_subset : ∀ e ∈ edges, e.parent ∈ vertices ∧ e.child ∈ vertices

/-- Acyclicity predicate placeholder via absence of self-support in edge set for length-1;
full DAG acyclicity is defined in `Graph.lean`. -/
def Digraph.hasSelfLoop (G : Digraph) : Prop :=
  ∃ e ∈ G.edges, e.parent = e.child

theorem Digraph.edges_in_vertices (G : Digraph) (e : DirEdge) (he : e ∈ G.edges) :
    e.parent ∈ G.vertices ∧ e.child ∈ G.vertices :=
  G.edges_subset e he

end PcsCausal
