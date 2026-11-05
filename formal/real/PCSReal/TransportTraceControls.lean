import PCSReal.TransportTrace
set_option autoImplicit false
namespace PCSReal.TransportTraceControls
open PCSReal.Transport
private def p (i j : Fin 2) : ℚ := if i = j then 0 else 1
private def initial (i : Fin 2) : ℚ := if i = 0 then 1 else 0
private def states (k : Nat) (i : Fin 2) : ℚ := if k % 2 = i.val then 1 else 0
private def times (k : Nat) : ℚ := k

theorem good_trace : PCSReal.TransportTrace.check p initial states times 1 2 = true := by decide +kernel

theorem good_trace_evolves : ∀ k, k ≤ 2 → ∀ i, states k i = evolve p initial k i :=
  (PCSReal.TransportTrace.check_sound good_trace).1

theorem wrong_initial_rejected :
    PCSReal.TransportTrace.check p initial (fun _ _ => 0) times 1 2 = false := by decide +kernel

theorem wrong_step_rejected :
    PCSReal.TransportTrace.check p initial (fun _ => initial) times 1 2 = false := by decide +kernel

theorem wrong_time_rejected :
    PCSReal.TransportTrace.check p initial states (fun k => (k : ℚ) + 1) 1 2 = false := by decide +kernel
end PCSReal.TransportTraceControls
