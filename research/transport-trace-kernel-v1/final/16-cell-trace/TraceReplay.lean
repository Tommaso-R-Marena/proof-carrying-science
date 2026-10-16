import PCSReal.TransportTrace
set_option autoImplicit false
set_option maxRecDepth 8192
set_option maxHeartbeats 2000000
namespace PCSTransportReplay
open PCSReal.Transport
-- Exact source contract: f7775ff52e83bb3bec02540e01034c354bd6756cd404c74cf26a35da9fcd800e
def volume (i : Fin 16) : ℚ := ([((1 : ℚ) / (2 : ℚ)), ((1 : ℚ) / (1 : ℚ)), ((3 : ℚ) / (2 : ℚ)), ((2 : ℚ) / (1 : ℚ)), ((5 : ℚ) / (2 : ℚ)), ((3 : ℚ) / (1 : ℚ)), ((7 : ℚ) / (2 : ℚ)), ((4 : ℚ) / (1 : ℚ)), ((9 : ℚ) / (2 : ℚ)), ((5 : ℚ) / (1 : ℚ)), ((11 : ℚ) / (2 : ℚ)), ((6 : ℚ) / (1 : ℚ)), ((13 : ℚ) / (2 : ℚ)), ((7 : ℚ) / (1 : ℚ)), ((15 : ℚ) / (2 : ℚ)), ((8 : ℚ) / (1 : ℚ))] : List ℚ).getD i.val 0
def matrix (i j : Fin 16) : ℚ := (([[((2047 : ℚ) / (2048 : ℚ)), ((1 : ℚ) / (2048 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ))], [((1 : ℚ) / (4096 : ℚ)), ((2047 : ℚ) / (2048 : ℚ)), ((1 : ℚ) / (4096 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ))], [((0 : ℚ) / (1 : ℚ)), ((1 : ℚ) / (6144 : ℚ)), ((3071 : ℚ) / (3072 : ℚ)), ((1 : ℚ) / (6144 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ))], [((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((1 : ℚ) / (8192 : ℚ)), ((4095 : ℚ) / (4096 : ℚ)), ((1 : ℚ) / (8192 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ))], [((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((1 : ℚ) / (10240 : ℚ)), ((5119 : ℚ) / (5120 : ℚ)), ((1 : ℚ) / (10240 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ))], [((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((1 : ℚ) / (12288 : ℚ)), ((6143 : ℚ) / (6144 : ℚ)), ((1 : ℚ) / (12288 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ))], [((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((1 : ℚ) / (14336 : ℚ)), ((7167 : ℚ) / (7168 : ℚ)), ((1 : ℚ) / (14336 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ))], [((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((1 : ℚ) / (16384 : ℚ)), ((8191 : ℚ) / (8192 : ℚ)), ((1 : ℚ) / (16384 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ))], [((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((1 : ℚ) / (18432 : ℚ)), ((9215 : ℚ) / (9216 : ℚ)), ((1 : ℚ) / (18432 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ))], [((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((1 : ℚ) / (20480 : ℚ)), ((10239 : ℚ) / (10240 : ℚ)), ((1 : ℚ) / (20480 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ))], [((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((1 : ℚ) / (22528 : ℚ)), ((11263 : ℚ) / (11264 : ℚ)), ((1 : ℚ) / (22528 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ))], [((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((1 : ℚ) / (24576 : ℚ)), ((12287 : ℚ) / (12288 : ℚ)), ((1 : ℚ) / (24576 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ))], [((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((1 : ℚ) / (26624 : ℚ)), ((13311 : ℚ) / (13312 : ℚ)), ((1 : ℚ) / (26624 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ))], [((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((1 : ℚ) / (28672 : ℚ)), ((14335 : ℚ) / (14336 : ℚ)), ((1 : ℚ) / (28672 : ℚ)), ((0 : ℚ) / (1 : ℚ))], [((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((1 : ℚ) / (30720 : ℚ)), ((15359 : ℚ) / (15360 : ℚ)), ((1 : ℚ) / (30720 : ℚ))], [((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((0 : ℚ) / (1 : ℚ)), ((1 : ℚ) / (32768 : ℚ)), ((32767 : ℚ) / (32768 : ℚ))]] : List (List ℚ)).getD i.val []).getD j.val 0
def initial (i : Fin 16) : ℚ := ([((1 : ℚ) / (4 : ℚ)), ((1 : ℚ) / (4 : ℚ)), ((1 : ℚ) / (4 : ℚ)), ((1 : ℚ) / (4 : ℚ)), ((1 : ℚ) / (4 : ℚ)), ((1 : ℚ) / (4 : ℚ)), ((1 : ℚ) / (4 : ℚ)), ((1 : ℚ) / (4 : ℚ)), ((1 : ℚ) / (4 : ℚ)), ((1 : ℚ) / (4 : ℚ)), ((1 : ℚ) / (4 : ℚ)), ((1 : ℚ) / (4 : ℚ)), ((1 : ℚ) / (4 : ℚ)), ((1 : ℚ) / (4 : ℚ)), ((1 : ℚ) / (4 : ℚ)), ((1 : ℚ) / (4 : ℚ))] : List ℚ).getD i.val 0
def lower : ℚ := ((1 : ℚ) / (4 : ℚ))
def upper : ℚ := ((1 : ℚ) / (4 : ℚ))
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
theorem all_real_initial_states (x : Fin 16 → ℝ) (lo hi : ℝ)
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
-- Exact trajectory bytes: 78657d9a4edc82ecc1eb1eea288439be29306ad079019dcbb9a9204cbdbe0f71
def states (k : Nat) (i : Fin 16) : ℚ := (([[((1 : ℚ) / (4 : ℚ)), ((1 : ℚ) / (4 : ℚ)), ((1 : ℚ) / (4 : ℚ)), ((1 : ℚ) / (4 : ℚ)), ((1 : ℚ) / (4 : ℚ)), ((1 : ℚ) / (4 : ℚ)), ((1 : ℚ) / (4 : ℚ)), ((1 : ℚ) / (4 : ℚ)), ((1 : ℚ) / (4 : ℚ)), ((1 : ℚ) / (4 : ℚ)), ((1 : ℚ) / (4 : ℚ)), ((1 : ℚ) / (4 : ℚ)), ((1 : ℚ) / (4 : ℚ)), ((1 : ℚ) / (4 : ℚ)), ((1 : ℚ) / (4 : ℚ)), ((1 : ℚ) / (4 : ℚ))], [((1 : ℚ) / (4 : ℚ)), ((1 : ℚ) / (4 : ℚ)), ((1 : ℚ) / (4 : ℚ)), ((1 : ℚ) / (4 : ℚ)), ((1 : ℚ) / (4 : ℚ)), ((1 : ℚ) / (4 : ℚ)), ((1 : ℚ) / (4 : ℚ)), ((1 : ℚ) / (4 : ℚ)), ((1 : ℚ) / (4 : ℚ)), ((1 : ℚ) / (4 : ℚ)), ((1 : ℚ) / (4 : ℚ)), ((1 : ℚ) / (4 : ℚ)), ((1 : ℚ) / (4 : ℚ)), ((1 : ℚ) / (4 : ℚ)), ((1 : ℚ) / (4 : ℚ)), ((1 : ℚ) / (4 : ℚ))]] : List (List ℚ)).getD k []).getD i.val 0
def times (k : Nat) : ℚ := ([((0 : ℚ) / (1 : ℚ)), ((1 : ℚ) / (1024 : ℚ))] : List ℚ).getD k 0
def dt : ℚ := ((1 : ℚ) / (1024 : ℚ))
theorem trace_checked : PCSReal.TransportTrace.check matrix initial states times dt 1 = true := by
  simp only [PCSReal.TransportTrace.check, decide_eq_true_eq]
  exact ⟨by decide +kernel, by decide +kernel, by decide +kernel⟩
theorem recorded_states_and_times :
    (∀ k, k ≤ 1 → ∀ i, states k i = evolve matrix initial k i) ∧
    (∀ k, k ≤ 1 → times k = (k : ℚ) * dt) :=
  PCSReal.TransportTrace.check_sound trace_checked
theorem recorded_invariants (k : Nat) (hk : k ≤ 1) :
    amount volume (states k) = amount volume initial ∧
    (∀ i, lower ≤ states k i ∧ states k i ≤ upper) ∧
    quadratic volume (states k) ≤ quadratic volume initial :=
  PCSReal.TransportTrace.recorded_invariants (PCSReal.Transport.check_sound matrix_checked)
    initial lower upper initial_bounds states 1 recorded_states_and_times.1 k hk
theorem adjacent_quadratic (k : Nat) (hk : k < 1) :
    quadratic volume (states (k + 1)) ≤ quadratic volume (states k) :=
  PCSReal.TransportTrace.adjacent_quadratic (PCSReal.Transport.check_sound matrix_checked)
    initial states 1 recorded_states_and_times.1 k hk
theorem recorded_real_states (k : Nat) (hk : k ≤ 1) :
    ∀ i, ((states k i : ℚ) : ℝ) =
      evolve (fun i j => (matrix i j : ℝ)) (fun j => (initial j : ℝ)) k i :=
  PCSReal.TransportTrace.real_trace_sound trace_checked k hk
end PCSTransportTraceReplay
#print axioms PCSTransportTraceReplay.trace_checked
#print axioms PCSTransportTraceReplay.recorded_states_and_times
#print axioms PCSTransportTraceReplay.recorded_invariants
#print axioms PCSTransportTraceReplay.adjacent_quadratic
#print axioms PCSTransportTraceReplay.recorded_real_states
