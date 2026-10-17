import PCSReal.Calibration
set_option autoImplicit false
set_option format.width 1000000
open Finset PCSReal.Calibration

namespace PCSCalibrationReplay.M3
def abscissa (i : Fin 14) : ℚ := ([((5 : ℚ) / (1 : ℚ)), ((6 : ℚ) / (1 : ℚ)), ((7 : ℚ) / (1 : ℚ)), ((8 : ℚ) / (1 : ℚ)), ((9 : ℚ) / (1 : ℚ)), ((10 : ℚ) / (1 : ℚ)), ((11 : ℚ) / (1 : ℚ)), ((12 : ℚ) / (1 : ℚ)), ((13 : ℚ) / (1 : ℚ)), ((14 : ℚ) / (1 : ℚ)), ((15 : ℚ) / (1 : ℚ)), ((16 : ℚ) / (1 : ℚ)), ((17 : ℚ) / (1 : ℚ)), ((18 : ℚ) / (1 : ℚ))] : List ℚ).getD i.val 0
def x (i : Fin 14) (j : Fin 3) : ℚ := abscissa i ^ j.val
def y (i : Fin 14) : ℚ := ([((1 : ℚ) / (10 : ℚ)), ((23 : ℚ) / (100 : ℚ)), ((47 : ℚ) / (100 : ℚ)), ((19 : ℚ) / (25 : ℚ)), ((23 : ℚ) / (20 : ℚ)), ((33 : ℚ) / (20 : ℚ)), ((57 : ℚ) / (25 : ℚ)), ((309 : ℚ) / (100 : ℚ)), ((441 : ℚ) / (100 : ℚ)), ((751 : ℚ) / (100 : ℚ)), ((1377 : ℚ) / (100 : ℚ)), ((599 : ℚ) / (25 : ℚ)), ((1869 : ℚ) / (50 : ℚ)), ((2823 : ℚ) / (50 : ℚ))] : List ℚ).getD i.val 0
def b (j : Fin 3) : ℚ := ([((1612491 : ℚ) / (36400 : ℚ)), ((-1571137 : ℚ) / (145600 : ℚ)), ((88967 : ℚ) / (145600 : ℚ))] : List ℚ).getD j.val 0
def xr (i : Fin 14) (j : Fin 3) : ℝ := (x i j : ℝ)
def yr (i : Fin 14) : ℝ := (y i : ℝ)
def br (j : Fin 3) : ℝ := (b j : ℝ)
theorem normal_checked : fitCheck x y b = true := by decide +kernel
theorem residual_checked : loss x y b = ((1876203471 : ℚ) / (7280000 : ℚ)) := by decide +kernel
theorem global_optimum : ∀ c : Fin 3 → ℝ,
    (((1876203471 : ℚ) / (7280000 : ℚ)) : ℝ) ≤ loss xr yr c := by
  have hs : loss xr yr br = (((1876203471 : ℚ) / (7280000 : ℚ)) : ℝ) := by
    calc
      loss xr yr br = ((loss x y b : ℚ) : ℝ) := (cast_loss x y b).symm
      _ = (((1876203471 : ℚ) / (7280000 : ℚ)) : ℝ) := by
        simpa only [Rat.cast_div, Rat.cast_intCast, Rat.cast_ofNat, Rat.cast_neg]
          using congrArg (fun a : ℚ => (a : ℝ)) residual_checked
  simpa only [hs] using global_minimum xr yr br (fit_check_sound normal_checked)
theorem excludes_every_better_model (threshold : ℝ)
    (h : threshold < (((1876203471 : ℚ) / (7280000 : ℚ)) : ℝ)) :
    ∀ c : Fin 3 → ℝ, threshold < loss xr yr c := by
  intro c
  exact h.trans_le (global_optimum c)
theorem uniform_error_exclusion (ε : ℝ) (he : 0 ≤ ε)
    (hgap : (14 : ℝ) * ε ^ 2 < (((1876203471 : ℚ) / (7280000 : ℚ)) : ℝ)) :
    ¬ (∃ c : Fin 3 → ℝ, ∀ i, |yr i - prediction xr c i| ≤ ε) :=
  PCSReal.Calibration.uniform_error_exclusion xr yr (((1876203471 : ℚ) / (7280000 : ℚ)) : ℝ) ε
    global_optimum he (by simpa using hgap)
end PCSCalibrationReplay.M3

#print axioms PCSCalibrationReplay.M3.normal_checked
#print axioms PCSCalibrationReplay.M3.residual_checked
#print axioms PCSCalibrationReplay.M3.global_optimum
#print axioms PCSCalibrationReplay.M3.excludes_every_better_model
#print axioms PCSCalibrationReplay.M3.uniform_error_exclusion
