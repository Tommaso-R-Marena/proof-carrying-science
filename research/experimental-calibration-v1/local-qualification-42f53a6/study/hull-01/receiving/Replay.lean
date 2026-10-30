import PCSReal.Calibration
set_option autoImplicit false
set_option format.width 1000000
open Finset PCSReal.Calibration

namespace PCSCalibrationReplay.M0
def abscissa (i : Fin 7) : ℚ := ([((5 : ℚ) / (1 : ℚ)), ((7 : ℚ) / (1 : ℚ)), ((9 : ℚ) / (1 : ℚ)), ((11 : ℚ) / (1 : ℚ)), ((13 : ℚ) / (1 : ℚ)), ((15 : ℚ) / (1 : ℚ)), ((17 : ℚ) / (1 : ℚ))] : List ℚ).getD i.val 0
def x (i : Fin 7) (j : Fin 2) : ℚ := abscissa i ^ j.val
def y (i : Fin 7) : ℚ := ([((1 : ℚ) / (25 : ℚ)), ((37 : ℚ) / (100 : ℚ)), ((53 : ℚ) / (50 : ℚ)), ((233 : ℚ) / (100 : ℚ)), ((461 : ℚ) / (100 : ℚ)), ((1199 : ℚ) / (100 : ℚ)), ((3501 : ℚ) / (100 : ℚ))] : List ℚ).getD i.val 0
def b (j : Fin 2) : ℚ := ([((-50271 : ℚ) / (2800 : ℚ)), ((1317 : ℚ) / (560 : ℚ))] : List ℚ).getD j.val 0
def xr (i : Fin 7) (j : Fin 2) : ℝ := (x i j : ℝ)
def yr (i : Fin 7) : ℝ := (y i : ℝ)
def br (j : Fin 2) : ℝ := (b j : ℝ)
theorem normal_checked : fitCheck x y b = true := by decide +kernel
theorem residual_checked : loss x y b = ((950133 : ℚ) / (2800 : ℚ)) := by decide +kernel
theorem global_optimum : ∀ c : Fin 2 → ℝ,
    (((950133 : ℚ) / (2800 : ℚ)) : ℝ) ≤ loss xr yr c := by
  have hs : loss xr yr br = (((950133 : ℚ) / (2800 : ℚ)) : ℝ) := by
    calc
      loss xr yr br = ((loss x y b : ℚ) : ℝ) := (cast_loss x y b).symm
      _ = (((950133 : ℚ) / (2800 : ℚ)) : ℝ) := by
        simpa only [Rat.cast_div, Rat.cast_intCast, Rat.cast_ofNat, Rat.cast_neg]
          using congrArg (fun a : ℚ => (a : ℝ)) residual_checked
  simpa only [hs] using global_minimum xr yr br (fit_check_sound normal_checked)
theorem excludes_every_better_model (threshold : ℝ)
    (h : threshold < (((950133 : ℚ) / (2800 : ℚ)) : ℝ)) :
    ∀ c : Fin 2 → ℝ, threshold < loss xr yr c := by
  intro c
  exact h.trans_le (global_optimum c)
theorem uniform_error_exclusion (ε : ℝ) (he : 0 ≤ ε)
    (hgap : (7 : ℝ) * ε ^ 2 < (((950133 : ℚ) / (2800 : ℚ)) : ℝ)) :
    ¬ (∃ c : Fin 2 → ℝ, ∀ i, |yr i - prediction xr c i| ≤ ε) :=
  PCSReal.Calibration.uniform_error_exclusion xr yr (((950133 : ℚ) / (2800 : ℚ)) : ℝ) ε
    global_optimum he (by simpa using hgap)
namespace Q0
def q (j : Fin 2) : ℚ := (((6 : ℚ) / (1 : ℚ)) : ℚ) ^ j.val
def w (i : Fin 7) : ℚ := ([((23 : ℚ) / (56 : ℚ)), ((9 : ℚ) / (28 : ℚ)), ((13 : ℚ) / (56 : ℚ)), ((1 : ℚ) / (7 : ℚ)), ((3 : ℚ) / (56 : ℚ)), ((-1 : ℚ) / (28 : ℚ)), ((-1 : ℚ) / (8 : ℚ))] : List ℚ).getD i.val 0
def d (j : Fin 2) : ℚ := ([((71 : ℚ) / (112 : ℚ)), ((-5 : ℚ) / (112 : ℚ))] : List ℚ).getD j.val 0
def wr (i : Fin 7) : ℝ := (w i : ℝ)
def qr (j : Fin 2) : ℝ := (q j : ℝ)
theorem dual_checked : dualCheck x w q d = true := by decide +kernel
theorem gain_checked : (∑ i, |w i|) = (((37 : ℚ) / (28 : ℚ)) : ℚ) := by decide +kernel
theorem real_gain : (∑ i, |wr i|) = (((37 : ℚ) / (28 : ℚ)) : ℝ) := by
  have h := congrArg (fun a : ℚ => (a : ℝ)) gain_checked
  simpa only [wr, Rat.cast_sum, Rat.cast_abs, Rat.cast_div, Rat.cast_intCast,
    Rat.cast_ofNat, Rat.cast_neg] using h
theorem fitted_query : dot wr yr = dot qr br :=
  dual_prediction xr yr wr qr br (fun j => (d j : ℝ))
    (fit_check_sound normal_checked) (dual_check_sound dual_checked).1
    (dual_check_sound dual_checked).2
theorem sharp_radius (ε radius : ℝ) (he : 0 ≤ ε) :
    (∀ z : Fin 7 → ℝ, (∀ i, |z i - yr i| ≤ ε) → |dot wr z - dot wr yr| ≤ radius) ↔
      ε * (((37 : ℚ) / (28 : ℚ)) : ℝ) ≤ radius := by
  simpa only [real_gain] using sharp_radius_iff wr yr ε radius he
theorem conditional_physical_enclosure (truth : Fin 2 → ℝ) (ε : ℝ)
    (hm : ∀ i, |yr i - prediction xr truth i| ≤ ε) :
    |dot wr yr - dot qr truth| ≤ ε * (((37 : ℚ) / (28 : ℚ)) : ℝ) := by
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
namespace Q1
def q (j : Fin 2) : ℚ := (((8 : ℚ) / (1 : ℚ)) : ℚ) ^ j.val
def w (i : Fin 7) : ℚ := ([((17 : ℚ) / (56 : ℚ)), ((1 : ℚ) / (4 : ℚ)), ((11 : ℚ) / (56 : ℚ)), ((1 : ℚ) / (7 : ℚ)), ((5 : ℚ) / (56 : ℚ)), ((1 : ℚ) / (28 : ℚ)), ((-1 : ℚ) / (56 : ℚ))] : List ℚ).getD i.val 0
def d (j : Fin 2) : ℚ := ([((7 : ℚ) / (16 : ℚ)), ((-3 : ℚ) / (112 : ℚ))] : List ℚ).getD j.val 0
def wr (i : Fin 7) : ℝ := (w i : ℝ)
def qr (j : Fin 2) : ℝ := (q j : ℝ)
theorem dual_checked : dualCheck x w q d = true := by decide +kernel
theorem gain_checked : (∑ i, |w i|) = (((29 : ℚ) / (28 : ℚ)) : ℚ) := by decide +kernel
theorem real_gain : (∑ i, |wr i|) = (((29 : ℚ) / (28 : ℚ)) : ℝ) := by
  have h := congrArg (fun a : ℚ => (a : ℝ)) gain_checked
  simpa only [wr, Rat.cast_sum, Rat.cast_abs, Rat.cast_div, Rat.cast_intCast,
    Rat.cast_ofNat, Rat.cast_neg] using h
theorem fitted_query : dot wr yr = dot qr br :=
  dual_prediction xr yr wr qr br (fun j => (d j : ℝ))
    (fit_check_sound normal_checked) (dual_check_sound dual_checked).1
    (dual_check_sound dual_checked).2
theorem sharp_radius (ε radius : ℝ) (he : 0 ≤ ε) :
    (∀ z : Fin 7 → ℝ, (∀ i, |z i - yr i| ≤ ε) → |dot wr z - dot wr yr| ≤ radius) ↔
      ε * (((29 : ℚ) / (28 : ℚ)) : ℝ) ≤ radius := by
  simpa only [real_gain] using sharp_radius_iff wr yr ε radius he
theorem conditional_physical_enclosure (truth : Fin 2 → ℝ) (ε : ℝ)
    (hm : ∀ i, |yr i - prediction xr truth i| ≤ ε) :
    |dot wr yr - dot qr truth| ≤ ε * (((29 : ℚ) / (28 : ℚ)) : ℝ) := by
  simpa only [real_gain] using physical_enclosure xr yr wr qr truth ε
    (dual_check_sound dual_checked).1 hm
