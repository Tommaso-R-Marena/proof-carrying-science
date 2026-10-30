import PCSReal.TransportTrace

/-! Proof construction for exactly the existing checker. A fault certificate
names one observed scalar; checking its inequality is sufficient to reject the
whole trace. No Python search result is a premise of these theorems. -/
set_option autoImplicit false
namespace PCSPortableTransportV2
open PCSReal.Transport PCSReal.TransportTrace

variable {n steps : Nat} {p : Fin n → Fin n → ℚ} {initial : Fin n → ℚ}
  {states : Nat → Fin n → ℚ} {times : Nat → ℚ} {dt : ℚ}

theorem rows_sound
    (zero : ∀ i, states 0 i = initial i)
    (rows : ∀ k : Fin steps, ∀ i, states (k.val + 1) i = step p (states k.val) i)
    (grid : ∀ k : Fin (steps + 1), times k.val = (k.val : ℚ) * dt) :
    PCSReal.TransportTrace.check p initial states times dt steps = true := by
  simp only [PCSReal.TransportTrace.check, decide_eq_true_eq]
  exact ⟨zero, rows, grid⟩

theorem initial_fault_rejects (i : Fin n) (bad : states 0 i ≠ initial i) :
    PCSReal.TransportTrace.check p initial states times dt steps = false := by
  apply Bool.eq_false_iff.mpr
  intro good
  simp only [PCSReal.TransportTrace.check, decide_eq_true_eq] at good
  exact bad (good.1 i)

theorem recurrence_fault_rejects (k : Fin steps) (i : Fin n)
    (bad : states (k.val + 1) i ≠ step p (states k.val) i) :
    PCSReal.TransportTrace.check p initial states times dt steps = false := by
  apply Bool.eq_false_iff.mpr
  intro good
  simp only [PCSReal.TransportTrace.check, decide_eq_true_eq] at good
  exact bad (good.2.1 k i)

theorem time_fault_rejects (k : Fin (steps + 1))
    (bad : times k.val ≠ (k.val : ℚ) * dt) :
    PCSReal.TransportTrace.check p initial states times dt steps = false := by
  apply Bool.eq_false_iff.mpr
  intro good
  simp only [PCSReal.TransportTrace.check, decide_eq_true_eq] at good
  exact bad (good.2.2 k)

end PCSPortableTransportV2
#print axioms PCSPortableTransportV2.rows_sound
#print axioms PCSPortableTransportV2.initial_fault_rejects
#print axioms PCSPortableTransportV2.recurrence_fault_rejects
#print axioms PCSPortableTransportV2.time_fault_rejects
