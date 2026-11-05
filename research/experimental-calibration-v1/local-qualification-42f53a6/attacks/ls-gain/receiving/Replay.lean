import PCSReal.Calibration
set_option autoImplicit false
set_option format.width 1000000
open Finset PCSReal.Calibration

namespace PCSCalibrationReplay.M0
def abscissa (i : Fin 7) : ℚ := ([((5 : ℚ) / (1 : ℚ)), ((7 : ℚ) / (1 : ℚ)), ((9 : ℚ) / (1 : ℚ)), ((11 : ℚ) / (1 : ℚ)), ((13 : ℚ) / (1 : ℚ)), ((15 : ℚ) / (1 : ℚ)), ((17 : ℚ) / (1 : ℚ))] : List ℚ).getD i.val 0
def x (i : Fin 7) (j : Fin 2) : ℚ := abscissa i ^ j.val
def y (i : Fin 7) : ℚ := ([((11 : ℚ) / (100 : ℚ)), ((47 : ℚ) / (100 : ℚ)), ((59 : ℚ) / (50 : ℚ)), ((261 : ℚ) / (100 : ℚ)), ((499 : ℚ) / (100 : ℚ)), ((1193 : ℚ) / (100 : ℚ)), ((131 : ℚ) / (4 : ℚ))] : List ℚ).getD i.val 0
def b (j : Fin 2) : ℚ := ([((-93883 : ℚ) / (5600 : ℚ)), ((2493 : ℚ) / (1120 : ℚ))] : List ℚ).getD j.val 0
def xr (i : Fin 7) (j : Fin 2) : ℝ := (x i j : ℝ)
def yr (i : Fin 7) : ℝ := (y i : ℝ)
def br (j : Fin 2) : ℝ := (b j : ℝ)
theorem normal_checked : fitCheck x y b = true := by decide +kernel
theorem residual_checked : loss x y b = ((77313911 : ℚ) / (280000 : ℚ)) := by decide +kernel
theorem global_optimum : ∀ c : Fin 2 → ℝ,
    (((77313911 : ℚ) / (280000 : ℚ)) : ℝ) ≤ loss xr yr c := by
  have hs : loss xr yr br = (((77313911 : ℚ) / (280000 : ℚ)) : ℝ) := by
    calc
      loss xr yr br = ((loss x y b : ℚ) : ℝ) := (cast_loss x y b).symm
      _ = (((77313911 : ℚ) / (280000 : ℚ)) : ℝ) := by
        simpa only [Rat.cast_div, Rat.cast_intCast, Rat.cast_ofNat, Rat.cast_neg]
          using congrArg (fun a : ℚ => (a : ℝ)) residual_checked
  simpa only [hs] using global_minimum xr yr br (fit_check_sound normal_checked)
theorem excludes_every_better_model (threshold : ℝ)
    (h : threshold < (((77313911 : ℚ) / (280000 : ℚ)) : ℝ)) :
    ∀ c : Fin 2 → ℝ, threshold < loss xr yr c := by
  intro c
  exact h.trans_le (global_optimum c)
theorem uniform_error_exclusion (ε : ℝ) (he : 0 ≤ ε)
    (hgap : (7 : ℝ) * ε ^ 2 < (((77313911 : ℚ) / (280000 : ℚ)) : ℝ)) :
    ¬ (∃ c : Fin 2 → ℝ, ∀ i, |yr i - prediction xr c i| ≤ ε) :=
  PCSReal.Calibration.uniform_error_exclusion xr yr (((77313911 : ℚ) / (280000 : ℚ)) : ℝ) ε
    global_optimum he (by simpa using hgap)
