import PCSReal.Calibration
set_option autoImplicit false
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
    dsimp only [xr, yr, br]
    rw [← cast_loss x y b, residual_checked]
    norm_num
  simpa only [hs] using global_minimum xr yr br (fit_check_sound normal_checked)
theorem excludes_every_better_model (threshold : ℝ)
    (h : threshold < (((77313911 : ℚ) / (280000 : ℚ)) : ℝ)) :
    ∀ c : Fin 2 → ℝ, threshold < loss xr yr c := by
  intro c
  exact h.trans_le (global_optimum c)
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
end PCSCalibrationReplay.M0

namespace PCSCalibrationReplay.M1
def abscissa (i : Fin 14) : ℚ := ([((5 : ℚ) / (1 : ℚ)), ((6 : ℚ) / (1 : ℚ)), ((7 : ℚ) / (1 : ℚ)), ((8 : ℚ) / (1 : ℚ)), ((9 : ℚ) / (1 : ℚ)), ((10 : ℚ) / (1 : ℚ)), ((11 : ℚ) / (1 : ℚ)), ((12 : ℚ) / (1 : ℚ)), ((13 : ℚ) / (1 : ℚ)), ((14 : ℚ) / (1 : ℚ)), ((15 : ℚ) / (1 : ℚ)), ((16 : ℚ) / (1 : ℚ)), ((17 : ℚ) / (1 : ℚ)), ((18 : ℚ) / (1 : ℚ))] : List ℚ).getD i.val 0
def x (i : Fin 14) (j : Fin 2) : ℚ := abscissa i ^ j.val
def y (i : Fin 14) : ℚ := ([((11 : ℚ) / (100 : ℚ)), ((27 : ℚ) / (100 : ℚ)), ((47 : ℚ) / (100 : ℚ)), ((39 : ℚ) / (50 : ℚ)), ((59 : ℚ) / (50 : ℚ)), ((91 : ℚ) / (50 : ℚ)), ((261 : ℚ) / (100 : ℚ)), ((94 : ℚ) / (25 : ℚ)), ((499 : ℚ) / (100 : ℚ)), ((179 : ℚ) / (25 : ℚ)), ((1193 : ℚ) / (100 : ℚ)), ((2011 : ℚ) / (100 : ℚ)), ((131 : ℚ) / (4 : ℚ)), ((4949 : ℚ) / (100 : ℚ))] : List ℚ).getD i.val 0
def b (j : Fin 2) : ℚ := ([((-1042131 : ℚ) / (45500 : ℚ)), ((129459 : ℚ) / (45500 : ℚ))] : List ℚ).getD j.val 0
def xr (i : Fin 14) (j : Fin 2) : ℝ := (x i j : ℝ)
def yr (i : Fin 14) : ℝ := (y i : ℝ)
def br (j : Fin 2) : ℝ := (b j : ℝ)
theorem normal_checked : fitCheck x y b = true := by decide +kernel
theorem residual_checked : loss x y b = ((2230647611 : ℚ) / (2275000 : ℚ)) := by decide +kernel
theorem global_optimum : ∀ c : Fin 2 → ℝ,
    (((2230647611 : ℚ) / (2275000 : ℚ)) : ℝ) ≤ loss xr yr c := by
  have hs : loss xr yr br = (((2230647611 : ℚ) / (2275000 : ℚ)) : ℝ) := by
    dsimp only [xr, yr, br]
    rw [← cast_loss x y b, residual_checked]
    norm_num
  simpa only [hs] using global_minimum xr yr br (fit_check_sound normal_checked)
theorem excludes_every_better_model (threshold : ℝ)
    (h : threshold < (((2230647611 : ℚ) / (2275000 : ℚ)) : ℝ)) :
    ∀ c : Fin 2 → ℝ, threshold < loss xr yr c := by
  intro c
  exact h.trans_le (global_optimum c)
end PCSCalibrationReplay.M1

