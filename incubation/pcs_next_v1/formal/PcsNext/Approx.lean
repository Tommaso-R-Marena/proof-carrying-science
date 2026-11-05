/-
  Approximation is not equality.
-/
namespace PcsNext.Approx

def approx (a b bound : Nat) : Bool :=
  (Int.natAbs (Int.ofNat a - Int.ofNat b) ≤ bound)

def exactEq (a b : Nat) : Bool := decide (a = b)

theorem approx_1_2_1 : approx 1 2 1 = true := by
  decide

theorem not_exactEq_1_2 : exactEq 1 2 = false := by
  decide

/-- Approximation within a bound does not imply exact equality. -/
theorem approx_not_necessarily_eq :
    approx 1 2 1 = true ∧ exactEq 1 2 = false := by
  exact ⟨approx_1_2_1, not_exactEq_1_2⟩

end PcsNext.Approx