namespace Q0
def q (j : Fin 2) : ℚ := (((6 : ℚ) / (1 : ℚ)) : ℚ) ^ j.val
def w (i : Fin 7) : ℚ := ([((23 : ℚ) / (56 : ℚ)), ((9 : ℚ) / (28 : ℚ)), ((13 : ℚ) / (56 : ℚ)), ((1 : ℚ) / (7 : ℚ)), ((3 : ℚ) / (56 : ℚ)), ((-1 : ℚ) / (28 : ℚ)), ((-1 : ℚ) / (8 : ℚ))] : List ℚ).getD i.val 0
def d (j : Fin 2) : ℚ := ([((71 : ℚ) / (112 : ℚ)), ((-5 : ℚ) / (112 : ℚ))] : List ℚ).getD j.val 0
def wr (i : Fin 7) : ℝ := (w i : ℝ)
def qr (j : Fin 2) : ℝ := (q j : ℝ)
theorem dual_checked : dualCheck x w q d = true := by decide +kernel
theorem gain_checked : (∑ i, |w i|) = (((0 : ℚ) / (1 : ℚ)) : ℚ) := by decide +kernel
theorem real_gain : (∑ i, |wr i|) = (((0 : ℚ) / (1 : ℚ)) : ℝ) := by
  have h := congrArg (fun a : ℚ => (a : ℝ)) gain_checked
  simpa only [wr, Rat.cast_sum, Rat.cast_abs, Rat.cast_div, Rat.cast_intCast,
    Rat.cast_ofNat, Rat.cast_neg] using h
theorem fitted_query : dot wr yr = dot qr br :=
  dual_prediction xr yr wr qr br (fun j => (d j : ℝ))
    (fit_check_sound normal_checked) (dual_check_sound dual_checked).1
    (dual_check_sound dual_checked).2
theorem sharp_radius (ε radius : ℝ) (he : 0 ≤ ε) :
    (∀ z : Fin 7 → ℝ, (∀ i, |z i - yr i| ≤ ε) → |dot wr z - dot wr yr| ≤ radius) ↔
      ε * (((0 : ℚ) / (1 : ℚ)) : ℝ) ≤ radius := by
  simpa only [real_gain] using sharp_radius_iff wr yr ε radius he
theorem conditional_physical_enclosure (truth : Fin 2 → ℝ) (ε : ℝ)
    (hm : ∀ i, |yr i - prediction xr truth i| ≤ ε) :
    |dot wr yr - dot qr truth| ≤ ε * (((0 : ℚ) / (1 : ℚ)) : ℝ) := by
  simpa only [real_gain] using physical_enclosure xr yr wr qr truth ε
    (dual_check_sound dual_checked).1 hm
end Q0
namespace Q0.Minimax
def w (i : Fin 7) : ℚ := ([((1 : ℚ) / (2 : ℚ)), ((1 : ℚ) / (2 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ))] : List ℚ).getD i.val 0
def a (j : Fin 2) : ℚ := ([((1 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ))] : List ℚ).getD j.val 0
def wr (i : Fin 7) : ℝ := (w i : ℝ)
def ar (j : Fin 2) : ℝ := (a j : ℝ)
theorem optimality_checked : minimaxCheck x w Q0.q a ((1 : ℚ) / (1 : ℚ)) = true := by decide +kernel
theorem gain_checked : (∑ i, |w i|) = (((1 : ℚ) / (1 : ℚ)) : ℚ) := by decide +kernel
theorem real_gain : (∑ i, |wr i|) = (((1 : ℚ) / (1 : ℚ)) : ℝ) := by
  have h := congrArg (fun a : ℚ => (a : ℝ)) gain_checked
  simpa only [wr, Rat.cast_sum, Rat.cast_abs, Rat.cast_div, Rat.cast_intCast,
    Rat.cast_ofNat, Rat.cast_neg] using h
theorem globally_minimal_gain (v : Fin 7 → ℝ) (hv : Reproduces xr v Q0.qr) :
    (((1 : ℚ) / (1 : ℚ)) : ℝ) ≤ ∑ i, |v i| := by
  have h := minimax_check_sound optimality_checked
  have hm := minimax_weights_optimal xr wr Q0.qr ar h.2.1 h.2.2 v hv
  simpa only [real_gain] using hm
