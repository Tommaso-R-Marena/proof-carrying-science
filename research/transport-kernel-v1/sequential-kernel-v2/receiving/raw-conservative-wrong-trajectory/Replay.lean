import PCSReal.Transport
set_option autoImplicit false
set_option maxRecDepth 8192
set_option maxHeartbeats 2000000
namespace PCSTransportReplay
open PCSReal.Transport
-- Exact source contract: 03d39878aedb0b1cbc24d6e56f8ce509d1cc66960f41294219c9e79dd3e57c37
def volume (i : Fin 5) : ℚ := ([((1 : ℚ) / (1 : ℚ)), ((2 : ℚ) / (1 : ℚ)), ((3 : ℚ) / (2 : ℚ)), ((1 : ℚ) / (2 : ℚ)), ((3 : ℚ) / (1 : ℚ))] : List ℚ).getD i.val 0
def matrix (i j : Fin 5) : ℚ := (([[((33 : ℚ) / (40 : ℚ)), ((1 : ℚ) / (8 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((1 : ℚ) / (20 : ℚ))], [((1 : ℚ) / (16 : ℚ)), ((7 : ℚ) / (8 : ℚ)), ((1 : ℚ) / (24 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((1 : ℚ) / (48 : ℚ))], [((0 : ℚ) / (1 : ℚ)), ((1 : ℚ) / (18 : ℚ)), ((79 : ℚ) / (90 : ℚ)), ((1 : ℚ) / (15 : ℚ)), ((0 : ℚ) / (1 : ℚ))], [((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((1 : ℚ) / (5 : ℚ)), ((27 : ℚ) / (40 : ℚ)), ((1 : ℚ) / (8 : ℚ))], [((1 : ℚ) / (60 : ℚ)), ((1 : ℚ) / (72 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((1 : ℚ) / (48 : ℚ)), ((683 : ℚ) / (720 : ℚ))]] : List (List ℚ)).getD i.val []).getD j.val 0
def initial (i : Fin 5) : ℚ := ([((1 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((1 : ℚ) / (4 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((1 : ℚ) / (8 : ℚ))] : List ℚ).getD i.val 0
def lower : ℚ := ((0 : ℚ) / (1 : ℚ))
def upper : ℚ := ((1 : ℚ) / (1 : ℚ))
theorem matrix_checked : check volume matrix = true := by
  simp only [check, decide_eq_true_eq]
  exact ⟨by decide +kernel, by decide +kernel, by decide +kernel, by decide +kernel⟩
theorem initial_bounds : ∀ i, lower ≤ initial i ∧ initial i ≤ upper := by decide +kernel
theorem declared_all_times (n : Nat) :
    amount volume (evolve matrix initial n) = amount volume initial ∧
    (∀ i, lower ≤ evolve matrix initial n i ∧ evolve matrix initial n i ≤ upper) ∧
    quadratic volume (evolve matrix initial (n + 1)) ≤ quadratic volume (evolve matrix initial n) ∧
    quadratic volume (evolve matrix initial n) ≤ quadratic volume initial :=
  all_times_contract (check_sound matrix_checked) initial lower upper initial_bounds n
theorem all_real_initial_states (x : Fin 5 → ℝ) (lo hi : ℝ)
    (hx : ∀ i, lo ≤ x i ∧ x i ≤ hi) (n : Nat) :
    amount (fun i => (volume i : ℝ)) (evolve (fun i j => (matrix i j : ℝ)) x n) =
      amount (fun i => (volume i : ℝ)) x ∧
    (∀ i, lo ≤ evolve (fun i j => (matrix i j : ℝ)) x n i ∧
      evolve (fun i j => (matrix i j : ℝ)) x n i ≤ hi) ∧
    quadratic (fun i => (volume i : ℝ)) (evolve (fun i j => (matrix i j : ℝ)) x (n + 1)) ≤
      quadratic (fun i => (volume i : ℝ)) (evolve (fun i j => (matrix i j : ℝ)) x n) ∧
    quadratic (fun i => (volume i : ℝ)) (evolve (fun i j => (matrix i j : ℝ)) x n) ≤
      quadratic (fun i => (volume i : ℝ)) x :=
  all_times_contract (rational_certificate_real matrix_checked) x lo hi hx n
end PCSTransportReplay
#print axioms PCSTransportReplay.matrix_checked
#print axioms PCSTransportReplay.initial_bounds
#print axioms PCSTransportReplay.declared_all_times
#print axioms PCSTransportReplay.all_real_initial_states
