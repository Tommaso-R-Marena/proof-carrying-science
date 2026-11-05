import PCSReal.Transport
set_option autoImplicit false
set_option maxRecDepth 8192
set_option maxHeartbeats 2000000
namespace PCSTransportReplay
open PCSReal.Transport
-- Exact source contract: 03d39878aedb0b1cbc24d6e56f8ce509d1cc66960f41294219c9e79dd3e57c37
def volume (i : Fin 5) : ℚ := ([((1 : ℚ) / (1 : ℚ)), ((2 : ℚ) / (1 : ℚ)), ((3 : ℚ) / (2 : ℚ)), ((1 : ℚ) / (2 : ℚ)), ((3 : ℚ) / (1 : ℚ))] : List ℚ).getD i.val 0
def matrix (i j : Fin 5) : ℚ := (([[((7 : ℚ) / (8 : ℚ)), ((3 : ℚ) / (40 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((1 : ℚ) / (20 : ℚ))], [((1 : ℚ) / (16 : ℚ)), ((7 : ℚ) / (8 : ℚ)), ((1 : ℚ) / (24 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((1 : ℚ) / (48 : ℚ))], [((0 : ℚ) / (1 : ℚ)), ((1 : ℚ) / (18 : ℚ)), ((79 : ℚ) / (90 : ℚ)), ((1 : ℚ) / (15 : ℚ)), ((0 : ℚ) / (1 : ℚ))], [((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((1 : ℚ) / (5 : ℚ)), ((27 : ℚ) / (40 : ℚ)), ((1 : ℚ) / (8 : ℚ))], [((1 : ℚ) / (60 : ℚ)), ((1 : ℚ) / (72 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((1 : ℚ) / (48 : ℚ)), ((683 : ℚ) / (720 : ℚ))]] : List (List ℚ)).getD i.val []).getD j.val 0
def initial (i : Fin 5) : ℚ := ([((1 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((1 : ℚ) / (4 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((1 : ℚ) / (8 : ℚ))] : List ℚ).getD i.val 0
def lower : ℚ := ((0 : ℚ) / (1 : ℚ))
def upper : ℚ := ((1 : ℚ) / (1 : ℚ))
theorem matrix_rejected : check volume matrix = false := by decide +kernel
end PCSTransportReplay
#print axioms PCSTransportReplay.matrix_rejected
