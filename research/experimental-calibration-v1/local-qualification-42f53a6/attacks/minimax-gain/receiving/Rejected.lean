import PCSReal.Calibration
set_option autoImplicit false
open Finset PCSReal.Calibration
namespace PCSCalibrationRejected
def u0 (i : Fin 7) : ℚ := ([((5 : ℚ) / (1 : ℚ)), ((7 : ℚ) / (1 : ℚ)), ((9 : ℚ) / (1 : ℚ)), ((11 : ℚ) / (1 : ℚ)), ((13 : ℚ) / (1 : ℚ)), ((15 : ℚ) / (1 : ℚ)), ((17 : ℚ) / (1 : ℚ))] : List ℚ).getD i.val 0
def x0 (i : Fin 7) (j : Fin 2) : ℚ := u0 i ^ j.val
def y0 (i : Fin 7) : ℚ := ([((11 : ℚ) / (100 : ℚ)), ((47 : ℚ) / (100 : ℚ)), ((59 : ℚ) / (50 : ℚ)), ((261 : ℚ) / (100 : ℚ)), ((499 : ℚ) / (100 : ℚ)), ((1193 : ℚ) / (100 : ℚ)), ((131 : ℚ) / (4 : ℚ))] : List ℚ).getD i.val 0
def b0 (j : Fin 2) : ℚ := ([((-93883 : ℚ) / (5600 : ℚ)), ((2493 : ℚ) / (1120 : ℚ))] : List ℚ).getD j.val 0
def q0_0 (j : Fin 2) : ℚ := (((6 : ℚ) / (1 : ℚ)) : ℚ) ^ j.val
def w0_0 (i : Fin 7) : ℚ := ([((23 : ℚ) / (56 : ℚ)), ((9 : ℚ) / (28 : ℚ)), ((13 : ℚ) / (56 : ℚ)), ((1 : ℚ) / (7 : ℚ)), ((3 : ℚ) / (56 : ℚ)), ((-1 : ℚ) / (28 : ℚ)), ((-1 : ℚ) / (8 : ℚ))] : List ℚ).getD i.val 0
def d0_0 (j : Fin 2) : ℚ := ([((71 : ℚ) / (112 : ℚ)), ((-5 : ℚ) / (112 : ℚ))] : List ℚ).getD j.val 0
def m0_0 (i : Fin 7) : ℚ := ([((1 : ℚ) / (2 : ℚ)), ((1 : ℚ) / (2 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ))] : List ℚ).getD i.val 0
def a0_0 (j : Fin 2) : ℚ := ([((1 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ))] : List ℚ).getD j.val 0
def allChecks : Bool := decide ((fitCheck x0 y0 b0 = true) ∧ (loss x0 y0 b0 = ((77313911 : ℚ) / (280000 : ℚ))) ∧ (dualCheck x0 w0_0 q0_0 d0_0 = true) ∧ ((∑ i, |w0_0 i|) = ((37 : ℚ) / (28 : ℚ))) ∧ (minimaxCheck x0 m0_0 q0_0 a0_0 ((0 : ℚ) / (1 : ℚ)) = true))
theorem certificate_rejected : allChecks = false := by decide +kernel
end PCSCalibrationRejected
#print axioms PCSCalibrationRejected.certificate_rejected