namespace PCSCalibrationReplay.M2
def abscissa (i : Fin 7) : ℚ := ([((5 : ℚ) / (1 : ℚ)), ((7 : ℚ) / (1 : ℚ)), ((9 : ℚ) / (1 : ℚ)), ((11 : ℚ) / (1 : ℚ)), ((13 : ℚ) / (1 : ℚ)), ((15 : ℚ) / (1 : ℚ)), ((17 : ℚ) / (1 : ℚ))] : List ℚ).getD i.val 0
def x (i : Fin 7) (j : Fin 3) : ℚ := abscissa i ^ j.val
def y (i : Fin 7) : ℚ := ([((11 : ℚ) / (100 : ℚ)), ((47 : ℚ) / (100 : ℚ)), ((59 : ℚ) / (50 : ℚ)), ((261 : ℚ) / (100 : ℚ)), ((499 : ℚ) / (100 : ℚ)), ((1193 : ℚ) / (100 : ℚ)), ((131 : ℚ) / (4 : ℚ))] : List ℚ).getD i.val 0
def b (j : Fin 3) : ℚ := ([((285959 : ℚ) / (11200 : ℚ)), ((-11149 : ℚ) / (1680 : ℚ)), ((2707 : ℚ) / (6720 : ℚ))] : List ℚ).getD j.val 0
def xr (i : Fin 7) (j : Fin 3) : ℝ := (x i j : ℝ)
def yr (i : Fin 7) : ℝ := (y i : ℝ)
def br (j : Fin 3) : ℝ := (b j : ℝ)
theorem normal_checked : fitCheck x y b = true := by decide +kernel
theorem residual_checked : loss x y b = ((1740911 : ℚ) / (30000 : ℚ)) := by decide +kernel
theorem global_optimum : ∀ c : Fin 3 → ℝ,
    (((1740911 : ℚ) / (30000 : ℚ)) : ℝ) ≤ loss xr yr c := by
  have hs : loss xr yr br = (((1740911 : ℚ) / (30000 : ℚ)) : ℝ) := by
    dsimp only [xr, yr, br]
    rw [← cast_loss x y b, residual_checked]
    norm_num
  simpa only [hs] using global_minimum xr yr br (fit_check_sound normal_checked)
theorem excludes_every_better_model (threshold : ℝ)
    (h : threshold < (((1740911 : ℚ) / (30000 : ℚ)) : ℝ)) :
    ∀ c : Fin 3 → ℝ, threshold < loss xr yr c := by
  intro c
  exact h.trans_le (global_optimum c)
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
end PCSCalibrationReplay.M2

namespace PCSCalibrationReplay.M3
def abscissa (i : Fin 14) : ℚ := ([((5 : ℚ) / (1 : ℚ)), ((6 : ℚ) / (1 : ℚ)), ((7 : ℚ) / (1 : ℚ)), ((8 : ℚ) / (1 : ℚ)), ((9 : ℚ) / (1 : ℚ)), ((10 : ℚ) / (1 : ℚ)), ((11 : ℚ) / (1 : ℚ)), ((12 : ℚ) / (1 : ℚ)), ((13 : ℚ) / (1 : ℚ)), ((14 : ℚ) / (1 : ℚ)), ((15 : ℚ) / (1 : ℚ)), ((16 : ℚ) / (1 : ℚ)), ((17 : ℚ) / (1 : ℚ)), ((18 : ℚ) / (1 : ℚ))] : List ℚ).getD i.val 0
def x (i : Fin 14) (j : Fin 3) : ℚ := abscissa i ^ j.val
def y (i : Fin 14) : ℚ := ([((11 : ℚ) / (100 : ℚ)), ((27 : ℚ) / (100 : ℚ)), ((47 : ℚ) / (100 : ℚ)), ((39 : ℚ) / (50 : ℚ)), ((59 : ℚ) / (50 : ℚ)), ((91 : ℚ) / (50 : ℚ)), ((261 : ℚ) / (100 : ℚ)), ((94 : ℚ) / (25 : ℚ)), ((499 : ℚ) / (100 : ℚ)), ((179 : ℚ) / (25 : ℚ)), ((1193 : ℚ) / (100 : ℚ)), ((2011 : ℚ) / (100 : ℚ)), ((131 : ℚ) / (4 : ℚ)), ((4949 : ℚ) / (100 : ℚ))] : List ℚ).getD i.val 0
def b (j : Fin 3) : ℚ := ([((6726051 : ℚ) / (182000 : ℚ)), ((-6569181 : ℚ) / (728000 : ℚ)), ((15027 : ℚ) / (29120 : ℚ))] : List ℚ).getD j.val 0
def xr (i : Fin 14) (j : Fin 3) : ℝ := (x i j : ℝ)
def yr (i : Fin 14) : ℝ := (y i : ℝ)
def br (j : Fin 3) : ℝ := (b j : ℝ)
theorem normal_checked : fitCheck x y b = true := by decide +kernel
theorem residual_checked : loss x y b = ((7464020651 : ℚ) / (36400000 : ℚ)) := by decide +kernel
theorem global_optimum : ∀ c : Fin 3 → ℝ,
    (((7464020651 : ℚ) / (36400000 : ℚ)) : ℝ) ≤ loss xr yr c := by
  have hs : loss xr yr br = (((7464020651 : ℚ) / (36400000 : ℚ)) : ℝ) := by
    dsimp only [xr, yr, br]
    rw [← cast_loss x y b, residual_checked]
    norm_num
  simpa only [hs] using global_minimum xr yr br (fit_check_sound normal_checked)
