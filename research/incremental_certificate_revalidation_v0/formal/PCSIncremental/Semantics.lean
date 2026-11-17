import PCSIncremental.Invalidation
import PCSIncremental.Cache

/-!
# Local checkers, fresh verification, and incremental acceptance
-/
namespace PCSIncremental

/-- A local verifier predicate: operation, version, policy, dependency values,
certificate payload, and claimed output. -/
abbrev LocalCheck :=
  OpId → VersionId → PolicyId → List Value → CertPayload → Value → Bool

/-- Assignment of outputs to node ids. -/
abbrev Assignment := NodeId → Value

/-- Resolve dependency outputs for a node under an assignment. -/
def depValues (n : Node) (σ : Assignment) : List Value :=
  n.deps.map σ

/-- Local check succeeds for a node under assignment and certificate. -/
def nodeChecks (check : LocalCheck) (n : Node) (σ : Assignment) (c : Certificate) : Prop :=
  check n.op n.version n.policy (depValues n σ) c.payload c.output = true
  ∧ σ n.id = c.output

/-- Fresh verification: every node has a certificate that locally checks. -/
def FreshValid (check : LocalCheck) (g : Graph) (σ : Assignment)
    (certs : NodeId → Certificate) : Prop :=
  ∀ n ∈ g.nodes, nodeChecks check n σ (certs n.id)

/-- Incremental decision for one node. -/
inductive NodeDecision where
  | reused (e : CacheEntry)
  | rechecked (c : Certificate)
  | rejected
  deriving Repr, DecidableEq

/-- Incremental verifier state after applying changes. -/
structure IncrementalResult where
  accepted : Bool
  outputs : Assignment
  reused : List NodeId
  rechecked : List NodeId
  rejected : List NodeId

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

/-- Apply a node-level definition change: replace nodes whose ids are in `changes`
with updated nodes from `g'`, requiring ids to match. -/
def sameTopologyIds (g g' : Graph) : Prop :=
  g.ids = g'.ids

/-- Incremental acceptance predicate (abstract):
unaffected nodes may be reused only with `reusePermitted`; affected nodes must
pass a fresh local check; the global assignment must be FreshValid. -/
structure IncrementalAccept (check : LocalCheck) (vs : ValidState)
    (g' : Graph) (changes : ChangeSet) (σ' : Assignment)
    (certs' : NodeId → Certificate) (cache' : Cache) : Prop where
  fresh' : FreshValid check g' σ' certs'
  /-- Reuse discipline: if a node is unaffected and we claim reuse from cache',
  the entry must be reuse-permitted for the current obligation. -/
  reuseDiscipline :
    ∀ n ∈ g'.nodes,
      Unaffected vs.graph changes n.id →
      (∃ e ∈ cache'.entries,
        e.key = obligationOf n (depValues n σ') ∧
        e.cert = certs' n.id) →
      ∃ e ∈ cache'.entries,
        reusePermitted e (obligationOf n (depValues n σ')) ∧
        e.cert = certs' n.id
  /-- Affected nodes are witnessed by the new certificates under σ'. -/
  affectedRechecked :
    ∀ n ∈ g'.nodes,
      Affected vs.graph changes n.id →
      nodeChecks check n σ' (certs' n.id)

end PCSIncremental
