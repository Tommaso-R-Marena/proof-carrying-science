import PCSIncremental.Certificate
import PCSIncremental.Dependency

/-!
# Cache lookup, eligibility, and authority

Finding a matching cache entry never by itself establishes mathematical validity.
Authority requires an explicit prior-acceptance witness under a trust model.
-/
namespace PCSIncremental

/-- A stored cache entry. `priorAccepted` records that a trusted verifier accepted it. -/
structure CacheEntry where
  key : ObligationKey
  cert : Certificate
  priorAccepted : Bool
  deriving Repr, DecidableEq, Inhabited

/-- Finite cache as a list of entries. -/
structure Cache where
  entries : List CacheEntry
  deriving Repr, DecidableEq, Inhabited

/-- Lookup by exact obligation key. -/
def Cache.lookup (c : Cache) (k : ObligationKey) : Option CacheEntry :=
  c.entries.find? (fun e => decide (e.key = k))

/-- Lookup is only a retrieval; it does not imply validity. -/
def lookupDoesNotProveValidity (_c : Cache) (_k : ObligationKey) : Prop :=
  True  -- documentary: presence is not a theorem of correctness

/-- Authority: entry was previously accepted. -/
def hasAuthority (e : CacheEntry) : Prop :=
  e.priorAccepted = true

/-- Safe reuse premise: eligible key and prior authority. -/
def reusePermitted (e : CacheEntry) (current : ObligationKey) : Prop :=
  eligible e.key current ∧ hasAuthority e

theorem reuse_requires_authority
    (e : CacheEntry) (current : ObligationKey)
    (h : reusePermitted e current) : hasAuthority e :=
  h.2

theorem reuse_requires_eligibility
    (e : CacheEntry) (current : ObligationKey)
    (h : reusePermitted e current) : eligible e.key current :=
  h.1

/-- Non-escalation: an entry without prior acceptance cannot satisfy reusePermitted. -/
theorem no_authority_no_reuse (e : CacheEntry) (current : ObligationKey)
    (h : e.priorAccepted = false) : ¬ reusePermitted e current := by
  intro hr
  have := hr.2
  unfold hasAuthority at this
  simp [h] at this

/-- A trusted prior verification state: graph, assignments, and authoritative cache. -/
structure ValidState where
  graph : Graph
  /-- Output assignment for each node id present in the graph. -/
  outputs : NodeId → Value
  cache : Cache
  /-- Every cache entry marked accepted was checked under `graph`. -/
  wellFormed : WellFormedIds graph
  acyclic : Acyclic graph

end PCSIncremental