theorem excludes_every_better_model (threshold : ℝ)
    (h : threshold < (((7464020651 : ℚ) / (36400000 : ℚ)) : ℝ)) :
    ∀ c : Fin 3 → ℝ, threshold < loss xr yr c := by
  intro c
  exact h.trans_le (global_optimum c)
end PCSCalibrationReplay.M3

namespace PCSCalibrationReplay.M4
def abscissa (i : Fin 7) : ℚ := ([((5 : ℚ) / (1 : ℚ)), ((7 : ℚ) / (1 : ℚ)), ((9 : ℚ) / (1 : ℚ)), ((11 : ℚ) / (1 : ℚ)), ((13 : ℚ) / (1 : ℚ)), ((15 : ℚ) / (1 : ℚ)), ((17 : ℚ) / (1 : ℚ))] : List ℚ).getD i.val 0
def x (i : Fin 7) (j : Fin 4) : ℚ := abscissa i ^ j.val
def y (i : Fin 7) : ℚ := ([((11 : ℚ) / (100 : ℚ)), ((47 : ℚ) / (100 : ℚ)), ((59 : ℚ) / (50 : ℚ)), ((261 : ℚ) / (100 : ℚ)), ((499 : ℚ) / (100 : ℚ)), ((1193 : ℚ) / (100 : ℚ)), ((131 : ℚ) / (4 : ℚ))] : List ℚ).getD i.val 0
def b (j : Fin 4) : ℚ := ([((-162031 : ℚ) / (4480 : ℚ)), ((182359 : ℚ) / (13440 : ℚ)), ((-106679 : ℚ) / (67200 : ℚ)), ((193 : ℚ) / (3200 : ℚ))] : List ℚ).getD j.val 0
def xr (i : Fin 7) (j : Fin 4) : ℝ := (x i j : ℝ)
def yr (i : Fin 7) : ℝ := (y i : ℝ)
def br (j : Fin 4) : ℝ := (b j : ℝ)
theorem normal_checked : fitCheck x y b = true := by decide +kernel
theorem residual_checked : loss x y b = ((464653 : ℚ) / (60000 : ℚ)) := by decide +kernel
theorem global_optimum : ∀ c : Fin 4 → ℝ,
    (((464653 : ℚ) / (60000 : ℚ)) : ℝ) ≤ loss xr yr c := by
  have hs : loss xr yr br = (((464653 : ℚ) / (60000 : ℚ)) : ℝ) := by
    dsimp only [xr, yr, br]
    rw [← cast_loss x y b, residual_checked]
    norm_num
  simpa only [hs] using global_minimum xr yr br (fit_check_sound normal_checked)
theorem excludes_every_better_model (threshold : ℝ)
    (h : threshold < (((464653 : ℚ) / (60000 : ℚ)) : ℝ)) :
    ∀ c : Fin 4 → ℝ, threshold < loss xr yr c := by
  intro c
  exact h.trans_le (global_optimum c)
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
end PCSCalibrationReplay.M4

