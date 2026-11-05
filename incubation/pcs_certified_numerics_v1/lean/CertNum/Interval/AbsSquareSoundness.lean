import CertNum.Interval.Arithmetic
import Mathlib.Tactic

/-!
# Absolute value and square soundness
-/

namespace CertNum.Interval

theorem mem_abs {x : ℚ} {I : Interval} (hx : x ∈ᵢ I) : |x| ∈ᵢ abs I := by
  cases I with
  | empty => exact False.elim hx
  | nonempty lo hi wf =>
    obtain ⟨hlo, hhi⟩ := hx
    dsimp [abs]
    split_ifs with hpos hneg
    · have hx0 : 0 ≤ x := le_trans hpos hlo
      rw [abs_of_nonneg hx0]
      exact mem_mk'_of_le hlo hhi
    · have hx0 : x ≤ 0 := le_trans hhi hneg
      rw [abs_of_nonpos hx0]
      exact mem_mk'_of_le (neg_le_neg hhi) (neg_le_neg hlo)
    · have hmax : |x| ≤ ratMax (-lo) hi := by
        cases le_total x 0 with
        | inl hxle =>
          rw [abs_of_nonpos hxle]
          exact le_trans (neg_le_neg hlo) (le_ratMax_left (-lo) hi)
        | inr hxge =>
          rw [abs_of_nonneg hxge]
          exact le_trans hhi (le_ratMax_right (-lo) hi)
      exact mem_mk'_of_le (abs_nonneg x) hmax

private theorem sq_le_sq_of_abs_le {a b : ℚ} (h : |a| ≤ |b|) : a * a ≤ b * b := by
  have ha := abs_nonneg a
  have := mul_self_le_mul_self ha h
  simpa [sq, abs_mul_abs_self] using this

theorem mem_square {x : ℚ} {I : Interval} (hx : x ∈ᵢ I) : (x * x) ∈ᵢ square I := by
  cases I with
  | empty => exact False.elim hx
  | nonempty lo hi wf =>
    obtain ⟨hlo, hhi⟩ := hx
    dsimp [square]
    split_ifs with hpos hneg
    · have hx0 : 0 ≤ x := le_trans hpos hlo
      exact mem_mk'_of_le (mul_self_le_mul_self hpos hlo) (mul_self_le_mul_self hx0 hhi)
    · have hx0 : x ≤ 0 := le_trans hhi hneg
      have hlower : hi * hi ≤ x * x := by
        apply sq_le_sq_of_abs_le
        rw [abs_of_nonpos hneg, abs_of_nonpos hx0]
        exact neg_le_neg hhi
      have hupper : x * x ≤ lo * lo := by
        apply sq_le_sq_of_abs_le
        rw [abs_of_nonpos hx0, abs_of_nonpos (le_trans hlo hx0)]
        exact neg_le_neg hlo
      exact mem_mk'_of_le hlower hupper
    · have hge : 0 ≤ x * x := mul_self_nonneg x
      have hle : x * x ≤ ratMax (lo * lo) (hi * hi) := by
        cases le_total x 0 with
        | inl hxle =>
          have : x * x ≤ lo * lo := by
            apply sq_le_sq_of_abs_le
            rw [abs_of_nonpos hxle, abs_of_nonpos (le_trans hlo hxle)]
            exact neg_le_neg hlo
          exact le_trans this (le_ratMax_left (lo * lo) (hi * hi))
        | inr hxge =>
          exact le_trans (mul_self_le_mul_self hxge hhi)
            (le_ratMax_right (lo * lo) (hi * hi))
      exact mem_mk'_of_le hge hle

end CertNum.Interval
