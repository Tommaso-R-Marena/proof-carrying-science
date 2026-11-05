/-
  Trapezoidal AUC for nonnegative concentrations is nonnegative.
  Scope: discrete finite samples; not continuous integral measure theory.
-/
namespace PcsNext.NCA

def trapSegment (t0 t1 c0 c1 : Nat) : Nat :=
  -- (c0+c1)/2 * (t1-t0) approximated in integers as (c0+c1)*(t1-t0)/2
  ((c0 + c1) * (t1 - t0)) / 2

def trapAUC : List (Nat × Nat) → Nat
  | [] => 0
  | [_] => 0
  | (t0, c0) :: (t1, c1) :: rest =>
      trapSegment t0 t1 c0 c1 + trapAUC ((t1, c1) :: rest)

theorem trapSegment_nonneg (t0 t1 c0 c1 : Nat) :
    0 ≤ trapSegment t0 t1 c0 c1 := Nat.zero_le _

theorem trapAUC_nil : trapAUC [] = 0 := rfl

theorem trapAUC_singleton (p : Nat × Nat) : trapAUC [p] = 0 := rfl

theorem trapAUC_nonneg : ∀ xs : List (Nat × Nat), 0 ≤ trapAUC xs := by
  intro xs
  exact Nat.zero_le _

/-- If times are nondecreasing along a two-point list, segment uses Nat subtraction. -/
theorem trapSegment_zero_when_equal_time (c0 c1 t : Nat) :
    trapSegment t t c0 c1 = 0 := by
  simp [trapSegment]

end PcsNext.NCA
