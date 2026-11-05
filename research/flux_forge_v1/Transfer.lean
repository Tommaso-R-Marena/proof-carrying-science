import Mathlib.Data.Rat.Cast.Order
import Mathlib.Tactic.FieldSimp
import Mathlib.Tactic.Linarith
import Mathlib.Tactic.Ring

/-!
Exact two-coordinate amount transfers. This mathematical interval describes
preservation of bounds and nonincrease of weighted pair energy relative to the
unmodified pair. It does not prove any browser, wire codec, physical model or
PCS authority correct. Other coordinates are unchanged by the intended use.
-/
set_option autoImplicit false
namespace PCSFluxForge

def energy (v w x y : ℚ) : ℚ := v * x ^ 2 + w * y ^ 2
def root (v w x y : ℚ) : ℚ := 2 * v * w * (x - y) / (v + w)

theorem amount (v w x y t : ℚ) (hv : v ≠ 0) (hw : w ≠ 0) :
    v * (x - t / v) + w * (y + t / w) = v * x + w * y := by
  field_simp [hv, hw]
  ring

theorem energy_delta (v w x y t : ℚ) (hv : 0 < v) (hw : 0 < w) :
    energy v w (x - t / v) (y + t / w) - energy v w x y =
      ((v + w) / (v * w)) * (t - 0) * (t - root v w x y) := by
  unfold energy root
  field_simp [ne_of_gt hv, ne_of_gt hw, ne_of_gt (add_pos hv hw)]
  ring

theorem energy_interval (v w x y t : ℚ) (hv : 0 < v) (hw : 0 < w) :
    energy v w (x - t / v) (y + t / w) ≤ energy v w x y ↔
      min 0 (root v w x y) ≤ t ∧ t ≤ max 0 (root v w x y) := by
  rw [← sub_nonpos, energy_delta v w x y t hv hw]
  have hc : 0 < (v + w) / (v * w) := div_pos (add_pos hv hw) (mul_pos hv hw)
  rw [mul_assoc]
  have hm (z : ℚ) : ((v + w) / (v * w)) * z ≤ 0 ↔ z ≤ 0 := by
    constructor
    · intro h
      by_contra! hz
      have := mul_pos hc hz
      linarith
    · intro h
      exact mul_nonpos_of_nonneg_of_nonpos hc.le h
  rw [hm]
  by_cases hr : 0 ≤ root v w x y
  · rw [min_eq_left hr, max_eq_right hr]
    exact sub_mul_sub_nonpos_iff t hr
  · have hr' : root v w x y ≤ 0 := le_of_not_ge hr
    rw [min_eq_right hr', max_eq_left hr', mul_comm]
    exact sub_mul_sub_nonpos_iff t hr'

theorem bounds_interval (v w x y t lo hi : ℚ) (hv : 0 < v) (hw : 0 < w) :
    (lo ≤ x - t / v ∧ x - t / v ≤ hi) ∧
      (lo ≤ y + t / w ∧ y + t / w ≤ hi) ↔
    max (v * (x - hi)) (w * (lo - y)) ≤ t ∧
      t ≤ min (v * (x - lo)) (w * (hi - y)) := by
  have hxlo : lo ≤ x - t / v ↔ t ≤ v * (x - lo) := by
    rw [le_sub_iff_add_le, ← le_sub_iff_add_le', div_le_iff₀ hv]
    ring_nf
  have hxhi : x - t / v ≤ hi ↔ v * (x - hi) ≤ t := by
    rw [sub_le_iff_le_add, ← sub_le_iff_le_add', le_div_iff₀ hv]
    ring_nf
  have hylo : lo ≤ y + t / w ↔ w * (lo - y) ≤ t := by
    rw [add_comm y, ← sub_le_iff_le_add, le_div_iff₀ hw]
    ring_nf
  have hyhi : y + t / w ≤ hi ↔ t ≤ w * (hi - y) := by
    rw [← le_sub_iff_add_le', div_le_iff₀ hw]
    ring_nf
  rw [hxlo, hxhi, hylo, hyhi, max_le_iff, le_min_iff]
  tauto

theorem feasible_interval (v w x y t lo hi : ℚ) (hv : 0 < v) (hw : 0 < w) :
    (((lo ≤ x - t / v ∧ x - t / v ≤ hi) ∧
       (lo ≤ y + t / w ∧ y + t / w ≤ hi)) ∧
      energy v w (x - t / v) (y + t / w) ≤ energy v w x y) ↔
    max (min 0 (root v w x y)) (max (v * (x - hi)) (w * (lo - y))) ≤ t ∧
      t ≤ min (max 0 (root v w x y)) (min (v * (x - lo)) (w * (hi - y))) := by
  rw [bounds_interval v w x y t lo hi hv hw, energy_interval v w x y t hv hw]
  simp only [max_le_iff, le_min_iff]
  tauto

theorem nonzero_changes (v x t : ℚ) (hv : v ≠ 0) (ht : t ≠ 0) :
    x - t / v ≠ x := by
  intro h
  have hz : t / v = 0 := by linarith
  exact (div_ne_zero ht hv) hz

end PCSFluxForge
