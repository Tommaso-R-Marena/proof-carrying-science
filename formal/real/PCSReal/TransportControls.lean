import PCSReal.Transport

set_option autoImplicit false
namespace PCSReal.TransportControls
open PCSReal.Transport

def volume (_ : Fin 2) : ℚ := 1
def uniform (_ _ : Fin 2) : ℚ := 1 / 2

theorem uniform_checked : check volume uniform = true := by decide +kernel

theorem uniform_all_times (x : Fin 2 → ℝ) (lo hi : ℝ)
    (hx : ∀ i, lo ≤ x i ∧ x i ≤ hi) (n : Nat) :
    amount (fun i => (volume i : ℝ)) (evolve (fun i j => (uniform i j : ℝ)) x n) =
      amount (fun i => (volume i : ℝ)) x ∧
    (∀ i, lo ≤ evolve (fun i j => (uniform i j : ℝ)) x n i ∧
      evolve (fun i j => (uniform i j : ℝ)) x n i ≤ hi) ∧
    quadratic (fun i => (volume i : ℝ)) (evolve (fun i j => (uniform i j : ℝ)) x (n + 1)) ≤
      quadratic (fun i => (volume i : ℝ)) (evolve (fun i j => (uniform i j : ℝ)) x n) ∧
    quadratic (fun i => (volume i : ℝ)) (evolve (fun i j => (uniform i j : ℝ)) x n) ≤
      quadratic (fun i => (volume i : ℝ)) x :=
  all_times_contract (rational_certificate_real uniform_checked) x lo hi hx n

theorem negative_weight_rejected :
    check volume (fun i j => if i = j then 2 else -1) = false := by decide +kernel

theorem nonconservative_rejected :
    check volume (fun _ j => if j = 0 then 1 else 0) = false := by decide +kernel

theorem wrong_row_sum_rejected :
    check volume (fun _ _ => 1) = false := by decide +kernel

theorem zero_volume_rejected :
    check (fun (i : Fin 2) => if i = 0 then 0 else 1) (fun i j => if i = j then 1 else 0) = false := by
  decide +kernel

/-- A CFL-boundary oscillation preserves the quadratic functional. Contraction
    is non-strict; convergence or strict dissipation is not inferred. -/
theorem oscillation_preserves_quadratic :
    quadratic volume (step (fun i j => if i = j then 0 else 1) (fun i => if i = 0 then 1 else 0)) =
      quadratic volume (fun i => if i = 0 then 1 else 0) := by decide +kernel

end PCSReal.TransportControls
