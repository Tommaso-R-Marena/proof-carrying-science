import Certificate
import Mathlib.Algebra.BigOperators.Fin
import Mathlib.Tactic.FinCases

/- Experimental parameterized counterexample. No production authority or codec
   refinement is inferred. Parameters and inequalities remain explicit. -/
set_option autoImplicit false
namespace PCSPortableInvariantFamily
open PCSReal.Transport

def volume (_ : Fin 2) : ℚ := 1
def initial (i : Fin 2) : ℚ := if i = 0 then 1 else 0
def mixed (a : ℚ) (i : Fin 2) : ℚ := if i = 0 then 1 - a else a
def matrix (a : ℚ) (i j : Fin 2) : ℚ := if i = j then 1 - a else a
def states (b : ℚ) (k : Nat) : Fin 2 → ℚ := if k = 0 then initial else mixed b
def times (k : Nat) : ℚ := k

theorem matrix_certified (a : ℚ) (ha : 0 ≤ a) (ha1 : a ≤ 1) :
    Certified volume (matrix a) := by
  apply of_detailed_balance
  · intro i; norm_num [volume]
  · intro i j; dsimp [matrix]; split_ifs <;> linarith
  · intro i; fin_cases i <;> simp [matrix, Fin.sum_univ_two]
  · intro i j; simp [volume, matrix, eq_comm]

theorem step_initial (a : ℚ) : step (matrix a) initial = mixed a := by
  funext i
  fin_cases i <;> simp [step, matrix, initial, mixed]

/-- For every 0≤a<b≤1/2, a certified symmetric transport model admits a false
one-step recording that conserves amount, stays within initial bounds and has
strictly *lower* energy than both the initial and the true next state. The exact
old trace checker rejects it. Invariant summaries cannot validate recurrence. -/
theorem invariant_counterexample_family (a b : ℚ)
    (ha : 0 ≤ a) (hab : a < b) (hb : b ≤ 1 / 2) :
    Certified volume (matrix a) ∧
    amount volume (mixed b) = amount volume initial ∧
    (∀ i, 0 ≤ mixed b i ∧ mixed b i ≤ 1) ∧
    quadratic volume (mixed b) < quadratic volume initial ∧
    quadratic volume (mixed b) < quadratic volume (step (matrix a) initial) ∧
    PCSReal.TransportTrace.check (matrix a) initial (states b) times 1 1 = false := by
  have hbp : 0 < b := lt_of_le_of_lt ha hab
  have hb1 : 0 < 1 - b := by linarith
  have hprod := mul_pos hbp hb1
  have hgap : 0 < (b - a) * (1 - a - b) :=
    mul_pos (sub_pos.mpr hab) (by linarith)
  refine ⟨matrix_certified a ha (by linarith), ?_, ?_, ?_, ?_, ?_⟩
  · simp [amount, volume, mixed, initial, Fin.sum_univ_two]
  · intro i; fin_cases i <;> simp [mixed] <;> constructor <;> linarith
  · simp [quadratic, volume, mixed, initial, Fin.sum_univ_two]
    nlinarith
  · rw [step_initial]
    simp [quadratic, volume, mixed, Fin.sum_univ_two]
    nlinarith
  · apply PCSPortableTransportV2.recurrence_fault_rejects (k := ⟨0, by decide⟩) (i := 0)
    have bad : (1 - b : ℚ) ≠ 1 - a := by intro h; linarith
    simpa [states, step_initial, mixed] using bad


/-- A forged trajectory can satisfy the invariant summaries at every natural
time and still be rejected by the exact checker at every positive horizon. -/
theorem all_times (a b : ℚ)
    (ha : 0 ≤ a) (hab : a < b) (hb : b ≤ 1 / 2) :
    (∀ k : Nat,
      amount volume (states b k) = amount volume initial ∧
      (∀ i, 0 ≤ states b k i ∧ states b k i ≤ 1) ∧
      quadratic volume (states b (k + 1)) ≤ quadratic volume (states b k)) ∧
    (∀ steps : Nat, 0 < steps →
      PCSReal.TransportTrace.check (matrix a) initial (states b) times 1 steps = false) := by
  have h := invariant_counterexample_family a b ha hab hb
  constructor
  · intro k
    cases k with
    | zero =>
      change amount volume initial = amount volume initial ∧
        (∀ i, 0 ≤ initial i ∧ initial i ≤ 1) ∧
        quadratic volume (mixed b) ≤ quadratic volume initial
      refine ⟨rfl, ?_, h.2.2.2.1.le⟩
      intro i; fin_cases i <;> norm_num [initial]
    | succ k =>
      change amount volume (mixed b) = amount volume initial ∧
        (∀ i, 0 ≤ mixed b i ∧ mixed b i ≤ 1) ∧
        quadratic volume (mixed b) ≤ quadratic volume (mixed b)
      exact ⟨h.2.1, h.2.2.1, le_rfl⟩
  · intro steps hs
    apply PCSPortableTransportV2.recurrence_fault_rejects (k := ⟨0, hs⟩) (i := 0)
    have bad : (1 - b : ℚ) ≠ 1 - a := by intro eq; linarith
    simpa [states, step_initial, mixed] using bad

end PCSPortableInvariantFamily
#print axioms PCSPortableInvariantFamily.matrix_certified
#print axioms PCSPortableInvariantFamily.step_initial
#print axioms PCSPortableInvariantFamily.invariant_counterexample_family

#print axioms PCSPortableInvariantFamily.all_times
