import PCSReal.Calibration
set_option autoImplicit false
set_option format.width 1000000
open Finset PCSReal.Calibration

namespace PCSCalibrationReplay.M5
def abscissa (i : Fin 14) : ℚ := ([((5 : ℚ) / (1 : ℚ)), ((6 : ℚ) / (1 : ℚ)), ((7 : ℚ) / (1 : ℚ)), ((8 : ℚ) / (1 : ℚ)), ((9 : ℚ) / (1 : ℚ)), ((10 : ℚ) / (1 : ℚ)), ((11 : ℚ) / (1 : ℚ)), ((12 : ℚ) / (1 : ℚ)), ((13 : ℚ) / (1 : ℚ)), ((14 : ℚ) / (1 : ℚ)), ((15 : ℚ) / (1 : ℚ)), ((16 : ℚ) / (1 : ℚ)), ((17 : ℚ) / (1 : ℚ)), ((18 : ℚ) / (1 : ℚ))] : List ℚ).getD i.val 0
def x (i : Fin 14) (j : Fin 4) : ℚ := abscissa i ^ j.val
def y (i : Fin 14) : ℚ := ([((1 : ℚ) / (10 : ℚ)), ((23 : ℚ) / (100 : ℚ)), ((47 : ℚ) / (100 : ℚ)), ((19 : ℚ) / (25 : ℚ)), ((23 : ℚ) / (20 : ℚ)), ((33 : ℚ) / (20 : ℚ)), ((57 : ℚ) / (25 : ℚ)), ((309 : ℚ) / (100 : ℚ)), ((441 : ℚ) / (100 : ℚ)), ((751 : ℚ) / (100 : ℚ)), ((1377 : ℚ) / (100 : ℚ)), ((599 : ℚ) / (25 : ℚ)), ((1869 : ℚ) / (50 : ℚ)), ((2823 : ℚ) / (50 : ℚ))] : List ℚ).getD i.val 0
def b (j : Fin 4) : ℚ := ([((-183907219 : ℚ) / (3403400 : ℚ)), ((803583679 : ℚ) / (40840800 : ℚ)), ((-15298649 : ℚ) / (6806800 : ℚ)), ((19337 : ℚ) / (233376 : ℚ))] : List ℚ).getD j.val 0
def xr (i : Fin 14) (j : Fin 4) : ℝ := (x i j : ℝ)
def yr (i : Fin 14) : ℝ := (y i : ℝ)
def br (j : Fin 4) : ℝ := (b j : ℝ)
theorem normal_checked : fitCheck x y b = true := by decide +kernel
theorem residual_checked : loss x y b = ((11835213101 : ℚ) / (680680000 : ℚ)) := by decide +kernel
theorem global_optimum : ∀ c : Fin 4 → ℝ,
    (((11835213101 : ℚ) / (680680000 : ℚ)) : ℝ) ≤ loss xr yr c := by
  have hs : loss xr yr br = (((11835213101 : ℚ) / (680680000 : ℚ)) : ℝ) := by
    calc
      loss xr yr br = ((loss x y b : ℚ) : ℝ) := (cast_loss x y b).symm
      _ = (((11835213101 : ℚ) / (680680000 : ℚ)) : ℝ) := by
        simpa only [Rat.cast_div, Rat.cast_intCast, Rat.cast_ofNat, Rat.cast_neg]
          using congrArg (fun a : ℚ => (a : ℝ)) residual_checked
  simpa only [hs] using global_minimum xr yr br (fit_check_sound normal_checked)
theorem excludes_every_better_model (threshold : ℝ)
    (h : threshold < (((11835213101 : ℚ) / (680680000 : ℚ)) : ℝ)) :
    ∀ c : Fin 4 → ℝ, threshold < loss xr yr c := by
  intro c
  exact h.trans_le (global_optimum c)
theorem uniform_error_exclusion (ε : ℝ) (he : 0 ≤ ε)
    (hgap : (14 : ℝ) * ε ^ 2 < (((11835213101 : ℚ) / (680680000 : ℚ)) : ℝ)) :
    ¬ (∃ c : Fin 4 → ℝ, ∀ i, |yr i - prediction xr c i| ≤ ε) :=
  PCSReal.Calibration.uniform_error_exclusion xr yr (((11835213101 : ℚ) / (680680000 : ℚ)) : ℝ) ε
    global_optimum he (by simpa using hgap)
end PCSCalibrationReplay.M5

#print axioms PCSCalibrationReplay.M5.normal_checked
#print axioms PCSCalibrationReplay.M5.residual_checked
#print axioms PCSCalibrationReplay.M5.global_optimum
#print axioms PCSCalibrationReplay.M5.excludes_every_better_model
#print axioms PCSCalibrationReplay.M5.uniform_error_exclusion
