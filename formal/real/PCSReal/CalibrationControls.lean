import PCSReal.Calibration

set_option autoImplicit false
namespace PCSReal.CalibrationControls
open Finset PCSReal.Calibration

def x (i : Fin 3) (j : Fin 2) : ℚ := if j.val = 0 then 1 else (i.val : ℚ)
def y (i : Fin 3) : ℚ := ([1,4,8] : List ℚ).getD i.val 0
def b (j : Fin 2) : ℚ := ([5/6,7/2] : List ℚ).getD j.val 0
def w (i : Fin 3) : ℚ := ([-7/6,1/3,11/6] : List ℚ).getD i.val 0
def q (j : Fin 2) : ℚ := ([1,4] : List ℚ).getD j.val 0
def d (j : Fin 2) : ℚ := ([-7/6,3/2] : List ℚ).getD j.val 0

theorem good_normal : fitCheck x y b = true := by decide +kernel
theorem wrong_coefficient_rejected : fitCheck x y (fun _ => 0) = false := by decide +kernel
theorem exact_nonzero_residual : loss x y b = 1/6 := by decide +kernel
theorem good_dual : dualCheck x w q d = true := by decide +kernel
theorem wrong_dual_rejected : dualCheck x (fun _ => 0) q d = false := by decide +kernel
theorem sharp_gain : (∑ i, |w i|) = 10/3 := by decide +kernel

def mw (i : Fin 3) : ℚ := ([-1,0,2] : List ℚ).getD i.val 0
def ma (j : Fin 2) : ℚ := ([-1,1] : List ℚ).getD j.val 0
theorem good_minimax : minimaxCheck x mw q ma 3 = true := by decide +kernel
theorem false_minimax_rejected : minimaxCheck x w q ma (10/3) = false := by decide +kernel

theorem smaller_uniform_radius_impossible :
    ¬ (∀ z : Fin 3 → ℝ, (∀ i, |z i| ≤ 1) →
      |dot (fun i => (w i : ℝ)) z| ≤ 3) := by
  intro h
  have hh := (sharp_radius_iff (fun i => (w i : ℝ)) (fun _ => 0) 1 3 (by norm_num)).1
    (by simpa [dot] using h)
  have hg : (∑ i, |(w i : ℝ)|) = (10/3 : ℝ) := by
    have hc := congrArg (fun a : ℚ => (a : ℝ)) sharp_gain
    simpa only [Rat.cast_sum, Rat.cast_abs, Rat.cast_div, Rat.cast_ofNat] using hc
  rw [hg] at hh
  norm_num at hh

end PCSReal.CalibrationControls
