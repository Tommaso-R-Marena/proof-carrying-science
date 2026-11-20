import ObservationAdequacy

/-! Observation channels with nondeterministic errors, including delayed reports
whose later compatibility set refines an earlier one. -/
set_option autoImplicit false
namespace RobustObservation

/-- Reachability is supplied by the finite domain. Compatibility may relate one
underlying episode to many reports and one report to many underlying episodes. -/
def monitor {E O : Type} (rows : List E) (canReport : E → O → Bool)
    (label : E → Bool) (o : O) : Option Bool :=
  ObservationAdequacy.monitor rows (fun e => canReport e o) label true

theorem exact_verdict {E O : Type} (rows : List E) (canReport : E → O → Bool)
    (label : E → Bool) (o : O) (b : Bool) :
    monitor rows canReport label o = some b ↔
      (∃ e ∈ rows, canReport e o = true) ∧
      ∀ e ∈ rows, canReport e o = true → label e = b :=
  ObservationAdequacy.monitor_exact ..

/-- Later/more reliable evidence may discard possibilities. Consistency of the
new report matters since the executable monitor abstains on an empty fiber. -/
theorem refinement {E O P : Type} (rows : List E) (label : E → Bool)
    (early : E → O → Bool) (late : E → P → Bool) (o : O) (p : P) (b : Bool)
    (nested : ∀ e ∈ rows, late e p = true → early e o = true)
    (reachable : ∃ e ∈ rows, late e p = true)
    (known : monitor rows early label o = some b) :
    monitor rows late label p = some b := by
  apply (exact_verdict ..).2
  exact ⟨reachable, fun e h r => ((exact_verdict ..).1 known).2 e h (nested e h r)⟩

/-- A fixed-length report has one Boolean channel per coordinate. -/
def Word : Nat → Type
  | 0 => Unit
  | n + 1 => Bool × Word n

def distance : (n : Nat) → Word n → Word n → Nat
  | 0, _, _ => 0
  | n + 1, x, y => (if x.1 = y.1 then 0 else 1) + distance n x.2 y.2

/-- Sharp confusability threshold for *unequal* integer error budgets. -/
theorem balls_intersect_iff (n : Nat) (x y : Word n) (a b : Nat) :
    (∃ z : Word n, distance n x z ≤ a ∧ distance n y z ≤ b) ↔
    distance n x y ≤ a + b := by
  induction n generalizing a b with
  | zero => simp [distance]; exact ⟨(), trivial⟩
  | succ n ih =>
    obtain ⟨x, xs⟩ := x
    obtain ⟨y, ys⟩ := y
    constructor
    · rintro ⟨⟨z, zs⟩, hx, hy⟩
      have tail := (ih xs ys (distance n xs zs) (distance n ys zs)).mp
        ⟨zs, Nat.le_refl _, Nat.le_refl _⟩
      cases x <;> cases y <;> cases z <;> simp [distance] at * <;> omega
    · intro h
      by_cases same : x = y
      · subst y
        obtain ⟨zs, hx, hy⟩ := (ih xs ys a b).mpr (by simpa [distance] using h)
        exact ⟨(x, zs), by simpa [distance], by simpa [distance]⟩
      · have opposite : y ≠ x := Ne.symm same
        simp [distance, same] at h
        cases a with
        | zero =>
          obtain ⟨zs, hx, hy⟩ := (ih xs ys 0 (b - 1)).mpr (by omega)
          exact ⟨(x, zs), by simpa [distance] using hx, by simp [distance, opposite]; omega⟩
        | succ a =>
          obtain ⟨zs, hx, hy⟩ := (ih xs ys a b).mpr (by omega)
          exact ⟨(y, zs), by simp [distance, same]; omega, by simpa [distance]⟩

def compatible {E : Type} {n : Nat} (encode : E → Word n) (radius : E → Nat)
    (e : E) (z : Word n) : Bool := decide (distance n (encode e) z ≤ radius e)

/-- A finite receiver is total and correct on every permitted corrupted report
exactly when every cross-label pair has disjoint Hamming balls. The necessity
argument also applies to *any* deterministic monitor issuing a verdict there. -/
theorem robust_monitor_iff {E : Type} {n : Nat} (rows : List E) (label : E → Bool)
    (encode : E → Word n) (radius : E → Nat) :
    (∀ e ∈ rows, ∀ z, distance n (encode e) z ≤ radius e →
      monitor rows (compatible encode radius) label z = some (label e)) ↔
    ∀ e ∈ rows, ∀ f ∈ rows, label e ≠ label f →
      radius e + radius f < distance n (encode e) (encode f) := by
  constructor
  · intro total e he f hf diff
    apply Nat.lt_of_not_ge
    intro near
    obtain ⟨z, ez, fz⟩ := (balls_intersect_iff ..).2 near
    exact diff (Option.some.inj ((total e he z ez).symm.trans (total f hf z fz)))
  · intro separated e he z ez
    apply (exact_verdict ..).2
    refine ⟨⟨e, he, by simpa [compatible] using ez⟩, ?_⟩
    intro f hf fz
    by_cases diff : label f = label e
    · exact diff
    have near := (balls_intersect_iff ..).1 ⟨z, ez, by simpa [compatible] using fz⟩
    have far := separated e he f hf (Ne.symm diff)
    omega

/-- If the separation threshold fails, no observation-only function can issue a
correct verdict on every reachable corruption of both episodes. No finite-table
assumption is needed for this impossibility direction. -/
theorem indistinguishable_pair {n : Nat} (x y : Word n) (a b : Nat) (p q : Bool)
    (different : p ≠ q) (near : distance n x y ≤ a + b) :
    ¬ ∃ m : Word n → Option Bool,
      (∀ z, distance n x z ≤ a → m z = some p) ∧
      (∀ z, distance n y z ≤ b → m z = some q) := by
  obtain ⟨z, hx, hy⟩ := (balls_intersect_iff ..).2 near
  rintro ⟨m, left, right⟩
  exact different (Option.some.inj ((left z hx).symm.trans (right z hy)))

/-- Quiet histories emit no effect. A delayed positive history first emits one at
its actual deadline. Completeness at a *single* observation time precisely
requires a uniform bound on all allowed deadlines, even on an infinite domain. -/
theorem deadline_iff (allowed : Nat → Prop) (t : Nat) :
    (∃ decode : Bool → Option Bool, decode false = some false ∧
      ∀ d, allowed d → decode (decide (d ≤ t)) = some true) ↔
    ∀ d, allowed d → d ≤ t := by
  constructor
  · rintro ⟨decode, quiet, sound⟩ d hd
    by_cases due : d ≤ t
    · exact due
    · have bad := sound d hd
      simp [due, quiet] at bad
  · intro bounded
    exact ⟨some, rfl, fun d hd => by simp [bounded d hd]⟩

/-- Every effect has an individual finite reporting time. With unbounded delays
the quiet history cannot be certified negative at any finite horizon by a
monitor that is correct on every allowed delayed-positive report at that time. -/
theorem no_uniform_timeout (t : Nat) :
    ¬ ∃ decode : Bool → Option Bool, decode false = some false ∧
      ∀ d, decode (decide (d ≤ t)) = some true := by
  rintro ⟨decode, quiet, all⟩
  have bound := (deadline_iff (fun _ => True) t).1 ⟨decode, quiet, fun d _ => all d⟩
  have bad := bound (t+1) trivial
  omega

#print axioms deadline_iff
#print axioms no_uniform_timeout
#print axioms exact_verdict
#print axioms refinement
#print axioms balls_intersect_iff
#print axioms robust_monitor_iff
#print axioms indistinguishable_pair
end RobustObservation