end Q1
namespace Q1.Minimax
def w (i : Fin 7) : ℚ := ([((1 : ℚ) / (4 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((3 : ℚ) / (4 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ))] : List ℚ).getD i.val 0
def a (j : Fin 2) : ℚ := ([((1 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ))] : List ℚ).getD j.val 0
def wr (i : Fin 7) : ℝ := (w i : ℝ)
def ar (j : Fin 2) : ℝ := (a j : ℝ)
theorem optimality_checked : minimaxCheck x w Q1.q a ((1 : ℚ) / (1 : ℚ)) = true := by decide +kernel
theorem gain_checked : (∑ i, |w i|) = (((1 : ℚ) / (1 : ℚ)) : ℚ) := by decide +kernel
theorem real_gain : (∑ i, |wr i|) = (((1 : ℚ) / (1 : ℚ)) : ℝ) := by
  have h := congrArg (fun a : ℚ => (a : ℝ)) gain_checked
  simpa only [wr, Rat.cast_sum, Rat.cast_abs, Rat.cast_div, Rat.cast_intCast,
    Rat.cast_ofNat, Rat.cast_neg] using h
theorem globally_minimal_gain (v : Fin 7 → ℝ) (hv : Reproduces xr v Q1.qr) :
    (((1 : ℚ) / (1 : ℚ)) : ℝ) ≤ ∑ i, |v i| := by
  have h := minimax_check_sound optimality_checked
  have hm := minimax_weights_optimal xr wr Q1.qr ar h.2.1 h.2.2 v hv
  simpa only [real_gain] using hm
theorem sharp_radius (ε radius : ℝ) (he : 0 ≤ ε) :
    (∀ z : Fin 7 → ℝ, (∀ i, |z i - yr i| ≤ ε) → |dot wr z - dot wr yr| ≤ radius) ↔
      ε * (((1 : ℚ) / (1 : ℚ)) : ℝ) ≤ radius := by
  simpa only [real_gain] using sharp_radius_iff wr yr ε radius he
theorem no_reproducing_estimator_has_smaller_radius (ε radius : ℝ) (he : 0 ≤ ε)
    (v : Fin 7 → ℝ) (hv : Reproduces xr v Q1.qr)
    (hr : ∀ z, (∀ i, |z i - yr i| ≤ ε) → |dot v z - dot v yr| ≤ radius) :
    ε * (((1 : ℚ) / (1 : ℚ)) : ℝ) ≤ radius := by
  have h := minimax_check_sound optimality_checked
  have hm := minimax_radius_lower_bound xr yr wr Q1.qr ar h.2.1 h.2.2 ε radius he v hv hr
  simpa only [real_gain] using hm
theorem conditional_physical_enclosure (truth : Fin 2 → ℝ) (ε : ℝ)
    (hm : ∀ i, |yr i - prediction xr truth i| ≤ ε) :
    |dot wr yr - dot Q1.qr truth| ≤ ε * (((1 : ℚ) / (1 : ℚ)) : ℝ) := by
  simpa only [real_gain] using physical_enclosure xr yr wr Q1.qr truth ε
    (minimax_check_sound optimality_checked).1 hm
theorem uniform_minimax_over_all_prediction_functions (ε radius : ℝ) (he : 0 ≤ ε) :
    (∃ estimator : (Fin 7 → ℝ) → ℝ,
      ∀ truth observed, (∀ i, |observed i - prediction xr truth i| ≤ ε) →
        |estimator observed - dot Q1.qr truth| ≤ radius) ↔
      ε * (((1 : ℚ) / (1 : ℚ)) : ℝ) ≤ radius := by
  have h := minimax_check_sound optimality_checked
  simpa only [real_gain] using
    minimax_over_all_estimators_iff xr wr Q1.qr ar h.1 h.2.1 h.2.2 ε radius he
end Q1.Minimax
namespace Q2
def q (j : Fin 2) : ℚ := (((10 : ℚ) / (1 : ℚ)) : ℚ) ^ j.val
def w (i : Fin 7) : ℚ := ([((11 : ℚ) / (56 : ℚ)), ((5 : ℚ) / (28 : ℚ)), ((9 : ℚ) / (56 : ℚ)), ((1 : ℚ) / (7 : ℚ)), ((1 : ℚ) / (8 : ℚ)), ((3 : ℚ) / (28 : ℚ)), ((5 : ℚ) / (56 : ℚ))] : List ℚ).getD i.val 0
def d (j : Fin 2) : ℚ := ([((27 : ℚ) / (112 : ℚ)), ((-1 : ℚ) / (112 : ℚ))] : List ℚ).getD j.val 0
def wr (i : Fin 7) : ℝ := (w i : ℝ)
def qr (j : Fin 2) : ℝ := (q j : ℝ)
theorem dual_checked : dualCheck x w q d = true := by decide +kernel
theorem gain_checked : (∑ i, |w i|) = (((1 : ℚ) / (1 : ℚ)) : ℚ) := by decide +kernel
theorem real_gain : (∑ i, |wr i|) = (((1 : ℚ) / (1 : ℚ)) : ℝ) := by
  have h := congrArg (fun a : ℚ => (a : ℝ)) gain_checked
  simpa only [wr, Rat.cast_sum, Rat.cast_abs, Rat.cast_div, Rat.cast_intCast,
    Rat.cast_ofNat, Rat.cast_neg] using h
theorem fitted_query : dot wr yr = dot qr br :=
  dual_prediction xr yr wr qr br (fun j => (d j : ℝ))
    (fit_check_sound normal_checked) (dual_check_sound dual_checked).1
    (dual_check_sound dual_checked).2
theorem sharp_radius (ε radius : ℝ) (he : 0 ≤ ε) :
    (∀ z : Fin 7 → ℝ, (∀ i, |z i - yr i| ≤ ε) → |dot wr z - dot wr yr| ≤ radius) ↔
      ε * (((1 : ℚ) / (1 : ℚ)) : ℝ) ≤ radius := by
  simpa only [real_gain] using sharp_radius_iff wr yr ε radius he
theorem conditional_physical_enclosure (truth : Fin 2 → ℝ) (ε : ℝ)
    (hm : ∀ i, |yr i - prediction xr truth i| ≤ ε) :
    |dot wr yr - dot qr truth| ≤ ε * (((1 : ℚ) / (1 : ℚ)) : ℝ) := by
  simpa only [real_gain] using physical_enclosure xr yr wr qr truth ε
    (dual_check_sound dual_checked).1 hm
end Q2
namespace Q2.Minimax
def w (i : Fin 7) : ℚ := ([((1 : ℚ) / (6 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((5 : ℚ) / (6 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ))] : List ℚ).getD i.val 0
def a (j : Fin 2) : ℚ := ([((1 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ))] : List ℚ).getD j.val 0
def wr (i : Fin 7) : ℝ := (w i : ℝ)
def ar (j : Fin 2) : ℝ := (a j : ℝ)
theorem optimality_checked : minimaxCheck x w Q2.q a ((1 : ℚ) / (1 : ℚ)) = true := by decide +kernel
theorem gain_checked : (∑ i, |w i|) = (((1 : ℚ) / (1 : ℚ)) : ℚ) := by decide +kernel
theorem real_gain : (∑ i, |wr i|) = (((1 : ℚ) / (1 : ℚ)) : ℝ) := by
  have h := congrArg (fun a : ℚ => (a : ℝ)) gain_checked
  simpa only [wr, Rat.cast_sum, Rat.cast_abs, Rat.cast_div, Rat.cast_intCast,
    Rat.cast_ofNat, Rat.cast_neg] using h
theorem globally_minimal_gain (v : Fin 7 → ℝ) (hv : Reproduces xr v Q2.qr) :
    (((1 : ℚ) / (1 : ℚ)) : ℝ) ≤ ∑ i, |v i| := by
  have h := minimax_check_sound optimality_checked
  have hm := minimax_weights_optimal xr wr Q2.qr ar h.2.1 h.2.2 v hv
  simpa only [real_gain] using hm
theorem sharp_radius (ε radius : ℝ) (he : 0 ≤ ε) :
    (∀ z : Fin 7 → ℝ, (∀ i, |z i - yr i| ≤ ε) → |dot wr z - dot wr yr| ≤ radius) ↔
      ε * (((1 : ℚ) / (1 : ℚ)) : ℝ) ≤ radius := by
  simpa only [real_gain] using sharp_radius_iff wr yr ε radius he
theorem no_reproducing_estimator_has_smaller_radius (ε radius : ℝ) (he : 0 ≤ ε)
    (v : Fin 7 → ℝ) (hv : Reproduces xr v Q2.qr)
    (hr : ∀ z, (∀ i, |z i - yr i| ≤ ε) → |dot v z - dot v yr| ≤ radius) :
    ε * (((1 : ℚ) / (1 : ℚ)) : ℝ) ≤ radius := by
  have h := minimax_check_sound optimality_checked
  have hm := minimax_radius_lower_bound xr yr wr Q2.qr ar h.2.1 h.2.2 ε radius he v hv hr
  simpa only [real_gain] using hm
theorem conditional_physical_enclosure (truth : Fin 2 → ℝ) (ε : ℝ)
    (hm : ∀ i, |yr i - prediction xr truth i| ≤ ε) :
    |dot wr yr - dot Q2.qr truth| ≤ ε * (((1 : ℚ) / (1 : ℚ)) : ℝ) := by
  simpa only [real_gain] using physical_enclosure xr yr wr Q2.qr truth ε
    (minimax_check_sound optimality_checked).1 hm
theorem uniform_minimax_over_all_prediction_functions (ε radius : ℝ) (he : 0 ≤ ε) :
    (∃ estimator : (Fin 7 → ℝ) → ℝ,
      ∀ truth observed, (∀ i, |observed i - prediction xr truth i| ≤ ε) →
        |estimator observed - dot Q2.qr truth| ≤ radius) ↔
      ε * (((1 : ℚ) / (1 : ℚ)) : ℝ) ≤ radius := by
  have h := minimax_check_sound optimality_checked
  simpa only [real_gain] using
    minimax_over_all_estimators_iff xr wr Q2.qr ar h.1 h.2.1 h.2.2 ε radius he
end Q2.Minimax
namespace Q3
def q (j : Fin 2) : ℚ := (((12 : ℚ) / (1 : ℚ)) : ℚ) ^ j.val
def w (i : Fin 7) : ℚ := ([((5 : ℚ) / (56 : ℚ)), ((3 : ℚ) / (28 : ℚ)), ((1 : ℚ) / (8 : ℚ)), ((1 : ℚ) / (7 : ℚ)), ((9 : ℚ) / (56 : ℚ)), ((5 : ℚ) / (28 : ℚ)), ((11 : ℚ) / (56 : ℚ))] : List ℚ).getD i.val 0
def d (j : Fin 2) : ℚ := ([((5 : ℚ) / (112 : ℚ)), ((1 : ℚ) / (112 : ℚ))] : List ℚ).getD j.val 0
def wr (i : Fin 7) : ℝ := (w i : ℝ)
def qr (j : Fin 2) : ℝ := (q j : ℝ)
theorem dual_checked : dualCheck x w q d = true := by decide +kernel
theorem gain_checked : (∑ i, |w i|) = (((1 : ℚ) / (1 : ℚ)) : ℚ) := by decide +kernel
theorem real_gain : (∑ i, |wr i|) = (((1 : ℚ) / (1 : ℚ)) : ℝ) := by
  have h := congrArg (fun a : ℚ => (a : ℝ)) gain_checked
  simpa only [wr, Rat.cast_sum, Rat.cast_abs, Rat.cast_div, Rat.cast_intCast,
    Rat.cast_ofNat, Rat.cast_neg] using h
theorem fitted_query : dot wr yr = dot qr br :=
  dual_prediction xr yr wr qr br (fun j => (d j : ℝ))
    (fit_check_sound normal_checked) (dual_check_sound dual_checked).1
    (dual_check_sound dual_checked).2
theorem sharp_radius (ε radius : ℝ) (he : 0 ≤ ε) :
    (∀ z : Fin 7 → ℝ, (∀ i, |z i - yr i| ≤ ε) → |dot wr z - dot wr yr| ≤ radius) ↔
      ε * (((1 : ℚ) / (1 : ℚ)) : ℝ) ≤ radius := by
  simpa only [real_gain] using sharp_radius_iff wr yr ε radius he
theorem conditional_physical_enclosure (truth : Fin 2 → ℝ) (ε : ℝ)
    (hm : ∀ i, |yr i - prediction xr truth i| ≤ ε) :
    |dot wr yr - dot qr truth| ≤ ε * (((1 : ℚ) / (1 : ℚ)) : ℝ) := by
  simpa only [real_gain] using physical_enclosure xr yr wr qr truth ε
    (dual_check_sound dual_checked).1 hm
end Q3
namespace Q3.Minimax
def w (i : Fin 7) : ℚ := ([((1 : ℚ) / (8 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((7 : ℚ) / (8 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ))] : List ℚ).getD i.val 0
def a (j : Fin 2) : ℚ := ([((1 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ))] : List ℚ).getD j.val 0
def wr (i : Fin 7) : ℝ := (w i : ℝ)
def ar (j : Fin 2) : ℝ := (a j : ℝ)
theorem optimality_checked : minimaxCheck x w Q3.q a ((1 : ℚ) / (1 : ℚ)) = true := by decide +kernel
theorem gain_checked : (∑ i, |w i|) = (((1 : ℚ) / (1 : ℚ)) : ℚ) := by decide +kernel
theorem real_gain : (∑ i, |wr i|) = (((1 : ℚ) / (1 : ℚ)) : ℝ) := by
  have h := congrArg (fun a : ℚ => (a : ℝ)) gain_checked
  simpa only [wr, Rat.cast_sum, Rat.cast_abs, Rat.cast_div, Rat.cast_intCast,
    Rat.cast_ofNat, Rat.cast_neg] using h
theorem globally_minimal_gain (v : Fin 7 → ℝ) (hv : Reproduces xr v Q3.qr) :
    (((1 : ℚ) / (1 : ℚ)) : ℝ) ≤ ∑ i, |v i| := by
  have h := minimax_check_sound optimality_checked
  have hm := minimax_weights_optimal xr wr Q3.qr ar h.2.1 h.2.2 v hv
  simpa only [real_gain] using hm
theorem sharp_radius (ε radius : ℝ) (he : 0 ≤ ε) :
    (∀ z : Fin 7 → ℝ, (∀ i, |z i - yr i| ≤ ε) → |dot wr z - dot wr yr| ≤ radius) ↔
      ε * (((1 : ℚ) / (1 : ℚ)) : ℝ) ≤ radius := by
  simpa only [real_gain] using sharp_radius_iff wr yr ε radius he
theorem no_reproducing_estimator_has_smaller_radius (ε radius : ℝ) (he : 0 ≤ ε)
    (v : Fin 7 → ℝ) (hv : Reproduces xr v Q3.qr)
    (hr : ∀ z, (∀ i, |z i - yr i| ≤ ε) → |dot v z - dot v yr| ≤ radius) :
    ε * (((1 : ℚ) / (1 : ℚ)) : ℝ) ≤ radius := by
  have h := minimax_check_sound optimality_checked
  have hm := minimax_radius_lower_bound xr yr wr Q3.qr ar h.2.1 h.2.2 ε radius he v hv hr
  simpa only [real_gain] using hm
theorem conditional_physical_enclosure (truth : Fin 2 → ℝ) (ε : ℝ)
    (hm : ∀ i, |yr i - prediction xr truth i| ≤ ε) :
    |dot wr yr - dot Q3.qr truth| ≤ ε * (((1 : ℚ) / (1 : ℚ)) : ℝ) := by
  simpa only [real_gain] using physical_enclosure xr yr wr Q3.qr truth ε
    (minimax_check_sound optimality_checked).1 hm
theorem uniform_minimax_over_all_prediction_functions (ε radius : ℝ) (he : 0 ≤ ε) :
    (∃ estimator : (Fin 7 → ℝ) → ℝ,
      ∀ truth observed, (∀ i, |observed i - prediction xr truth i| ≤ ε) →
        |estimator observed - dot Q3.qr truth| ≤ radius) ↔
      ε * (((1 : ℚ) / (1 : ℚ)) : ℝ) ≤ radius := by
  have h := minimax_check_sound optimality_checked
  simpa only [real_gain] using
    minimax_over_all_estimators_iff xr wr Q3.qr ar h.1 h.2.1 h.2.2 ε radius he
end Q3.Minimax
namespace Q4
def q (j : Fin 2) : ℚ := (((14 : ℚ) / (1 : ℚ)) : ℚ) ^ j.val
def w (i : Fin 7) : ℚ := ([((-1 : ℚ) / (56 : ℚ)), ((1 : ℚ) / (28 : ℚ)), ((5 : ℚ) / (56 : ℚ)), ((1 : ℚ) / (7 : ℚ)), ((11 : ℚ) / (56 : ℚ)), ((1 : ℚ) / (4 : ℚ)), ((17 : ℚ) / (56 : ℚ))] : List ℚ).getD i.val 0
def d (j : Fin 2) : ℚ := ([((-17 : ℚ) / (112 : ℚ)), ((3 : ℚ) / (112 : ℚ))] : List ℚ).getD j.val 0
def wr (i : Fin 7) : ℝ := (w i : ℝ)
def qr (j : Fin 2) : ℝ := (q j : ℝ)
theorem dual_checked : dualCheck x w q d = true := by decide +kernel
theorem gain_checked : (∑ i, |w i|) = (((29 : ℚ) / (28 : ℚ)) : ℚ) := by decide +kernel
theorem real_gain : (∑ i, |wr i|) = (((29 : ℚ) / (28 : ℚ)) : ℝ) := by
  have h := congrArg (fun a : ℚ => (a : ℝ)) gain_checked
  simpa only [wr, Rat.cast_sum, Rat.cast_abs, Rat.cast_div, Rat.cast_intCast,
    Rat.cast_ofNat, Rat.cast_neg] using h
theorem fitted_query : dot wr yr = dot qr br :=
  dual_prediction xr yr wr qr br (fun j => (d j : ℝ))
    (fit_check_sound normal_checked) (dual_check_sound dual_checked).1
    (dual_check_sound dual_checked).2
theorem sharp_radius (ε radius : ℝ) (he : 0 ≤ ε) :
    (∀ z : Fin 7 → ℝ, (∀ i, |z i - yr i| ≤ ε) → |dot wr z - dot wr yr| ≤ radius) ↔
      ε * (((29 : ℚ) / (28 : ℚ)) : ℝ) ≤ radius := by
  simpa only [real_gain] using sharp_radius_iff wr yr ε radius he
theorem conditional_physical_enclosure (truth : Fin 2 → ℝ) (ε : ℝ)
    (hm : ∀ i, |yr i - prediction xr truth i| ≤ ε) :
    |dot wr yr - dot qr truth| ≤ ε * (((29 : ℚ) / (28 : ℚ)) : ℝ) := by
  simpa only [real_gain] using physical_enclosure xr yr wr qr truth ε
    (dual_check_sound dual_checked).1 hm
end Q4
namespace Q4.Minimax
def w (i : Fin 7) : ℚ := ([((1 : ℚ) / (10 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((9 : ℚ) / (10 : ℚ)), ((0 : ℚ) / (1 : ℚ))] : List ℚ).getD i.val 0
def a (j : Fin 2) : ℚ := ([((1 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ))] : List ℚ).getD j.val 0
def wr (i : Fin 7) : ℝ := (w i : ℝ)
def ar (j : Fin 2) : ℝ := (a j : ℝ)
theorem optimality_checked : minimaxCheck x w Q4.q a ((1 : ℚ) / (1 : ℚ)) = true := by decide +kernel
theorem gain_checked : (∑ i, |w i|) = (((1 : ℚ) / (1 : ℚ)) : ℚ) := by decide +kernel
theorem real_gain : (∑ i, |wr i|) = (((1 : ℚ) / (1 : ℚ)) : ℝ) := by
  have h := congrArg (fun a : ℚ => (a : ℝ)) gain_checked
  simpa only [wr, Rat.cast_sum, Rat.cast_abs, Rat.cast_div, Rat.cast_intCast,
    Rat.cast_ofNat, Rat.cast_neg] using h
theorem globally_minimal_gain (v : Fin 7 → ℝ) (hv : Reproduces xr v Q4.qr) :
    (((1 : ℚ) / (1 : ℚ)) : ℝ) ≤ ∑ i, |v i| := by
  have h := minimax_check_sound optimality_checked
  have hm := minimax_weights_optimal xr wr Q4.qr ar h.2.1 h.2.2 v hv
  simpa only [real_gain] using hm
theorem sharp_radius (ε radius : ℝ) (he : 0 ≤ ε) :
    (∀ z : Fin 7 → ℝ, (∀ i, |z i - yr i| ≤ ε) → |dot wr z - dot wr yr| ≤ radius) ↔
      ε * (((1 : ℚ) / (1 : ℚ)) : ℝ) ≤ radius := by
  simpa only [real_gain] using sharp_radius_iff wr yr ε radius he
theorem no_reproducing_estimator_has_smaller_radius (ε radius : ℝ) (he : 0 ≤ ε)
    (v : Fin 7 → ℝ) (hv : Reproduces xr v Q4.qr)
    (hr : ∀ z, (∀ i, |z i - yr i| ≤ ε) → |dot v z - dot v yr| ≤ radius) :
    ε * (((1 : ℚ) / (1 : ℚ)) : ℝ) ≤ radius := by
  have h := minimax_check_sound optimality_checked
  have hm := minimax_radius_lower_bound xr yr wr Q4.qr ar h.2.1 h.2.2 ε radius he v hv hr
  simpa only [real_gain] using hm
theorem conditional_physical_enclosure (truth : Fin 2 → ℝ) (ε : ℝ)
    (hm : ∀ i, |yr i - prediction xr truth i| ≤ ε) :
    |dot wr yr - dot Q4.qr truth| ≤ ε * (((1 : ℚ) / (1 : ℚ)) : ℝ) := by
  simpa only [real_gain] using physical_enclosure xr yr wr Q4.qr truth ε
    (minimax_check_sound optimality_checked).1 hm
theorem uniform_minimax_over_all_prediction_functions (ε radius : ℝ) (he : 0 ≤ ε) :
    (∃ estimator : (Fin 7 → ℝ) → ℝ,
      ∀ truth observed, (∀ i, |observed i - prediction xr truth i| ≤ ε) →
        |estimator observed - dot Q4.qr truth| ≤ radius) ↔
      ε * (((1 : ℚ) / (1 : ℚ)) : ℝ) ≤ radius := by
  have h := minimax_check_sound optimality_checked
  simpa only [real_gain] using
    minimax_over_all_estimators_iff xr wr Q4.qr ar h.1 h.2.1 h.2.2 ε radius he
end Q4.Minimax
namespace Q5
def q (j : Fin 2) : ℚ := (((16 : ℚ) / (1 : ℚ)) : ℚ) ^ j.val
def w (i : Fin 7) : ℚ := ([((-1 : ℚ) / (8 : ℚ)), ((-1 : ℚ) / (28 : ℚ)), ((3 : ℚ) / (56 : ℚ)), ((1 : ℚ) / (7 : ℚ)), ((13 : ℚ) / (56 : ℚ)), ((9 : ℚ) / (28 : ℚ)), ((23 : ℚ) / (56 : ℚ))] : List ℚ).getD i.val 0
def d (j : Fin 2) : ℚ := ([((-39 : ℚ) / (112 : ℚ)), ((5 : ℚ) / (112 : ℚ))] : List ℚ).getD j.val 0
def wr (i : Fin 7) : ℝ := (w i : ℝ)
def qr (j : Fin 2) : ℝ := (q j : ℝ)
theorem dual_checked : dualCheck x w q d = true := by decide +kernel
theorem gain_checked : (∑ i, |w i|) = (((37 : ℚ) / (28 : ℚ)) : ℚ) := by decide +kernel
theorem real_gain : (∑ i, |wr i|) = (((37 : ℚ) / (28 : ℚ)) : ℝ) := by
  have h := congrArg (fun a : ℚ => (a : ℝ)) gain_checked
  simpa only [wr, Rat.cast_sum, Rat.cast_abs, Rat.cast_div, Rat.cast_intCast,
    Rat.cast_ofNat, Rat.cast_neg] using h
theorem fitted_query : dot wr yr = dot qr br :=
  dual_prediction xr yr wr qr br (fun j => (d j : ℝ))
    (fit_check_sound normal_checked) (dual_check_sound dual_checked).1
    (dual_check_sound dual_checked).2
theorem sharp_radius (ε radius : ℝ) (he : 0 ≤ ε) :
    (∀ z : Fin 7 → ℝ, (∀ i, |z i - yr i| ≤ ε) → |dot wr z - dot wr yr| ≤ radius) ↔
      ε * (((37 : ℚ) / (28 : ℚ)) : ℝ) ≤ radius := by
  simpa only [real_gain] using sharp_radius_iff wr yr ε radius he
theorem conditional_physical_enclosure (truth : Fin 2 → ℝ) (ε : ℝ)
    (hm : ∀ i, |yr i - prediction xr truth i| ≤ ε) :
    |dot wr yr - dot qr truth| ≤ ε * (((37 : ℚ) / (28 : ℚ)) : ℝ) := by
  simpa only [real_gain] using physical_enclosure xr yr wr qr truth ε
    (dual_check_sound dual_checked).1 hm
end Q5
namespace Q5.Minimax
def w (i : Fin 7) : ℚ := ([((1 : ℚ) / (12 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((11 : ℚ) / (12 : ℚ))] : List ℚ).getD i.val 0
def a (j : Fin 2) : ℚ := ([((1 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ))] : List ℚ).getD j.val 0
def wr (i : Fin 7) : ℝ := (w i : ℝ)
def ar (j : Fin 2) : ℝ := (a j : ℝ)
theorem optimality_checked : minimaxCheck x w Q5.q a ((1 : ℚ) / (1 : ℚ)) = true := by decide +kernel
theorem gain_checked : (∑ i, |w i|) = (((1 : ℚ) / (1 : ℚ)) : ℚ) := by decide +kernel
theorem real_gain : (∑ i, |wr i|) = (((1 : ℚ) / (1 : ℚ)) : ℝ) := by
  have h := congrArg (fun a : ℚ => (a : ℝ)) gain_checked
  simpa only [wr, Rat.cast_sum, Rat.cast_abs, Rat.cast_div, Rat.cast_intCast,
    Rat.cast_ofNat, Rat.cast_neg] using h
theorem globally_minimal_gain (v : Fin 7 → ℝ) (hv : Reproduces xr v Q5.qr) :
    (((1 : ℚ) / (1 : ℚ)) : ℝ) ≤ ∑ i, |v i| := by
  have h := minimax_check_sound optimality_checked
  have hm := minimax_weights_optimal xr wr Q5.qr ar h.2.1 h.2.2 v hv
  simpa only [real_gain] using hm
theorem sharp_radius (ε radius : ℝ) (he : 0 ≤ ε) :
    (∀ z : Fin 7 → ℝ, (∀ i, |z i - yr i| ≤ ε) → |dot wr z - dot wr yr| ≤ radius) ↔
      ε * (((1 : ℚ) / (1 : ℚ)) : ℝ) ≤ radius := by
  simpa only [real_gain] using sharp_radius_iff wr yr ε radius he
theorem no_reproducing_estimator_has_smaller_radius (ε radius : ℝ) (he : 0 ≤ ε)
    (v : Fin 7 → ℝ) (hv : Reproduces xr v Q5.qr)
    (hr : ∀ z, (∀ i, |z i - yr i| ≤ ε) → |dot v z - dot v yr| ≤ radius) :
    ε * (((1 : ℚ) / (1 : ℚ)) : ℝ) ≤ radius := by
  have h := minimax_check_sound optimality_checked
  have hm := minimax_radius_lower_bound xr yr wr Q5.qr ar h.2.1 h.2.2 ε radius he v hv hr
  simpa only [real_gain] using hm
theorem conditional_physical_enclosure (truth : Fin 2 → ℝ) (ε : ℝ)
    (hm : ∀ i, |yr i - prediction xr truth i| ≤ ε) :
    |dot wr yr - dot Q5.qr truth| ≤ ε * (((1 : ℚ) / (1 : ℚ)) : ℝ) := by
  simpa only [real_gain] using physical_enclosure xr yr wr Q5.qr truth ε
    (minimax_check_sound optimality_checked).1 hm
theorem uniform_minimax_over_all_prediction_functions (ε radius : ℝ) (he : 0 ≤ ε) :
    (∃ estimator : (Fin 7 → ℝ) → ℝ,
      ∀ truth observed, (∀ i, |observed i - prediction xr truth i| ≤ ε) →
        |estimator observed - dot Q5.qr truth| ≤ radius) ↔
      ε * (((1 : ℚ) / (1 : ℚ)) : ℝ) ≤ radius := by
  have h := minimax_check_sound optimality_checked
  simpa only [real_gain] using
    minimax_over_all_estimators_iff xr wr Q5.qr ar h.1 h.2.1 h.2.2 ε radius he
end Q5.Minimax
namespace Q6
def q (j : Fin 2) : ℚ := (((18 : ℚ) / (1 : ℚ)) : ℚ) ^ j.val
def w (i : Fin 7) : ℚ := ([((-13 : ℚ) / (56 : ℚ)), ((-3 : ℚ) / (28 : ℚ)), ((1 : ℚ) / (56 : ℚ)), ((1 : ℚ) / (7 : ℚ)), ((15 : ℚ) / (56 : ℚ)), ((11 : ℚ) / (28 : ℚ)), ((29 : ℚ) / (56 : ℚ))] : List ℚ).getD i.val 0
def d (j : Fin 2) : ℚ := ([((-61 : ℚ) / (112 : ℚ)), ((1 : ℚ) / (16 : ℚ))] : List ℚ).getD j.val 0
def wr (i : Fin 7) : ℝ := (w i : ℝ)
def qr (j : Fin 2) : ℝ := (q j : ℝ)
theorem dual_checked : dualCheck x w q d = true := by decide +kernel
theorem gain_checked : (∑ i, |w i|) = (((47 : ℚ) / (28 : ℚ)) : ℚ) := by decide +kernel
theorem real_gain : (∑ i, |wr i|) = (((47 : ℚ) / (28 : ℚ)) : ℝ) := by
  have h := congrArg (fun a : ℚ => (a : ℝ)) gain_checked
  simpa only [wr, Rat.cast_sum, Rat.cast_abs, Rat.cast_div, Rat.cast_intCast,
    Rat.cast_ofNat, Rat.cast_neg] using h
theorem fitted_query : dot wr yr = dot qr br :=
  dual_prediction xr yr wr qr br (fun j => (d j : ℝ))
    (fit_check_sound normal_checked) (dual_check_sound dual_checked).1
    (dual_check_sound dual_checked).2
theorem sharp_radius (ε radius : ℝ) (he : 0 ≤ ε) :
    (∀ z : Fin 7 → ℝ, (∀ i, |z i - yr i| ≤ ε) → |dot wr z - dot wr yr| ≤ radius) ↔
      ε * (((47 : ℚ) / (28 : ℚ)) : ℝ) ≤ radius := by
  simpa only [real_gain] using sharp_radius_iff wr yr ε radius he
theorem conditional_physical_enclosure (truth : Fin 2 → ℝ) (ε : ℝ)
    (hm : ∀ i, |yr i - prediction xr truth i| ≤ ε) :
    |dot wr yr - dot qr truth| ≤ ε * (((47 : ℚ) / (28 : ℚ)) : ℝ) := by
  simpa only [real_gain] using physical_enclosure xr yr wr qr truth ε
    (dual_check_sound dual_checked).1 hm
end Q6
namespace Q6.Minimax
def w (i : Fin 7) : ℚ := ([((-1 : ℚ) / (12 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((13 : ℚ) / (12 : ℚ))] : List ℚ).getD i.val 0
def a (j : Fin 2) : ℚ := ([((-11 : ℚ) / (6 : ℚ)), ((1 : ℚ) / (6 : ℚ))] : List ℚ).getD j.val 0
def wr (i : Fin 7) : ℝ := (w i : ℝ)
def ar (j : Fin 2) : ℝ := (a j : ℝ)
theorem optimality_checked : minimaxCheck x w Q6.q a ((7 : ℚ) / (6 : ℚ)) = true := by decide +kernel
theorem gain_checked : (∑ i, |w i|) = (((7 : ℚ) / (6 : ℚ)) : ℚ) := by decide +kernel
theorem real_gain : (∑ i, |wr i|) = (((7 : ℚ) / (6 : ℚ)) : ℝ) := by
  have h := congrArg (fun a : ℚ => (a : ℝ)) gain_checked
  simpa only [wr, Rat.cast_sum, Rat.cast_abs, Rat.cast_div, Rat.cast_intCast,
    Rat.cast_ofNat, Rat.cast_neg] using h
theorem globally_minimal_gain (v : Fin 7 → ℝ) (hv : Reproduces xr v Q6.qr) :
    (((7 : ℚ) / (6 : ℚ)) : ℝ) ≤ ∑ i, |v i| := by
  have h := minimax_check_sound optimality_checked
  have hm := minimax_weights_optimal xr wr Q6.qr ar h.2.1 h.2.2 v hv
  simpa only [real_gain] using hm
theorem sharp_radius (ε radius : ℝ) (he : 0 ≤ ε) :
    (∀ z : Fin 7 → ℝ, (∀ i, |z i - yr i| ≤ ε) → |dot wr z - dot wr yr| ≤ radius) ↔
      ε * (((7 : ℚ) / (6 : ℚ)) : ℝ) ≤ radius := by
  simpa only [real_gain] using sharp_radius_iff wr yr ε radius he
theorem no_reproducing_estimator_has_smaller_radius (ε radius : ℝ) (he : 0 ≤ ε)
    (v : Fin 7 → ℝ) (hv : Reproduces xr v Q6.qr)
    (hr : ∀ z, (∀ i, |z i - yr i| ≤ ε) → |dot v z - dot v yr| ≤ radius) :
    ε * (((7 : ℚ) / (6 : ℚ)) : ℝ) ≤ radius := by
  have h := minimax_check_sound optimality_checked
  have hm := minimax_radius_lower_bound xr yr wr Q6.qr ar h.2.1 h.2.2 ε radius he v hv hr
  simpa only [real_gain] using hm
theorem conditional_physical_enclosure (truth : Fin 2 → ℝ) (ε : ℝ)
    (hm : ∀ i, |yr i - prediction xr truth i| ≤ ε) :
    |dot wr yr - dot Q6.qr truth| ≤ ε * (((7 : ℚ) / (6 : ℚ)) : ℝ) := by
  simpa only [real_gain] using physical_enclosure xr yr wr Q6.qr truth ε
    (minimax_check_sound optimality_checked).1 hm
theorem uniform_minimax_over_all_prediction_functions (ε radius : ℝ) (he : 0 ≤ ε) :
    (∃ estimator : (Fin 7 → ℝ) → ℝ,
      ∀ truth observed, (∀ i, |observed i - prediction xr truth i| ≤ ε) →
        |estimator observed - dot Q6.qr truth| ≤ radius) ↔
      ε * (((7 : ℚ) / (6 : ℚ)) : ℝ) ≤ radius := by
  have h := minimax_check_sound optimality_checked
  simpa only [real_gain] using
    minimax_over_all_estimators_iff xr wr Q6.qr ar h.1 h.2.1 h.2.2 ε radius he
end Q6.Minimax
namespace Q7
def q (j : Fin 2) : ℚ := (((24 : ℚ) / (1 : ℚ)) : ℚ) ^ j.val
def w (i : Fin 7) : ℚ := ([((-31 : ℚ) / (56 : ℚ)), ((-9 : ℚ) / (28 : ℚ)), ((-5 : ℚ) / (56 : ℚ)), ((1 : ℚ) / (7 : ℚ)), ((3 : ℚ) / (8 : ℚ)), ((17 : ℚ) / (28 : ℚ)), ((47 : ℚ) / (56 : ℚ))] : List ℚ).getD i.val 0
def d (j : Fin 2) : ℚ := ([((-127 : ℚ) / (112 : ℚ)), ((13 : ℚ) / (112 : ℚ))] : List ℚ).getD j.val 0
def wr (i : Fin 7) : ℝ := (w i : ℝ)
def qr (j : Fin 2) : ℝ := (q j : ℝ)
theorem dual_checked : dualCheck x w q d = true := by decide +kernel
theorem gain_checked : (∑ i, |w i|) = (((41 : ℚ) / (14 : ℚ)) : ℚ) := by decide +kernel
theorem real_gain : (∑ i, |wr i|) = (((41 : ℚ) / (14 : ℚ)) : ℝ) := by
  have h := congrArg (fun a : ℚ => (a : ℝ)) gain_checked
  simpa only [wr, Rat.cast_sum, Rat.cast_abs, Rat.cast_div, Rat.cast_intCast,
    Rat.cast_ofNat, Rat.cast_neg] using h
theorem fitted_query : dot wr yr = dot qr br :=
  dual_prediction xr yr wr qr br (fun j => (d j : ℝ))
    (fit_check_sound normal_checked) (dual_check_sound dual_checked).1
    (dual_check_sound dual_checked).2
theorem sharp_radius (ε radius : ℝ) (he : 0 ≤ ε) :
    (∀ z : Fin 7 → ℝ, (∀ i, |z i - yr i| ≤ ε) → |dot wr z - dot wr yr| ≤ radius) ↔
      ε * (((41 : ℚ) / (14 : ℚ)) : ℝ) ≤ radius := by
  simpa only [real_gain] using sharp_radius_iff wr yr ε radius he
theorem conditional_physical_enclosure (truth : Fin 2 → ℝ) (ε : ℝ)
    (hm : ∀ i, |yr i - prediction xr truth i| ≤ ε) :
    |dot wr yr - dot qr truth| ≤ ε * (((41 : ℚ) / (14 : ℚ)) : ℝ) := by
  simpa only [real_gain] using physical_enclosure xr yr wr qr truth ε
    (dual_check_sound dual_checked).1 hm
end Q7
namespace Q7.Minimax
def w (i : Fin 7) : ℚ := ([((-7 : ℚ) / (12 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((19 : ℚ) / (12 : ℚ))] : List ℚ).getD i.val 0
def a (j : Fin 2) : ℚ := ([((-11 : ℚ) / (6 : ℚ)), ((1 : ℚ) / (6 : ℚ))] : List ℚ).getD j.val 0
def wr (i : Fin 7) : ℝ := (w i : ℝ)
def ar (j : Fin 2) : ℝ := (a j : ℝ)
theorem optimality_checked : minimaxCheck x w Q7.q a ((13 : ℚ) / (6 : ℚ)) = true := by decide +kernel
theorem gain_checked : (∑ i, |w i|) = (((13 : ℚ) / (6 : ℚ)) : ℚ) := by decide +kernel
theorem real_gain : (∑ i, |wr i|) = (((13 : ℚ) / (6 : ℚ)) : ℝ) := by
  have h := congrArg (fun a : ℚ => (a : ℝ)) gain_checked
  simpa only [wr, Rat.cast_sum, Rat.cast_abs, Rat.cast_div, Rat.cast_intCast,
    Rat.cast_ofNat, Rat.cast_neg] using h
theorem globally_minimal_gain (v : Fin 7 → ℝ) (hv : Reproduces xr v Q7.qr) :
    (((13 : ℚ) / (6 : ℚ)) : ℝ) ≤ ∑ i, |v i| := by
  have h := minimax_check_sound optimality_checked
  have hm := minimax_weights_optimal xr wr Q7.qr ar h.2.1 h.2.2 v hv
  simpa only [real_gain] using hm
theorem sharp_radius (ε radius : ℝ) (he : 0 ≤ ε) :
    (∀ z : Fin 7 → ℝ, (∀ i, |z i - yr i| ≤ ε) → |dot wr z - dot wr yr| ≤ radius) ↔
      ε * (((13 : ℚ) / (6 : ℚ)) : ℝ) ≤ radius := by
  simpa only [real_gain] using sharp_radius_iff wr yr ε radius he
theorem no_reproducing_estimator_has_smaller_radius (ε radius : ℝ) (he : 0 ≤ ε)
    (v : Fin 7 → ℝ) (hv : Reproduces xr v Q7.qr)
    (hr : ∀ z, (∀ i, |z i - yr i| ≤ ε) → |dot v z - dot v yr| ≤ radius) :
    ε * (((13 : ℚ) / (6 : ℚ)) : ℝ) ≤ radius := by
  have h := minimax_check_sound optimality_checked
  have hm := minimax_radius_lower_bound xr yr wr Q7.qr ar h.2.1 h.2.2 ε radius he v hv hr
  simpa only [real_gain] using hm
theorem conditional_physical_enclosure (truth : Fin 2 → ℝ) (ε : ℝ)
    (hm : ∀ i, |yr i - prediction xr truth i| ≤ ε) :
    |dot wr yr - dot Q7.qr truth| ≤ ε * (((13 : ℚ) / (6 : ℚ)) : ℝ) := by
  simpa only [real_gain] using physical_enclosure xr yr wr Q7.qr truth ε
    (minimax_check_sound optimality_checked).1 hm
theorem uniform_minimax_over_all_prediction_functions (ε radius : ℝ) (he : 0 ≤ ε) :
    (∃ estimator : (Fin 7 → ℝ) → ℝ,
      ∀ truth observed, (∀ i, |observed i - prediction xr truth i| ≤ ε) →
        |estimator observed - dot Q7.qr truth| ≤ radius) ↔
      ε * (((13 : ℚ) / (6 : ℚ)) : ℝ) ≤ radius := by
  have h := minimax_check_sound optimality_checked
  simpa only [real_gain] using
    minimax_over_all_estimators_iff xr wr Q7.qr ar h.1 h.2.1 h.2.2 ε radius he
end Q7.Minimax
end PCSCalibrationReplay.M0

namespace PCSCalibrationReplay.M1
def abscissa (i : Fin 14) : ℚ := ([((5 : ℚ) / (1 : ℚ)), ((6 : ℚ) / (1 : ℚ)), ((7 : ℚ) / (1 : ℚ)), ((8 : ℚ) / (1 : ℚ)), ((9 : ℚ) / (1 : ℚ)), ((10 : ℚ) / (1 : ℚ)), ((11 : ℚ) / (1 : ℚ)), ((12 : ℚ) / (1 : ℚ)), ((13 : ℚ) / (1 : ℚ)), ((14 : ℚ) / (1 : ℚ)), ((15 : ℚ) / (1 : ℚ)), ((16 : ℚ) / (1 : ℚ)), ((17 : ℚ) / (1 : ℚ)), ((18 : ℚ) / (1 : ℚ))] : List ℚ).getD i.val 0
def x (i : Fin 14) (j : Fin 2) : ℚ := abscissa i ^ j.val
def y (i : Fin 14) : ℚ := ([((1 : ℚ) / (25 : ℚ)), ((17 : ℚ) / (100 : ℚ)), ((37 : ℚ) / (100 : ℚ)), ((33 : ℚ) / (50 : ℚ)), ((53 : ℚ) / (50 : ℚ)), ((159 : ℚ) / (100 : ℚ)), ((233 : ℚ) / (100 : ℚ)), ((329 : ℚ) / (100 : ℚ)), ((461 : ℚ) / (100 : ℚ)), ((711 : ℚ) / (100 : ℚ)), ((1199 : ℚ) / (100 : ℚ)), ((2109 : ℚ) / (100 : ℚ)), ((3501 : ℚ) / (100 : ℚ)), ((259 : ℚ) / (5 : ℚ))] : List ℚ).getD i.val 0
def b (j : Fin 2) : ℚ := ([((-1107867 : ℚ) / (45500 : ℚ)), ((68109 : ℚ) / (22750 : ℚ))] : List ℚ).getD j.val 0
def xr (i : Fin 14) (j : Fin 2) : ℝ := (x i j : ℝ)
def yr (i : Fin 14) : ℝ := (y i : ℝ)
def br (j : Fin 2) : ℝ := (b j : ℝ)
theorem normal_checked : fitCheck x y b = true := by decide +kernel
theorem residual_checked : loss x y b = ((1283397867 : ℚ) / (1137500 : ℚ)) := by decide +kernel
theorem global_optimum : ∀ c : Fin 2 → ℝ,
    (((1283397867 : ℚ) / (1137500 : ℚ)) : ℝ) ≤ loss xr yr c := by
  have hs : loss xr yr br = (((1283397867 : ℚ) / (1137500 : ℚ)) : ℝ) := by
    calc
      loss xr yr br = ((loss x y b : ℚ) : ℝ) := (cast_loss x y b).symm
      _ = (((1283397867 : ℚ) / (1137500 : ℚ)) : ℝ) := by
        simpa only [Rat.cast_div, Rat.cast_intCast, Rat.cast_ofNat, Rat.cast_neg]
          using congrArg (fun a : ℚ => (a : ℝ)) residual_checked
  simpa only [hs] using global_minimum xr yr br (fit_check_sound normal_checked)
theorem excludes_every_better_model (threshold : ℝ)
    (h : threshold < (((1283397867 : ℚ) / (1137500 : ℚ)) : ℝ)) :
    ∀ c : Fin 2 → ℝ, threshold < loss xr yr c := by
  intro c
  exact h.trans_le (global_optimum c)
theorem uniform_error_exclusion (ε : ℝ) (he : 0 ≤ ε)
    (hgap : (14 : ℝ) * ε ^ 2 < (((1283397867 : ℚ) / (1137500 : ℚ)) : ℝ)) :
    ¬ (∃ c : Fin 2 → ℝ, ∀ i, |yr i - prediction xr c i| ≤ ε) :=
  PCSReal.Calibration.uniform_error_exclusion xr yr (((1283397867 : ℚ) / (1137500 : ℚ)) : ℝ) ε
    global_optimum he (by simpa using hgap)
end PCSCalibrationReplay.M1

namespace PCSCalibrationReplay.M2
def abscissa (i : Fin 7) : ℚ := ([((5 : ℚ) / (1 : ℚ)), ((7 : ℚ) / (1 : ℚ)), ((9 : ℚ) / (1 : ℚ)), ((11 : ℚ) / (1 : ℚ)), ((13 : ℚ) / (1 : ℚ)), ((15 : ℚ) / (1 : ℚ)), ((17 : ℚ) / (1 : ℚ))] : List ℚ).getD i.val 0
def x (i : Fin 7) (j : Fin 3) : ℚ := abscissa i ^ j.val
def y (i : Fin 7) : ℚ := ([((1 : ℚ) / (25 : ℚ)), ((37 : ℚ) / (100 : ℚ)), ((53 : ℚ) / (50 : ℚ)), ((233 : ℚ) / (100 : ℚ)), ((461 : ℚ) / (100 : ℚ)), ((1199 : ℚ) / (100 : ℚ)), ((3501 : ℚ) / (100 : ℚ))] : List ℚ).getD i.val 0
def b (j : Fin 3) : ℚ := ([((40017 : ℚ) / (1400 : ℚ)), ((-20717 : ℚ) / (2800 : ℚ)), ((1241 : ℚ) / (2800 : ℚ))] : List ℚ).getD j.val 0
def xr (i : Fin 7) (j : Fin 3) : ℝ := (x i j : ℝ)
def yr (i : Fin 7) : ℝ := (y i : ℝ)
def br (j : Fin 3) : ℝ := (b j : ℝ)
theorem normal_checked : fitCheck x y b = true := by decide +kernel
theorem residual_checked : loss x y b = ((5272353 : ℚ) / (70000 : ℚ)) := by decide +kernel
theorem global_optimum : ∀ c : Fin 3 → ℝ,
    (((5272353 : ℚ) / (70000 : ℚ)) : ℝ) ≤ loss xr yr c := by
  have hs : loss xr yr br = (((5272353 : ℚ) / (70000 : ℚ)) : ℝ) := by
    calc
      loss xr yr br = ((loss x y b : ℚ) : ℝ) := (cast_loss x y b).symm
      _ = (((5272353 : ℚ) / (70000 : ℚ)) : ℝ) := by
        simpa only [Rat.cast_div, Rat.cast_intCast, Rat.cast_ofNat, Rat.cast_neg]
          using congrArg (fun a : ℚ => (a : ℝ)) residual_checked
  simpa only [hs] using global_minimum xr yr br (fit_check_sound normal_checked)
theorem excludes_every_better_model (threshold : ℝ)
    (h : threshold < (((5272353 : ℚ) / (70000 : ℚ)) : ℝ)) :
    ∀ c : Fin 3 → ℝ, threshold < loss xr yr c := by
  intro c
  exact h.trans_le (global_optimum c)
theorem uniform_error_exclusion (ε : ℝ) (he : 0 ≤ ε)
    (hgap : (7 : ℝ) * ε ^ 2 < (((5272353 : ℚ) / (70000 : ℚ)) : ℝ)) :
    ¬ (∃ c : Fin 3 → ℝ, ∀ i, |yr i - prediction xr c i| ≤ ε) :=
  PCSReal.Calibration.uniform_error_exclusion xr yr (((5272353 : ℚ) / (70000 : ℚ)) : ℝ) ε
    global_optimum he (by simpa using hgap)
namespace Q0
def q (j : Fin 3) : ℚ := (((6 : ℚ) / (1 : ℚ)) : ℚ) ^ j.val
def w (i : Fin 7) : ℚ := ([((61 : ℚ) / (112 : ℚ)), ((9 : ℚ) / (28 : ℚ)), ((17 : ℚ) / (112 : ℚ)), ((1 : ℚ) / (28 : ℚ)), ((-3 : ℚ) / (112 : ℚ)), ((-1 : ℚ) / (28 : ℚ)), ((1 : ℚ) / (112 : ℚ))] : List ℚ).getD i.val 0
def d (j : Fin 3) : ℚ := ([((599 : ℚ) / (448 : ℚ)), ((-43 : ℚ) / (224 : ℚ)), ((3 : ℚ) / (448 : ℚ))] : List ℚ).getD j.val 0
def wr (i : Fin 7) : ℝ := (w i : ℝ)
def qr (j : Fin 3) : ℝ := (q j : ℝ)
theorem dual_checked : dualCheck x w q d = true := by decide +kernel
theorem gain_checked : (∑ i, |w i|) = (((9 : ℚ) / (8 : ℚ)) : ℚ) := by decide +kernel
theorem real_gain : (∑ i, |wr i|) = (((9 : ℚ) / (8 : ℚ)) : ℝ) := by
  have h := congrArg (fun a : ℚ => (a : ℝ)) gain_checked
  simpa only [wr, Rat.cast_sum, Rat.cast_abs, Rat.cast_div, Rat.cast_intCast,
    Rat.cast_ofNat, Rat.cast_neg] using h
theorem fitted_query : dot wr yr = dot qr br :=
  dual_prediction xr yr wr qr br (fun j => (d j : ℝ))
    (fit_check_sound normal_checked) (dual_check_sound dual_checked).1
    (dual_check_sound dual_checked).2
theorem sharp_radius (ε radius : ℝ) (he : 0 ≤ ε) :
    (∀ z : Fin 7 → ℝ, (∀ i, |z i - yr i| ≤ ε) → |dot wr z - dot wr yr| ≤ radius) ↔
      ε * (((9 : ℚ) / (8 : ℚ)) : ℝ) ≤ radius := by
  simpa only [real_gain] using sharp_radius_iff wr yr ε radius he
theorem conditional_physical_enclosure (truth : Fin 3 → ℝ) (ε : ℝ)
    (hm : ∀ i, |yr i - prediction xr truth i| ≤ ε) :
    |dot wr yr - dot qr truth| ≤ ε * (((9 : ℚ) / (8 : ℚ)) : ℝ) := by
  simpa only [real_gain] using physical_enclosure xr yr wr qr truth ε
    (dual_check_sound dual_checked).1 hm
end Q0
namespace Q0.Minimax
def w (i : Fin 7) : ℚ := ([((11 : ℚ) / (24 : ℚ)), ((11 : ℚ) / (20 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((-1 : ℚ) / (120 : ℚ))] : List ℚ).getD i.val 0
def a (j : Fin 3) : ℚ := ([((5 : ℚ) / (12 : ℚ)), ((1 : ℚ) / (5 : ℚ)), ((-1 : ℚ) / (60 : ℚ))] : List ℚ).getD j.val 0
def wr (i : Fin 7) : ℝ := (w i : ℝ)
def ar (j : Fin 3) : ℝ := (a j : ℝ)
theorem optimality_checked : minimaxCheck x w Q0.q a ((61 : ℚ) / (60 : ℚ)) = true := by decide +kernel
theorem gain_checked : (∑ i, |w i|) = (((61 : ℚ) / (60 : ℚ)) : ℚ) := by decide +kernel
theorem real_gain : (∑ i, |wr i|) = (((61 : ℚ) / (60 : ℚ)) : ℝ) := by
  have h := congrArg (fun a : ℚ => (a : ℝ)) gain_checked
  simpa only [wr, Rat.cast_sum, Rat.cast_abs, Rat.cast_div, Rat.cast_intCast,
    Rat.cast_ofNat, Rat.cast_neg] using h
theorem globally_minimal_gain (v : Fin 7 → ℝ) (hv : Reproduces xr v Q0.qr) :
    (((61 : ℚ) / (60 : ℚ)) : ℝ) ≤ ∑ i, |v i| := by
  have h := minimax_check_sound optimality_checked
  have hm := minimax_weights_optimal xr wr Q0.qr ar h.2.1 h.2.2 v hv
  simpa only [real_gain] using hm
theorem sharp_radius (ε radius : ℝ) (he : 0 ≤ ε) :
    (∀ z : Fin 7 → ℝ, (∀ i, |z i - yr i| ≤ ε) → |dot wr z - dot wr yr| ≤ radius) ↔
      ε * (((61 : ℚ) / (60 : ℚ)) : ℝ) ≤ radius := by
  simpa only [real_gain] using sharp_radius_iff wr yr ε radius he
theorem no_reproducing_estimator_has_smaller_radius (ε radius : ℝ) (he : 0 ≤ ε)
    (v : Fin 7 → ℝ) (hv : Reproduces xr v Q0.qr)
    (hr : ∀ z, (∀ i, |z i - yr i| ≤ ε) → |dot v z - dot v yr| ≤ radius) :
    ε * (((61 : ℚ) / (60 : ℚ)) : ℝ) ≤ radius := by
  have h := minimax_check_sound optimality_checked
  have hm := minimax_radius_lower_bound xr yr wr Q0.qr ar h.2.1 h.2.2 ε radius he v hv hr
  simpa only [real_gain] using hm
theorem conditional_physical_enclosure (truth : Fin 3 → ℝ) (ε : ℝ)
    (hm : ∀ i, |yr i - prediction xr truth i| ≤ ε) :
    |dot wr yr - dot Q0.qr truth| ≤ ε * (((61 : ℚ) / (60 : ℚ)) : ℝ) := by
  simpa only [real_gain] using physical_enclosure xr yr wr Q0.qr truth ε
    (minimax_check_sound optimality_checked).1 hm
theorem uniform_minimax_over_all_prediction_functions (ε radius : ℝ) (he : 0 ≤ ε) :
    (∃ estimator : (Fin 7 → ℝ) → ℝ,
      ∀ truth observed, (∀ i, |observed i - prediction xr truth i| ≤ ε) →
        |estimator observed - dot Q0.qr truth| ≤ radius) ↔
      ε * (((61 : ℚ) / (60 : ℚ)) : ℝ) ≤ radius := by
  have h := minimax_check_sound optimality_checked
  simpa only [real_gain] using
    minimax_over_all_estimators_iff xr wr Q0.qr ar h.1 h.2.1 h.2.2 ε radius he
end Q0.Minimax
namespace Q1
def q (j : Fin 3) : ℚ := (((8 : ℚ) / (1 : ℚ)) : ℚ) ^ j.val
def w (i : Fin 7) : ℚ := ([((67 : ℚ) / (336 : ℚ)), ((1 : ℚ) / (4 : ℚ)), ((29 : ℚ) / (112 : ℚ)), ((19 : ℚ) / (84 : ℚ)), ((17 : ℚ) / (112 : ℚ)), ((1 : ℚ) / (28 : ℚ)), ((-41 : ℚ) / (336 : ℚ))] : List ℚ).getD i.val 0
def d (j : Fin 3) : ℚ := ([((-7 : ℚ) / (64 : ℚ)), ((59 : ℚ) / (672 : ℚ)), ((-1 : ℚ) / (192 : ℚ))] : List ℚ).getD j.val 0
def wr (i : Fin 7) : ℝ := (w i : ℝ)
def qr (j : Fin 3) : ℝ := (q j : ℝ)
theorem dual_checked : dualCheck x w q d = true := by decide +kernel
theorem gain_checked : (∑ i, |w i|) = (((209 : ℚ) / (168 : ℚ)) : ℚ) := by decide +kernel
theorem real_gain : (∑ i, |wr i|) = (((209 : ℚ) / (168 : ℚ)) : ℝ) := by
  have h := congrArg (fun a : ℚ => (a : ℝ)) gain_checked
  simpa only [wr, Rat.cast_sum, Rat.cast_abs, Rat.cast_div, Rat.cast_intCast,
    Rat.cast_ofNat, Rat.cast_neg] using h
theorem fitted_query : dot wr yr = dot qr br :=
  dual_prediction xr yr wr qr br (fun j => (d j : ℝ))
    (fit_check_sound normal_checked) (dual_check_sound dual_checked).1
    (dual_check_sound dual_checked).2
theorem sharp_radius (ε radius : ℝ) (he : 0 ≤ ε) :
    (∀ z : Fin 7 → ℝ, (∀ i, |z i - yr i| ≤ ε) → |dot wr z - dot wr yr| ≤ radius) ↔
      ε * (((209 : ℚ) / (168 : ℚ)) : ℝ) ≤ radius := by
  simpa only [real_gain] using sharp_radius_iff wr yr ε radius he
theorem conditional_physical_enclosure (truth : Fin 3 → ℝ) (ε : ℝ)
    (hm : ∀ i, |yr i - prediction xr truth i| ≤ ε) :
    |dot wr yr - dot qr truth| ≤ ε * (((209 : ℚ) / (168 : ℚ)) : ℝ) := by
  simpa only [real_gain] using physical_enclosure xr yr wr qr truth ε
    (dual_check_sound dual_checked).1 hm
end Q1
namespace Q1.Minimax
def w (i : Fin 7) : ℚ := ([((0 : ℚ) / (1 : ℚ)), ((9 : ℚ) / (20 : ℚ)), ((9 : ℚ) / (16 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((-1 : ℚ) / (80 : ℚ))] : List ℚ).getD i.val 0
def a (j : Fin 3) : ℚ := ([((-23 : ℚ) / (40 : ℚ)), ((2 : ℚ) / (5 : ℚ)), ((-1 : ℚ) / (40 : ℚ))] : List ℚ).getD j.val 0
def wr (i : Fin 7) : ℝ := (w i : ℝ)
def ar (j : Fin 3) : ℝ := (a j : ℝ)
theorem optimality_checked : minimaxCheck x w Q1.q a ((41 : ℚ) / (40 : ℚ)) = true := by decide +kernel
theorem gain_checked : (∑ i, |w i|) = (((41 : ℚ) / (40 : ℚ)) : ℚ) := by decide +kernel
theorem real_gain : (∑ i, |wr i|) = (((41 : ℚ) / (40 : ℚ)) : ℝ) := by
  have h := congrArg (fun a : ℚ => (a : ℝ)) gain_checked
  simpa only [wr, Rat.cast_sum, Rat.cast_abs, Rat.cast_div, Rat.cast_intCast,
    Rat.cast_ofNat, Rat.cast_neg] using h
theorem globally_minimal_gain (v : Fin 7 → ℝ) (hv : Reproduces xr v Q1.qr) :
    (((41 : ℚ) / (40 : ℚ)) : ℝ) ≤ ∑ i, |v i| := by
  have h := minimax_check_sound optimality_checked
  have hm := minimax_weights_optimal xr wr Q1.qr ar h.2.1 h.2.2 v hv
  simpa only [real_gain] using hm
theorem sharp_radius (ε radius : ℝ) (he : 0 ≤ ε) :
    (∀ z : Fin 7 → ℝ, (∀ i, |z i - yr i| ≤ ε) → |dot wr z - dot wr yr| ≤ radius) ↔
      ε * (((41 : ℚ) / (40 : ℚ)) : ℝ) ≤ radius := by
  simpa only [real_gain] using sharp_radius_iff wr yr ε radius he
theorem no_reproducing_estimator_has_smaller_radius (ε radius : ℝ) (he : 0 ≤ ε)
    (v : Fin 7 → ℝ) (hv : Reproduces xr v Q1.qr)
    (hr : ∀ z, (∀ i, |z i - yr i| ≤ ε) → |dot v z - dot v yr| ≤ radius) :
    ε * (((41 : ℚ) / (40 : ℚ)) : ℝ) ≤ radius := by
  have h := minimax_check_sound optimality_checked
  have hm := minimax_radius_lower_bound xr yr wr Q1.qr ar h.2.1 h.2.2 ε radius he v hv hr
  simpa only [real_gain] using hm
theorem conditional_physical_enclosure (truth : Fin 3 → ℝ) (ε : ℝ)
    (hm : ∀ i, |yr i - prediction xr truth i| ≤ ε) :
    |dot wr yr - dot Q1.qr truth| ≤ ε * (((41 : ℚ) / (40 : ℚ)) : ℝ) := by
  simpa only [real_gain] using physical_enclosure xr yr wr Q1.qr truth ε
    (minimax_check_sound optimality_checked).1 hm
theorem uniform_minimax_over_all_prediction_functions (ε radius : ℝ) (he : 0 ≤ ε) :
    (∃ estimator : (Fin 7 → ℝ) → ℝ,
      ∀ truth observed, (∀ i, |observed i - prediction xr truth i| ≤ ε) →
        |estimator observed - dot Q1.qr truth| ≤ radius) ↔
      ε * (((41 : ℚ) / (40 : ℚ)) : ℝ) ≤ radius := by
  have h := minimax_check_sound optimality_checked
  simpa only [real_gain] using
    minimax_over_all_estimators_iff xr wr Q1.qr ar h.1 h.2.1 h.2.2 ε radius he
end Q1.Minimax
namespace Q2
def q (j : Fin 3) : ℚ := (((10 : ℚ) / (1 : ℚ)) : ℚ) ^ j.val
def w (i : Fin 7) : ℚ := ([((-3 : ℚ) / (112 : ℚ)), ((5 : ℚ) / (28 : ℚ)), ((33 : ℚ) / (112 : ℚ)), ((9 : ℚ) / (28 : ℚ)), ((29 : ℚ) / (112 : ℚ)), ((3 : ℚ) / (28 : ℚ)), ((-15 : ℚ) / (112 : ℚ))] : List ℚ).getD i.val 0
def d (j : Fin 3) : ℚ := ([((-417 : ℚ) / (448 : ℚ)), ((53 : ℚ) / (224 : ℚ)), ((-5 : ℚ) / (448 : ℚ))] : List ℚ).getD j.val 0
def wr (i : Fin 7) : ℝ := (w i : ℝ)
def qr (j : Fin 3) : ℝ := (q j : ℝ)
theorem dual_checked : dualCheck x w q d = true := by decide +kernel
theorem gain_checked : (∑ i, |w i|) = (((37 : ℚ) / (28 : ℚ)) : ℚ) := by decide +kernel
theorem real_gain : (∑ i, |wr i|) = (((37 : ℚ) / (28 : ℚ)) : ℝ) := by
  have h := congrArg (fun a : ℚ => (a : ℝ)) gain_checked
  simpa only [wr, Rat.cast_sum, Rat.cast_abs, Rat.cast_div, Rat.cast_intCast,
    Rat.cast_ofNat, Rat.cast_neg] using h
theorem fitted_query : dot wr yr = dot qr br :=
  dual_prediction xr yr wr qr br (fun j => (d j : ℝ))
    (fit_check_sound normal_checked) (dual_check_sound dual_checked).1
    (dual_check_sound dual_checked).2
theorem sharp_radius (ε radius : ℝ) (he : 0 ≤ ε) :
    (∀ z : Fin 7 → ℝ, (∀ i, |z i - yr i| ≤ ε) → |dot wr z - dot wr yr| ≤ radius) ↔
      ε * (((37 : ℚ) / (28 : ℚ)) : ℝ) ≤ radius := by
  simpa only [real_gain] using sharp_radius_iff wr yr ε radius he
theorem conditional_physical_enclosure (truth : Fin 3 → ℝ) (ε : ℝ)
    (hm : ∀ i, |yr i - prediction xr truth i| ≤ ε) :
    |dot wr yr - dot qr truth| ≤ ε * (((37 : ℚ) / (28 : ℚ)) : ℝ) := by
  simpa only [real_gain] using physical_enclosure xr yr wr qr truth ε
    (dual_check_sound dual_checked).1 hm
end Q2
namespace Q2.Minimax
def w (i : Fin 7) : ℚ := ([((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((7 : ℚ) / (16 : ℚ)), ((7 : ℚ) / (12 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((-1 : ℚ) / (48 : ℚ))] : List ℚ).getD i.val 0
def a (j : Fin 3) : ℚ := ([((-25 : ℚ) / (8 : ℚ)), ((5 : ℚ) / (6 : ℚ)), ((-1 : ℚ) / (24 : ℚ))] : List ℚ).getD j.val 0
def wr (i : Fin 7) : ℝ := (w i : ℝ)
def ar (j : Fin 3) : ℝ := (a j : ℝ)
theorem optimality_checked : minimaxCheck x w Q2.q a ((25 : ℚ) / (24 : ℚ)) = true := by decide +kernel
theorem gain_checked : (∑ i, |w i|) = (((25 : ℚ) / (24 : ℚ)) : ℚ) := by decide +kernel
theorem real_gain : (∑ i, |wr i|) = (((25 : ℚ) / (24 : ℚ)) : ℝ) := by
  have h := congrArg (fun a : ℚ => (a : ℝ)) gain_checked
  simpa only [wr, Rat.cast_sum, Rat.cast_abs, Rat.cast_div, Rat.cast_intCast,
    Rat.cast_ofNat, Rat.cast_neg] using h
theorem globally_minimal_gain (v : Fin 7 → ℝ) (hv : Reproduces xr v Q2.qr) :
    (((25 : ℚ) / (24 : ℚ)) : ℝ) ≤ ∑ i, |v i| := by
  have h := minimax_check_sound optimality_checked
  have hm := minimax_weights_optimal xr wr Q2.qr ar h.2.1 h.2.2 v hv
  simpa only [real_gain] using hm
theorem sharp_radius (ε radius : ℝ) (he : 0 ≤ ε) :
    (∀ z : Fin 7 → ℝ, (∀ i, |z i - yr i| ≤ ε) → |dot wr z - dot wr yr| ≤ radius) ↔
      ε * (((25 : ℚ) / (24 : ℚ)) : ℝ) ≤ radius := by
  simpa only [real_gain] using sharp_radius_iff wr yr ε radius he
theorem no_reproducing_estimator_has_smaller_radius (ε radius : ℝ) (he : 0 ≤ ε)
    (v : Fin 7 → ℝ) (hv : Reproduces xr v Q2.qr)
    (hr : ∀ z, (∀ i, |z i - yr i| ≤ ε) → |dot v z - dot v yr| ≤ radius) :
    ε * (((25 : ℚ) / (24 : ℚ)) : ℝ) ≤ radius := by
  have h := minimax_check_sound optimality_checked
  have hm := minimax_radius_lower_bound xr yr wr Q2.qr ar h.2.1 h.2.2 ε radius he v hv hr
  simpa only [real_gain] using hm
theorem conditional_physical_enclosure (truth : Fin 3 → ℝ) (ε : ℝ)
    (hm : ∀ i, |yr i - prediction xr truth i| ≤ ε) :
    |dot wr yr - dot Q2.qr truth| ≤ ε * (((25 : ℚ) / (24 : ℚ)) : ℝ) := by
  simpa only [real_gain] using physical_enclosure xr yr wr Q2.qr truth ε
    (minimax_check_sound optimality_checked).1 hm
theorem uniform_minimax_over_all_prediction_functions (ε radius : ℝ) (he : 0 ≤ ε) :
    (∃ estimator : (Fin 7 → ℝ) → ℝ,
      ∀ truth observed, (∀ i, |observed i - prediction xr truth i| ≤ ε) →
        |estimator observed - dot Q2.qr truth| ≤ radius) ↔
      ε * (((25 : ℚ) / (24 : ℚ)) : ℝ) ≤ radius := by
  have h := minimax_check_sound optimality_checked
  simpa only [real_gain] using
    minimax_over_all_estimators_iff xr wr Q2.qr ar h.1 h.2.1 h.2.2 ε radius he
end Q2.Minimax
namespace Q3
def q (j : Fin 3) : ℚ := (((12 : ℚ) / (1 : ℚ)) : ℚ) ^ j.val
def w (i : Fin 7) : ℚ := ([((-15 : ℚ) / (112 : ℚ)), ((3 : ℚ) / (28 : ℚ)), ((29 : ℚ) / (112 : ℚ)), ((9 : ℚ) / (28 : ℚ)), ((33 : ℚ) / (112 : ℚ)), ((5 : ℚ) / (28 : ℚ)), ((-3 : ℚ) / (112 : ℚ))] : List ℚ).getD i.val 0
def d (j : Fin 3) : ℚ := ([((-505 : ℚ) / (448 : ℚ)), ((57 : ℚ) / (224 : ℚ)), ((-5 : ℚ) / (448 : ℚ))] : List ℚ).getD j.val 0
def wr (i : Fin 7) : ℝ := (w i : ℝ)
def qr (j : Fin 3) : ℝ := (q j : ℝ)
theorem dual_checked : dualCheck x w q d = true := by decide +kernel
theorem gain_checked : (∑ i, |w i|) = (((37 : ℚ) / (28 : ℚ)) : ℚ) := by decide +kernel
theorem real_gain : (∑ i, |wr i|) = (((37 : ℚ) / (28 : ℚ)) : ℝ) := by
  have h := congrArg (fun a : ℚ => (a : ℝ)) gain_checked
  simpa only [wr, Rat.cast_sum, Rat.cast_abs, Rat.cast_div, Rat.cast_intCast,
    Rat.cast_ofNat, Rat.cast_neg] using h
theorem fitted_query : dot wr yr = dot qr br :=
  dual_prediction xr yr wr qr br (fun j => (d j : ℝ))
    (fit_check_sound normal_checked) (dual_check_sound dual_checked).1
    (dual_check_sound dual_checked).2
theorem sharp_radius (ε radius : ℝ) (he : 0 ≤ ε) :
    (∀ z : Fin 7 → ℝ, (∀ i, |z i - yr i| ≤ ε) → |dot wr z - dot wr yr| ≤ radius) ↔
      ε * (((37 : ℚ) / (28 : ℚ)) : ℝ) ≤ radius := by
  simpa only [real_gain] using sharp_radius_iff wr yr ε radius he
theorem conditional_physical_enclosure (truth : Fin 3 → ℝ) (ε : ℝ)
    (hm : ∀ i, |yr i - prediction xr truth i| ≤ ε) :
    |dot wr yr - dot qr truth| ≤ ε * (((37 : ℚ) / (28 : ℚ)) : ℝ) := by
  simpa only [real_gain] using physical_enclosure xr yr wr qr truth ε
    (dual_check_sound dual_checked).1 hm
end Q3
namespace Q3.Minimax
def w (i : Fin 7) : ℚ := ([((-1 : ℚ) / (48 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((7 : ℚ) / (12 : ℚ)), ((7 : ℚ) / (16 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ))] : List ℚ).getD i.val 0
def a (j : Fin 3) : ℚ := ([((-119 : ℚ) / (24 : ℚ)), ((1 : ℚ) / (1 : ℚ)), ((-1 : ℚ) / (24 : ℚ))] : List ℚ).getD j.val 0
def wr (i : Fin 7) : ℝ := (w i : ℝ)
def ar (j : Fin 3) : ℝ := (a j : ℝ)
theorem optimality_checked : minimaxCheck x w Q3.q a ((25 : ℚ) / (24 : ℚ)) = true := by decide +kernel
theorem gain_checked : (∑ i, |w i|) = (((25 : ℚ) / (24 : ℚ)) : ℚ) := by decide +kernel
theorem real_gain : (∑ i, |wr i|) = (((25 : ℚ) / (24 : ℚ)) : ℝ) := by
  have h := congrArg (fun a : ℚ => (a : ℝ)) gain_checked
  simpa only [wr, Rat.cast_sum, Rat.cast_abs, Rat.cast_div, Rat.cast_intCast,
    Rat.cast_ofNat, Rat.cast_neg] using h
theorem globally_minimal_gain (v : Fin 7 → ℝ) (hv : Reproduces xr v Q3.qr) :
    (((25 : ℚ) / (24 : ℚ)) : ℝ) ≤ ∑ i, |v i| := by
  have h := minimax_check_sound optimality_checked
  have hm := minimax_weights_optimal xr wr Q3.qr ar h.2.1 h.2.2 v hv
  simpa only [real_gain] using hm
theorem sharp_radius (ε radius : ℝ) (he : 0 ≤ ε) :
    (∀ z : Fin 7 → ℝ, (∀ i, |z i - yr i| ≤ ε) → |dot wr z - dot wr yr| ≤ radius) ↔
      ε * (((25 : ℚ) / (24 : ℚ)) : ℝ) ≤ radius := by
  simpa only [real_gain] using sharp_radius_iff wr yr ε radius he
theorem no_reproducing_estimator_has_smaller_radius (ε radius : ℝ) (he : 0 ≤ ε)
    (v : Fin 7 → ℝ) (hv : Reproduces xr v Q3.qr)
    (hr : ∀ z, (∀ i, |z i - yr i| ≤ ε) → |dot v z - dot v yr| ≤ radius) :
    ε * (((25 : ℚ) / (24 : ℚ)) : ℝ) ≤ radius := by
  have h := minimax_check_sound optimality_checked
  have hm := minimax_radius_lower_bound xr yr wr Q3.qr ar h.2.1 h.2.2 ε radius he v hv hr
  simpa only [real_gain] using hm
theorem conditional_physical_enclosure (truth : Fin 3 → ℝ) (ε : ℝ)
    (hm : ∀ i, |yr i - prediction xr truth i| ≤ ε) :
    |dot wr yr - dot Q3.qr truth| ≤ ε * (((25 : ℚ) / (24 : ℚ)) : ℝ) := by
  simpa only [real_gain] using physical_enclosure xr yr wr Q3.qr truth ε
    (minimax_check_sound optimality_checked).1 hm
theorem uniform_minimax_over_all_prediction_functions (ε radius : ℝ) (he : 0 ≤ ε) :
    (∃ estimator : (Fin 7 → ℝ) → ℝ,
      ∀ truth observed, (∀ i, |observed i - prediction xr truth i| ≤ ε) →
        |estimator observed - dot Q3.qr truth| ≤ radius) ↔
      ε * (((25 : ℚ) / (24 : ℚ)) : ℝ) ≤ radius := by
  have h := minimax_check_sound optimality_checked
  simpa only [real_gain] using
    minimax_over_all_estimators_iff xr wr Q3.qr ar h.1 h.2.1 h.2.2 ε radius he
end Q3.Minimax
namespace Q4
def q (j : Fin 3) : ℚ := (((14 : ℚ) / (1 : ℚ)) : ℚ) ^ j.val
def w (i : Fin 7) : ℚ := ([((-41 : ℚ) / (336 : ℚ)), ((1 : ℚ) / (28 : ℚ)), ((17 : ℚ) / (112 : ℚ)), ((19 : ℚ) / (84 : ℚ)), ((29 : ℚ) / (112 : ℚ)), ((1 : ℚ) / (4 : ℚ)), ((67 : ℚ) / (336 : ℚ))] : List ℚ).getD i.val 0
def d (j : Fin 3) : ℚ := ([((-313 : ℚ) / (448 : ℚ)), ((95 : ℚ) / (672 : ℚ)), ((-1 : ℚ) / (192 : ℚ))] : List ℚ).getD j.val 0
def wr (i : Fin 7) : ℝ := (w i : ℝ)
def qr (j : Fin 3) : ℝ := (q j : ℝ)
theorem dual_checked : dualCheck x w q d = true := by decide +kernel
theorem gain_checked : (∑ i, |w i|) = (((209 : ℚ) / (168 : ℚ)) : ℚ) := by decide +kernel
theorem real_gain : (∑ i, |wr i|) = (((209 : ℚ) / (168 : ℚ)) : ℝ) := by
  have h := congrArg (fun a : ℚ => (a : ℝ)) gain_checked
  simpa only [wr, Rat.cast_sum, Rat.cast_abs, Rat.cast_div, Rat.cast_intCast,
    Rat.cast_ofNat, Rat.cast_neg] using h
theorem fitted_query : dot wr yr = dot qr br :=
  dual_prediction xr yr wr qr br (fun j => (d j : ℝ))
    (fit_check_sound normal_checked) (dual_check_sound dual_checked).1
    (dual_check_sound dual_checked).2
theorem sharp_radius (ε radius : ℝ) (he : 0 ≤ ε) :
    (∀ z : Fin 7 → ℝ, (∀ i, |z i - yr i| ≤ ε) → |dot wr z - dot wr yr| ≤ radius) ↔
      ε * (((209 : ℚ) / (168 : ℚ)) : ℝ) ≤ radius := by
  simpa only [real_gain] using sharp_radius_iff wr yr ε radius he
theorem conditional_physical_enclosure (truth : Fin 3 → ℝ) (ε : ℝ)
    (hm : ∀ i, |yr i - prediction xr truth i| ≤ ε) :
    |dot wr yr - dot qr truth| ≤ ε * (((209 : ℚ) / (168 : ℚ)) : ℝ) := by
  simpa only [real_gain] using physical_enclosure xr yr wr qr truth ε
    (dual_check_sound dual_checked).1 hm
end Q4
namespace Q4.Minimax
def w (i : Fin 7) : ℚ := ([((-1 : ℚ) / (80 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((9 : ℚ) / (16 : ℚ)), ((9 : ℚ) / (20 : ℚ)), ((0 : ℚ) / (1 : ℚ))] : List ℚ).getD i.val 0
def a (j : Fin 3) : ℚ := ([((-31 : ℚ) / (8 : ℚ)), ((7 : ℚ) / (10 : ℚ)), ((-1 : ℚ) / (40 : ℚ))] : List ℚ).getD j.val 0
def wr (i : Fin 7) : ℝ := (w i : ℝ)
def ar (j : Fin 3) : ℝ := (a j : ℝ)
theorem optimality_checked : minimaxCheck x w Q4.q a ((41 : ℚ) / (40 : ℚ)) = true := by decide +kernel
theorem gain_checked : (∑ i, |w i|) = (((41 : ℚ) / (40 : ℚ)) : ℚ) := by decide +kernel
theorem real_gain : (∑ i, |wr i|) = (((41 : ℚ) / (40 : ℚ)) : ℝ) := by
  have h := congrArg (fun a : ℚ => (a : ℝ)) gain_checked
  simpa only [wr, Rat.cast_sum, Rat.cast_abs, Rat.cast_div, Rat.cast_intCast,
    Rat.cast_ofNat, Rat.cast_neg] using h
theorem globally_minimal_gain (v : Fin 7 → ℝ) (hv : Reproduces xr v Q4.qr) :
    (((41 : ℚ) / (40 : ℚ)) : ℝ) ≤ ∑ i, |v i| := by
  have h := minimax_check_sound optimality_checked
  have hm := minimax_weights_optimal xr wr Q4.qr ar h.2.1 h.2.2 v hv
  simpa only [real_gain] using hm
theorem sharp_radius (ε radius : ℝ) (he : 0 ≤ ε) :
    (∀ z : Fin 7 → ℝ, (∀ i, |z i - yr i| ≤ ε) → |dot wr z - dot wr yr| ≤ radius) ↔
      ε * (((41 : ℚ) / (40 : ℚ)) : ℝ) ≤ radius := by
  simpa only [real_gain] using sharp_radius_iff wr yr ε radius he
theorem no_reproducing_estimator_has_smaller_radius (ε radius : ℝ) (he : 0 ≤ ε)
    (v : Fin 7 → ℝ) (hv : Reproduces xr v Q4.qr)
    (hr : ∀ z, (∀ i, |z i - yr i| ≤ ε) → |dot v z - dot v yr| ≤ radius) :
    ε * (((41 : ℚ) / (40 : ℚ)) : ℝ) ≤ radius := by
  have h := minimax_check_sound optimality_checked
  have hm := minimax_radius_lower_bound xr yr wr Q4.qr ar h.2.1 h.2.2 ε radius he v hv hr
  simpa only [real_gain] using hm
theorem conditional_physical_enclosure (truth : Fin 3 → ℝ) (ε : ℝ)
    (hm : ∀ i, |yr i - prediction xr truth i| ≤ ε) :
    |dot wr yr - dot Q4.qr truth| ≤ ε * (((41 : ℚ) / (40 : ℚ)) : ℝ) := by
  simpa only [real_gain] using physical_enclosure xr yr wr Q4.qr truth ε
    (minimax_check_sound optimality_checked).1 hm
theorem uniform_minimax_over_all_prediction_functions (ε radius : ℝ) (he : 0 ≤ ε) :
    (∃ estimator : (Fin 7 → ℝ) → ℝ,
      ∀ truth observed, (∀ i, |observed i - prediction xr truth i| ≤ ε) →
        |estimator observed - dot Q4.qr truth| ≤ radius) ↔
      ε * (((41 : ℚ) / (40 : ℚ)) : ℝ) ≤ radius := by
  have h := minimax_check_sound optimality_checked
  simpa only [real_gain] using
    minimax_over_all_estimators_iff xr wr Q4.qr ar h.1 h.2.1 h.2.2 ε radius he
end Q4.Minimax
namespace Q5
def q (j : Fin 3) : ℚ := (((16 : ℚ) / (1 : ℚ)) : ℚ) ^ j.val
def w (i : Fin 7) : ℚ := ([((1 : ℚ) / (112 : ℚ)), ((-1 : ℚ) / (28 : ℚ)), ((-3 : ℚ) / (112 : ℚ)), ((1 : ℚ) / (28 : ℚ)), ((17 : ℚ) / (112 : ℚ)), ((9 : ℚ) / (28 : ℚ)), ((61 : ℚ) / (112 : ℚ))] : List ℚ).getD i.val 0
def d (j : Fin 3) : ℚ := ([((159 : ℚ) / (448 : ℚ)), ((-23 : ℚ) / (224 : ℚ)), ((3 : ℚ) / (448 : ℚ))] : List ℚ).getD j.val 0
def wr (i : Fin 7) : ℝ := (w i : ℝ)
def qr (j : Fin 3) : ℝ := (q j : ℝ)
theorem dual_checked : dualCheck x w q d = true := by decide +kernel
theorem gain_checked : (∑ i, |w i|) = (((9 : ℚ) / (8 : ℚ)) : ℚ) := by decide +kernel
theorem real_gain : (∑ i, |wr i|) = (((9 : ℚ) / (8 : ℚ)) : ℝ) := by
  have h := congrArg (fun a : ℚ => (a : ℝ)) gain_checked
  simpa only [wr, Rat.cast_sum, Rat.cast_abs, Rat.cast_div, Rat.cast_intCast,
    Rat.cast_ofNat, Rat.cast_neg] using h
theorem fitted_query : dot wr yr = dot qr br :=
  dual_prediction xr yr wr qr br (fun j => (d j : ℝ))
    (fit_check_sound normal_checked) (dual_check_sound dual_checked).1
    (dual_check_sound dual_checked).2
theorem sharp_radius (ε radius : ℝ) (he : 0 ≤ ε) :
    (∀ z : Fin 7 → ℝ, (∀ i, |z i - yr i| ≤ ε) → |dot wr z - dot wr yr| ≤ radius) ↔
      ε * (((9 : ℚ) / (8 : ℚ)) : ℝ) ≤ radius := by
  simpa only [real_gain] using sharp_radius_iff wr yr ε radius he
theorem conditional_physical_enclosure (truth : Fin 3 → ℝ) (ε : ℝ)
    (hm : ∀ i, |yr i - prediction xr truth i| ≤ ε) :
    |dot wr yr - dot qr truth| ≤ ε * (((9 : ℚ) / (8 : ℚ)) : ℝ) := by
  simpa only [real_gain] using physical_enclosure xr yr wr qr truth ε
    (dual_check_sound dual_checked).1 hm
end Q5
namespace Q5.Minimax
def w (i : Fin 7) : ℚ := ([((-1 : ℚ) / (120 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((11 : ℚ) / (20 : ℚ)), ((11 : ℚ) / (24 : ℚ))] : List ℚ).getD i.val 0
def a (j : Fin 3) : ℚ := ([((-13 : ℚ) / (4 : ℚ)), ((8 : ℚ) / (15 : ℚ)), ((-1 : ℚ) / (60 : ℚ))] : List ℚ).getD j.val 0
def wr (i : Fin 7) : ℝ := (w i : ℝ)
def ar (j : Fin 3) : ℝ := (a j : ℝ)
theorem optimality_checked : minimaxCheck x w Q5.q a ((61 : ℚ) / (60 : ℚ)) = true := by decide +kernel
theorem gain_checked : (∑ i, |w i|) = (((61 : ℚ) / (60 : ℚ)) : ℚ) := by decide +kernel
theorem real_gain : (∑ i, |wr i|) = (((61 : ℚ) / (60 : ℚ)) : ℝ) := by
  have h := congrArg (fun a : ℚ => (a : ℝ)) gain_checked
  simpa only [wr, Rat.cast_sum, Rat.cast_abs, Rat.cast_div, Rat.cast_intCast,
    Rat.cast_ofNat, Rat.cast_neg] using h
theorem globally_minimal_gain (v : Fin 7 → ℝ) (hv : Reproduces xr v Q5.qr) :
    (((61 : ℚ) / (60 : ℚ)) : ℝ) ≤ ∑ i, |v i| := by
  have h := minimax_check_sound optimality_checked
  have hm := minimax_weights_optimal xr wr Q5.qr ar h.2.1 h.2.2 v hv
  simpa only [real_gain] using hm
theorem sharp_radius (ε radius : ℝ) (he : 0 ≤ ε) :
    (∀ z : Fin 7 → ℝ, (∀ i, |z i - yr i| ≤ ε) → |dot wr z - dot wr yr| ≤ radius) ↔
      ε * (((61 : ℚ) / (60 : ℚ)) : ℝ) ≤ radius := by
  simpa only [real_gain] using sharp_radius_iff wr yr ε radius he
theorem no_reproducing_estimator_has_smaller_radius (ε radius : ℝ) (he : 0 ≤ ε)
    (v : Fin 7 → ℝ) (hv : Reproduces xr v Q5.qr)
    (hr : ∀ z, (∀ i, |z i - yr i| ≤ ε) → |dot v z - dot v yr| ≤ radius) :
    ε * (((61 : ℚ) / (60 : ℚ)) : ℝ) ≤ radius := by
  have h := minimax_check_sound optimality_checked
  have hm := minimax_radius_lower_bound xr yr wr Q5.qr ar h.2.1 h.2.2 ε radius he v hv hr
  simpa only [real_gain] using hm
theorem conditional_physical_enclosure (truth : Fin 3 → ℝ) (ε : ℝ)
    (hm : ∀ i, |yr i - prediction xr truth i| ≤ ε) :
    |dot wr yr - dot Q5.qr truth| ≤ ε * (((61 : ℚ) / (60 : ℚ)) : ℝ) := by
  simpa only [real_gain] using physical_enclosure xr yr wr Q5.qr truth ε
    (minimax_check_sound optimality_checked).1 hm
theorem uniform_minimax_over_all_prediction_functions (ε radius : ℝ) (he : 0 ≤ ε) :
    (∃ estimator : (Fin 7 → ℝ) → ℝ,
      ∀ truth observed, (∀ i, |observed i - prediction xr truth i| ≤ ε) →
        |estimator observed - dot Q5.qr truth| ≤ radius) ↔
      ε * (((61 : ℚ) / (60 : ℚ)) : ℝ) ≤ radius := by
  have h := minimax_check_sound optimality_checked
  simpa only [real_gain] using
    minimax_over_all_estimators_iff xr wr Q5.qr ar h.1 h.2.1 h.2.2 ε radius he
end Q5.Minimax
namespace Q6
def q (j : Fin 3) : ℚ := (((18 : ℚ) / (1 : ℚ)) : ℚ) ^ j.val
def w (i : Fin 7) : ℚ := ([((29 : ℚ) / (112 : ℚ)), ((-3 : ℚ) / (28 : ℚ)), ((-31 : ℚ) / (112 : ℚ)), ((-1 : ℚ) / (4 : ℚ)), ((-3 : ℚ) / (112 : ℚ)), ((11 : ℚ) / (28 : ℚ)), ((113 : ℚ) / (112 : ℚ))] : List ℚ).getD i.val 0
def d (j : Fin 3) : ℚ := ([((911 : ℚ) / (448 : ℚ)), ((-107 : ℚ) / (224 : ℚ)), ((11 : ℚ) / (448 : ℚ))] : List ℚ).getD j.val 0
def wr (i : Fin 7) : ℝ := (w i : ℝ)
def qr (j : Fin 3) : ℝ := (q j : ℝ)
theorem dual_checked : dualCheck x w q d = true := by decide +kernel
theorem gain_checked : (∑ i, |w i|) = (((65 : ℚ) / (28 : ℚ)) : ℚ) := by decide +kernel
theorem real_gain : (∑ i, |wr i|) = (((65 : ℚ) / (28 : ℚ)) : ℝ) := by
  have h := congrArg (fun a : ℚ => (a : ℝ)) gain_checked
  simpa only [wr, Rat.cast_sum, Rat.cast_abs, Rat.cast_div, Rat.cast_intCast,
    Rat.cast_ofNat, Rat.cast_neg] using h
theorem fitted_query : dot wr yr = dot qr br :=
  dual_prediction xr yr wr qr br (fun j => (d j : ℝ))
    (fit_check_sound normal_checked) (dual_check_sound dual_checked).1
    (dual_check_sound dual_checked).2
theorem sharp_radius (ε radius : ℝ) (he : 0 ≤ ε) :
    (∀ z : Fin 7 → ℝ, (∀ i, |z i - yr i| ≤ ε) → |dot wr z - dot wr yr| ≤ radius) ↔
      ε * (((65 : ℚ) / (28 : ℚ)) : ℝ) ≤ radius := by
  simpa only [real_gain] using sharp_radius_iff wr yr ε radius he
theorem conditional_physical_enclosure (truth : Fin 3 → ℝ) (ε : ℝ)
    (hm : ∀ i, |yr i - prediction xr truth i| ≤ ε) :
    |dot wr yr - dot qr truth| ≤ ε * (((65 : ℚ) / (28 : ℚ)) : ℝ) := by
  simpa only [real_gain] using physical_enclosure xr yr wr qr truth ε
    (dual_check_sound dual_checked).1 hm
end Q6
namespace Q6.Minimax
def w (i : Fin 7) : ℚ := ([((7 : ℚ) / (72 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((-13 : ℚ) / (36 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((91 : ℚ) / (72 : ℚ))] : List ℚ).getD i.val 0
def a (j : Fin 3) : ℚ := ([((103 : ℚ) / (18 : ℚ)), ((-11 : ℚ) / (9 : ℚ)), ((1 : ℚ) / (18 : ℚ))] : List ℚ).getD j.val 0
def wr (i : Fin 7) : ℝ := (w i : ℝ)
def ar (j : Fin 3) : ℝ := (a j : ℝ)
theorem optimality_checked : minimaxCheck x w Q6.q a ((31 : ℚ) / (18 : ℚ)) = true := by decide +kernel
theorem gain_checked : (∑ i, |w i|) = (((31 : ℚ) / (18 : ℚ)) : ℚ) := by decide +kernel
theorem real_gain : (∑ i, |wr i|) = (((31 : ℚ) / (18 : ℚ)) : ℝ) := by
  have h := congrArg (fun a : ℚ => (a : ℝ)) gain_checked
  simpa only [wr, Rat.cast_sum, Rat.cast_abs, Rat.cast_div, Rat.cast_intCast,
    Rat.cast_ofNat, Rat.cast_neg] using h
theorem globally_minimal_gain (v : Fin 7 → ℝ) (hv : Reproduces xr v Q6.qr) :
    (((31 : ℚ) / (18 : ℚ)) : ℝ) ≤ ∑ i, |v i| := by
  have h := minimax_check_sound optimality_checked
  have hm := minimax_weights_optimal xr wr Q6.qr ar h.2.1 h.2.2 v hv
  simpa only [real_gain] using hm
theorem sharp_radius (ε radius : ℝ) (he : 0 ≤ ε) :
    (∀ z : Fin 7 → ℝ, (∀ i, |z i - yr i| ≤ ε) → |dot wr z - dot wr yr| ≤ radius) ↔
      ε * (((31 : ℚ) / (18 : ℚ)) : ℝ) ≤ radius := by
  simpa only [real_gain] using sharp_radius_iff wr yr ε radius he
theorem no_reproducing_estimator_has_smaller_radius (ε radius : ℝ) (he : 0 ≤ ε)
    (v : Fin 7 → ℝ) (hv : Reproduces xr v Q6.qr)
    (hr : ∀ z, (∀ i, |z i - yr i| ≤ ε) → |dot v z - dot v yr| ≤ radius) :
    ε * (((31 : ℚ) / (18 : ℚ)) : ℝ) ≤ radius := by
  have h := minimax_check_sound optimality_checked
  have hm := minimax_radius_lower_bound xr yr wr Q6.qr ar h.2.1 h.2.2 ε radius he v hv hr
  simpa only [real_gain] using hm
theorem conditional_physical_enclosure (truth : Fin 3 → ℝ) (ε : ℝ)
    (hm : ∀ i, |yr i - prediction xr truth i| ≤ ε) :
    |dot wr yr - dot Q6.qr truth| ≤ ε * (((31 : ℚ) / (18 : ℚ)) : ℝ) := by
  simpa only [real_gain] using physical_enclosure xr yr wr Q6.qr truth ε
    (minimax_check_sound optimality_checked).1 hm
theorem uniform_minimax_over_all_prediction_functions (ε radius : ℝ) (he : 0 ≤ ε) :
    (∃ estimator : (Fin 7 → ℝ) → ℝ,
      ∀ truth observed, (∀ i, |observed i - prediction xr truth i| ≤ ε) →
        |estimator observed - dot Q6.qr truth| ≤ radius) ↔
      ε * (((31 : ℚ) / (18 : ℚ)) : ℝ) ≤ radius := by
  have h := minimax_check_sound optimality_checked
  simpa only [real_gain] using
    minimax_over_all_estimators_iff xr wr Q6.qr ar h.1 h.2.1 h.2.2 ε radius he
end Q6.Minimax
namespace Q7
def q (j : Fin 3) : ℚ := (((24 : ℚ) / (1 : ℚ)) : ℚ) ^ j.val
def w (i : Fin 7) : ℚ := ([((193 : ℚ) / (112 : ℚ)), ((-9 : ℚ) / (28 : ℚ)), ((-163 : ℚ) / (112 : ℚ)), ((-47 : ℚ) / (28 : ℚ)), ((-111 : ℚ) / (112 : ℚ)), ((17 : ℚ) / (28 : ℚ)), ((349 : ℚ) / (112 : ℚ))] : List ℚ).getD i.val 0
def d (j : Fin 3) : ℚ := ([((4847 : ℚ) / (448 : ℚ)), ((-535 : ℚ) / (224 : ℚ)), ((51 : ℚ) / (448 : ℚ))] : List ℚ).getD j.val 0
def wr (i : Fin 7) : ℝ := (w i : ℝ)
def qr (j : Fin 3) : ℝ := (q j : ℝ)
theorem dual_checked : dualCheck x w q d = true := by decide +kernel
theorem gain_checked : (∑ i, |w i|) = (((277 : ℚ) / (28 : ℚ)) : ℚ) := by decide +kernel
theorem real_gain : (∑ i, |wr i|) = (((277 : ℚ) / (28 : ℚ)) : ℝ) := by
  have h := congrArg (fun a : ℚ => (a : ℝ)) gain_checked
  simpa only [wr, Rat.cast_sum, Rat.cast_abs, Rat.cast_div, Rat.cast_intCast,
    Rat.cast_ofNat, Rat.cast_neg] using h
theorem fitted_query : dot wr yr = dot qr br :=
  dual_prediction xr yr wr qr br (fun j => (d j : ℝ))
    (fit_check_sound normal_checked) (dual_check_sound dual_checked).1
    (dual_check_sound dual_checked).2
theorem sharp_radius (ε radius : ℝ) (he : 0 ≤ ε) :
    (∀ z : Fin 7 → ℝ, (∀ i, |z i - yr i| ≤ ε) → |dot wr z - dot wr yr| ≤ radius) ↔
      ε * (((277 : ℚ) / (28 : ℚ)) : ℝ) ≤ radius := by
  simpa only [real_gain] using sharp_radius_iff wr yr ε radius he
theorem conditional_physical_enclosure (truth : Fin 3 → ℝ) (ε : ℝ)
    (hm : ∀ i, |yr i - prediction xr truth i| ≤ ε) :
    |dot wr yr - dot qr truth| ≤ ε * (((277 : ℚ) / (28 : ℚ)) : ℝ) := by
  simpa only [real_gain] using physical_enclosure xr yr wr qr truth ε
    (dual_check_sound dual_checked).1 hm
end Q7
namespace Q7.Minimax
def w (i : Fin 7) : ℚ := ([((91 : ℚ) / (72 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((-133 : ℚ) / (36 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((247 : ℚ) / (72 : ℚ))] : List ℚ).getD i.val 0
def a (j : Fin 3) : ℚ := ([((103 : ℚ) / (18 : ℚ)), ((-11 : ℚ) / (9 : ℚ)), ((1 : ℚ) / (18 : ℚ))] : List ℚ).getD j.val 0
def wr (i : Fin 7) : ℝ := (w i : ℝ)
def ar (j : Fin 3) : ℝ := (a j : ℝ)
theorem optimality_checked : minimaxCheck x w Q7.q a ((151 : ℚ) / (18 : ℚ)) = true := by decide +kernel
theorem gain_checked : (∑ i, |w i|) = (((151 : ℚ) / (18 : ℚ)) : ℚ) := by decide +kernel
theorem real_gain : (∑ i, |wr i|) = (((151 : ℚ) / (18 : ℚ)) : ℝ) := by
  have h := congrArg (fun a : ℚ => (a : ℝ)) gain_checked
  simpa only [wr, Rat.cast_sum, Rat.cast_abs, Rat.cast_div, Rat.cast_intCast,
    Rat.cast_ofNat, Rat.cast_neg] using h
theorem globally_minimal_gain (v : Fin 7 → ℝ) (hv : Reproduces xr v Q7.qr) :
    (((151 : ℚ) / (18 : ℚ)) : ℝ) ≤ ∑ i, |v i| := by
  have h := minimax_check_sound optimality_checked
  have hm := minimax_weights_optimal xr wr Q7.qr ar h.2.1 h.2.2 v hv
  simpa only [real_gain] using hm
theorem sharp_radius (ε radius : ℝ) (he : 0 ≤ ε) :
    (∀ z : Fin 7 → ℝ, (∀ i, |z i - yr i| ≤ ε) → |dot wr z - dot wr yr| ≤ radius) ↔
      ε * (((151 : ℚ) / (18 : ℚ)) : ℝ) ≤ radius := by
  simpa only [real_gain] using sharp_radius_iff wr yr ε radius he
theorem no_reproducing_estimator_has_smaller_radius (ε radius : ℝ) (he : 0 ≤ ε)
    (v : Fin 7 → ℝ) (hv : Reproduces xr v Q7.qr)
    (hr : ∀ z, (∀ i, |z i - yr i| ≤ ε) → |dot v z - dot v yr| ≤ radius) :
    ε * (((151 : ℚ) / (18 : ℚ)) : ℝ) ≤ radius := by
  have h := minimax_check_sound optimality_checked
  have hm := minimax_radius_lower_bound xr yr wr Q7.qr ar h.2.1 h.2.2 ε radius he v hv hr
  simpa only [real_gain] using hm
theorem conditional_physical_enclosure (truth : Fin 3 → ℝ) (ε : ℝ)
    (hm : ∀ i, |yr i - prediction xr truth i| ≤ ε) :
    |dot wr yr - dot Q7.qr truth| ≤ ε * (((151 : ℚ) / (18 : ℚ)) : ℝ) := by
  simpa only [real_gain] using physical_enclosure xr yr wr Q7.qr truth ε
    (minimax_check_sound optimality_checked).1 hm
theorem uniform_minimax_over_all_prediction_functions (ε radius : ℝ) (he : 0 ≤ ε) :
    (∃ estimator : (Fin 7 → ℝ) → ℝ,
      ∀ truth observed, (∀ i, |observed i - prediction xr truth i| ≤ ε) →
        |estimator observed - dot Q7.qr truth| ≤ radius) ↔
      ε * (((151 : ℚ) / (18 : ℚ)) : ℝ) ≤ radius := by
  have h := minimax_check_sound optimality_checked
  simpa only [real_gain] using
    minimax_over_all_estimators_iff xr wr Q7.qr ar h.1 h.2.1 h.2.2 ε radius he
end Q7.Minimax
end PCSCalibrationReplay.M2

namespace PCSCalibrationReplay.M3
def abscissa (i : Fin 14) : ℚ := ([((5 : ℚ) / (1 : ℚ)), ((6 : ℚ) / (1 : ℚ)), ((7 : ℚ) / (1 : ℚ)), ((8 : ℚ) / (1 : ℚ)), ((9 : ℚ) / (1 : ℚ)), ((10 : ℚ) / (1 : ℚ)), ((11 : ℚ) / (1 : ℚ)), ((12 : ℚ) / (1 : ℚ)), ((13 : ℚ) / (1 : ℚ)), ((14 : ℚ) / (1 : ℚ)), ((15 : ℚ) / (1 : ℚ)), ((16 : ℚ) / (1 : ℚ)), ((17 : ℚ) / (1 : ℚ)), ((18 : ℚ) / (1 : ℚ))] : List ℚ).getD i.val 0
def x (i : Fin 14) (j : Fin 3) : ℚ := abscissa i ^ j.val
def y (i : Fin 14) : ℚ := ([((1 : ℚ) / (25 : ℚ)), ((17 : ℚ) / (100 : ℚ)), ((37 : ℚ) / (100 : ℚ)), ((33 : ℚ) / (50 : ℚ)), ((53 : ℚ) / (50 : ℚ)), ((159 : ℚ) / (100 : ℚ)), ((233 : ℚ) / (100 : ℚ)), ((329 : ℚ) / (100 : ℚ)), ((461 : ℚ) / (100 : ℚ)), ((711 : ℚ) / (100 : ℚ)), ((1199 : ℚ) / (100 : ℚ)), ((2109 : ℚ) / (100 : ℚ)), ((3501 : ℚ) / (100 : ℚ)), ((259 : ℚ) / (5 : ℚ))] : List ℚ).getD i.val 0
def b (j : Fin 3) : ℚ := ([((7293087 : ℚ) / (182000 : ℚ)), ((-7119297 : ℚ) / (728000 : ℚ)), ((80859 : ℚ) / (145600 : ℚ))] : List ℚ).getD j.val 0
def xr (i : Fin 14) (j : Fin 3) : ℝ := (x i j : ℝ)
def yr (i : Fin 14) : ℝ := (y i : ℝ)
def br (j : Fin 3) : ℝ := (b j : ℝ)
theorem normal_checked : fitCheck x y b = true := by decide +kernel
theorem residual_checked : loss x y b = ((8377842339 : ℚ) / (36400000 : ℚ)) := by decide +kernel
theorem global_optimum : ∀ c : Fin 3 → ℝ,
    (((8377842339 : ℚ) / (36400000 : ℚ)) : ℝ) ≤ loss xr yr c := by
  have hs : loss xr yr br = (((8377842339 : ℚ) / (36400000 : ℚ)) : ℝ) := by
    calc
      loss xr yr br = ((loss x y b : ℚ) : ℝ) := (cast_loss x y b).symm
      _ = (((8377842339 : ℚ) / (36400000 : ℚ)) : ℝ) := by
        simpa only [Rat.cast_div, Rat.cast_intCast, Rat.cast_ofNat, Rat.cast_neg]
          using congrArg (fun a : ℚ => (a : ℝ)) residual_checked
  simpa only [hs] using global_minimum xr yr br (fit_check_sound normal_checked)
theorem excludes_every_better_model (threshold : ℝ)
    (h : threshold < (((8377842339 : ℚ) / (36400000 : ℚ)) : ℝ)) :
    ∀ c : Fin 3 → ℝ, threshold < loss xr yr c := by
  intro c
  exact h.trans_le (global_optimum c)
theorem uniform_error_exclusion (ε : ℝ) (he : 0 ≤ ε)
    (hgap : (14 : ℝ) * ε ^ 2 < (((8377842339 : ℚ) / (36400000 : ℚ)) : ℝ)) :
    ¬ (∃ c : Fin 3 → ℝ, ∀ i, |yr i - prediction xr c i| ≤ ε) :=
  PCSReal.Calibration.uniform_error_exclusion xr yr (((8377842339 : ℚ) / (36400000 : ℚ)) : ℝ) ε
    global_optimum he (by simpa using hgap)
end PCSCalibrationReplay.M3

namespace PCSCalibrationReplay.M4
def abscissa (i : Fin 7) : ℚ := ([((5 : ℚ) / (1 : ℚ)), ((7 : ℚ) / (1 : ℚ)), ((9 : ℚ) / (1 : ℚ)), ((11 : ℚ) / (1 : ℚ)), ((13 : ℚ) / (1 : ℚ)), ((15 : ℚ) / (1 : ℚ)), ((17 : ℚ) / (1 : ℚ))] : List ℚ).getD i.val 0
def x (i : Fin 7) (j : Fin 4) : ℚ := abscissa i ^ j.val
def y (i : Fin 7) : ℚ := ([((1 : ℚ) / (25 : ℚ)), ((37 : ℚ) / (100 : ℚ)), ((53 : ℚ) / (50 : ℚ)), ((233 : ℚ) / (100 : ℚ)), ((461 : ℚ) / (100 : ℚ)), ((1199 : ℚ) / (100 : ℚ)), ((3501 : ℚ) / (100 : ℚ))] : List ℚ).getD i.val 0
def b (j : Fin 4) : ℚ := ([((-233787 : ℚ) / (5600 : ℚ)), ((87541 : ℚ) / (5600 : ℚ)), ((-10223 : ℚ) / (5600 : ℚ)), ((11 : ℚ) / (160 : ℚ))] : List ℚ).getD j.val 0
def xr (i : Fin 7) (j : Fin 4) : ℝ := (x i j : ℝ)
def yr (i : Fin 7) : ℝ := (y i : ℝ)
def br (j : Fin 4) : ℝ := (b j : ℝ)
theorem normal_checked : fitCheck x y b = true := by decide +kernel
theorem residual_checked : loss x y b = ((698553 : ℚ) / (70000 : ℚ)) := by decide +kernel
theorem global_optimum : ∀ c : Fin 4 → ℝ,
    (((698553 : ℚ) / (70000 : ℚ)) : ℝ) ≤ loss xr yr c := by
  have hs : loss xr yr br = (((698553 : ℚ) / (70000 : ℚ)) : ℝ) := by
    calc
      loss xr yr br = ((loss x y b : ℚ) : ℝ) := (cast_loss x y b).symm
      _ = (((698553 : ℚ) / (70000 : ℚ)) : ℝ) := by
        simpa only [Rat.cast_div, Rat.cast_intCast, Rat.cast_ofNat, Rat.cast_neg]
          using congrArg (fun a : ℚ => (a : ℝ)) residual_checked
  simpa only [hs] using global_minimum xr yr br (fit_check_sound normal_checked)
theorem excludes_every_better_model (threshold : ℝ)
    (h : threshold < (((698553 : ℚ) / (70000 : ℚ)) : ℝ)) :
    ∀ c : Fin 4 → ℝ, threshold < loss xr yr c := by
  intro c
  exact h.trans_le (global_optimum c)
theorem uniform_error_exclusion (ε : ℝ) (he : 0 ≤ ε)
    (hgap : (7 : ℝ) * ε ^ 2 < (((698553 : ℚ) / (70000 : ℚ)) : ℝ)) :
    ¬ (∃ c : Fin 4 → ℝ, ∀ i, |yr i - prediction xr c i| ≤ ε) :=
  PCSReal.Calibration.uniform_error_exclusion xr yr (((698553 : ℚ) / (70000 : ℚ)) : ℝ) ε
    global_optimum he (by simpa using hgap)
namespace Q0
def q (j : Fin 4) : ℚ := (((6 : ℚ) / (1 : ℚ)) : ℚ) ^ j.val
def w (i : Fin 7) : ℚ := ([((331 : ℚ) / (672 : ℚ)), ((251 : ℚ) / (672 : ℚ)), ((137 : ℚ) / (672 : ℚ)), ((1 : ℚ) / (28 : ℚ)), ((-53 : ℚ) / (672 : ℚ)), ((-59 : ℚ) / (672 : ℚ)), ((41 : ℚ) / (672 : ℚ))] : List ℚ).getD i.val 0
def d (j : Fin 4) : ℚ := ([((2441 : ℚ) / (10752 : ℚ)), ((5533 : ℚ) / (32256 : ℚ)), ((-313 : ℚ) / (10752 : ℚ)), ((5 : ℚ) / (4608 : ℚ))] : List ℚ).getD j.val 0
def wr (i : Fin 7) : ℝ := (w i : ℝ)
def qr (j : Fin 4) : ℝ := (q j : ℝ)
theorem dual_checked : dualCheck x w q d = true := by decide +kernel
theorem gain_checked : (∑ i, |w i|) = (((4 : ℚ) / (3 : ℚ)) : ℚ) := by decide +kernel
theorem real_gain : (∑ i, |wr i|) = (((4 : ℚ) / (3 : ℚ)) : ℝ) := by
  have h := congrArg (fun a : ℚ => (a : ℝ)) gain_checked
  simpa only [wr, Rat.cast_sum, Rat.cast_abs, Rat.cast_div, Rat.cast_intCast,
    Rat.cast_ofNat, Rat.cast_neg] using h
theorem fitted_query : dot wr yr = dot qr br :=
  dual_prediction xr yr wr qr br (fun j => (d j : ℝ))
    (fit_check_sound normal_checked) (dual_check_sound dual_checked).1
    (dual_check_sound dual_checked).2
theorem sharp_radius (ε radius : ℝ) (he : 0 ≤ ε) :
    (∀ z : Fin 7 → ℝ, (∀ i, |z i - yr i| ≤ ε) → |dot wr z - dot wr yr| ≤ radius) ↔
      ε * (((4 : ℚ) / (3 : ℚ)) : ℝ) ≤ radius := by
  simpa only [real_gain] using sharp_radius_iff wr yr ε radius he
theorem conditional_physical_enclosure (truth : Fin 4 → ℝ) (ε : ℝ)
    (hm : ∀ i, |yr i - prediction xr truth i| ≤ ε) :
    |dot wr yr - dot qr truth| ≤ ε * (((4 : ℚ) / (3 : ℚ)) : ℝ) := by
  simpa only [real_gain] using physical_enclosure xr yr wr qr truth ε
    (dual_check_sound dual_checked).1 hm
end Q0
namespace Q0.Minimax
def w (i : Fin 7) : ℚ := ([((77 : ℚ) / (192 : ℚ)), ((77 : ℚ) / (120 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((-11 : ℚ) / (192 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((7 : ℚ) / (480 : ℚ))] : List ℚ).getD i.val 0
def a (j : Fin 4) : ℚ := ([((-499 : ℚ) / (96 : ℚ)), ((239 : ℚ) / (96 : ℚ)), ((-29 : ℚ) / (96 : ℚ)), ((1 : ℚ) / (96 : ℚ))] : List ℚ).getD j.val 0
def wr (i : Fin 7) : ℝ := (w i : ℝ)
def ar (j : Fin 4) : ℝ := (a j : ℝ)
theorem optimality_checked : minimaxCheck x w Q0.q a ((107 : ℚ) / (96 : ℚ)) = true := by decide +kernel
theorem gain_checked : (∑ i, |w i|) = (((107 : ℚ) / (96 : ℚ)) : ℚ) := by decide +kernel
theorem real_gain : (∑ i, |wr i|) = (((107 : ℚ) / (96 : ℚ)) : ℝ) := by
  have h := congrArg (fun a : ℚ => (a : ℝ)) gain_checked
  simpa only [wr, Rat.cast_sum, Rat.cast_abs, Rat.cast_div, Rat.cast_intCast,
    Rat.cast_ofNat, Rat.cast_neg] using h
theorem globally_minimal_gain (v : Fin 7 → ℝ) (hv : Reproduces xr v Q0.qr) :
    (((107 : ℚ) / (96 : ℚ)) : ℝ) ≤ ∑ i, |v i| := by
  have h := minimax_check_sound optimality_checked
  have hm := minimax_weights_optimal xr wr Q0.qr ar h.2.1 h.2.2 v hv
  simpa only [real_gain] using hm
theorem sharp_radius (ε radius : ℝ) (he : 0 ≤ ε) :
    (∀ z : Fin 7 → ℝ, (∀ i, |z i - yr i| ≤ ε) → |dot wr z - dot wr yr| ≤ radius) ↔
      ε * (((107 : ℚ) / (96 : ℚ)) : ℝ) ≤ radius := by
  simpa only [real_gain] using sharp_radius_iff wr yr ε radius he
theorem no_reproducing_estimator_has_smaller_radius (ε radius : ℝ) (he : 0 ≤ ε)
    (v : Fin 7 → ℝ) (hv : Reproduces xr v Q0.qr)
    (hr : ∀ z, (∀ i, |z i - yr i| ≤ ε) → |dot v z - dot v yr| ≤ radius) :
    ε * (((107 : ℚ) / (96 : ℚ)) : ℝ) ≤ radius := by
  have h := minimax_check_sound optimality_checked
  have hm := minimax_radius_lower_bound xr yr wr Q0.qr ar h.2.1 h.2.2 ε radius he v hv hr
  simpa only [real_gain] using hm
theorem conditional_physical_enclosure (truth : Fin 4 → ℝ) (ε : ℝ)
    (hm : ∀ i, |yr i - prediction xr truth i| ≤ ε) :
    |dot wr yr - dot Q0.qr truth| ≤ ε * (((107 : ℚ) / (96 : ℚ)) : ℝ) := by
  simpa only [real_gain] using physical_enclosure xr yr wr Q0.qr truth ε
    (minimax_check_sound optimality_checked).1 hm
theorem uniform_minimax_over_all_prediction_functions (ε radius : ℝ) (he : 0 ≤ ε) :
    (∃ estimator : (Fin 7 → ℝ) → ℝ,
      ∀ truth observed, (∀ i, |observed i - prediction xr truth i| ≤ ε) →
        |estimator observed - dot Q0.qr truth| ≤ radius) ↔
      ε * (((107 : ℚ) / (96 : ℚ)) : ℝ) ≤ radius := by
  have h := minimax_check_sound optimality_checked
  simpa only [real_gain] using
    minimax_over_all_estimators_iff xr wr Q0.qr ar h.1 h.2.1 h.2.2 ε radius he
end Q0.Minimax
namespace Q1
def q (j : Fin 4) : ℚ := (((8 : ℚ) / (1 : ℚ)) : ℚ) ^ j.val
def w (i : Fin 7) : ℚ := ([((1 : ℚ) / (672 : ℚ)), ((43 : ℚ) / (96 : ℚ)), ((307 : ℚ) / (672 : ℚ)), ((19 : ℚ) / (84 : ℚ)), ((-31 : ℚ) / (672 : ℚ)), ((-109 : ℚ) / (672 : ℚ)), ((17 : ℚ) / (224 : ℚ))] : List ℚ).getD i.val 0
def d (j : Fin 4) : ℚ := ([((-6647 : ℚ) / (1536 : ℚ)), ((47387 : ℚ) / (32256 : ℚ)), ((-217 : ℚ) / (1536 : ℚ)), ((19 : ℚ) / (4608 : ℚ))] : List ℚ).getD j.val 0
def wr (i : Fin 7) : ℝ := (w i : ℝ)
def qr (j : Fin 4) : ℝ := (q j : ℝ)
theorem dual_checked : dualCheck x w q d = true := by decide +kernel
theorem gain_checked : (∑ i, |w i|) = (((17 : ℚ) / (12 : ℚ)) : ℚ) := by decide +kernel
theorem real_gain : (∑ i, |wr i|) = (((17 : ℚ) / (12 : ℚ)) : ℝ) := by
  have h := congrArg (fun a : ℚ => (a : ℝ)) gain_checked
  simpa only [wr, Rat.cast_sum, Rat.cast_abs, Rat.cast_div, Rat.cast_intCast,
    Rat.cast_ofNat, Rat.cast_neg] using h
theorem fitted_query : dot wr yr = dot qr br :=
  dual_prediction xr yr wr qr br (fun j => (d j : ℝ))
    (fit_check_sound normal_checked) (dual_check_sound dual_checked).1
    (dual_check_sound dual_checked).2
theorem sharp_radius (ε radius : ℝ) (he : 0 ≤ ε) :
    (∀ z : Fin 7 → ℝ, (∀ i, |z i - yr i| ≤ ε) → |dot wr z - dot wr yr| ≤ radius) ↔
      ε * (((17 : ℚ) / (12 : ℚ)) : ℝ) ≤ radius := by
  simpa only [real_gain] using sharp_radius_iff wr yr ε radius he
theorem conditional_physical_enclosure (truth : Fin 4 → ℝ) (ε : ℝ)
    (hm : ∀ i, |yr i - prediction xr truth i| ≤ ε) :
    |dot wr yr - dot qr truth| ≤ ε * (((17 : ℚ) / (12 : ℚ)) : ℝ) := by
  simpa only [real_gain] using physical_enclosure xr yr wr qr truth ε
    (dual_check_sound dual_checked).1 hm
end Q1
namespace Q1.Minimax
def w (i : Fin 7) : ℚ := ([((-5 : ℚ) / (64 : ℚ)), ((5 : ℚ) / (8 : ℚ)), ((15 : ℚ) / (32 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((-1 : ℚ) / (64 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ))] : List ℚ).getD i.val 0
def a (j : Fin 4) : ℚ := ([((-341 : ℚ) / (16 : ℚ)), ((335 : ℚ) / (48 : ℚ)), ((-11 : ℚ) / (16 : ℚ)), ((1 : ℚ) / (48 : ℚ))] : List ℚ).getD j.val 0
def wr (i : Fin 7) : ℝ := (w i : ℝ)
def ar (j : Fin 4) : ℝ := (a j : ℝ)
theorem optimality_checked : minimaxCheck x w Q1.q a ((19 : ℚ) / (16 : ℚ)) = true := by decide +kernel
theorem gain_checked : (∑ i, |w i|) = (((19 : ℚ) / (16 : ℚ)) : ℚ) := by decide +kernel
theorem real_gain : (∑ i, |wr i|) = (((19 : ℚ) / (16 : ℚ)) : ℝ) := by
  have h := congrArg (fun a : ℚ => (a : ℝ)) gain_checked
  simpa only [wr, Rat.cast_sum, Rat.cast_abs, Rat.cast_div, Rat.cast_intCast,
    Rat.cast_ofNat, Rat.cast_neg] using h
theorem globally_minimal_gain (v : Fin 7 → ℝ) (hv : Reproduces xr v Q1.qr) :
    (((19 : ℚ) / (16 : ℚ)) : ℝ) ≤ ∑ i, |v i| := by
  have h := minimax_check_sound optimality_checked
  have hm := minimax_weights_optimal xr wr Q1.qr ar h.2.1 h.2.2 v hv
  simpa only [real_gain] using hm
theorem sharp_radius (ε radius : ℝ) (he : 0 ≤ ε) :
    (∀ z : Fin 7 → ℝ, (∀ i, |z i - yr i| ≤ ε) → |dot wr z - dot wr yr| ≤ radius) ↔
      ε * (((19 : ℚ) / (16 : ℚ)) : ℝ) ≤ radius := by
  simpa only [real_gain] using sharp_radius_iff wr yr ε radius he
theorem no_reproducing_estimator_has_smaller_radius (ε radius : ℝ) (he : 0 ≤ ε)
    (v : Fin 7 → ℝ) (hv : Reproduces xr v Q1.qr)
    (hr : ∀ z, (∀ i, |z i - yr i| ≤ ε) → |dot v z - dot v yr| ≤ radius) :
    ε * (((19 : ℚ) / (16 : ℚ)) : ℝ) ≤ radius := by
  have h := minimax_check_sound optimality_checked
  have hm := minimax_radius_lower_bound xr yr wr Q1.qr ar h.2.1 h.2.2 ε radius he v hv hr
  simpa only [real_gain] using hm
theorem conditional_physical_enclosure (truth : Fin 4 → ℝ) (ε : ℝ)
    (hm : ∀ i, |yr i - prediction xr truth i| ≤ ε) :
    |dot wr yr - dot Q1.qr truth| ≤ ε * (((19 : ℚ) / (16 : ℚ)) : ℝ) := by
  simpa only [real_gain] using physical_enclosure xr yr wr Q1.qr truth ε
    (minimax_check_sound optimality_checked).1 hm
theorem uniform_minimax_over_all_prediction_functions (ε radius : ℝ) (he : 0 ≤ ε) :
    (∃ estimator : (Fin 7 → ℝ) → ℝ,
      ∀ truth observed, (∀ i, |observed i - prediction xr truth i| ≤ ε) →
        |estimator observed - dot Q1.qr truth| ≤ radius) ↔
      ε * (((19 : ℚ) / (16 : ℚ)) : ℝ) ≤ radius := by
  have h := minimax_check_sound optimality_checked
  simpa only [real_gain] using
    minimax_over_all_estimators_iff xr wr Q1.qr ar h.1 h.2.1 h.2.2 ε radius he
end Q1.Minimax
namespace Q2
def q (j : Fin 4) : ℚ := (((10 : ℚ) / (1 : ℚ)) : ℚ) ^ j.val
def w (i : Fin 7) : ℚ := ([((-27 : ℚ) / (224 : ℚ)), ((61 : ℚ) / (224 : ℚ)), ((87 : ℚ) / (224 : ℚ)), ((9 : ℚ) / (28 : ℚ)), ((37 : ℚ) / (224 : ℚ)), ((3 : ℚ) / (224 : ℚ)), ((-9 : ℚ) / (224 : ℚ))] : List ℚ).getD i.val 0
def d (j : Fin 4) : ℚ := ([((-10497 : ℚ) / (3584 : ℚ)), ((3193 : ℚ) / (3584 : ℚ)), ((-271 : ℚ) / (3584 : ℚ)), ((1 : ℚ) / (512 : ℚ))] : List ℚ).getD j.val 0
def wr (i : Fin 7) : ℝ := (w i : ℝ)
def qr (j : Fin 4) : ℝ := (q j : ℝ)
theorem dual_checked : dualCheck x w q d = true := by decide +kernel
theorem gain_checked : (∑ i, |w i|) = (((37 : ℚ) / (28 : ℚ)) : ℚ) := by decide +kernel
theorem real_gain : (∑ i, |wr i|) = (((37 : ℚ) / (28 : ℚ)) : ℝ) := by
  have h := congrArg (fun a : ℚ => (a : ℝ)) gain_checked
  simpa only [wr, Rat.cast_sum, Rat.cast_abs, Rat.cast_div, Rat.cast_intCast,
    Rat.cast_ofNat, Rat.cast_neg] using h
theorem fitted_query : dot wr yr = dot qr br :=
  dual_prediction xr yr wr qr br (fun j => (d j : ℝ))
    (fit_check_sound normal_checked) (dual_check_sound dual_checked).1
    (dual_check_sound dual_checked).2
theorem sharp_radius (ε radius : ℝ) (he : 0 ≤ ε) :
    (∀ z : Fin 7 → ℝ, (∀ i, |z i - yr i| ≤ ε) → |dot wr z - dot wr yr| ≤ radius) ↔
      ε * (((37 : ℚ) / (28 : ℚ)) : ℝ) ≤ radius := by
  simpa only [real_gain] using sharp_radius_iff wr yr ε radius he
theorem conditional_physical_enclosure (truth : Fin 4 → ℝ) (ε : ℝ)
    (hm : ∀ i, |yr i - prediction xr truth i| ≤ ε) :
    |dot wr yr - dot qr truth| ≤ ε * (((37 : ℚ) / (28 : ℚ)) : ℝ) := by
  simpa only [real_gain] using physical_enclosure xr yr wr qr truth ε
    (dual_check_sound dual_checked).1 hm
end Q2
namespace Q2.Minimax
def w (i : Fin 7) : ℚ := ([((-7 : ℚ) / (288 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((35 : ℚ) / (64 : ℚ)), ((35 : ℚ) / (72 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((-5 : ℚ) / (576 : ℚ))] : List ℚ).getD i.val 0
def a (j : Fin 4) : ℚ := ([((-287 : ℚ) / (32 : ℚ)), ((679 : ℚ) / (288 : ℚ)), ((-49 : ℚ) / (288 : ℚ)), ((1 : ℚ) / (288 : ℚ))] : List ℚ).getD j.val 0
def wr (i : Fin 7) : ℝ := (w i : ℝ)
def ar (j : Fin 4) : ℝ := (a j : ℝ)
theorem optimality_checked : minimaxCheck x w Q2.q a ((307 : ℚ) / (288 : ℚ)) = true := by decide +kernel
theorem gain_checked : (∑ i, |w i|) = (((307 : ℚ) / (288 : ℚ)) : ℚ) := by decide +kernel
theorem real_gain : (∑ i, |wr i|) = (((307 : ℚ) / (288 : ℚ)) : ℝ) := by
  have h := congrArg (fun a : ℚ => (a : ℝ)) gain_checked
  simpa only [wr, Rat.cast_sum, Rat.cast_abs, Rat.cast_div, Rat.cast_intCast,
    Rat.cast_ofNat, Rat.cast_neg] using h
theorem globally_minimal_gain (v : Fin 7 → ℝ) (hv : Reproduces xr v Q2.qr) :
    (((307 : ℚ) / (288 : ℚ)) : ℝ) ≤ ∑ i, |v i| := by
  have h := minimax_check_sound optimality_checked
  have hm := minimax_weights_optimal xr wr Q2.qr ar h.2.1 h.2.2 v hv
  simpa only [real_gain] using hm
theorem sharp_radius (ε radius : ℝ) (he : 0 ≤ ε) :
    (∀ z : Fin 7 → ℝ, (∀ i, |z i - yr i| ≤ ε) → |dot wr z - dot wr yr| ≤ radius) ↔
      ε * (((307 : ℚ) / (288 : ℚ)) : ℝ) ≤ radius := by
  simpa only [real_gain] using sharp_radius_iff wr yr ε radius he
theorem no_reproducing_estimator_has_smaller_radius (ε radius : ℝ) (he : 0 ≤ ε)
    (v : Fin 7 → ℝ) (hv : Reproduces xr v Q2.qr)
    (hr : ∀ z, (∀ i, |z i - yr i| ≤ ε) → |dot v z - dot v yr| ≤ radius) :
    ε * (((307 : ℚ) / (288 : ℚ)) : ℝ) ≤ radius := by
  have h := minimax_check_sound optimality_checked
  have hm := minimax_radius_lower_bound xr yr wr Q2.qr ar h.2.1 h.2.2 ε radius he v hv hr
  simpa only [real_gain] using hm
theorem conditional_physical_enclosure (truth : Fin 4 → ℝ) (ε : ℝ)
    (hm : ∀ i, |yr i - prediction xr truth i| ≤ ε) :
    |dot wr yr - dot Q2.qr truth| ≤ ε * (((307 : ℚ) / (288 : ℚ)) : ℝ) := by
  simpa only [real_gain] using physical_enclosure xr yr wr Q2.qr truth ε
    (minimax_check_sound optimality_checked).1 hm
theorem uniform_minimax_over_all_prediction_functions (ε radius : ℝ) (he : 0 ≤ ε) :
    (∃ estimator : (Fin 7 → ℝ) → ℝ,
      ∀ truth observed, (∀ i, |observed i - prediction xr truth i| ≤ ε) →
        |estimator observed - dot Q2.qr truth| ≤ radius) ↔
      ε * (((307 : ℚ) / (288 : ℚ)) : ℝ) ≤ radius := by
  have h := minimax_check_sound optimality_checked
  simpa only [real_gain] using
    minimax_over_all_estimators_iff xr wr Q2.qr ar h.1 h.2.1 h.2.2 ε radius he
end Q2.Minimax
namespace Q3
def q (j : Fin 4) : ℚ := (((12 : ℚ) / (1 : ℚ)) : ℚ) ^ j.val
def w (i : Fin 7) : ℚ := ([((-9 : ℚ) / (224 : ℚ)), ((3 : ℚ) / (224 : ℚ)), ((37 : ℚ) / (224 : ℚ)), ((9 : ℚ) / (28 : ℚ)), ((87 : ℚ) / (224 : ℚ)), ((61 : ℚ) / (224 : ℚ)), ((-27 : ℚ) / (224 : ℚ))] : List ℚ).getD i.val 0
def d (j : Fin 4) : ℚ := ([((3121 : ℚ) / (3584 : ℚ)), ((-1433 : ℚ) / (3584 : ℚ)), ((191 : ℚ) / (3584 : ℚ)), ((-1 : ℚ) / (512 : ℚ))] : List ℚ).getD j.val 0
def wr (i : Fin 7) : ℝ := (w i : ℝ)
def qr (j : Fin 4) : ℝ := (q j : ℝ)
theorem dual_checked : dualCheck x w q d = true := by decide +kernel
theorem gain_checked : (∑ i, |w i|) = (((37 : ℚ) / (28 : ℚ)) : ℚ) := by decide +kernel
theorem real_gain : (∑ i, |wr i|) = (((37 : ℚ) / (28 : ℚ)) : ℝ) := by
  have h := congrArg (fun a : ℚ => (a : ℝ)) gain_checked
  simpa only [wr, Rat.cast_sum, Rat.cast_abs, Rat.cast_div, Rat.cast_intCast,
    Rat.cast_ofNat, Rat.cast_neg] using h
theorem fitted_query : dot wr yr = dot qr br :=
  dual_prediction xr yr wr qr br (fun j => (d j : ℝ))
    (fit_check_sound normal_checked) (dual_check_sound dual_checked).1
    (dual_check_sound dual_checked).2
theorem sharp_radius (ε radius : ℝ) (he : 0 ≤ ε) :
    (∀ z : Fin 7 → ℝ, (∀ i, |z i - yr i| ≤ ε) → |dot wr z - dot wr yr| ≤ radius) ↔
      ε * (((37 : ℚ) / (28 : ℚ)) : ℝ) ≤ radius := by
  simpa only [real_gain] using sharp_radius_iff wr yr ε radius he
theorem conditional_physical_enclosure (truth : Fin 4 → ℝ) (ε : ℝ)
    (hm : ∀ i, |yr i - prediction xr truth i| ≤ ε) :
    |dot wr yr - dot qr truth| ≤ ε * (((37 : ℚ) / (28 : ℚ)) : ℝ) := by
  simpa only [real_gain] using physical_enclosure xr yr wr qr truth ε
    (dual_check_sound dual_checked).1 hm
end Q3
namespace Q3.Minimax
def w (i : Fin 7) : ℚ := ([((-5 : ℚ) / (576 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((35 : ℚ) / (72 : ℚ)), ((35 : ℚ) / (64 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((-7 : ℚ) / (288 : ℚ))] : List ℚ).getD i.val 0
def a (j : Fin 4) : ℚ := ([((-713 : ℚ) / (288 : ℚ)), ((25 : ℚ) / (288 : ℚ)), ((17 : ℚ) / (288 : ℚ)), ((-1 : ℚ) / (288 : ℚ))] : List ℚ).getD j.val 0
def wr (i : Fin 7) : ℝ := (w i : ℝ)
def ar (j : Fin 4) : ℝ := (a j : ℝ)
theorem optimality_checked : minimaxCheck x w Q3.q a ((307 : ℚ) / (288 : ℚ)) = true := by decide +kernel
theorem gain_checked : (∑ i, |w i|) = (((307 : ℚ) / (288 : ℚ)) : ℚ) := by decide +kernel
theorem real_gain : (∑ i, |wr i|) = (((307 : ℚ) / (288 : ℚ)) : ℝ) := by
  have h := congrArg (fun a : ℚ => (a : ℝ)) gain_checked
  simpa only [wr, Rat.cast_sum, Rat.cast_abs, Rat.cast_div, Rat.cast_intCast,
    Rat.cast_ofNat, Rat.cast_neg] using h
theorem globally_minimal_gain (v : Fin 7 → ℝ) (hv : Reproduces xr v Q3.qr) :
    (((307 : ℚ) / (288 : ℚ)) : ℝ) ≤ ∑ i, |v i| := by
  have h := minimax_check_sound optimality_checked
  have hm := minimax_weights_optimal xr wr Q3.qr ar h.2.1 h.2.2 v hv
  simpa only [real_gain] using hm
theorem sharp_radius (ε radius : ℝ) (he : 0 ≤ ε) :
    (∀ z : Fin 7 → ℝ, (∀ i, |z i - yr i| ≤ ε) → |dot wr z - dot wr yr| ≤ radius) ↔
      ε * (((307 : ℚ) / (288 : ℚ)) : ℝ) ≤ radius := by
  simpa only [real_gain] using sharp_radius_iff wr yr ε radius he
theorem no_reproducing_estimator_has_smaller_radius (ε radius : ℝ) (he : 0 ≤ ε)
    (v : Fin 7 → ℝ) (hv : Reproduces xr v Q3.qr)
    (hr : ∀ z, (∀ i, |z i - yr i| ≤ ε) → |dot v z - dot v yr| ≤ radius) :
    ε * (((307 : ℚ) / (288 : ℚ)) : ℝ) ≤ radius := by
  have h := minimax_check_sound optimality_checked
  have hm := minimax_radius_lower_bound xr yr wr Q3.qr ar h.2.1 h.2.2 ε radius he v hv hr
  simpa only [real_gain] using hm
theorem conditional_physical_enclosure (truth : Fin 4 → ℝ) (ε : ℝ)
    (hm : ∀ i, |yr i - prediction xr truth i| ≤ ε) :
    |dot wr yr - dot Q3.qr truth| ≤ ε * (((307 : ℚ) / (288 : ℚ)) : ℝ) := by
  simpa only [real_gain] using physical_enclosure xr yr wr Q3.qr truth ε
    (minimax_check_sound optimality_checked).1 hm
theorem uniform_minimax_over_all_prediction_functions (ε radius : ℝ) (he : 0 ≤ ε) :
    (∃ estimator : (Fin 7 → ℝ) → ℝ,
      ∀ truth observed, (∀ i, |observed i - prediction xr truth i| ≤ ε) →
        |estimator observed - dot Q3.qr truth| ≤ radius) ↔
      ε * (((307 : ℚ) / (288 : ℚ)) : ℝ) ≤ radius := by
  have h := minimax_check_sound optimality_checked
  simpa only [real_gain] using
    minimax_over_all_estimators_iff xr wr Q3.qr ar h.1 h.2.1 h.2.2 ε radius he
end Q3.Minimax
namespace Q4
def q (j : Fin 4) : ℚ := (((14 : ℚ) / (1 : ℚ)) : ℚ) ^ j.val
def w (i : Fin 7) : ℚ := ([((17 : ℚ) / (224 : ℚ)), ((-109 : ℚ) / (672 : ℚ)), ((-31 : ℚ) / (672 : ℚ)), ((19 : ℚ) / (84 : ℚ)), ((307 : ℚ) / (672 : ℚ)), ((43 : ℚ) / (96 : ℚ)), ((1 : ℚ) / (672 : ℚ))] : List ℚ).getD i.val 0
def d (j : Fin 4) : ℚ := ([((37841 : ℚ) / (10752 : ℚ)), ((-39995 : ℚ) / (32256 : ℚ)), ((67 : ℚ) / (512 : ℚ)), ((-19 : ℚ) / (4608 : ℚ))] : List ℚ).getD j.val 0
def wr (i : Fin 7) : ℝ := (w i : ℝ)
def qr (j : Fin 4) : ℝ := (q j : ℝ)
theorem dual_checked : dualCheck x w q d = true := by decide +kernel
theorem gain_checked : (∑ i, |w i|) = (((17 : ℚ) / (12 : ℚ)) : ℚ) := by decide +kernel
theorem real_gain : (∑ i, |wr i|) = (((17 : ℚ) / (12 : ℚ)) : ℝ) := by
  have h := congrArg (fun a : ℚ => (a : ℝ)) gain_checked
  simpa only [wr, Rat.cast_sum, Rat.cast_abs, Rat.cast_div, Rat.cast_intCast,
    Rat.cast_ofNat, Rat.cast_neg] using h
theorem fitted_query : dot wr yr = dot qr br :=
  dual_prediction xr yr wr qr br (fun j => (d j : ℝ))
    (fit_check_sound normal_checked) (dual_check_sound dual_checked).1
    (dual_check_sound dual_checked).2
theorem sharp_radius (ε radius : ℝ) (he : 0 ≤ ε) :
    (∀ z : Fin 7 → ℝ, (∀ i, |z i - yr i| ≤ ε) → |dot wr z - dot wr yr| ≤ radius) ↔
      ε * (((17 : ℚ) / (12 : ℚ)) : ℝ) ≤ radius := by
  simpa only [real_gain] using sharp_radius_iff wr yr ε radius he
theorem conditional_physical_enclosure (truth : Fin 4 → ℝ) (ε : ℝ)
    (hm : ∀ i, |yr i - prediction xr truth i| ≤ ε) :
    |dot wr yr - dot qr truth| ≤ ε * (((17 : ℚ) / (12 : ℚ)) : ℝ) := by
  simpa only [real_gain] using physical_enclosure xr yr wr qr truth ε
    (dual_check_sound dual_checked).1 hm
end Q4
namespace Q4.Minimax
def w (i : Fin 7) : ℚ := ([((7 : ℚ) / (160 : ℚ)), ((-3 : ℚ) / (32 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((21 : ℚ) / (32 : ℚ)), ((63 : ℚ) / (160 : ℚ)), ((0 : ℚ) / (1 : ℚ))] : List ℚ).getD i.val 0
def a (j : Fin 4) : ℚ := ([((341 : ℚ) / (16 : ℚ)), ((-335 : ℚ) / (48 : ℚ)), ((11 : ℚ) / (16 : ℚ)), ((-1 : ℚ) / (48 : ℚ))] : List ℚ).getD j.val 0
def wr (i : Fin 7) : ℝ := (w i : ℝ)
def ar (j : Fin 4) : ℝ := (a j : ℝ)
theorem optimality_checked : minimaxCheck x w Q4.q a ((19 : ℚ) / (16 : ℚ)) = true := by decide +kernel
theorem gain_checked : (∑ i, |w i|) = (((19 : ℚ) / (16 : ℚ)) : ℚ) := by decide +kernel
theorem real_gain : (∑ i, |wr i|) = (((19 : ℚ) / (16 : ℚ)) : ℝ) := by
  have h := congrArg (fun a : ℚ => (a : ℝ)) gain_checked
  simpa only [wr, Rat.cast_sum, Rat.cast_abs, Rat.cast_div, Rat.cast_intCast,
    Rat.cast_ofNat, Rat.cast_neg] using h
theorem globally_minimal_gain (v : Fin 7 → ℝ) (hv : Reproduces xr v Q4.qr) :
    (((19 : ℚ) / (16 : ℚ)) : ℝ) ≤ ∑ i, |v i| := by
  have h := minimax_check_sound optimality_checked
  have hm := minimax_weights_optimal xr wr Q4.qr ar h.2.1 h.2.2 v hv
  simpa only [real_gain] using hm
theorem sharp_radius (ε radius : ℝ) (he : 0 ≤ ε) :
    (∀ z : Fin 7 → ℝ, (∀ i, |z i - yr i| ≤ ε) → |dot wr z - dot wr yr| ≤ radius) ↔
      ε * (((19 : ℚ) / (16 : ℚ)) : ℝ) ≤ radius := by
  simpa only [real_gain] using sharp_radius_iff wr yr ε radius he
theorem no_reproducing_estimator_has_smaller_radius (ε radius : ℝ) (he : 0 ≤ ε)
    (v : Fin 7 → ℝ) (hv : Reproduces xr v Q4.qr)
    (hr : ∀ z, (∀ i, |z i - yr i| ≤ ε) → |dot v z - dot v yr| ≤ radius) :
    ε * (((19 : ℚ) / (16 : ℚ)) : ℝ) ≤ radius := by
  have h := minimax_check_sound optimality_checked
  have hm := minimax_radius_lower_bound xr yr wr Q4.qr ar h.2.1 h.2.2 ε radius he v hv hr
  simpa only [real_gain] using hm
theorem conditional_physical_enclosure (truth : Fin 4 → ℝ) (ε : ℝ)
    (hm : ∀ i, |yr i - prediction xr truth i| ≤ ε) :
    |dot wr yr - dot Q4.qr truth| ≤ ε * (((19 : ℚ) / (16 : ℚ)) : ℝ) := by
  simpa only [real_gain] using physical_enclosure xr yr wr Q4.qr truth ε
    (minimax_check_sound optimality_checked).1 hm
theorem uniform_minimax_over_all_prediction_functions (ε radius : ℝ) (he : 0 ≤ ε) :
    (∃ estimator : (Fin 7 → ℝ) → ℝ,
      ∀ truth observed, (∀ i, |observed i - prediction xr truth i| ≤ ε) →
        |estimator observed - dot Q4.qr truth| ≤ radius) ↔
      ε * (((19 : ℚ) / (16 : ℚ)) : ℝ) ≤ radius := by
  have h := minimax_check_sound optimality_checked
  simpa only [real_gain] using
    minimax_over_all_estimators_iff xr wr Q4.qr ar h.1 h.2.1 h.2.2 ε radius he
end Q4.Minimax
namespace Q5
def q (j : Fin 4) : ℚ := (((16 : ℚ) / (1 : ℚ)) : ℚ) ^ j.val
def w (i : Fin 7) : ℚ := ([((41 : ℚ) / (672 : ℚ)), ((-59 : ℚ) / (672 : ℚ)), ((-53 : ℚ) / (672 : ℚ)), ((1 : ℚ) / (28 : ℚ)), ((137 : ℚ) / (672 : ℚ)), ((251 : ℚ) / (672 : ℚ)), ((331 : ℚ) / (672 : ℚ))] : List ℚ).getD i.val 0
def d (j : Fin 4) : ℚ := ([((15751 : ℚ) / (10752 : ℚ)), ((-15037 : ℚ) / (32256 : ℚ)), ((457 : ℚ) / (10752 : ℚ)), ((-5 : ℚ) / (4608 : ℚ))] : List ℚ).getD j.val 0
def wr (i : Fin 7) : ℝ := (w i : ℝ)
def qr (j : Fin 4) : ℝ := (q j : ℝ)
theorem dual_checked : dualCheck x w q d = true := by decide +kernel
theorem gain_checked : (∑ i, |w i|) = (((4 : ℚ) / (3 : ℚ)) : ℚ) := by decide +kernel
theorem real_gain : (∑ i, |wr i|) = (((4 : ℚ) / (3 : ℚ)) : ℝ) := by
  have h := congrArg (fun a : ℚ => (a : ℝ)) gain_checked
  simpa only [wr, Rat.cast_sum, Rat.cast_abs, Rat.cast_div, Rat.cast_intCast,
    Rat.cast_ofNat, Rat.cast_neg] using h
theorem fitted_query : dot wr yr = dot qr br :=
  dual_prediction xr yr wr qr br (fun j => (d j : ℝ))
    (fit_check_sound normal_checked) (dual_check_sound dual_checked).1
    (dual_check_sound dual_checked).2
theorem sharp_radius (ε radius : ℝ) (he : 0 ≤ ε) :
    (∀ z : Fin 7 → ℝ, (∀ i, |z i - yr i| ≤ ε) → |dot wr z - dot wr yr| ≤ radius) ↔
      ε * (((4 : ℚ) / (3 : ℚ)) : ℝ) ≤ radius := by
  simpa only [real_gain] using sharp_radius_iff wr yr ε radius he
theorem conditional_physical_enclosure (truth : Fin 4 → ℝ) (ε : ℝ)
    (hm : ∀ i, |yr i - prediction xr truth i| ≤ ε) :
    |dot wr yr - dot qr truth| ≤ ε * (((4 : ℚ) / (3 : ℚ)) : ℝ) := by
  simpa only [real_gain] using physical_enclosure xr yr wr qr truth ε
    (dual_check_sound dual_checked).1 hm
end Q5
namespace Q5.Minimax
def w (i : Fin 7) : ℚ := ([((7 : ℚ) / (480 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((-11 : ℚ) / (192 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((77 : ℚ) / (120 : ℚ)), ((77 : ℚ) / (192 : ℚ))] : List ℚ).getD i.val 0
def a (j : Fin 4) : ℚ := ([((457 : ℚ) / (32 : ℚ)), ((-415 : ℚ) / (96 : ℚ)), ((37 : ℚ) / (96 : ℚ)), ((-1 : ℚ) / (96 : ℚ))] : List ℚ).getD j.val 0
def wr (i : Fin 7) : ℝ := (w i : ℝ)
def ar (j : Fin 4) : ℝ := (a j : ℝ)
theorem optimality_checked : minimaxCheck x w Q5.q a ((107 : ℚ) / (96 : ℚ)) = true := by decide +kernel
theorem gain_checked : (∑ i, |w i|) = (((107 : ℚ) / (96 : ℚ)) : ℚ) := by decide +kernel
theorem real_gain : (∑ i, |wr i|) = (((107 : ℚ) / (96 : ℚ)) : ℝ) := by
  have h := congrArg (fun a : ℚ => (a : ℝ)) gain_checked
  simpa only [wr, Rat.cast_sum, Rat.cast_abs, Rat.cast_div, Rat.cast_intCast,
    Rat.cast_ofNat, Rat.cast_neg] using h
theorem globally_minimal_gain (v : Fin 7 → ℝ) (hv : Reproduces xr v Q5.qr) :
    (((107 : ℚ) / (96 : ℚ)) : ℝ) ≤ ∑ i, |v i| := by
  have h := minimax_check_sound optimality_checked
  have hm := minimax_weights_optimal xr wr Q5.qr ar h.2.1 h.2.2 v hv
  simpa only [real_gain] using hm
theorem sharp_radius (ε radius : ℝ) (he : 0 ≤ ε) :
    (∀ z : Fin 7 → ℝ, (∀ i, |z i - yr i| ≤ ε) → |dot wr z - dot wr yr| ≤ radius) ↔
      ε * (((107 : ℚ) / (96 : ℚ)) : ℝ) ≤ radius := by
  simpa only [real_gain] using sharp_radius_iff wr yr ε radius he
theorem no_reproducing_estimator_has_smaller_radius (ε radius : ℝ) (he : 0 ≤ ε)
    (v : Fin 7 → ℝ) (hv : Reproduces xr v Q5.qr)
    (hr : ∀ z, (∀ i, |z i - yr i| ≤ ε) → |dot v z - dot v yr| ≤ radius) :
    ε * (((107 : ℚ) / (96 : ℚ)) : ℝ) ≤ radius := by
  have h := minimax_check_sound optimality_checked
  have hm := minimax_radius_lower_bound xr yr wr Q5.qr ar h.2.1 h.2.2 ε radius he v hv hr
  simpa only [real_gain] using hm
theorem conditional_physical_enclosure (truth : Fin 4 → ℝ) (ε : ℝ)
    (hm : ∀ i, |yr i - prediction xr truth i| ≤ ε) :
    |dot wr yr - dot Q5.qr truth| ≤ ε * (((107 : ℚ) / (96 : ℚ)) : ℝ) := by
  simpa only [real_gain] using physical_enclosure xr yr wr Q5.qr truth ε
    (minimax_check_sound optimality_checked).1 hm
theorem uniform_minimax_over_all_prediction_functions (ε radius : ℝ) (he : 0 ≤ ε) :
    (∃ estimator : (Fin 7 → ℝ) → ℝ,
      ∀ truth observed, (∀ i, |observed i - prediction xr truth i| ≤ ε) →
        |estimator observed - dot Q5.qr truth| ≤ radius) ↔
      ε * (((107 : ℚ) / (96 : ℚ)) : ℝ) ≤ radius := by
  have h := minimax_check_sound optimality_checked
  simpa only [real_gain] using
    minimax_over_all_estimators_iff xr wr Q5.qr ar h.1 h.2.1 h.2.2 ε radius he
end Q5.Minimax
namespace Q6
def q (j : Fin 4) : ℚ := (((18 : ℚ) / (1 : ℚ)) : ℚ) ^ j.val
def w (i : Fin 7) : ℚ := ([((-169 : ℚ) / (672 : ℚ)), ((271 : ℚ) / (672 : ℚ)), ((157 : ℚ) / (672 : ℚ)), ((-1 : ℚ) / (4 : ℚ)), ((-361 : ℚ) / (672 : ℚ)), ((-79 : ℚ) / (672 : ℚ)), ((1021 : ℚ) / (672 : ℚ))] : List ℚ).getD i.val 0
def d (j : Fin 4) : ℚ := ([((-95099 : ℚ) / (10752 : ℚ)), ((99497 : ℚ) / (32256 : ℚ)), ((-3509 : ℚ) / (10752 : ℚ)), ((49 : ℚ) / (4608 : ℚ))] : List ℚ).getD j.val 0
def wr (i : Fin 7) : ℝ := (w i : ℝ)
def qr (j : Fin 4) : ℝ := (q j : ℝ)
theorem dual_checked : dualCheck x w q d = true := by decide +kernel
theorem gain_checked : (∑ i, |w i|) = (((53 : ℚ) / (16 : ℚ)) : ℚ) := by decide +kernel
theorem real_gain : (∑ i, |wr i|) = (((53 : ℚ) / (16 : ℚ)) : ℝ) := by
  have h := congrArg (fun a : ℚ => (a : ℝ)) gain_checked
  simpa only [wr, Rat.cast_sum, Rat.cast_abs, Rat.cast_div, Rat.cast_intCast,
    Rat.cast_ofNat, Rat.cast_neg] using h
theorem fitted_query : dot wr yr = dot qr br :=
  dual_prediction xr yr wr qr br (fun j => (d j : ℝ))
    (fit_check_sound normal_checked) (dual_check_sound dual_checked).1
    (dual_check_sound dual_checked).2
theorem sharp_radius (ε radius : ℝ) (he : 0 ≤ ε) :
    (∀ z : Fin 7 → ℝ, (∀ i, |z i - yr i| ≤ ε) → |dot wr z - dot wr yr| ≤ radius) ↔
      ε * (((53 : ℚ) / (16 : ℚ)) : ℝ) ≤ radius := by
  simpa only [real_gain] using sharp_radius_iff wr yr ε radius he
theorem conditional_physical_enclosure (truth : Fin 4 → ℝ) (ε : ℝ)
    (hm : ∀ i, |yr i - prediction xr truth i| ≤ ε) :
    |dot wr yr - dot qr truth| ≤ ε * (((53 : ℚ) / (16 : ℚ)) : ℝ) := by
  simpa only [real_gain] using physical_enclosure xr yr wr qr truth ε
    (dual_check_sound dual_checked).1 hm
end Q6
namespace Q6.Minimax
def w (i : Fin 7) : ℚ := ([((-55 : ℚ) / (192 : ℚ)), ((13 : ℚ) / (24 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((-143 : ℚ) / (192 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((143 : ℚ) / (96 : ℚ))] : List ℚ).getD i.val 0
def a (j : Fin 4) : ℚ := ([((-341 : ℚ) / (16 : ℚ)), ((335 : ℚ) / (48 : ℚ)), ((-11 : ℚ) / (16 : ℚ)), ((1 : ℚ) / (48 : ℚ))] : List ℚ).getD j.val 0
def wr (i : Fin 7) : ℝ := (w i : ℝ)
def ar (j : Fin 4) : ℝ := (a j : ℝ)
theorem optimality_checked : minimaxCheck x w Q6.q a ((49 : ℚ) / (16 : ℚ)) = true := by decide +kernel
theorem gain_checked : (∑ i, |w i|) = (((49 : ℚ) / (16 : ℚ)) : ℚ) := by decide +kernel
theorem real_gain : (∑ i, |wr i|) = (((49 : ℚ) / (16 : ℚ)) : ℝ) := by
  have h := congrArg (fun a : ℚ => (a : ℝ)) gain_checked
  simpa only [wr, Rat.cast_sum, Rat.cast_abs, Rat.cast_div, Rat.cast_intCast,
    Rat.cast_ofNat, Rat.cast_neg] using h
theorem globally_minimal_gain (v : Fin 7 → ℝ) (hv : Reproduces xr v Q6.qr) :
    (((49 : ℚ) / (16 : ℚ)) : ℝ) ≤ ∑ i, |v i| := by
  have h := minimax_check_sound optimality_checked
  have hm := minimax_weights_optimal xr wr Q6.qr ar h.2.1 h.2.2 v hv
  simpa only [real_gain] using hm
theorem sharp_radius (ε radius : ℝ) (he : 0 ≤ ε) :
    (∀ z : Fin 7 → ℝ, (∀ i, |z i - yr i| ≤ ε) → |dot wr z - dot wr yr| ≤ radius) ↔
      ε * (((49 : ℚ) / (16 : ℚ)) : ℝ) ≤ radius := by
  simpa only [real_gain] using sharp_radius_iff wr yr ε radius he
theorem no_reproducing_estimator_has_smaller_radius (ε radius : ℝ) (he : 0 ≤ ε)
    (v : Fin 7 → ℝ) (hv : Reproduces xr v Q6.qr)
    (hr : ∀ z, (∀ i, |z i - yr i| ≤ ε) → |dot v z - dot v yr| ≤ radius) :
    ε * (((49 : ℚ) / (16 : ℚ)) : ℝ) ≤ radius := by
  have h := minimax_check_sound optimality_checked
  have hm := minimax_radius_lower_bound xr yr wr Q6.qr ar h.2.1 h.2.2 ε radius he v hv hr
  simpa only [real_gain] using hm
theorem conditional_physical_enclosure (truth : Fin 4 → ℝ) (ε : ℝ)
    (hm : ∀ i, |yr i - prediction xr truth i| ≤ ε) :
    |dot wr yr - dot Q6.qr truth| ≤ ε * (((49 : ℚ) / (16 : ℚ)) : ℝ) := by
  simpa only [real_gain] using physical_enclosure xr yr wr Q6.qr truth ε
    (minimax_check_sound optimality_checked).1 hm
theorem uniform_minimax_over_all_prediction_functions (ε radius : ℝ) (he : 0 ≤ ε) :
    (∃ estimator : (Fin 7 → ℝ) → ℝ,
      ∀ truth observed, (∀ i, |observed i - prediction xr truth i| ≤ ε) →
        |estimator observed - dot Q6.qr truth| ≤ radius) ↔
      ε * (((49 : ℚ) / (16 : ℚ)) : ℝ) ≤ radius := by
  have h := minimax_check_sound optimality_checked
  simpa only [real_gain] using
    minimax_over_all_estimators_iff xr wr Q6.qr ar h.1 h.2.1 h.2.2 ε radius he
end Q6.Minimax
namespace Q7
def q (j : Fin 4) : ℚ := (((24 : ℚ) / (1 : ℚ)) : ℚ) ^ j.val
def w (i : Fin 7) : ℚ := ([((-3119 : ℚ) / (672 : ℚ)), ((4061 : ℚ) / (672 : ℚ)), ((3299 : ℚ) / (672 : ℚ)), ((-47 : ℚ) / (28 : ℚ)), ((-4943 : ℚ) / (672 : ℚ)), ((-3869 : ℚ) / (672 : ℚ)), ((6371 : ℚ) / (672 : ℚ))] : List ℚ).getD i.val 0
def d (j : Fin 4) : ℚ := ([((-1342129 : ℚ) / (10752 : ℚ)), ((1355755 : ℚ) / (32256 : ℚ)), ((-45823 : ℚ) / (10752 : ℚ)), ((611 : ℚ) / (4608 : ℚ))] : List ℚ).getD j.val 0
def wr (i : Fin 7) : ℝ := (w i : ℝ)
def qr (j : Fin 4) : ℝ := (q j : ℝ)
theorem dual_checked : dualCheck x w q d = true := by decide +kernel
theorem gain_checked : (∑ i, |w i|) = (((4465 : ℚ) / (112 : ℚ)) : ℚ) := by decide +kernel
theorem real_gain : (∑ i, |wr i|) = (((4465 : ℚ) / (112 : ℚ)) : ℝ) := by
  have h := congrArg (fun a : ℚ => (a : ℝ)) gain_checked
  simpa only [wr, Rat.cast_sum, Rat.cast_abs, Rat.cast_div, Rat.cast_intCast,
    Rat.cast_ofNat, Rat.cast_neg] using h
theorem fitted_query : dot wr yr = dot qr br :=
  dual_prediction xr yr wr qr br (fun j => (d j : ℝ))
    (fit_check_sound normal_checked) (dual_check_sound dual_checked).1
    (dual_check_sound dual_checked).2
theorem sharp_radius (ε radius : ℝ) (he : 0 ≤ ε) :
    (∀ z : Fin 7 → ℝ, (∀ i, |z i - yr i| ≤ ε) → |dot wr z - dot wr yr| ≤ radius) ↔
      ε * (((4465 : ℚ) / (112 : ℚ)) : ℝ) ≤ radius := by
  simpa only [real_gain] using sharp_radius_iff wr yr ε radius he
theorem conditional_physical_enclosure (truth : Fin 4 → ℝ) (ε : ℝ)
    (hm : ∀ i, |yr i - prediction xr truth i| ≤ ε) :
    |dot wr yr - dot qr truth| ≤ ε * (((4465 : ℚ) / (112 : ℚ)) : ℝ) := by
  simpa only [real_gain] using physical_enclosure xr yr wr qr truth ε
    (dual_check_sound dual_checked).1 hm
end Q7
namespace Q7.Minimax
def w (i : Fin 7) : ℚ := ([((-1309 : ℚ) / (192 : ℚ)), ((1463 : ℚ) / (120 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((-2261 : ℚ) / (192 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((3553 : ℚ) / (480 : ℚ))] : List ℚ).getD i.val 0
def a (j : Fin 4) : ℚ := ([((-341 : ℚ) / (16 : ℚ)), ((335 : ℚ) / (48 : ℚ)), ((-11 : ℚ) / (16 : ℚ)), ((1 : ℚ) / (48 : ℚ))] : List ℚ).getD j.val 0
def wr (i : Fin 7) : ℝ := (w i : ℝ)
def ar (j : Fin 4) : ℝ := (a j : ℝ)
theorem optimality_checked : minimaxCheck x w Q7.q a ((611 : ℚ) / (16 : ℚ)) = true := by decide +kernel
theorem gain_checked : (∑ i, |w i|) = (((611 : ℚ) / (16 : ℚ)) : ℚ) := by decide +kernel
theorem real_gain : (∑ i, |wr i|) = (((611 : ℚ) / (16 : ℚ)) : ℝ) := by
  have h := congrArg (fun a : ℚ => (a : ℝ)) gain_checked
  simpa only [wr, Rat.cast_sum, Rat.cast_abs, Rat.cast_div, Rat.cast_intCast,
    Rat.cast_ofNat, Rat.cast_neg] using h
theorem globally_minimal_gain (v : Fin 7 → ℝ) (hv : Reproduces xr v Q7.qr) :
    (((611 : ℚ) / (16 : ℚ)) : ℝ) ≤ ∑ i, |v i| := by
  have h := minimax_check_sound optimality_checked
  have hm := minimax_weights_optimal xr wr Q7.qr ar h.2.1 h.2.2 v hv
  simpa only [real_gain] using hm
theorem sharp_radius (ε radius : ℝ) (he : 0 ≤ ε) :
    (∀ z : Fin 7 → ℝ, (∀ i, |z i - yr i| ≤ ε) → |dot wr z - dot wr yr| ≤ radius) ↔
      ε * (((611 : ℚ) / (16 : ℚ)) : ℝ) ≤ radius := by
  simpa only [real_gain] using sharp_radius_iff wr yr ε radius he
theorem no_reproducing_estimator_has_smaller_radius (ε radius : ℝ) (he : 0 ≤ ε)
    (v : Fin 7 → ℝ) (hv : Reproduces xr v Q7.qr)
    (hr : ∀ z, (∀ i, |z i - yr i| ≤ ε) → |dot v z - dot v yr| ≤ radius) :
    ε * (((611 : ℚ) / (16 : ℚ)) : ℝ) ≤ radius := by
  have h := minimax_check_sound optimality_checked
  have hm := minimax_radius_lower_bound xr yr wr Q7.qr ar h.2.1 h.2.2 ε radius he v hv hr
  simpa only [real_gain] using hm
theorem conditional_physical_enclosure (truth : Fin 4 → ℝ) (ε : ℝ)
    (hm : ∀ i, |yr i - prediction xr truth i| ≤ ε) :
    |dot wr yr - dot Q7.qr truth| ≤ ε * (((611 : ℚ) / (16 : ℚ)) : ℝ) := by
  simpa only [real_gain] using physical_enclosure xr yr wr Q7.qr truth ε
    (minimax_check_sound optimality_checked).1 hm
theorem uniform_minimax_over_all_prediction_functions (ε radius : ℝ) (he : 0 ≤ ε) :
    (∃ estimator : (Fin 7 → ℝ) → ℝ,
      ∀ truth observed, (∀ i, |observed i - prediction xr truth i| ≤ ε) →
        |estimator observed - dot Q7.qr truth| ≤ radius) ↔
      ε * (((611 : ℚ) / (16 : ℚ)) : ℝ) ≤ radius := by
  have h := minimax_check_sound optimality_checked
  simpa only [real_gain] using
    minimax_over_all_estimators_iff xr wr Q7.qr ar h.1 h.2.1 h.2.2 ε radius he
end Q7.Minimax
end PCSCalibrationReplay.M4

namespace PCSCalibrationReplay.M5
def abscissa (i : Fin 14) : ℚ := ([((5 : ℚ) / (1 : ℚ)), ((6 : ℚ) / (1 : ℚ)), ((7 : ℚ) / (1 : ℚ)), ((8 : ℚ) / (1 : ℚ)), ((9 : ℚ) / (1 : ℚ)), ((10 : ℚ) / (1 : ℚ)), ((11 : ℚ) / (1 : ℚ)), ((12 : ℚ) / (1 : ℚ)), ((13 : ℚ) / (1 : ℚ)), ((14 : ℚ) / (1 : ℚ)), ((15 : ℚ) / (1 : ℚ)), ((16 : ℚ) / (1 : ℚ)), ((17 : ℚ) / (1 : ℚ)), ((18 : ℚ) / (1 : ℚ))] : List ℚ).getD i.val 0
def x (i : Fin 14) (j : Fin 4) : ℚ := abscissa i ^ j.val
def y (i : Fin 14) : ℚ := ([((1 : ℚ) / (25 : ℚ)), ((17 : ℚ) / (100 : ℚ)), ((37 : ℚ) / (100 : ℚ)), ((33 : ℚ) / (50 : ℚ)), ((53 : ℚ) / (50 : ℚ)), ((159 : ℚ) / (100 : ℚ)), ((233 : ℚ) / (100 : ℚ)), ((329 : ℚ) / (100 : ℚ)), ((461 : ℚ) / (100 : ℚ)), ((711 : ℚ) / (100 : ℚ)), ((1199 : ℚ) / (100 : ℚ)), ((2109 : ℚ) / (100 : ℚ)), ((3501 : ℚ) / (100 : ℚ)), ((259 : ℚ) / (5 : ℚ))] : List ℚ).getD i.val 0
def b (j : Fin 4) : ℚ := ([((-175634037 : ℚ) / (3403400 : ℚ)), ((253548717 : ℚ) / (13613600 : ℚ)), ((-2872047 : ℚ) / (1361360 : ℚ)), ((150231 : ℚ) / (1944800 : ℚ))] : List ℚ).getD j.val 0
def xr (i : Fin 14) (j : Fin 4) : ℝ := (x i j : ℝ)
def yr (i : Fin 14) : ℝ := (y i : ℝ)
def br (j : Fin 4) : ℝ := (b j : ℝ)
theorem normal_checked : fitCheck x y b = true := by decide +kernel
theorem residual_checked : loss x y b = ((2895745113 : ℚ) / (136136000 : ℚ)) := by decide +kernel
theorem global_optimum : ∀ c : Fin 4 → ℝ,
    (((2895745113 : ℚ) / (136136000 : ℚ)) : ℝ) ≤ loss xr yr c := by
  have hs : loss xr yr br = (((2895745113 : ℚ) / (136136000 : ℚ)) : ℝ) := by
    calc
      loss xr yr br = ((loss x y b : ℚ) : ℝ) := (cast_loss x y b).symm
      _ = (((2895745113 : ℚ) / (136136000 : ℚ)) : ℝ) := by
        simpa only [Rat.cast_div, Rat.cast_intCast, Rat.cast_ofNat, Rat.cast_neg]
          using congrArg (fun a : ℚ => (a : ℝ)) residual_checked
  simpa only [hs] using global_minimum xr yr br (fit_check_sound normal_checked)
theorem excludes_every_better_model (threshold : ℝ)
    (h : threshold < (((2895745113 : ℚ) / (136136000 : ℚ)) : ℝ)) :
    ∀ c : Fin 4 → ℝ, threshold < loss xr yr c := by
  intro c
  exact h.trans_le (global_optimum c)
theorem uniform_error_exclusion (ε : ℝ) (he : 0 ≤ ε)
    (hgap : (14 : ℝ) * ε ^ 2 < (((2895745113 : ℚ) / (136136000 : ℚ)) : ℝ)) :
    ¬ (∃ c : Fin 4 → ℝ, ∀ i, |yr i - prediction xr c i| ≤ ε) :=
  PCSReal.Calibration.uniform_error_exclusion xr yr (((2895745113 : ℚ) / (136136000 : ℚ)) : ℝ) ε
    global_optimum he (by simpa using hgap)
end PCSCalibrationReplay.M5

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
#print axioms PCSCalibrationReplay.M0.Q1.dual_checked
#print axioms PCSCalibrationReplay.M0.Q1.gain_checked
#print axioms PCSCalibrationReplay.M0.Q1.real_gain
#print axioms PCSCalibrationReplay.M0.Q1.fitted_query
#print axioms PCSCalibrationReplay.M0.Q1.sharp_radius
#print axioms PCSCalibrationReplay.M0.Q1.conditional_physical_enclosure
#print axioms PCSCalibrationReplay.M0.Q1.Minimax.optimality_checked
#print axioms PCSCalibrationReplay.M0.Q1.Minimax.gain_checked
#print axioms PCSCalibrationReplay.M0.Q1.Minimax.real_gain
#print axioms PCSCalibrationReplay.M0.Q1.Minimax.globally_minimal_gain
#print axioms PCSCalibrationReplay.M0.Q1.Minimax.sharp_radius
#print axioms PCSCalibrationReplay.M0.Q1.Minimax.no_reproducing_estimator_has_smaller_radius
#print axioms PCSCalibrationReplay.M0.Q1.Minimax.conditional_physical_enclosure
#print axioms PCSCalibrationReplay.M0.Q1.Minimax.uniform_minimax_over_all_prediction_functions
#print axioms PCSCalibrationReplay.M0.Q2.dual_checked
#print axioms PCSCalibrationReplay.M0.Q2.gain_checked
#print axioms PCSCalibrationReplay.M0.Q2.real_gain
#print axioms PCSCalibrationReplay.M0.Q2.fitted_query
#print axioms PCSCalibrationReplay.M0.Q2.sharp_radius
#print axioms PCSCalibrationReplay.M0.Q2.conditional_physical_enclosure
#print axioms PCSCalibrationReplay.M0.Q2.Minimax.optimality_checked
#print axioms PCSCalibrationReplay.M0.Q2.Minimax.gain_checked
#print axioms PCSCalibrationReplay.M0.Q2.Minimax.real_gain
#print axioms PCSCalibrationReplay.M0.Q2.Minimax.globally_minimal_gain
#print axioms PCSCalibrationReplay.M0.Q2.Minimax.sharp_radius
#print axioms PCSCalibrationReplay.M0.Q2.Minimax.no_reproducing_estimator_has_smaller_radius
#print axioms PCSCalibrationReplay.M0.Q2.Minimax.conditional_physical_enclosure
#print axioms PCSCalibrationReplay.M0.Q2.Minimax.uniform_minimax_over_all_prediction_functions
#print axioms PCSCalibrationReplay.M0.Q3.dual_checked
#print axioms PCSCalibrationReplay.M0.Q3.gain_checked
#print axioms PCSCalibrationReplay.M0.Q3.real_gain
#print axioms PCSCalibrationReplay.M0.Q3.fitted_query
#print axioms PCSCalibrationReplay.M0.Q3.sharp_radius
#print axioms PCSCalibrationReplay.M0.Q3.conditional_physical_enclosure
#print axioms PCSCalibrationReplay.M0.Q3.Minimax.optimality_checked
#print axioms PCSCalibrationReplay.M0.Q3.Minimax.gain_checked
#print axioms PCSCalibrationReplay.M0.Q3.Minimax.real_gain
#print axioms PCSCalibrationReplay.M0.Q3.Minimax.globally_minimal_gain
#print axioms PCSCalibrationReplay.M0.Q3.Minimax.sharp_radius
#print axioms PCSCalibrationReplay.M0.Q3.Minimax.no_reproducing_estimator_has_smaller_radius
#print axioms PCSCalibrationReplay.M0.Q3.Minimax.conditional_physical_enclosure
#print axioms PCSCalibrationReplay.M0.Q3.Minimax.uniform_minimax_over_all_prediction_functions
#print axioms PCSCalibrationReplay.M0.Q4.dual_checked
#print axioms PCSCalibrationReplay.M0.Q4.gain_checked
#print axioms PCSCalibrationReplay.M0.Q4.real_gain
#print axioms PCSCalibrationReplay.M0.Q4.fitted_query
#print axioms PCSCalibrationReplay.M0.Q4.sharp_radius
#print axioms PCSCalibrationReplay.M0.Q4.conditional_physical_enclosure
#print axioms PCSCalibrationReplay.M0.Q4.Minimax.optimality_checked
#print axioms PCSCalibrationReplay.M0.Q4.Minimax.gain_checked
#print axioms PCSCalibrationReplay.M0.Q4.Minimax.real_gain
#print axioms PCSCalibrationReplay.M0.Q4.Minimax.globally_minimal_gain
#print axioms PCSCalibrationReplay.M0.Q4.Minimax.sharp_radius
#print axioms PCSCalibrationReplay.M0.Q4.Minimax.no_reproducing_estimator_has_smaller_radius
#print axioms PCSCalibrationReplay.M0.Q4.Minimax.conditional_physical_enclosure
#print axioms PCSCalibrationReplay.M0.Q4.Minimax.uniform_minimax_over_all_prediction_functions
#print axioms PCSCalibrationReplay.M0.Q5.dual_checked
#print axioms PCSCalibrationReplay.M0.Q5.gain_checked
#print axioms PCSCalibrationReplay.M0.Q5.real_gain
#print axioms PCSCalibrationReplay.M0.Q5.fitted_query
#print axioms PCSCalibrationReplay.M0.Q5.sharp_radius
#print axioms PCSCalibrationReplay.M0.Q5.conditional_physical_enclosure
#print axioms PCSCalibrationReplay.M0.Q5.Minimax.optimality_checked
#print axioms PCSCalibrationReplay.M0.Q5.Minimax.gain_checked
#print axioms PCSCalibrationReplay.M0.Q5.Minimax.real_gain
#print axioms PCSCalibrationReplay.M0.Q5.Minimax.globally_minimal_gain
#print axioms PCSCalibrationReplay.M0.Q5.Minimax.sharp_radius
#print axioms PCSCalibrationReplay.M0.Q5.Minimax.no_reproducing_estimator_has_smaller_radius
#print axioms PCSCalibrationReplay.M0.Q5.Minimax.conditional_physical_enclosure
#print axioms PCSCalibrationReplay.M0.Q5.Minimax.uniform_minimax_over_all_prediction_functions
#print axioms PCSCalibrationReplay.M0.Q6.dual_checked
#print axioms PCSCalibrationReplay.M0.Q6.gain_checked
#print axioms PCSCalibrationReplay.M0.Q6.real_gain
#print axioms PCSCalibrationReplay.M0.Q6.fitted_query
#print axioms PCSCalibrationReplay.M0.Q6.sharp_radius
#print axioms PCSCalibrationReplay.M0.Q6.conditional_physical_enclosure
#print axioms PCSCalibrationReplay.M0.Q6.Minimax.optimality_checked
#print axioms PCSCalibrationReplay.M0.Q6.Minimax.gain_checked
#print axioms PCSCalibrationReplay.M0.Q6.Minimax.real_gain
#print axioms PCSCalibrationReplay.M0.Q6.Minimax.globally_minimal_gain
#print axioms PCSCalibrationReplay.M0.Q6.Minimax.sharp_radius
#print axioms PCSCalibrationReplay.M0.Q6.Minimax.no_reproducing_estimator_has_smaller_radius
#print axioms PCSCalibrationReplay.M0.Q6.Minimax.conditional_physical_enclosure
#print axioms PCSCalibrationReplay.M0.Q6.Minimax.uniform_minimax_over_all_prediction_functions
#print axioms PCSCalibrationReplay.M0.Q7.dual_checked
#print axioms PCSCalibrationReplay.M0.Q7.gain_checked
#print axioms PCSCalibrationReplay.M0.Q7.real_gain
#print axioms PCSCalibrationReplay.M0.Q7.fitted_query
#print axioms PCSCalibrationReplay.M0.Q7.sharp_radius
#print axioms PCSCalibrationReplay.M0.Q7.conditional_physical_enclosure
#print axioms PCSCalibrationReplay.M0.Q7.Minimax.optimality_checked
#print axioms PCSCalibrationReplay.M0.Q7.Minimax.gain_checked
#print axioms PCSCalibrationReplay.M0.Q7.Minimax.real_gain
#print axioms PCSCalibrationReplay.M0.Q7.Minimax.globally_minimal_gain
#print axioms PCSCalibrationReplay.M0.Q7.Minimax.sharp_radius
#print axioms PCSCalibrationReplay.M0.Q7.Minimax.no_reproducing_estimator_has_smaller_radius
#print axioms PCSCalibrationReplay.M0.Q7.Minimax.conditional_physical_enclosure
#print axioms PCSCalibrationReplay.M0.Q7.Minimax.uniform_minimax_over_all_prediction_functions
#print axioms PCSCalibrationReplay.M1.normal_checked
#print axioms PCSCalibrationReplay.M1.residual_checked
#print axioms PCSCalibrationReplay.M1.global_optimum
#print axioms PCSCalibrationReplay.M1.excludes_every_better_model
#print axioms PCSCalibrationReplay.M1.uniform_error_exclusion
#print axioms PCSCalibrationReplay.M2.normal_checked
#print axioms PCSCalibrationReplay.M2.residual_checked
#print axioms PCSCalibrationReplay.M2.global_optimum
#print axioms PCSCalibrationReplay.M2.excludes_every_better_model
#print axioms PCSCalibrationReplay.M2.uniform_error_exclusion
#print axioms PCSCalibrationReplay.M2.Q0.dual_checked
#print axioms PCSCalibrationReplay.M2.Q0.gain_checked
#print axioms PCSCalibrationReplay.M2.Q0.real_gain
#print axioms PCSCalibrationReplay.M2.Q0.fitted_query
#print axioms PCSCalibrationReplay.M2.Q0.sharp_radius
#print axioms PCSCalibrationReplay.M2.Q0.conditional_physical_enclosure
#print axioms PCSCalibrationReplay.M2.Q0.Minimax.optimality_checked
#print axioms PCSCalibrationReplay.M2.Q0.Minimax.gain_checked
#print axioms PCSCalibrationReplay.M2.Q0.Minimax.real_gain
#print axioms PCSCalibrationReplay.M2.Q0.Minimax.globally_minimal_gain
#print axioms PCSCalibrationReplay.M2.Q0.Minimax.sharp_radius
#print axioms PCSCalibrationReplay.M2.Q0.Minimax.no_reproducing_estimator_has_smaller_radius
#print axioms PCSCalibrationReplay.M2.Q0.Minimax.conditional_physical_enclosure
#print axioms PCSCalibrationReplay.M2.Q0.Minimax.uniform_minimax_over_all_prediction_functions
#print axioms PCSCalibrationReplay.M2.Q1.dual_checked
#print axioms PCSCalibrationReplay.M2.Q1.gain_checked
#print axioms PCSCalibrationReplay.M2.Q1.real_gain
#print axioms PCSCalibrationReplay.M2.Q1.fitted_query
#print axioms PCSCalibrationReplay.M2.Q1.sharp_radius
#print axioms PCSCalibrationReplay.M2.Q1.conditional_physical_enclosure
#print axioms PCSCalibrationReplay.M2.Q1.Minimax.optimality_checked
#print axioms PCSCalibrationReplay.M2.Q1.Minimax.gain_checked
#print axioms PCSCalibrationReplay.M2.Q1.Minimax.real_gain
#print axioms PCSCalibrationReplay.M2.Q1.Minimax.globally_minimal_gain
#print axioms PCSCalibrationReplay.M2.Q1.Minimax.sharp_radius
#print axioms PCSCalibrationReplay.M2.Q1.Minimax.no_reproducing_estimator_has_smaller_radius
#print axioms PCSCalibrationReplay.M2.Q1.Minimax.conditional_physical_enclosure
#print axioms PCSCalibrationReplay.M2.Q1.Minimax.uniform_minimax_over_all_prediction_functions
#print axioms PCSCalibrationReplay.M2.Q2.dual_checked
#print axioms PCSCalibrationReplay.M2.Q2.gain_checked
#print axioms PCSCalibrationReplay.M2.Q2.real_gain
#print axioms PCSCalibrationReplay.M2.Q2.fitted_query
#print axioms PCSCalibrationReplay.M2.Q2.sharp_radius
#print axioms PCSCalibrationReplay.M2.Q2.conditional_physical_enclosure
#print axioms PCSCalibrationReplay.M2.Q2.Minimax.optimality_checked
#print axioms PCSCalibrationReplay.M2.Q2.Minimax.gain_checked
#print axioms PCSCalibrationReplay.M2.Q2.Minimax.real_gain
#print axioms PCSCalibrationReplay.M2.Q2.Minimax.globally_minimal_gain
#print axioms PCSCalibrationReplay.M2.Q2.Minimax.sharp_radius
#print axioms PCSCalibrationReplay.M2.Q2.Minimax.no_reproducing_estimator_has_smaller_radius
#print axioms PCSCalibrationReplay.M2.Q2.Minimax.conditional_physical_enclosure
#print axioms PCSCalibrationReplay.M2.Q2.Minimax.uniform_minimax_over_all_prediction_functions
#print axioms PCSCalibrationReplay.M2.Q3.dual_checked
#print axioms PCSCalibrationReplay.M2.Q3.gain_checked
#print axioms PCSCalibrationReplay.M2.Q3.real_gain
#print axioms PCSCalibrationReplay.M2.Q3.fitted_query
#print axioms PCSCalibrationReplay.M2.Q3.sharp_radius
#print axioms PCSCalibrationReplay.M2.Q3.conditional_physical_enclosure
#print axioms PCSCalibrationReplay.M2.Q3.Minimax.optimality_checked
#print axioms PCSCalibrationReplay.M2.Q3.Minimax.gain_checked
#print axioms PCSCalibrationReplay.M2.Q3.Minimax.real_gain
#print axioms PCSCalibrationReplay.M2.Q3.Minimax.globally_minimal_gain
#print axioms PCSCalibrationReplay.M2.Q3.Minimax.sharp_radius
#print axioms PCSCalibrationReplay.M2.Q3.Minimax.no_reproducing_estimator_has_smaller_radius
#print axioms PCSCalibrationReplay.M2.Q3.Minimax.conditional_physical_enclosure
#print axioms PCSCalibrationReplay.M2.Q3.Minimax.uniform_minimax_over_all_prediction_functions
#print axioms PCSCalibrationReplay.M2.Q4.dual_checked
#print axioms PCSCalibrationReplay.M2.Q4.gain_checked
#print axioms PCSCalibrationReplay.M2.Q4.real_gain
#print axioms PCSCalibrationReplay.M2.Q4.fitted_query
#print axioms PCSCalibrationReplay.M2.Q4.sharp_radius
#print axioms PCSCalibrationReplay.M2.Q4.conditional_physical_enclosure
#print axioms PCSCalibrationReplay.M2.Q4.Minimax.optimality_checked
#print axioms PCSCalibrationReplay.M2.Q4.Minimax.gain_checked
#print axioms PCSCalibrationReplay.M2.Q4.Minimax.real_gain
#print axioms PCSCalibrationReplay.M2.Q4.Minimax.globally_minimal_gain
#print axioms PCSCalibrationReplay.M2.Q4.Minimax.sharp_radius
#print axioms PCSCalibrationReplay.M2.Q4.Minimax.no_reproducing_estimator_has_smaller_radius
#print axioms PCSCalibrationReplay.M2.Q4.Minimax.conditional_physical_enclosure
#print axioms PCSCalibrationReplay.M2.Q4.Minimax.uniform_minimax_over_all_prediction_functions
#print axioms PCSCalibrationReplay.M2.Q5.dual_checked
#print axioms PCSCalibrationReplay.M2.Q5.gain_checked
#print axioms PCSCalibrationReplay.M2.Q5.real_gain
#print axioms PCSCalibrationReplay.M2.Q5.fitted_query
#print axioms PCSCalibrationReplay.M2.Q5.sharp_radius
#print axioms PCSCalibrationReplay.M2.Q5.conditional_physical_enclosure
#print axioms PCSCalibrationReplay.M2.Q5.Minimax.optimality_checked
#print axioms PCSCalibrationReplay.M2.Q5.Minimax.gain_checked
#print axioms PCSCalibrationReplay.M2.Q5.Minimax.real_gain
#print axioms PCSCalibrationReplay.M2.Q5.Minimax.globally_minimal_gain
#print axioms PCSCalibrationReplay.M2.Q5.Minimax.sharp_radius
#print axioms PCSCalibrationReplay.M2.Q5.Minimax.no_reproducing_estimator_has_smaller_radius
#print axioms PCSCalibrationReplay.M2.Q5.Minimax.conditional_physical_enclosure
#print axioms PCSCalibrationReplay.M2.Q5.Minimax.uniform_minimax_over_all_prediction_functions
#print axioms PCSCalibrationReplay.M2.Q6.dual_checked
#print axioms PCSCalibrationReplay.M2.Q6.gain_checked
#print axioms PCSCalibrationReplay.M2.Q6.real_gain
#print axioms PCSCalibrationReplay.M2.Q6.fitted_query
#print axioms PCSCalibrationReplay.M2.Q6.sharp_radius
#print axioms PCSCalibrationReplay.M2.Q6.conditional_physical_enclosure
#print axioms PCSCalibrationReplay.M2.Q6.Minimax.optimality_checked
#print axioms PCSCalibrationReplay.M2.Q6.Minimax.gain_checked
#print axioms PCSCalibrationReplay.M2.Q6.Minimax.real_gain
#print axioms PCSCalibrationReplay.M2.Q6.Minimax.globally_minimal_gain
#print axioms PCSCalibrationReplay.M2.Q6.Minimax.sharp_radius
#print axioms PCSCalibrationReplay.M2.Q6.Minimax.no_reproducing_estimator_has_smaller_radius
#print axioms PCSCalibrationReplay.M2.Q6.Minimax.conditional_physical_enclosure
#print axioms PCSCalibrationReplay.M2.Q6.Minimax.uniform_minimax_over_all_prediction_functions
#print axioms PCSCalibrationReplay.M2.Q7.dual_checked
#print axioms PCSCalibrationReplay.M2.Q7.gain_checked
#print axioms PCSCalibrationReplay.M2.Q7.real_gain
#print axioms PCSCalibrationReplay.M2.Q7.fitted_query
#print axioms PCSCalibrationReplay.M2.Q7.sharp_radius
#print axioms PCSCalibrationReplay.M2.Q7.conditional_physical_enclosure
#print axioms PCSCalibrationReplay.M2.Q7.Minimax.optimality_checked
#print axioms PCSCalibrationReplay.M2.Q7.Minimax.gain_checked
#print axioms PCSCalibrationReplay.M2.Q7.Minimax.real_gain
#print axioms PCSCalibrationReplay.M2.Q7.Minimax.globally_minimal_gain
#print axioms PCSCalibrationReplay.M2.Q7.Minimax.sharp_radius
#print axioms PCSCalibrationReplay.M2.Q7.Minimax.no_reproducing_estimator_has_smaller_radius
#print axioms PCSCalibrationReplay.M2.Q7.Minimax.conditional_physical_enclosure
#print axioms PCSCalibrationReplay.M2.Q7.Minimax.uniform_minimax_over_all_prediction_functions
#print axioms PCSCalibrationReplay.M3.normal_checked
#print axioms PCSCalibrationReplay.M3.residual_checked
#print axioms PCSCalibrationReplay.M3.global_optimum
#print axioms PCSCalibrationReplay.M3.excludes_every_better_model
#print axioms PCSCalibrationReplay.M3.uniform_error_exclusion
#print axioms PCSCalibrationReplay.M4.normal_checked
#print axioms PCSCalibrationReplay.M4.residual_checked
#print axioms PCSCalibrationReplay.M4.global_optimum
#print axioms PCSCalibrationReplay.M4.excludes_every_better_model
#print axioms PCSCalibrationReplay.M4.uniform_error_exclusion
#print axioms PCSCalibrationReplay.M4.Q0.dual_checked
#print axioms PCSCalibrationReplay.M4.Q0.gain_checked
#print axioms PCSCalibrationReplay.M4.Q0.real_gain
#print axioms PCSCalibrationReplay.M4.Q0.fitted_query
#print axioms PCSCalibrationReplay.M4.Q0.sharp_radius
#print axioms PCSCalibrationReplay.M4.Q0.conditional_physical_enclosure
#print axioms PCSCalibrationReplay.M4.Q0.Minimax.optimality_checked
#print axioms PCSCalibrationReplay.M4.Q0.Minimax.gain_checked
#print axioms PCSCalibrationReplay.M4.Q0.Minimax.real_gain
#print axioms PCSCalibrationReplay.M4.Q0.Minimax.globally_minimal_gain
#print axioms PCSCalibrationReplay.M4.Q0.Minimax.sharp_radius
#print axioms PCSCalibrationReplay.M4.Q0.Minimax.no_reproducing_estimator_has_smaller_radius
#print axioms PCSCalibrationReplay.M4.Q0.Minimax.conditional_physical_enclosure
#print axioms PCSCalibrationReplay.M4.Q0.Minimax.uniform_minimax_over_all_prediction_functions
#print axioms PCSCalibrationReplay.M4.Q1.dual_checked
#print axioms PCSCalibrationReplay.M4.Q1.gain_checked
#print axioms PCSCalibrationReplay.M4.Q1.real_gain
#print axioms PCSCalibrationReplay.M4.Q1.fitted_query
#print axioms PCSCalibrationReplay.M4.Q1.sharp_radius
#print axioms PCSCalibrationReplay.M4.Q1.conditional_physical_enclosure
#print axioms PCSCalibrationReplay.M4.Q1.Minimax.optimality_checked
#print axioms PCSCalibrationReplay.M4.Q1.Minimax.gain_checked
#print axioms PCSCalibrationReplay.M4.Q1.Minimax.real_gain
#print axioms PCSCalibrationReplay.M4.Q1.Minimax.globally_minimal_gain
#print axioms PCSCalibrationReplay.M4.Q1.Minimax.sharp_radius
#print axioms PCSCalibrationReplay.M4.Q1.Minimax.no_reproducing_estimator_has_smaller_radius
#print axioms PCSCalibrationReplay.M4.Q1.Minimax.conditional_physical_enclosure
#print axioms PCSCalibrationReplay.M4.Q1.Minimax.uniform_minimax_over_all_prediction_functions
#print axioms PCSCalibrationReplay.M4.Q2.dual_checked
#print axioms PCSCalibrationReplay.M4.Q2.gain_checked
#print axioms PCSCalibrationReplay.M4.Q2.real_gain
#print axioms PCSCalibrationReplay.M4.Q2.fitted_query
#print axioms PCSCalibrationReplay.M4.Q2.sharp_radius
#print axioms PCSCalibrationReplay.M4.Q2.conditional_physical_enclosure
#print axioms PCSCalibrationReplay.M4.Q2.Minimax.optimality_checked
#print axioms PCSCalibrationReplay.M4.Q2.Minimax.gain_checked
#print axioms PCSCalibrationReplay.M4.Q2.Minimax.real_gain
#print axioms PCSCalibrationReplay.M4.Q2.Minimax.globally_minimal_gain
#print axioms PCSCalibrationReplay.M4.Q2.Minimax.sharp_radius
#print axioms PCSCalibrationReplay.M4.Q2.Minimax.no_reproducing_estimator_has_smaller_radius
#print axioms PCSCalibrationReplay.M4.Q2.Minimax.conditional_physical_enclosure
#print axioms PCSCalibrationReplay.M4.Q2.Minimax.uniform_minimax_over_all_prediction_functions
#print axioms PCSCalibrationReplay.M4.Q3.dual_checked
#print axioms PCSCalibrationReplay.M4.Q3.gain_checked
#print axioms PCSCalibrationReplay.M4.Q3.real_gain
#print axioms PCSCalibrationReplay.M4.Q3.fitted_query
#print axioms PCSCalibrationReplay.M4.Q3.sharp_radius
#print axioms PCSCalibrationReplay.M4.Q3.conditional_physical_enclosure
#print axioms PCSCalibrationReplay.M4.Q3.Minimax.optimality_checked
#print axioms PCSCalibrationReplay.M4.Q3.Minimax.gain_checked
#print axioms PCSCalibrationReplay.M4.Q3.Minimax.real_gain
#print axioms PCSCalibrationReplay.M4.Q3.Minimax.globally_minimal_gain
#print axioms PCSCalibrationReplay.M4.Q3.Minimax.sharp_radius
#print axioms PCSCalibrationReplay.M4.Q3.Minimax.no_reproducing_estimator_has_smaller_radius
#print axioms PCSCalibrationReplay.M4.Q3.Minimax.conditional_physical_enclosure
#print axioms PCSCalibrationReplay.M4.Q3.Minimax.uniform_minimax_over_all_prediction_functions
#print axioms PCSCalibrationReplay.M4.Q4.dual_checked
#print axioms PCSCalibrationReplay.M4.Q4.gain_checked
#print axioms PCSCalibrationReplay.M4.Q4.real_gain
#print axioms PCSCalibrationReplay.M4.Q4.fitted_query
#print axioms PCSCalibrationReplay.M4.Q4.sharp_radius
#print axioms PCSCalibrationReplay.M4.Q4.conditional_physical_enclosure
#print axioms PCSCalibrationReplay.M4.Q4.Minimax.optimality_checked
#print axioms PCSCalibrationReplay.M4.Q4.Minimax.gain_checked
#print axioms PCSCalibrationReplay.M4.Q4.Minimax.real_gain
#print axioms PCSCalibrationReplay.M4.Q4.Minimax.globally_minimal_gain
#print axioms PCSCalibrationReplay.M4.Q4.Minimax.sharp_radius
#print axioms PCSCalibrationReplay.M4.Q4.Minimax.no_reproducing_estimator_has_smaller_radius
#print axioms PCSCalibrationReplay.M4.Q4.Minimax.conditional_physical_enclosure
#print axioms PCSCalibrationReplay.M4.Q4.Minimax.uniform_minimax_over_all_prediction_functions
#print axioms PCSCalibrationReplay.M4.Q5.dual_checked
#print axioms PCSCalibrationReplay.M4.Q5.gain_checked
#print axioms PCSCalibrationReplay.M4.Q5.real_gain
#print axioms PCSCalibrationReplay.M4.Q5.fitted_query
#print axioms PCSCalibrationReplay.M4.Q5.sharp_radius
#print axioms PCSCalibrationReplay.M4.Q5.conditional_physical_enclosure
#print axioms PCSCalibrationReplay.M4.Q5.Minimax.optimality_checked
#print axioms PCSCalibrationReplay.M4.Q5.Minimax.gain_checked
#print axioms PCSCalibrationReplay.M4.Q5.Minimax.real_gain
#print axioms PCSCalibrationReplay.M4.Q5.Minimax.globally_minimal_gain
#print axioms PCSCalibrationReplay.M4.Q5.Minimax.sharp_radius
#print axioms PCSCalibrationReplay.M4.Q5.Minimax.no_reproducing_estimator_has_smaller_radius
#print axioms PCSCalibrationReplay.M4.Q5.Minimax.conditional_physical_enclosure
#print axioms PCSCalibrationReplay.M4.Q5.Minimax.uniform_minimax_over_all_prediction_functions
#print axioms PCSCalibrationReplay.M4.Q6.dual_checked
#print axioms PCSCalibrationReplay.M4.Q6.gain_checked
#print axioms PCSCalibrationReplay.M4.Q6.real_gain
#print axioms PCSCalibrationReplay.M4.Q6.fitted_query
#print axioms PCSCalibrationReplay.M4.Q6.sharp_radius
#print axioms PCSCalibrationReplay.M4.Q6.conditional_physical_enclosure
#print axioms PCSCalibrationReplay.M4.Q6.Minimax.optimality_checked
#print axioms PCSCalibrationReplay.M4.Q6.Minimax.gain_checked
#print axioms PCSCalibrationReplay.M4.Q6.Minimax.real_gain
#print axioms PCSCalibrationReplay.M4.Q6.Minimax.globally_minimal_gain
#print axioms PCSCalibrationReplay.M4.Q6.Minimax.sharp_radius
#print axioms PCSCalibrationReplay.M4.Q6.Minimax.no_reproducing_estimator_has_smaller_radius
#print axioms PCSCalibrationReplay.M4.Q6.Minimax.conditional_physical_enclosure
#print axioms PCSCalibrationReplay.M4.Q6.Minimax.uniform_minimax_over_all_prediction_functions
#print axioms PCSCalibrationReplay.M4.Q7.dual_checked
#print axioms PCSCalibrationReplay.M4.Q7.gain_checked
#print axioms PCSCalibrationReplay.M4.Q7.real_gain
#print axioms PCSCalibrationReplay.M4.Q7.fitted_query
#print axioms PCSCalibrationReplay.M4.Q7.sharp_radius
#print axioms PCSCalibrationReplay.M4.Q7.conditional_physical_enclosure
#print axioms PCSCalibrationReplay.M4.Q7.Minimax.optimality_checked
#print axioms PCSCalibrationReplay.M4.Q7.Minimax.gain_checked
#print axioms PCSCalibrationReplay.M4.Q7.Minimax.real_gain
#print axioms PCSCalibrationReplay.M4.Q7.Minimax.globally_minimal_gain
#print axioms PCSCalibrationReplay.M4.Q7.Minimax.sharp_radius
#print axioms PCSCalibrationReplay.M4.Q7.Minimax.no_reproducing_estimator_has_smaller_radius
#print axioms PCSCalibrationReplay.M4.Q7.Minimax.conditional_physical_enclosure
#print axioms PCSCalibrationReplay.M4.Q7.Minimax.uniform_minimax_over_all_prediction_functions
#print axioms PCSCalibrationReplay.M5.normal_checked
#print axioms PCSCalibrationReplay.M5.residual_checked
#print axioms PCSCalibrationReplay.M5.global_optimum
#print axioms PCSCalibrationReplay.M5.excludes_every_better_model
#print axioms PCSCalibrationReplay.M5.uniform_error_exclusion
