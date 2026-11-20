/-
Proof-Carrying Causal Reasoning v1 — finite DAG fragments.

These are ordinary-kernel proofs about concrete finite graphs used by the
Python checker. They do not import Mathlib, do not claim general backdoor
soundness for arbitrary SCMs, and do not grant production PCS authority.
-/
namespace PcsPccr

/-- A directed edge. -/
structure Edge where
  src : String
  dst : String
  deriving DecidableEq, Repr

/-- Finite named DAG fragment (acyclicity is an external obligation here). -/
structure FinDAG where
  nodes : List String
  edges : List Edge
  deriving Repr

def FinDAG.hasEdge (g : FinDAG) (u v : String) : Bool :=
  (g.edges.find? (fun e => e.src == u && e.dst == v)).isSome

def FinDAG.parents (g : FinDAG) (v : String) : List String :=
  g.edges.filterMap (fun e => if e.dst == v then some e.src else none)

def FinDAG.children (g : FinDAG) (u : String) : List String :=
  g.edges.filterMap (fun e => if e.src == u then some e.dst else none)

/-- Descendant check by bounded BFS (depth ≤ |nodes|). -/
def FinDAG.isDescendant (g : FinDAG) (anc desc : String) : Bool :=
  Id.run do
    let mut seen : List String := []
    let mut q : List String := g.children anc
    let bound := g.nodes.length + 1
    let mut i := 0
    while i < bound do
      match q with
      | [] => return false
      | x :: xs =>
        if x == desc then return true
        if seen.contains x then
          q := xs
        else
          seen := x :: seen
          q := xs ++ g.children x
        i := i + 1
    return false

/-- Backdoor criterion side-condition: Z contains no descendant of treatment. -/
def noDescendantsOfTreatment (g : FinDAG) (treatment : String) (Z : List String) : Bool :=
  Z.all (fun z => !(g.isDescendant treatment z))

/-- Classical confounder graph: Z→X, Z→Y, X→Y. -/
def confounderGraph : FinDAG :=
  { nodes := ["Z", "X", "Y"]
    edges := [⟨"Z", "X"⟩, ⟨"Z", "Y"⟩, ⟨"X", "Y"⟩] }

/-- Collider graph: X→C, Y→C. -/
def colliderGraph : FinDAG :=
  { nodes := ["X", "Y", "C"]
    edges := [⟨"X", "C"⟩, ⟨"Y", "C"⟩] }

/-- Pure mediation: X→M→Y. -/
def mediationGraph : FinDAG :=
  { nodes := ["X", "M", "Y"]
    edges := [⟨"X", "M"⟩, ⟨"M", "Y"⟩] }

end PcsPccr
