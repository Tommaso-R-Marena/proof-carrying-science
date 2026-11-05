import PcsEpistemic.Evidence

/-!
Finite claim–evidence–artifact dependency graphs.
-/
set_option autoImplicit false

namespace PcsEpistemic

structure Artifact where
  id : Nat
  deriving DecidableEq, Repr

structure EvidenceNode where
  id : Nat
  cls : EvidenceClass
  artifacts : List Nat
  claims : List Nat
  deriving DecidableEq, Repr

structure ClaimNode where
  id : Nat
  requiredClass : EvidenceClass
  requiredEvidence : List Nat
  deriving DecidableEq, Repr

structure WorkflowNode where
  id : Nat
  inputs : List Nat
  outputs : List Nat
  deriving DecidableEq, Repr

structure DepGraph where
  artifacts : List Nat
  workflow : List WorkflowNode
  evidence : List EvidenceNode
  claims : List ClaimNode
  deriving DecidableEq, Repr

def memNat (xs : List Nat) (x : Nat) : Bool :=
  xs.any (fun y => decide (y = x))

def WorkflowNode.consumes (n : WorkflowNode) (aid : Nat) : Bool :=
  memNat n.inputs aid

def WorkflowNode.produces (n : WorkflowNode) (aid : Nat) : Bool :=
  memNat n.outputs aid

/-- One-step artifact consumers through workflow edges. -/
def consumers (g : DepGraph) (aid : Nat) : List Nat :=
  (g.workflow.filter (fun n => n.consumes aid)).flatMap (fun n => n.outputs)

/-- Reflexive-transitive closure of artifact dependence (bounded iteration). -/
def reachArtifacts (g : DepGraph) (seeds : List Nat) : List Nat :=
  let rec go (fuel : Nat) (frontier : List Nat) (acc : List Nat) : List Nat :=
    match fuel with
    | 0 => acc
    | fuel'+1 =>
      match frontier with
      | [] => acc
      | a :: rest =>
        if memNat acc a then
          go fuel' rest acc
        else
          let next := consumers g a
          go fuel' (rest ++ next) (acc ++ [a])
  go (g.artifacts.length + g.workflow.length + seeds.length + 1) seeds []

def evidenceTouches (e : EvidenceNode) (arts : List Nat) : Bool :=
  e.artifacts.any (fun a => memNat arts a)

def claimsRequiring (g : DepGraph) (eids : List Nat) : List Nat :=
  g.claims.filterMap (fun c =>
    if c.requiredEvidence.any (fun e => memNat eids e) then some c.id else none)

def evidenceAffected (g : DepGraph) (arts : List Nat) : List Nat :=
  g.evidence.filterMap (fun e => if evidenceTouches e arts then some e.id else none)

/-- Declared-graph impact from changed artifacts. -/
def impact (g : DepGraph) (changed : List Nat) : List Nat × List Nat × List Nat :=
  let arts := reachArtifacts g changed
  let ev := evidenceAffected g arts
  let cl := claimsRequiring g ev
  (arts, ev, cl)

def claimById (g : DepGraph) (cid : Nat) : Option ClaimNode :=
  g.claims.find? (fun c => c.id = cid)

def evidenceById (g : DepGraph) (eid : Nat) : Option EvidenceNode :=
  g.evidence.find? (fun e => e.id = eid)

end PcsEpistemic