namespace PCSCalibrationReplay.M5
def abscissa (i : Fin 14) : ℚ := ([((5 : ℚ) / (1 : ℚ)), ((6 : ℚ) / (1 : ℚ)), ((7 : ℚ) / (1 : ℚ)), ((8 : ℚ) / (1 : ℚ)), ((9 : ℚ) / (1 : ℚ)), ((10 : ℚ) / (1 : ℚ)), ((11 : ℚ) / (1 : ℚ)), ((12 : ℚ) / (1 : ℚ)), ((13 : ℚ) / (1 : ℚ)), ((14 : ℚ) / (1 : ℚ)), ((15 : ℚ) / (1 : ℚ)), ((16 : ℚ) / (1 : ℚ)), ((17 : ℚ) / (1 : ℚ)), ((18 : ℚ) / (1 : ℚ))] : List ℚ).getD i.val 0
def x (i : Fin 14) (j : Fin 4) : ℚ := abscissa i ^ j.val
def y (i : Fin 14) : ℚ := ([((11 : ℚ) / (100 : ℚ)), ((27 : ℚ) / (100 : ℚ)), ((47 : ℚ) / (100 : ℚ)), ((39 : ℚ) / (50 : ℚ)), ((59 : ℚ) / (50 : ℚ)), ((91 : ℚ) / (50 : ℚ)), ((261 : ℚ) / (100 : ℚ)), ((94 : ℚ) / (25 : ℚ)), ((499 : ℚ) / (100 : ℚ)), ((179 : ℚ) / (25 : ℚ)), ((1193 : ℚ) / (100 : ℚ)), ((2011 : ℚ) / (100 : ℚ)), ((131 : ℚ) / (4 : ℚ)), ((4949 : ℚ) / (100 : ℚ))] : List ℚ).getD i.val 0
def b (j : Fin 4) : ℚ := ([((-83241761 : ℚ) / (1701700 : ℚ)), ((13808923 : ℚ) / (785400 : ℚ)), ((-26958677 : ℚ) / (13613600 : ℚ)), ((422159 : ℚ) / (5834400 : ℚ))] : List ℚ).getD j.val 0
def xr (i : Fin 14) (j : Fin 4) : ℝ := (x i j : ℝ)
def yr (i : Fin 14) : ℝ := (y i : ℝ)
def br (j : Fin 4) : ℝ := (b j : ℝ)
theorem normal_checked : fitCheck x y b = true := by decide +kernel
theorem residual_checked : loss x y b = ((14824431277 : ℚ) / (680680000 : ℚ)) := by decide +kernel
theorem global_optimum : ∀ c : Fin 4 → ℝ,
    (((14824431277 : ℚ) / (680680000 : ℚ)) : ℝ) ≤ loss xr yr c := by
  have hs : loss xr yr br = (((14824431277 : ℚ) / (680680000 : ℚ)) : ℝ) := by
    dsimp only [xr, yr, br]
    rw [← cast_loss x y b, residual_checked]
    norm_num
  simpa only [hs] using global_minimum xr yr br (fit_check_sound normal_checked)
theorem excludes_every_better_model (threshold : ℝ)
    (h : threshold < (((14824431277 : ℚ) / (680680000 : ℚ)) : ℝ)) :
    ∀ c : Fin 4 → ℝ, threshold < loss xr yr c := by
  intro c
  exact h.trans_le (global_optimum c)
end PCSCalibrationReplay.M5

