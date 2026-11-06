import Init

/-!
Research-only conditional cache soundness.

The checker, policy, source observation and COMPLETE dependency projection are
parameters. The result does not prove that a Python parser discovers all semantic
dependencies, that a mutable filesystem is immutable, or that a digest is
collision-free. No submitted source or neural model supplies checking authority.
-/
set_option autoImplicit false
namespace PCSScientificIntake

variable {Key Byte Policy Result : Type}

/-- Ordered exact source inputs, preserving dependency names and bytes. -/
def project (snapshot : Key → Byte) : List Key → List (Key × Byte)
  | [] => []
  | key :: rest => (key, snapshot key) :: project snapshot rest

/-- Equality is required only on the declared complete input projection. -/
theorem projection_congr (oldSnapshot newSnapshot : Key → Byte)
    (keys : List Key)
    (same : ∀ key, key ∈ keys → oldSnapshot key = newSnapshot key) :
    project oldSnapshot keys = project newSnapshot keys := by
  induction keys with
  | nil => rfl
  | cons key rest ih =>
    have head := same key (List.Mem.head rest)
    have tail : ∀ k, k ∈ rest → oldSnapshot k = newSnapshot k := by
      intro k member
      exact same k (List.Mem.tail key member)
    simp only [project]
    rw [head, ih tail]

/-- A fixed pure checker can reuse its result when all its inputs are equal. -/
theorem fixed_checker_reuse
    (checker : Policy → List (Key × Byte) → Result) (policy : Policy)
    (oldSnapshot newSnapshot : Key → Byte) (completeInputs : List Key)
    (same : ∀ key, key ∈ completeInputs → oldSnapshot key = newSnapshot key) :
    checker policy (project oldSnapshot completeInputs) =
      checker policy (project newSnapshot completeInputs) := by
  rw [projection_congr oldSnapshot newSnapshot completeInputs same]

/-- Reuse across two records additionally requires the same fixed policy. -/
theorem policy_bound_reuse
    (checker : Policy → List (Key × Byte) → Result)
    (oldPolicy newPolicy : Policy) (samePolicy : oldPolicy = newPolicy)
    (oldSnapshot newSnapshot : Key → Byte) (completeInputs : List Key)
    (same : ∀ key, key ∈ completeInputs → oldSnapshot key = newSnapshot key) :
    checker oldPolicy (project oldSnapshot completeInputs) =
      checker newPolicy (project newSnapshot completeInputs) := by
  rw [samePolicy]
  exact fixed_checker_reuse checker newPolicy oldSnapshot newSnapshot completeInputs same

/-- Reflexive transitive dependency reachability in an arbitrary finite graph. -/
inductive Reachable (dependencies : Key → List Key) (root : Key) : Key → Prop
  | root : Reachable dependencies root root
  | dependency {prior next : Key} : Reachable dependencies root prior →
      next ∈ dependencies prior → Reachable dependencies root next

/-- A dependency-closed retained set contains every transitively required node. -/
theorem closed_contains_reachable (dependencies : Key → List Key)
    (retained : List Key)
    (closed : ∀ prior, prior ∈ retained →
      ∀ next, next ∈ dependencies prior → next ∈ retained)
    (root : Key) (rootRetained : root ∈ retained)
    (leaf : Key) (path : Reachable dependencies root leaf) :
    leaf ∈ retained := by
  induction path with
  | root => exact rootRetained
  | @dependency prior next previous edge ih => exact closed prior ih next edge

/-- Changes outside a closed complete dependency set do not invalidate the
result of a fixed pure checker. Completeness is an explicit premise. -/
theorem closed_dependency_reuse
    (checker : Policy → List (Key × Byte) → Result) (policy : Policy)
    (dependencies : Key → List Key) (root : Key) (retained : List Key)
    (rootRetained : root ∈ retained)
    (closed : ∀ prior, prior ∈ retained →
      ∀ next, next ∈ dependencies prior → next ∈ retained)
    (completeInputs : List Key)
    (complete : ∀ key, key ∈ completeInputs → Reachable dependencies root key)
    (oldSnapshot newSnapshot : Key → Byte)
    (sameRetained : ∀ key, key ∈ retained → oldSnapshot key = newSnapshot key) :
    checker policy (project oldSnapshot completeInputs) =
      checker policy (project newSnapshot completeInputs) := by
  apply fixed_checker_reuse checker policy oldSnapshot newSnapshot completeInputs
  intro key member
  exact sameRetained key
    (closed_contains_reachable dependencies retained closed root rootRetained key
      (complete key member))

end PCSScientificIntake

#print axioms PCSScientificIntake.projection_congr
#print axioms PCSScientificIntake.fixed_checker_reuse
#print axioms PCSScientificIntake.policy_bound_reuse
#print axioms PCSScientificIntake.closed_contains_reachable
#print axioms PCSScientificIntake.closed_dependency_reuse
