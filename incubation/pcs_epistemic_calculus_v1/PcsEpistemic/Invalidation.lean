import PcsEpistemic.Graph
import PcsEpistemic.Assures

/-!
# Invalidation reachability

Founding target (FORMAL_SEMANTICS_DRAFT §7 / commons INV-006).
-/
set_option autoImplicit false

namespace PcsEpistemic

structure ImpactReport where
  affectedArtifacts : List Nat
  affectedEvidence : List Nat
  affectedClaims : List Nat
  deriving DecidableEq, Repr

def computeImpact (g : DepGraph) (changed : List Nat) : ImpactReport :=
  let (arts, ev, cl) := impact g changed
  ⟨arts, ev, cl⟩

def claimAffected (report : ImpactReport) (cid : Nat) : Bool :=
  memNat report.affectedClaims cid

def declaredNonImpact (g : DepGraph) (changed : List Nat) (cid : Nat) : Bool :=
  !(claimAffected (computeImpact g changed) cid)

structure HiddenDependency where
  changed : Nat
  hiddenClaim : Nat
  deriving DecidableEq, Repr

/-- Completeness is an explicit hypothesis, never inferred from the graph alone. -/
def NonImpact (g : DepGraph) (changed : List Nat) (cid : Nat)
    (dependencyComplete : Bool) : Prop :=
  dependencyComplete = true ∧ declaredNonImpact g changed cid = true

theorem nonimpact_requires_completeness
    (g : DepGraph) (changed : List Nat) (cid : Nat)
    (h : NonImpact g changed cid true) :
    declaredNonImpact g changed cid = true :=
  h.2

theorem hidden_dependency_blocks_world_nonimpact
    (g : DepGraph) (h : HiddenDependency)
    (hdecl : declaredNonImpact g [h.changed] h.hiddenClaim = true) :
    declaredNonImpact g [h.changed] h.hiddenClaim = true ∧
      ¬ NonImpact g [h.changed] h.hiddenClaim false := by
  refine ⟨hdecl, ?_⟩
  intro hni
  cases hni with
  | intro hfalse _ =>
    exact Bool.false_ne_true hfalse

def mustReplay (report : ImpactReport) (eid : Nat) : Bool :=
  memNat report.affectedEvidence eid

theorem affected_evidence_must_replay
    (g : DepGraph) (changed : List Nat) (eid : Nat)
    (h : memNat (computeImpact g changed).affectedEvidence eid = true) :
    mustReplay (computeImpact g changed) eid = true :=
  h

/-- Leaf covering for invalidation: required evidence in the affected set
    forces the claim id into `claimsRequiring`. -/
theorem claimsRequiring_covers
    (g : DepGraph) (eids : List Nat) (c : ClaimNode)
    (hc : c ∈ g.claims)
    (eid : Nat)
    (heid : eid ∈ c.requiredEvidence)
    (haff : memNat eids eid = true) :
    c.id ∈ claimsRequiring g eids := by
  unfold claimsRequiring
  have hany :
      c.requiredEvidence.any (fun e => memNat eids e) = true :=
    List.any_eq_true.mpr ⟨eid, heid, haff⟩
  exact List.mem_filterMap.mpr ⟨c, hc, by simp [hany]⟩

theorem claim_requiring_affected_evidence_is_affected
    (g : DepGraph) (changed : List Nat) (c : ClaimNode)
    (hc : c ∈ g.claims)
    (eid : Nat)
    (heid : eid ∈ c.requiredEvidence)
    (haff : memNat (computeImpact g changed).affectedEvidence eid = true) :
    c.id ∈ (computeImpact g changed).affectedClaims := by
  simpa [computeImpact, impact] using
    claimsRequiring_covers g (evidenceAffected g (reachArtifacts g changed)) c hc eid heid
      (by simpa [computeImpact, impact] using haff)

end PcsEpistemic