#print axioms PCSCalibrationReplay.M0.normal_checked
#print axioms PCSCalibrationReplay.M0.residual_checked
#print axioms PCSCalibrationReplay.M0.global_optimum
#print axioms PCSCalibrationReplay.M0.excludes_every_better_model
#print axioms PCSCalibrationReplay.M0.Q0.dual_checked
#print axioms PCSCalibrationReplay.M0.Q0.gain_checked
#print axioms PCSCalibrationReplay.M0.Q0.real_gain
#print axioms PCSCalibrationReplay.M0.Q0.fitted_query
#print axioms PCSCalibrationReplay.M0.Q0.sharp_radius
#print axioms PCSCalibrationReplay.M0.Q0.conditional_physical_enclosure
#print axioms PCSCalibrationReplay.M0.Q1.dual_checked
#print axioms PCSCalibrationReplay.M0.Q1.gain_checked
#print axioms PCSCalibrationReplay.M0.Q1.real_gain
#print axioms PCSCalibrationReplay.M0.Q1.fitted_query
#print axioms PCSCalibrationReplay.M0.Q1.sharp_radius
#print axioms PCSCalibrationReplay.M0.Q1.conditional_physical_enclosure
#print axioms PCSCalibrationReplay.M0.Q2.dual_checked
#print axioms PCSCalibrationReplay.M0.Q2.gain_checked
#print axioms PCSCalibrationReplay.M0.Q2.real_gain
#print axioms PCSCalibrationReplay.M0.Q2.fitted_query
#print axioms PCSCalibrationReplay.M0.Q2.sharp_radius
#print axioms PCSCalibrationReplay.M0.Q2.conditional_physical_enclosure
#print axioms PCSCalibrationReplay.M0.Q3.dual_checked
#print axioms PCSCalibrationReplay.M0.Q3.gain_checked
#print axioms PCSCalibrationReplay.M0.Q3.real_gain
#print axioms PCSCalibrationReplay.M0.Q3.fitted_query
#print axioms PCSCalibrationReplay.M0.Q3.sharp_radius
#print axioms PCSCalibrationReplay.M0.Q3.conditional_physical_enclosure
#print axioms PCSCalibrationReplay.M0.Q4.dual_checked
#print axioms PCSCalibrationReplay.M0.Q4.gain_checked
#print axioms PCSCalibrationReplay.M0.Q4.real_gain
#print axioms PCSCalibrationReplay.M0.Q4.fitted_query
#print axioms PCSCalibrationReplay.M0.Q4.sharp_radius
#print axioms PCSCalibrationReplay.M0.Q4.conditional_physical_enclosure
#print axioms PCSCalibrationReplay.M0.Q5.dual_checked
#print axioms PCSCalibrationReplay.M0.Q5.gain_checked
#print axioms PCSCalibrationReplay.M0.Q5.real_gain
#print axioms PCSCalibrationReplay.M0.Q5.fitted_query
#print axioms PCSCalibrationReplay.M0.Q5.sharp_radius
#print axioms PCSCalibrationReplay.M0.Q5.conditional_physical_enclosure
#print axioms PCSCalibrationReplay.M0.Q6.dual_checked
#print axioms PCSCalibrationReplay.M0.Q6.gain_checked
#print axioms PCSCalibrationReplay.M0.Q6.real_gain
#print axioms PCSCalibrationReplay.M0.Q6.fitted_query
#print axioms PCSCalibrationReplay.M0.Q6.sharp_radius
#print axioms PCSCalibrationReplay.M0.Q6.conditional_physical_enclosure
#print axioms PCSCalibrationReplay.M0.Q7.dual_checked
#print axioms PCSCalibrationReplay.M0.Q7.gain_checked
#print axioms PCSCalibrationReplay.M0.Q7.real_gain
#print axioms PCSCalibrationReplay.M0.Q7.fitted_query
#print axioms PCSCalibrationReplay.M0.Q7.sharp_radius
#print axioms PCSCalibrationReplay.M0.Q7.conditional_physical_enclosure
#print axioms PCSCalibrationReplay.M1.normal_checked
#print axioms PCSCalibrationReplay.M1.residual_checked
#print axioms PCSCalibrationReplay.M1.global_optimum
#print axioms PCSCalibrationReplay.M1.excludes_every_better_model
#print axioms PCSCalibrationReplay.M2.normal_checked
#print axioms PCSCalibrationReplay.M2.residual_checked
#print axioms PCSCalibrationReplay.M2.global_optimum
#print axioms PCSCalibrationReplay.M2.excludes_every_better_model
#print axioms PCSCalibrationReplay.M2.Q0.dual_checked
#print axioms PCSCalibrationReplay.M2.Q0.gain_checked
#print axioms PCSCalibrationReplay.M2.Q0.real_gain
#print axioms PCSCalibrationReplay.M2.Q0.fitted_query
#print axioms PCSCalibrationReplay.M2.Q0.sharp_radius
#print axioms PCSCalibrationReplay.M2.Q0.conditional_physical_enclosure
#print axioms PCSCalibrationReplay.M2.Q1.dual_checked
#print axioms PCSCalibrationReplay.M2.Q1.gain_checked
#print axioms PCSCalibrationReplay.M2.Q1.real_gain
#print axioms PCSCalibrationReplay.M2.Q1.fitted_query
#print axioms PCSCalibrationReplay.M2.Q1.sharp_radius
#print axioms PCSCalibrationReplay.M2.Q1.conditional_physical_enclosure
#print axioms PCSCalibrationReplay.M2.Q2.dual_checked
#print axioms PCSCalibrationReplay.M2.Q2.gain_checked
#print axioms PCSCalibrationReplay.M2.Q2.real_gain
#print axioms PCSCalibrationReplay.M2.Q2.fitted_query
#print axioms PCSCalibrationReplay.M2.Q2.sharp_radius
#print axioms PCSCalibrationReplay.M2.Q2.conditional_physical_enclosure
#print axioms PCSCalibrationReplay.M2.Q3.dual_checked
#print axioms PCSCalibrationReplay.M2.Q3.gain_checked
#print axioms PCSCalibrationReplay.M2.Q3.real_gain
#print axioms PCSCalibrationReplay.M2.Q3.fitted_query
#print axioms PCSCalibrationReplay.M2.Q3.sharp_radius
#print axioms PCSCalibrationReplay.M2.Q3.conditional_physical_enclosure
#print axioms PCSCalibrationReplay.M2.Q4.dual_checked
#print axioms PCSCalibrationReplay.M2.Q4.gain_checked
#print axioms PCSCalibrationReplay.M2.Q4.real_gain
#print axioms PCSCalibrationReplay.M2.Q4.fitted_query
#print axioms PCSCalibrationReplay.M2.Q4.sharp_radius
#print axioms PCSCalibrationReplay.M2.Q4.conditional_physical_enclosure
#print axioms PCSCalibrationReplay.M2.Q5.dual_checked
#print axioms PCSCalibrationReplay.M2.Q5.gain_checked
#print axioms PCSCalibrationReplay.M2.Q5.real_gain
#print axioms PCSCalibrationReplay.M2.Q5.fitted_query
#print axioms PCSCalibrationReplay.M2.Q5.sharp_radius
#print axioms PCSCalibrationReplay.M2.Q5.conditional_physical_enclosure
#print axioms PCSCalibrationReplay.M2.Q6.dual_checked
#print axioms PCSCalibrationReplay.M2.Q6.gain_checked
#print axioms PCSCalibrationReplay.M2.Q6.real_gain
#print axioms PCSCalibrationReplay.M2.Q6.fitted_query
#print axioms PCSCalibrationReplay.M2.Q6.sharp_radius
#print axioms PCSCalibrationReplay.M2.Q6.conditional_physical_enclosure
#print axioms PCSCalibrationReplay.M2.Q7.dual_checked
#print axioms PCSCalibrationReplay.M2.Q7.gain_checked
#print axioms PCSCalibrationReplay.M2.Q7.real_gain
#print axioms PCSCalibrationReplay.M2.Q7.fitted_query
#print axioms PCSCalibrationReplay.M2.Q7.sharp_radius
#print axioms PCSCalibrationReplay.M2.Q7.conditional_physical_enclosure
#print axioms PCSCalibrationReplay.M3.normal_checked
#print axioms PCSCalibrationReplay.M3.residual_checked
#print axioms PCSCalibrationReplay.M3.global_optimum
#print axioms PCSCalibrationReplay.M3.excludes_every_better_model
#print axioms PCSCalibrationReplay.M4.normal_checked
#print axioms PCSCalibrationReplay.M4.residual_checked
#print axioms PCSCalibrationReplay.M4.global_optimum
#print axioms PCSCalibrationReplay.M4.excludes_every_better_model
#print axioms PCSCalibrationReplay.M4.Q0.dual_checked
#print axioms PCSCalibrationReplay.M4.Q0.gain_checked
#print axioms PCSCalibrationReplay.M4.Q0.real_gain
#print axioms PCSCalibrationReplay.M4.Q0.fitted_query
#print axioms PCSCalibrationReplay.M4.Q0.sharp_radius
#print axioms PCSCalibrationReplay.M4.Q0.conditional_physical_enclosure
#print axioms PCSCalibrationReplay.M4.Q1.dual_checked
#print axioms PCSCalibrationReplay.M4.Q1.gain_checked
#print axioms PCSCalibrationReplay.M4.Q1.real_gain
#print axioms PCSCalibrationReplay.M4.Q1.fitted_query
#print axioms PCSCalibrationReplay.M4.Q1.sharp_radius
#print axioms PCSCalibrationReplay.M4.Q1.conditional_physical_enclosure
#print axioms PCSCalibrationReplay.M4.Q2.dual_checked
#print axioms PCSCalibrationReplay.M4.Q2.gain_checked
#print axioms PCSCalibrationReplay.M4.Q2.real_gain
#print axioms PCSCalibrationReplay.M4.Q2.fitted_query
#print axioms PCSCalibrationReplay.M4.Q2.sharp_radius
#print axioms PCSCalibrationReplay.M4.Q2.conditional_physical_enclosure
#print axioms PCSCalibrationReplay.M4.Q3.dual_checked
#print axioms PCSCalibrationReplay.M4.Q3.gain_checked
#print axioms PCSCalibrationReplay.M4.Q3.real_gain
#print axioms PCSCalibrationReplay.M4.Q3.fitted_query
#print axioms PCSCalibrationReplay.M4.Q3.sharp_radius
#print axioms PCSCalibrationReplay.M4.Q3.conditional_physical_enclosure
#print axioms PCSCalibrationReplay.M4.Q4.dual_checked
#print axioms PCSCalibrationReplay.M4.Q4.gain_checked
#print axioms PCSCalibrationReplay.M4.Q4.real_gain
#print axioms PCSCalibrationReplay.M4.Q4.fitted_query
#print axioms PCSCalibrationReplay.M4.Q4.sharp_radius
#print axioms PCSCalibrationReplay.M4.Q4.conditional_physical_enclosure
#print axioms PCSCalibrationReplay.M4.Q5.dual_checked
#print axioms PCSCalibrationReplay.M4.Q5.gain_checked
#print axioms PCSCalibrationReplay.M4.Q5.real_gain
#print axioms PCSCalibrationReplay.M4.Q5.fitted_query
#print axioms PCSCalibrationReplay.M4.Q5.sharp_radius
#print axioms PCSCalibrationReplay.M4.Q5.conditional_physical_enclosure
#print axioms PCSCalibrationReplay.M4.Q6.dual_checked
#print axioms PCSCalibrationReplay.M4.Q6.gain_checked
#print axioms PCSCalibrationReplay.M4.Q6.real_gain
#print axioms PCSCalibrationReplay.M4.Q6.fitted_query
#print axioms PCSCalibrationReplay.M4.Q6.sharp_radius
#print axioms PCSCalibrationReplay.M4.Q6.conditional_physical_enclosure
#print axioms PCSCalibrationReplay.M4.Q7.dual_checked
#print axioms PCSCalibrationReplay.M4.Q7.gain_checked
#print axioms PCSCalibrationReplay.M4.Q7.real_gain
#print axioms PCSCalibrationReplay.M4.Q7.fitted_query
#print axioms PCSCalibrationReplay.M4.Q7.sharp_radius
#print axioms PCSCalibrationReplay.M4.Q7.conditional_physical_enclosure
#print axioms PCSCalibrationReplay.M5.normal_checked
#print axioms PCSCalibrationReplay.M5.residual_checked
#print axioms PCSCalibrationReplay.M5.global_optimum
#print axioms PCSCalibrationReplay.M5.excludes_every_better_model
