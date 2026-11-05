import CertNum.Interval.Arithmetic
import Mathlib.Tactic

/-!
# Multiplication soundness (corner extrema)
-/

namespace CertNum.Interval

/-- For `y ∈ [c,d]`, `a*y` lies between `min(a*c,a*d)` and `max(a*c,a*d)`. -/
private theorem mul_const_mem_endpoints (a c d y : ℚ) (hc : c ≤ y) (hd : y ≤ d) :
    ratMin (a * c) (a * d) ≤ a * y ∧ a * y ≤ ratMax (a * c) (a * d) := by
  cases le_total 0 a with
  | inl ha =>
    -- 0 ≤ a
    constructor
    · exact le_trans (ratMin_le_left (a * c) (a * d)) (mul_le_mul_of_nonneg_left hc ha)
    · exact le_trans (mul_le_mul_of_nonneg_left hd ha) (le_ratMax_right (a * c) (a * d))
  | inr ha =>
    -- a ≤ 0
    constructor
    · exact le_trans (ratMin_le_right (a * c) (a * d)) (mul_le_mul_of_nonpos_left hd ha)
    · exact le_trans (mul_le_mul_of_nonpos_left hc ha) (le_ratMax_left (a * c) (a * d))

private theorem mul_le_corners {a b c d x y : ℚ}
    (ha : a ≤ x) (hb : x ≤ b) (hc : c ≤ y) (hd : y ≤ d) :
    x * y ≤ ratMax4 (a * c) (a * d) (b * c) (b * d) := by
  cases le_total 0 y with
  | inl hy =>
    -- 0 ≤ y ⇒ x*y ≤ b*y
    have hxy : x * y ≤ b * y := mul_le_mul_of_nonneg_right hb hy
    have hby := mul_const_mem_endpoints b c d y hc hd
    have hmax : ratMax (b * c) (b * d) ≤ ratMax4 (a * c) (a * d) (b * c) (b * d) := by
      unfold ratMax4
      exact le_ratMax_right _ _
    exact le_trans hxy (le_trans hby.2 hmax)
  | inr hy =>
    -- y ≤ 0 ⇒ x*y ≤ a*y
    have hxy : x * y ≤ a * y := mul_le_mul_of_nonpos_right ha hy
    have hay := mul_const_mem_endpoints a c d y hc hd
    have hmax : ratMax (a * c) (a * d) ≤ ratMax4 (a * c) (a * d) (b * c) (b * d) := by
      unfold ratMax4
      exact le_ratMax_left _ _
    exact le_trans hxy (le_trans hay.2 hmax)

private theorem mul_ge_corners {a b c d x y : ℚ}
    (ha : a ≤ x) (hb : x ≤ b) (hc : c ≤ y) (hd : y ≤ d) :
    ratMin4 (a * c) (a * d) (b * c) (b * d) ≤ x * y := by
  cases le_total 0 y with
  | inl hy =>
    -- 0 ≤ y ⇒ a*y ≤ x*y
    have hxy : a * y ≤ x * y := mul_le_mul_of_nonneg_right ha hy
    have hay := mul_const_mem_endpoints a c d y hc hd
    have hmin : ratMin4 (a * c) (a * d) (b * c) (b * d) ≤ ratMin (a * c) (a * d) := by
      unfold ratMin4
      exact ratMin_le_left _ _
    exact le_trans hmin (le_trans hay.1 hxy)
  | inr hy =>
    -- y ≤ 0 ⇒ b*y ≤ x*y
    have hxy : b * y ≤ x * y := mul_le_mul_of_nonpos_right hb hy
    have hby := mul_const_mem_endpoints b c d y hc hd
    have hmin : ratMin4 (a * c) (a * d) (b * c) (b * d) ≤ ratMin (b * c) (b * d) := by
      unfold ratMin4
      exact ratMin_le_right _ _
    exact le_trans hmin (le_trans hby.1 hxy)

theorem mem_mul {x y : ℚ} {I J : Interval}
    (hx : x ∈ᵢ I) (hy : y ∈ᵢ J) : (x * y) ∈ᵢ mul I J := by
  cases I with
  | empty => exact False.elim hx
  | nonempty a b hab =>
    cases J with
    | empty => exact False.elim hy
    | nonempty c d hcd =>
      obtain ⟨ha, hb⟩ := hx
      obtain ⟨hc, hd⟩ := hy
      dsimp [mul]
      exact mem_mk'_of_le (mul_ge_corners ha hb hc hd) (mul_le_corners ha hb hc hd)

end CertNum.Interval
