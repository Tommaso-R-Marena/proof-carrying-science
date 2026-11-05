import PCSReal.TransportTrace
set_option autoImplicit false
set_option maxRecDepth 8192
set_option maxHeartbeats 2000000
namespace PCSTransportReplay
open PCSReal.Transport
-- Exact source contract: 914d4bc3969337116cfb0e2532603a90b4a2c6edd9e269ac0b81d96559004072
def volume (i : Fin 2) : ℚ := ([((1 : ℚ) / (1 : ℚ)), ((1 : ℚ) / (1 : ℚ))] : List ℚ).getD i.val 0
def matrix (i j : Fin 2) : ℚ := (([[((0 : ℚ) / (1 : ℚ)), ((1 : ℚ) / (1 : ℚ))], [((1 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ))]] : List (List ℚ)).getD i.val []).getD j.val 0
def initial (i : Fin 2) : ℚ := ([((1 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ))] : List ℚ).getD i.val 0
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
theorem all_real_initial_states (x : Fin 2 → ℝ) (lo hi : ℝ)
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

namespace PCSTransportTraceReplay
open PCSReal.Transport PCSTransportReplay
-- Exact trajectory bytes: e2443be1ed71f7843025cdfb9364103129d4c6da4eb67697a0aef3e4e16a8c96
def states (k : Nat) (i : Fin 2) : ℚ := (([[((1 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ))], [((0 : ℚ) / (1 : ℚ)), ((1 : ℚ) / (1 : ℚ))], [((1 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ))], [((0 : ℚ) / (1 : ℚ)), ((1 : ℚ) / (1 : ℚ))], [((1 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ))], [((0 : ℚ) / (1 : ℚ)), ((1 : ℚ) / (1 : ℚ))], [((1 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ))], [((0 : ℚ) / (1 : ℚ)), ((1 : ℚ) / (1 : ℚ))], [((1 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ))], [((0 : ℚ) / (1 : ℚ)), ((1 : ℚ) / (1 : ℚ))], [((1 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ))], [((0 : ℚ) / (1 : ℚ)), ((1 : ℚ) / (1 : ℚ))], [((1 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ))], [((0 : ℚ) / (1 : ℚ)), ((1 : ℚ) / (1 : ℚ))], [((1 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ))], [((0 : ℚ) / (1 : ℚ)), ((1 : ℚ) / (1 : ℚ))], [((1 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ))], [((0 : ℚ) / (1 : ℚ)), ((1 : ℚ) / (1 : ℚ))], [((1 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ))], [((0 : ℚ) / (1 : ℚ)), ((1 : ℚ) / (1 : ℚ))], [((1 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ))], [((0 : ℚ) / (1 : ℚ)), ((1 : ℚ) / (1 : ℚ))], [((1 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ))], [((0 : ℚ) / (1 : ℚ)), ((1 : ℚ) / (1 : ℚ))], [((1 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ))], [((0 : ℚ) / (1 : ℚ)), ((1 : ℚ) / (1 : ℚ))], [((1 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ))], [((0 : ℚ) / (1 : ℚ)), ((1 : ℚ) / (1 : ℚ))], [((1 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ))], [((0 : ℚ) / (1 : ℚ)), ((1 : ℚ) / (1 : ℚ))], [((1 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ))], [((0 : ℚ) / (1 : ℚ)), ((1 : ℚ) / (1 : ℚ))], [((1 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ))], [((0 : ℚ) / (1 : ℚ)), ((1 : ℚ) / (1 : ℚ))], [((1 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ))], [((0 : ℚ) / (1 : ℚ)), ((1 : ℚ) / (1 : ℚ))], [((1 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ))], [((0 : ℚ) / (1 : ℚ)), ((1 : ℚ) / (1 : ℚ))], [((1 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ))], [((0 : ℚ) / (1 : ℚ)), ((1 : ℚ) / (1 : ℚ))], [((1 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ))], [((0 : ℚ) / (1 : ℚ)), ((1 : ℚ) / (1 : ℚ))], [((1 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ))], [((0 : ℚ) / (1 : ℚ)), ((1 : ℚ) / (1 : ℚ))], [((1 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ))], [((0 : ℚ) / (1 : ℚ)), ((1 : ℚ) / (1 : ℚ))], [((1 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ))], [((0 : ℚ) / (1 : ℚ)), ((1 : ℚ) / (1 : ℚ))], [((1 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ))], [((0 : ℚ) / (1 : ℚ)), ((1 : ℚ) / (1 : ℚ))], [((1 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ))], [((0 : ℚ) / (1 : ℚ)), ((1 : ℚ) / (1 : ℚ))], [((1 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ))], [((0 : ℚ) / (1 : ℚ)), ((1 : ℚ) / (1 : ℚ))], [((1 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ))], [((0 : ℚ) / (1 : ℚ)), ((1 : ℚ) / (1 : ℚ))], [((1 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ))], [((0 : ℚ) / (1 : ℚ)), ((1 : ℚ) / (1 : ℚ))], [((1 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ))], [((0 : ℚ) / (1 : ℚ)), ((1 : ℚ) / (1 : ℚ))], [((1 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ))], [((0 : ℚ) / (1 : ℚ)), ((1 : ℚ) / (1 : ℚ))], [((1 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ))], [((0 : ℚ) / (1 : ℚ)), ((1 : ℚ) / (1 : ℚ))], [((1 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ))]] : List (List ℚ)).getD k []).getD i.val 0
def times (k : Nat) : ℚ := ([((0 : ℚ) / (1 : ℚ)), ((1 : ℚ) / (1 : ℚ)), ((2 : ℚ) / (1 : ℚ)), ((3 : ℚ) / (1 : ℚ)), ((4 : ℚ) / (1 : ℚ)), ((5 : ℚ) / (1 : ℚ)), ((6 : ℚ) / (1 : ℚ)), ((7 : ℚ) / (1 : ℚ)), ((8 : ℚ) / (1 : ℚ)), ((9 : ℚ) / (1 : ℚ)), ((10 : ℚ) / (1 : ℚ)), ((11 : ℚ) / (1 : ℚ)), ((12 : ℚ) / (1 : ℚ)), ((13 : ℚ) / (1 : ℚ)), ((14 : ℚ) / (1 : ℚ)), ((15 : ℚ) / (1 : ℚ)), ((16 : ℚ) / (1 : ℚ)), ((17 : ℚ) / (1 : ℚ)), ((18 : ℚ) / (1 : ℚ)), ((19 : ℚ) / (1 : ℚ)), ((20 : ℚ) / (1 : ℚ)), ((21 : ℚ) / (1 : ℚ)), ((22 : ℚ) / (1 : ℚ)), ((23 : ℚ) / (1 : ℚ)), ((24 : ℚ) / (1 : ℚ)), ((25 : ℚ) / (1 : ℚ)), ((26 : ℚ) / (1 : ℚ)), ((27 : ℚ) / (1 : ℚ)), ((28 : ℚ) / (1 : ℚ)), ((29 : ℚ) / (1 : ℚ)), ((30 : ℚ) / (1 : ℚ)), ((31 : ℚ) / (1 : ℚ)), ((32 : ℚ) / (1 : ℚ)), ((33 : ℚ) / (1 : ℚ)), ((34 : ℚ) / (1 : ℚ)), ((35 : ℚ) / (1 : ℚ)), ((36 : ℚ) / (1 : ℚ)), ((37 : ℚ) / (1 : ℚ)), ((38 : ℚ) / (1 : ℚ)), ((39 : ℚ) / (1 : ℚ)), ((40 : ℚ) / (1 : ℚ)), ((41 : ℚ) / (1 : ℚ)), ((42 : ℚ) / (1 : ℚ)), ((43 : ℚ) / (1 : ℚ)), ((44 : ℚ) / (1 : ℚ)), ((45 : ℚ) / (1 : ℚ)), ((46 : ℚ) / (1 : ℚ)), ((47 : ℚ) / (1 : ℚ)), ((48 : ℚ) / (1 : ℚ)), ((49 : ℚ) / (1 : ℚ)), ((50 : ℚ) / (1 : ℚ)), ((51 : ℚ) / (1 : ℚ)), ((52 : ℚ) / (1 : ℚ)), ((53 : ℚ) / (1 : ℚ)), ((54 : ℚ) / (1 : ℚ)), ((55 : ℚ) / (1 : ℚ)), ((56 : ℚ) / (1 : ℚ)), ((57 : ℚ) / (1 : ℚ)), ((58 : ℚ) / (1 : ℚ)), ((59 : ℚ) / (1 : ℚ)), ((60 : ℚ) / (1 : ℚ)), ((61 : ℚ) / (1 : ℚ)), ((62 : ℚ) / (1 : ℚ)), ((63 : ℚ) / (1 : ℚ)), ((64 : ℚ) / (1 : ℚ))] : List ℚ).getD k 0
def dt : ℚ := ((1 : ℚ) / (1 : ℚ))
theorem trace_checked : PCSReal.TransportTrace.check matrix initial states times dt 64 = true := by
  simp only [PCSReal.TransportTrace.check, decide_eq_true_eq]
  exact ⟨by decide +kernel, by decide +kernel, by decide +kernel⟩
