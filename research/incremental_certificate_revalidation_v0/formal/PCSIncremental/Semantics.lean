import PCSIncremental.Invalidation
import PCSIncremental.Cache

/-!
# Local checkers, fresh verification, and incremental acceptance

`LocalCheck` binds **evidence** (matching Python `local_check_node`), not only
op/version/policy/deps. `IncrementalAccept` does **not** assume `FreshValid`
on the updated graph; that is derived by `incremental_implies_fresh`.

Logical vs operational: `ChangesComplete` / `idsCovered` are operational
obligations for constructing per-node premises. Once Affected-recheck and
Unaffected-reuse premises hold, they are not required in the logical case split.
-/

namespace PCSIncremental

/-- Local verifier: operation, version, policy, **evidence**, dependency values,
certificate payload, and claimed output.
Matches executable `local_check_node` (evidence matters for constants). -/
abbrev LocalCheck :=
  OpId → VersionId → PolicyId → EvidenceId → List Value → CertPayload → Value → Bool

/-- Assignment of outputs to node ids. -/
abbrev Assignment := NodeId → Value

/-- Resolve dependency outputs for a node under an assignment. -/
def depValues (n : Node) (σ : Assignment) : List Value :=
  n.deps.map σ

/-- Local check succeeds for a node under assignment and certificate. -/
def nodeChecks (check : LocalCheck) (n : Node) (σ : Assignment) (c : Certificate) : Prop :=
  check n.op n.version n.policy n.evidence (depValues n σ) c.payload c.output = true
  ∧ σ n.id = c.output

/-- Fresh verification: every node has a certificate that locally checks. -/
def FreshValid (check : LocalCheck) (g : Graph) (σ : Assignment)
    (certs : NodeId → Certificate) : Prop :=
  ∀ n ∈ g.nodes, nodeChecks check n σ (certs n.id)

/-- Definitional fields that must be stable for safe reuse. -/
def sameDefn (n m : Node) : Prop :=
  n.op = m.op ∧ n.deps = m.deps ∧ n.policy = m.policy ∧
  n.version = m.version ∧ n.evidence = m.evidence

/-- Boolean decision procedure for `sameDefn`. -/
def sameDefnB (n m : Node) : Bool :=
  (n.op == m.op) && (n.deps == m.deps) && (n.policy == m.policy) &&
  (n.version == m.version) && (n.evidence == m.evidence)

theorem sameDefnB_iff (n m : Node) : sameDefnB n m = true ↔ sameDefn n m := by
  constructor
  · intro h
    simp only [sameDefnB, Bool.and_eq_true, beq_iff_eq] at h
    refine ⟨h.1.1.1.1, h.1.1.1.2, h.1.1.2, h.1.2, h.2⟩
  · intro ⟨hop, hdeps, hpol, hver, hev⟩
    simp only [sameDefnB, Bool.and_eq_true, beq_iff_eq, hop, hdeps, hpol, hver, hev,
      and_self]

/-- Complete change accounting: any definitional difference is listed in `changes`.
Invalidation then uses the **updated** graph `g'` (new dependency edges). -/
def ChangesComplete (g g' : Graph) (changes : ChangeSet) : Prop :=
  ∀ n' ∈ g'.nodes, ∀ n ∈ g.nodes,
    n.id = n'.id → ¬ sameDefn n n' → n'.id ∈ changes

/-- Hypothesis recording that a ValidState was obtained by fresh verification. -/
structure FreshWitness (check : LocalCheck) (vs : ValidState) where
  certs : NodeId → Certificate
  fresh : FreshValid check vs.graph vs.outputs certs
  /-- Cache authority agrees with fresh checks for stored entries. -/
  cacheSound :
    ∀ e ∈ vs.cache.entries,
      e.priorAccepted = true →
        ∃ n ∈ vs.graph.nodes,
          e.key = obligationOf n (depValues n vs.outputs) ∧
          e.cert.output = vs.outputs n.id ∧
          nodeChecks check n vs.outputs e.cert

/-- Incremental acceptance — premises only; does **not** include `FreshValid g'`.
Invalidation topology is `g'` (updated graph). -/
structure IncrementalAccept (check : LocalCheck) (vs : ValidState)
    (g' : Graph) (changes : ChangeSet) (σ' : Assignment)
    (certs' : NodeId → Certificate) where
  /-- Prior state was freshly verified with a sound authoritative cache. -/
  prior : FreshWitness check vs
  /-- Definitional edits are completely listed (operational seed completeness). -/
  changesComplete : ChangesComplete vs.graph g' changes
  /-- Every updated-graph node id existed in the prior graph. -/
  idsCovered : ∀ n' ∈ g'.nodes, ∃ n ∈ vs.graph.nodes, n.id = n'.id
  /-- Affected nodes (new-graph Downstream from changes) are locally rechecked. -/
  affectedRechecked :
    ∀ n ∈ g'.nodes,
      Affected g' changes n.id →
      nodeChecks check n σ' (certs' n.id)
  /-- Unaffected nodes reuse an eligible, authoritative prior-cache entry. -/
  unaffectedReused :
    ∀ n ∈ g'.nodes,
      Unaffected g' changes n.id →
        ∃ e ∈ vs.cache.entries,
          reusePermitted e (obligationOf n (depValues n σ')) ∧
          certs' n.id = e.cert ∧
          σ' n.id = e.cert.output

/-- Logical acceptance: only the per-node evidence premises (no change accounting).
Useful when an algorithm has already established those premises. -/
structure LogicalAccept (check : LocalCheck) (vs : ValidState)
    (g' : Graph) (changes : ChangeSet) (σ' : Assignment)
    (certs' : NodeId → Certificate) where
  prior : FreshWitness check vs
  affectedRechecked :
    ∀ n ∈ g'.nodes,
      Affected g' changes n.id →
      nodeChecks check n σ' (certs' n.id)
  unaffectedReused :
    ∀ n ∈ g'.nodes,
      Unaffected g' changes n.id →
        ∃ e ∈ vs.cache.entries,
          reusePermitted e (obligationOf n (depValues n σ')) ∧
          certs' n.id = e.cert ∧
          σ' n.id = e.cert.output

def IncrementalAccept.toLogical
    {check : LocalCheck} {vs : ValidState}
    {g' : Graph} {changes : ChangeSet} {σ' : Assignment}
    {certs' : NodeId → Certificate}
    (h : IncrementalAccept check vs g' changes σ' certs') :
    LogicalAccept check vs g' changes σ' certs' where
  prior := h.prior
  affectedRechecked := h.affectedRechecked
  unaffectedReused := h.unaffectedReused

end PCSIncremental