theorem sharp_radius (ε radius : ℝ) (he : 0 ≤ ε) :
    (∀ z : Fin 7 → ℝ, (∀ i, |z i - yr i| ≤ ε) → |dot wr z - dot wr yr| ≤ radius) ↔
      ε * (((1 : ℚ) / (1 : ℚ)) : ℝ) ≤ radius := by
  simpa only [real_gain] using sharp_radius_iff wr yr ε radius he
theorem no_reproducing_estimator_has_smaller_radius (ε radius : ℝ) (he : 0 ≤ ε)
    (v : Fin 7 → ℝ) (hv : Reproduces xr v Q0.qr)
    (hr : ∀ z, (∀ i, |z i - yr i| ≤ ε) → |dot v z - dot v yr| ≤ radius) :
    ε * (((1 : ℚ) / (1 : ℚ)) : ℝ) ≤ radius := by
  have h := minimax_check_sound optimality_checked
  have hm := minimax_radius_lower_bound xr yr wr Q0.qr ar h.2.1 h.2.2 ε radius he v hv hr
  simpa only [real_gain] using hm
theorem conditional_physical_enclosure (truth : Fin 2 → ℝ) (ε : ℝ)
    (hm : ∀ i, |yr i - prediction xr truth i| ≤ ε) :
    |dot wr yr - dot Q0.qr truth| ≤ ε * (((1 : ℚ) / (1 : ℚ)) : ℝ) := by
  simpa only [real_gain] using physical_enclosure xr yr wr Q0.qr truth ε
    (minimax_check_sound optimality_checked).1 hm
theorem uniform_minimax_over_all_prediction_functions (ε radius : ℝ) (he : 0 ≤ ε) :
    (∃ estimator : (Fin 7 → ℝ) → ℝ,
      ∀ truth observed, (∀ i, |observed i - prediction xr truth i| ≤ ε) →
        |estimator observed - dot Q0.qr truth| ≤ radius) ↔
      ε * (((1 : ℚ) / (1 : ℚ)) : ℝ) ≤ radius := by
  have h := minimax_check_sound optimality_checked
  simpa only [real_gain] using
    minimax_over_all_estimators_iff xr wr Q0.qr ar h.1 h.2.1 h.2.2 ε radius he
end Q0.Minimax
end PCSCalibrationReplay.M0

#print axioms PCSCalibrationReplay.M0.normal_checked
#print axioms PCSCalibrationReplay.M0.residual_checked
#print axioms PCSCalibrationReplay.M0.global_optimum
#print axioms PCSCalibrationReplay.M0.excludes_every_better_model
#print axioms PCSCalibrationReplay.M0.uniform_error_exclusion
#print axioms PCSCalibrationReplay.M0.Q0.dual_checked
#print axioms PCSCalibrationReplay.M0.Q0.gain_checked
#print axioms PCSCalibrationReplay.M0.Q0.real_gain
#print axioms PCSCalibrationReplay.M0.Q0.fitted_query
#print axioms PCSCalibrationReplay.M0.Q0.sharp_radius
#print axioms PCSCalibrationReplay.M0.Q0.conditional_physical_enclosure
#print axioms PCSCalibrationReplay.M0.Q0.Minimax.optimality_checked
#print axioms PCSCalibrationReplay.M0.Q0.Minimax.gain_checked
#print axioms PCSCalibrationReplay.M0.Q0.Minimax.real_gain
#print axioms PCSCalibrationReplay.M0.Q0.Minimax.globally_minimal_gain
#print axioms PCSCalibrationReplay.M0.Q0.Minimax.sharp_radius
#print axioms PCSCalibrationReplay.M0.Q0.Minimax.no_reproducing_estimator_has_smaller_radius
#print axioms PCSCalibrationReplay.M0.Q0.Minimax.conditional_physical_enclosure
#print axioms PCSCalibrationReplay.M0.Q0.Minimax.uniform_minimax_over_all_prediction_functions
