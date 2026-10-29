/-
  Exact Nat conversion facts for restricted clearance units.
  1 mL/min = 60 mL/h = 6/100 L/h  (equivalently 3/50).
  This is discrete arithmetic — not a floating-point semantics proof.
-/
namespace PcsNext.Units

/-- Scale factor numerator/denominator: mL/min → L/h is * 3/50 (= 0.06). -/
def mL_per_min_to_L_per_h_num : Nat := 3
def mL_per_min_to_L_per_h_den : Nat := 50

theorem mL_per_min_factor_pos : 0 < mL_per_min_to_L_per_h_den := by
  decide

/-- Converting v mL/min yields (v * 3) / 50 litres per hour (exact on Nats). -/
def convert_mL_per_min (v : Nat) : Nat × Nat :=
  (v * mL_per_min_to_L_per_h_num, mL_per_min_to_L_per_h_den)

theorem convert_mL_per_min_one : convert_mL_per_min 1 = (3, 50) := by
  simp [convert_mL_per_min, mL_per_min_to_L_per_h_num, mL_per_min_to_L_per_h_den]

theorem convert_mL_per_min_zero : convert_mL_per_min 0 = (0, 50) := by
  simp [convert_mL_per_min, mL_per_min_to_L_per_h_num, mL_per_min_to_L_per_h_den]

/-- Identity: L/h → L/h leaves the value unchanged. -/
def convert_L_per_h (v : Nat) : Nat := v

theorem convert_L_per_h_id (v : Nat) : convert_L_per_h v = v := rfl

/-- Distinct unit tags cannot be silently identified: mL/min factor ≠ 1. -/
theorem mL_per_min_not_identity_scale :
    mL_per_min_to_L_per_h_num ≠ mL_per_min_to_L_per_h_den := by
  decide

end PcsNext.Units
