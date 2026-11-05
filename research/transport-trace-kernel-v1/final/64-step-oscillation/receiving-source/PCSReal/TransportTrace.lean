import PCSReal.Transport

/-! Finite recorded data are related to the declared recurrence by ordinary
kernel reduction. These theorems do not refine a CSV parser or native runtime. -/
set_option autoImplicit false
namespace PCSReal.TransportTrace
open PCSReal.Transport

variable {ι K : Type*} [Fintype ι]
  [Field K] [LinearOrder K] [IsStrictOrderedRing K]

omit [LinearOrder K] [IsStrictOrderedRing K] in
theorem bounded_recurrence_unique (p : ι → ι → K) (initial : ι → K)
    (states : Nat → ι → K) (steps : Nat)
    (hzero : ∀ i, states 0 i = initial i)
    (hstep : ∀ k, k < steps → ∀ i, states (k + 1) i = step p (states k) i) :
    ∀ k, k ≤ steps → ∀ i, states k i = evolve p initial k i := by
  intro k
  induction k with
  | zero => intro _; exact hzero
  | succ k ih =>
    intro hk i
    have hlt : k < steps := Nat.lt_of_succ_le hk
    rw [hstep k hlt i]
    change step p (states k) i = step p (evolve p initial k) i
    rw [funext (ih (Nat.le_of_lt hlt))]

def check {n : Nat} (p : Fin n → Fin n → ℚ) (initial : Fin n → ℚ)
    (states : Nat → Fin n → ℚ) (times : Nat → ℚ) (dt : ℚ) (steps : Nat) : Bool :=
  decide ((∀ i, states 0 i = initial i) ∧
    (∀ k : Fin steps, ∀ i, states (k.val + 1) i = step p (states k.val) i) ∧
    (∀ k : Fin (steps + 1), times k.val = (k.val : ℚ) * dt))

theorem check_sound {n : Nat} {p : Fin n → Fin n → ℚ} {initial : Fin n → ℚ}
    {states : Nat → Fin n → ℚ} {times : Nat → ℚ} {dt : ℚ} {steps : Nat}
    (h : check p initial states times dt steps = true) :
    (∀ k, k ≤ steps → ∀ i, states k i = evolve p initial k i) ∧
    (∀ k, k ≤ steps → times k = (k : ℚ) * dt) := by
  simp only [check, decide_eq_true_eq] at h
  constructor
  · exact bounded_recurrence_unique p initial states steps h.1
      (fun k hk => h.2.1 ⟨k, hk⟩)
  · intro k hk
    exact h.2.2 ⟨k, Nat.lt_succ_of_le hk⟩

theorem recorded_invariants {v : ι → K} {p : ι → ι → K} (h : Certified v p)
    (initial : ι → K) (lo hi : K) (hx : ∀ i, lo ≤ initial i ∧ initial i ≤ hi)
    (states : Nat → ι → K) (steps : Nat)
    (heq : ∀ k, k ≤ steps → ∀ i, states k i = evolve p initial k i)
    (k : Nat) (hk : k ≤ steps) :
    amount v (states k) = amount v initial ∧
    (∀ i, lo ≤ states k i ∧ states k i ≤ hi) ∧
    quadratic v (states k) ≤ quadratic v initial := by
  rw [funext (heq k hk)]
  exact ⟨amount_all_times h initial k, bounds_all_times h initial lo hi hx k,
    quadratic_all_times h initial k⟩

theorem adjacent_quadratic {v : ι → K} {p : ι → ι → K} (h : Certified v p)
    (initial : ι → K) (states : Nat → ι → K) (steps : Nat)
    (heq : ∀ k, k ≤ steps → ∀ i, states k i = evolve p initial k i)
    (k : Nat) (hk : k < steps) : quadratic v (states (k + 1)) ≤ quadratic v (states k) := by
  rw [funext (heq (k + 1) (Nat.succ_le_of_lt hk)), funext (heq k (Nat.le_of_lt hk))]
  exact quadratic_step h _

theorem cast_step {n : Nat} (p : Fin n → Fin n → ℚ) (x : Fin n → ℚ) (i : Fin n) :
    ((step p x i : ℚ) : ℝ) = step (fun i j => (p i j : ℝ)) (fun j => (x j : ℝ)) i := by
  simp only [step, Rat.cast_sum, Rat.cast_mul]

theorem cast_evolve {n : Nat} (p : Fin n → Fin n → ℚ) (x : Fin n → ℚ) (k : Nat) :
    ∀ i, ((evolve p x k i : ℚ) : ℝ) =
      evolve (fun i j => (p i j : ℝ)) (fun j => (x j : ℝ)) k i := by
  induction k with
  | zero => intro i; rfl
  | succ k ih =>
    intro i
    change ((step p (evolve p x k) i : ℚ) : ℝ) = _
    rw [cast_step]
    rw [funext ih]
    rfl

theorem real_trace_sound {n : Nat} {p : Fin n → Fin n → ℚ} {initial : Fin n → ℚ}
    {states : Nat → Fin n → ℚ} {times : Nat → ℚ} {dt : ℚ} {steps : Nat}
    (h : check p initial states times dt steps = true) (k : Nat) (hk : k ≤ steps) :
    ∀ i, ((states k i : ℚ) : ℝ) =
      evolve (fun i j => (p i j : ℝ)) (fun j => (initial j : ℝ)) k i := by
  intro i
  rw [(check_sound h).1 k hk i, cast_evolve]
end PCSReal.TransportTrace
