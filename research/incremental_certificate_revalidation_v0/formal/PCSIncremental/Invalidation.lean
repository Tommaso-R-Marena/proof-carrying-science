import PCSIncremental.Dependency
import PCSIncremental.Cache

/-!
# Invalidation: affected dependency closure

The mathematical affected set is defined inductively. Correspondence of the
Python affected-closure algorithm to `Affected` is differentially tested.
-/

namespace PCSIncremental

abbrev ChangeSet := List NodeId

/-- Inductive characterization of the affected set. -/
def Affected (g : Graph) (changes : ChangeSet) (id : NodeId) : Prop :=
  ∃ root ∈ changes, Downstream g root id

theorem invalidation_sound
    (g : Graph) (changes : ChangeSet) (root leaf : NodeId)
    (hroot : root ∈ changes) (hpath : Downstream g root leaf) :
    Affected g changes leaf :=
  ⟨root, hroot, hpath⟩

theorem invalidation_complete
    (g : Graph) (changes : ChangeSet) (leaf : NodeId)
    (h : Affected g changes leaf) :
    ∃ root ∈ changes, Downstream g root leaf :=
  h

def Unaffected (g : Graph) (changes : ChangeSet) (id : NodeId) : Prop :=
  ¬ Affected g changes id

theorem unaffected_not_changed
    (g : Graph) (changes : ChangeSet) (id : NodeId)
    (h : Unaffected g changes id) : id ∉ changes := by
  intro hin
  exact h ⟨id, hin, Downstream.refl g id⟩

theorem affected_of_change
    (g : Graph) (changes : ChangeSet) (id : NodeId) (h : id ∈ changes) :
    Affected g changes id :=
  ⟨id, h, Downstream.refl g id⟩

/-- Single-step dependents of a node. -/
def collectDependents (g : Graph) (prior : NodeId) : List NodeId :=
  g.nodes.filterMap fun n =>
    if decide (prior ∈ n.deps) then some n.id else none

/-- If `next` depends on `prior` and `prior` is Affected, then `next` is Affected. -/
theorem affected_step
    (g : Graph) (changes : ChangeSet) (prior next : NodeId)
    (hp : Affected g changes prior) (hd : dependsOn g next prior) :
    Affected g changes next := by
  rcases hp with ⟨root, hr, path⟩
  exact ⟨root, hr, Downstream.cons path hd⟩

/-- Transport Downstream along equal dependsOn relations. -/
theorem downstream_transport
    (g₁ g₂ : Graph) (root leaf : NodeId)
    (hsame : ∀ next prior, dependsOn g₁ next prior ↔ dependsOn g₂ next prior)
    (h : Downstream g₁ root leaf) : Downstream g₂ root leaf := by
  induction h with
  | refl => exact Downstream.refl g₂ root
  | cons path hd ih =>
      exact Downstream.cons ih ((hsame _ _).1 hd)

/-- Syntactic sensitivity: Affected depends on declared edges, not semantic values. -/
theorem affected_topology_only
    (g₁ g₂ : Graph) (changes : ChangeSet)
    (hsame : ∀ next prior, dependsOn g₁ next prior ↔ dependsOn g₂ next prior)
    (id : NodeId) :
    Affected g₁ changes id ↔ Affected g₂ changes id := by
  constructor
  · intro h
    rcases h with ⟨root, hr, path⟩
    exact ⟨root, hr, downstream_transport g₁ g₂ root id hsame path⟩
  · intro h
    rcases h with ⟨root, hr, path⟩
    have hsame' : ∀ next prior, dependsOn g₂ next prior ↔ dependsOn g₁ next prior := by
      intro next prior; exact (hsame next prior).symm
    exact ⟨root, hr, downstream_transport g₂ g₁ root id hsame' path⟩


/-- `Affected` is the least predicate containing `changes` and closed under `dependsOn`. -/
theorem affected_least
    (g : Graph) (changes : ChangeSet) (P : NodeId → Prop)
    (hseeds : ∀ id ∈ changes, P id)
    (hstep : ∀ prior next, P prior → dependsOn g next prior → P next)
    (id : NodeId) (h : Affected g changes id) : P id := by
  rcases h with ⟨root, hr, path⟩
  have hroot : P root := hseeds root hr
  clear hr
  induction path with
  | refl => exact hroot
  | cons path' hd ih => exact hstep _ _ ih hd

end PCSIncremental
