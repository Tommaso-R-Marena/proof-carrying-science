/-
Graph-theoretic foundations for finite causal DAGs.
-/
import PcsCausal.Basic
import Mathlib.Data.Finset.Card

namespace PcsCausal

/-- Parent set of `v` in a digraph. -/
def Digraph.parents (G : Digraph) (v : Vertex) : Finset Vertex :=
  G.edges.filter (fun e => e.child = v) |>.image (fun e => e.parent)

/-- Hard intervention mutilation: delete all edges into the intervened vertices. -/
def Digraph.mutilate (G : Digraph) (intervened : Finset Vertex) : Digraph :=
  {
    vertices := G.vertices
    edges := G.edges.filter (fun e => e.child ∉ intervened)
    edges_subset := by
      intro e he
      have he' : e ∈ G.edges := (Finset.mem_filter.mp he).1
      exact G.edges_subset e he'
  }

/-- Mutilation preserves the vertex set. -/
theorem Digraph.mutilate_vertices (G : Digraph) (I : Finset Vertex) :
    (G.mutilate I).vertices = G.vertices := rfl

/-- Mutilation never introduces new edges. -/
theorem Digraph.mutilate_edges_subset (G : Digraph) (I : Finset Vertex) :
    (G.mutilate I).edges ⊆ G.edges := by
  intro e he
  exact (Finset.mem_filter.mp he).1

/-- After mutilation, intervened nodes have no incoming edges. -/
theorem Digraph.mutilate_no_incoming
    (G : Digraph) (I : Finset Vertex) (v : Vertex) (hv : v ∈ I) :
    ∀ e ∈ (G.mutilate I).edges, e.child ≠ v := by
  intro e he
  have hfilt := (Finset.mem_filter.mp he).2
  intro hchild
  exact hfilt (hchild ▸ hv)

end PcsCausal
