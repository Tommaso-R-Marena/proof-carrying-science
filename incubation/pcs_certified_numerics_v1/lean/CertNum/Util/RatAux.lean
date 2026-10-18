import Mathlib.Data.Rat.Init
import Mathlib.Tactic.SplitIfs
import Mathlib.Tactic.Linarith

/-!
Auxiliary rational min/max helpers.
-/

namespace CertNum

def ratMin (a b : ℚ) : ℚ := if a ≤ b then a else b
def ratMax (a b : ℚ) : ℚ := if a ≤ b then b else a

theorem ratMin_le_left (a b : ℚ) : ratMin a b ≤ a := by
  unfold ratMin
  split_ifs with h
  · exact le_rfl
  · exact le_of_not_ge h

theorem ratMin_le_right (a b : ℚ) : ratMin a b ≤ b := by
  unfold ratMin
  split_ifs with h
  · exact h
  · exact le_rfl

theorem le_ratMax_left (a b : ℚ) : a ≤ ratMax a b := by
  unfold ratMax
  split_ifs with h
  · exact h
  · exact le_rfl

theorem le_ratMax_right (a b : ℚ) : b ≤ ratMax a b := by
  unfold ratMax
  split_ifs with h
  · exact le_rfl
  · exact le_of_not_ge h

theorem ratMin_le_ratMax (a b : ℚ) : ratMin a b ≤ ratMax a b := by
  unfold ratMin ratMax
  split_ifs <;> linarith

def ratMin4 (a b c d : ℚ) : ℚ := ratMin (ratMin a b) (ratMin c d)
def ratMax4 (a b c d : ℚ) : ℚ := ratMax (ratMax a b) (ratMax c d)

theorem le_of_ratMin4 (a b c d : ℚ) :
    ratMin4 a b c d ≤ a ∧ ratMin4 a b c d ≤ b ∧
    ratMin4 a b c d ≤ c ∧ ratMin4 a b c d ≤ d := by
  refine ⟨?_, ?_, ?_, ?_⟩ <;> unfold ratMin4 <;>
    first
    | exact (ratMin_le_left _ _).trans (ratMin_le_left a b)
    | exact (ratMin_le_left _ _).trans (ratMin_le_right a b)
    | exact (ratMin_le_right _ _).trans (ratMin_le_left c d)
    | exact (ratMin_le_right _ _).trans (ratMin_le_right c d)

theorem le_ratMax4 (a b c d : ℚ) :
    a ≤ ratMax4 a b c d ∧ b ≤ ratMax4 a b c d ∧
    c ≤ ratMax4 a b c d ∧ d ≤ ratMax4 a b c d := by
  refine ⟨?_, ?_, ?_, ?_⟩ <;> unfold ratMax4 <;>
    first
    | exact (le_ratMax_left a b).trans (le_ratMax_left _ _)
    | exact (le_ratMax_right a b).trans (le_ratMax_left _ _)
    | exact (le_ratMax_left c d).trans (le_ratMax_right _ _)
    | exact (le_ratMax_right c d).trans (le_ratMax_right _ _)

end CertNum
