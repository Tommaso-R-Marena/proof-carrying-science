import Std

/-!
Writ/12 research model: proof-carrying provenance checks.

The program computes a finite security-label edge check for explicit lineage.
The claims depend on every real derivation edge being represented, correct
root classifications, no implicit flows, no unauthorized declassification, and
a trusted host enforcing the checked condition. This file does not prove the
Python validator implements this model.
-/
namespace Writ12

/-- Declarative condition: children are at least as sensitive as every parent. -/
def FlowSound {n : Nat} (parents : Fin n → List (Fin n)) (label : Fin n → Nat) : Prop :=
  ∀ (child parent : Fin n), parent ∈ parents child → label parent ≤ label child

/-- Executable finite check; the parent lists are provided by a trusted caller. -/
def CheckFlow {n : Nat} (parents : Fin n → List (Fin n)) (label : Fin n → Nat) : Bool :=
  (List.finRange n).all (fun child =>
    (parents child).all (fun parent => decide (label parent ≤ label child)))

/-- The executable checker checks exactly the declarative edge condition. -/
theorem checkFlow_iff {n : Nat} (parents : Fin n → List (Fin n))
    (label : Fin n → Nat) : CheckFlow parents label = true ↔ FlowSound parents label := by
  simp [CheckFlow, FlowSound, List.all_eq_true, List.mem_finRange]

/-- A root can reach a child through any finite number of declared edges. -/
inductive Reaches {n : Nat} (parents : Fin n → List (Fin n)) : Fin n → Fin n → Prop where
  | refl (root : Fin n) : Reaches parents root root
  | step {root middle child : Fin n}
      (prev : Reaches parents root middle)
      (edge : middle ∈ parents child) : Reaches parents root child

/-- Sensitivity cannot be decreased along an arbitrarily long derivation. -/
theorem nonlaundering {n : Nat} {parents : Fin n → List (Fin n)}
    {label : Fin n → Nat} (safe : FlowSound parents label)
    {root child : Fin n} (path : Reaches parents root child) :
    label root ≤ label child := by
  induction path with
  | refl _ => exact Nat.le_refl _
  | step prev edge ih => exact Nat.le_trans ih (safe _ _ edge)

/-- No descendant of a secret root can be released to a lower sink without
    an explicitly authorized downgrade outside this no-declassification model. -/
theorem forbidden_release {n : Nat} {parents : Fin n → List (Fin n)}
    {label : Fin n → Nat} (safe : FlowSound parents label)
    {root child : Fin n} (path : Reaches parents root child)
    {sink : Nat} (protected : sink < label root) :
    ¬ label child ≤ sink := by
  intro release
  exact Nat.not_le_of_gt protected (Nat.le_trans (nonlaundering safe path) release)

/-- Actual acceptance of a restricted sink is evidence that every ancestor of
    the output respects that sink classification, under the edge assumption. -/
theorem checked_release_sound {n : Nat} {parents : Fin n → List (Fin n)}
    {label : Fin n → Nat} (checked : CheckFlow parents label = true)
    {root child : Fin n} (path : Reaches parents root child)
    {sink : Nat} (release : label child ≤ sink) : label root ≤ sink := by
  exact Nat.le_trans (nonlaundering ((checkFlow_iff parents label).mp checked) path) release

end Writ12