theorem recorded_states_and_times :
    (∀ k, k ≤ 64 → ∀ i, states k i = evolve matrix initial k i) ∧
    (∀ k, k ≤ 64 → times k = (k : ℚ) * dt) :=
  PCSReal.TransportTrace.check_sound trace_checked
theorem recorded_invariants (k : Nat) (hk : k ≤ 64) :
    amount volume (states k) = amount volume initial ∧
    (∀ i, lower ≤ states k i ∧ states k i ≤ upper) ∧
    quadratic volume (states k) ≤ quadratic volume initial :=
  PCSReal.TransportTrace.recorded_invariants (PCSReal.Transport.check_sound matrix_checked)
    initial lower upper initial_bounds states 64 recorded_states_and_times.1 k hk
theorem adjacent_quadratic (k : Nat) (hk : k < 64) :
    quadratic volume (states (k + 1)) ≤ quadratic volume (states k) :=
  PCSReal.TransportTrace.adjacent_quadratic (PCSReal.Transport.check_sound matrix_checked)
    initial states 64 recorded_states_and_times.1 k hk
theorem recorded_real_states (k : Nat) (hk : k ≤ 64) :
    ∀ i, ((states k i : ℚ) : ℝ) =
      evolve (fun i j => (matrix i j : ℝ)) (fun j => (initial j : ℝ)) k i :=
  PCSReal.TransportTrace.real_trace_sound trace_checked k hk
end PCSTransportTraceReplay
#print axioms PCSTransportTraceReplay.trace_checked
#print axioms PCSTransportTraceReplay.recorded_states_and_times
#print axioms PCSTransportTraceReplay.recorded_invariants
#print axioms PCSTransportTraceReplay.adjacent_quadratic
#print axioms PCSTransportTraceReplay.recorded_real_states
