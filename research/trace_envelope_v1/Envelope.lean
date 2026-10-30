import PCSReal.TransportTrace

/-! A posteriori error bounds against the declared discrete recurrence.
    No physical-model, decoder or external-executable correctness is inferred. -/
set_option autoImplicit false
namespace PCSTraceEnvelope
open Finset PCSReal.Transport
variable {ι K : Type*} [Fintype ι]
  [Field K] [LinearOrder K] [IsStrictOrderedRing K]

def Within (x y : ι → K) (e : K) : Prop :=
  ∀ i, -e ≤ x i - y i ∧ x i - y i ≤ e

def radius (eta : K) (eps : Nat → K) : Nat → K
  | 0 => eta
  | k + 1 => radius eta eps k + eps k

omit [LinearOrder K] [IsStrictOrderedRing K] in
theorem step_sub (p : ι → ι → K) (x y : ι → K) (i : ι) :
    step p (fun j => x j - y j) i = step p x i - step p y i := by
  simp only [step, mul_sub, sum_sub_distrib]

theorem within_step {v : ι → K} {p : ι → ι → K} (h : Certified v p)
    (x y : ι → K) (e : K) (he : Within x y e) :
    Within (step p x) (step p y) e := by
  intro i
  rw [← step_sub]
  exact ⟨step_lower h _ (-e) (fun j => (he j).1) i,
    step_upper h _ e (fun j => (he j).2) i⟩

omit [IsStrictOrderedRing K] in
theorem step_add_const {v : ι → K} {p : ι → ι → K} (h : Certified v p)
    (x : ι → K) (c : K) (i : ι) :
    step p (fun j => x j + c) i = step p x i + c := by
  simp only [step, mul_add, sum_add_distrib, ← sum_mul, h.row_sum, one_mul]

theorem coherent_residual {v : ι → K} {p : ι → ι → K} (h : Certified v p)
    (initial : ι → K) (d : K) (k : Nat) (i : ι) :
    (evolve p initial (k + 1) i + ((k + 1 : Nat) : K) * d) -
      step p (fun j => evolve p initial k j + (k : K) * d) i = d := by
  rw [step_add_const h]
  simp only [evolve, Nat.cast_add, Nat.cast_one]
  ring

omit [LinearOrder K] [IsStrictOrderedRing K] in
theorem radius_constant (eta d : K) (k : Nat) :
    radius eta (fun _ => d) k = eta + (k : K) * d := by
  induction k with
  | zero => simp [radius]
  | succ k ih => simp only [radius, ih, Nat.cast_add, Nat.cast_one]; ring

theorem coherent_sharp (p : ι → ι → K)
    (initial : ι → K) (d : K) (hd : 0 ≤ d) (k : Nat) (i : ι) :
    |(evolve p initial k i + (k : K) * d) - evolve p initial k i| =
      radius 0 (fun _ => d) k := by
  rw [radius_constant]
  have hn : 0 ≤ (k : K) * d := mul_nonneg (Nat.cast_nonneg k) hd
  simpa only [add_sub_cancel_left, zero_add] using abs_of_nonneg hn

omit [Fintype ι] in
theorem within_trans (x y z : ι → K) (a b : K)
    (hxy : Within x y a) (hyz : Within y z b) : Within x z (a + b) := by
  intro i
  have hx := hxy i
  have hy := hyz i
  constructor <;> linarith

theorem propagate {v : ι → K} {p : ι → ι → K} (h : Certified v p)
    (initial : ι → K) (states : Nat → ι → K) (eta : K) (eps : Nat → K)
    (N : Nat) (hzero : Within (states 0) initial eta)
    (hstep : ∀ k, k < N → Within (states (k + 1)) (step p (states k)) (eps k)) :
    ∀ k, k ≤ N → Within (states k) (evolve p initial k) (radius eta eps k) := by
  intro k
  induction k with
  | zero => intro _; exact hzero
  | succ k ih =>
    intro hk
    have hlt : k < N := Nat.lt_of_succ_le hk
    have prev := within_step h (states k) (evolve p initial k) (radius eta eps k)
      (ih (Nat.le_of_lt hlt))
    have combined := within_trans _ _ _ _ _ (hstep k hlt) prev
    simpa only [evolve, radius, add_comm] using combined

theorem radius_mono (eta : K) (eps : Nat → K) (N : Nat)
    (heps : ∀ k, k < N → 0 ≤ eps k) :
    ∀ k, k ≤ N → radius eta eps k ≤ radius eta eps N := by
  induction N with
  | zero => intro k hk; have : k = 0 := Nat.eq_zero_of_le_zero hk; subst k; exact le_rfl
  | succ N ih =>
    intro k hk
    rcases Nat.eq_or_lt_of_le hk with rfl | hlt
    · exact le_rfl
    · have hp := ih (fun j hj => heps j (Nat.lt_succ_of_lt hj)) k (Nat.le_of_lt_succ hlt)
      have hn := heps N (Nat.lt_succ_self N)
      change radius eta eps k ≤ radius eta eps N + eps N
      linarith

theorem uniform {v : ι → K} {p : ι → ι → K} (h : Certified v p)
    (initial : ι → K) (states : Nat → ι → K) (eta : K) (eps : Nat → K)
    (N : Nat) (tol : K) (hzero : Within (states 0) initial eta)
    (hstep : ∀ k, k < N → Within (states (k + 1)) (step p (states k)) (eps k))
    (heps : ∀ k, k < N → 0 ≤ eps k) (htol : radius eta eps N ≤ tol) :
    ∀ k, k ≤ N → Within (states k) (evolve p initial k) tol := by
  intro k hk i
  have hp := propagate h initial states eta eps N hzero hstep k hk i
  have hm := le_trans (radius_mono eta eps N heps k hk) htol
  constructor <;> linarith

instance withinDecidable {n : Nat} (x y : Fin n → ℚ) (e : ℚ) :
    Decidable (Within x y e) := inferInstanceAs (Decidable (∀ i, -e ≤ x i - y i ∧ x i - y i ≤ e))

def check {n : Nat} (p : Fin n → Fin n → ℚ) (initial : Fin n → ℚ)
    (states : Nat → Fin n → ℚ) (times : Nat → ℚ) (dt eta : ℚ)
    (eps : Nat → ℚ) (N : Nat) : Bool :=
  decide ((0 ≤ eta) ∧ Within (states 0) initial eta ∧
    (∀ k : Fin N, 0 ≤ eps k.val ∧
      Within (states (k.val + 1)) (step p (states k.val)) (eps k.val)) ∧
    (∀ k : Fin (N + 1), times k.val = (k.val : ℚ) * dt))

theorem check_sound {n : Nat} {v : Fin n → ℚ} {p : Fin n → Fin n → ℚ}
    (hmodel : Certified v p) {initial : Fin n → ℚ} {states : Nat → Fin n → ℚ}
    {times : Nat → ℚ} {dt eta : ℚ} {eps : Nat → ℚ} {N : Nat}
    (h : check p initial states times dt eta eps N = true) :
    (∀ k, k ≤ N → Within (states k) (evolve p initial k) (radius eta eps k)) ∧
    (∀ k, k ≤ N → times k = (k : ℚ) * dt) := by
  simp only [check, decide_eq_true_eq] at h
  exact ⟨propagate hmodel initial states eta eps N h.2.1
    (fun k hk => (h.2.2.1 ⟨k, hk⟩).2),
    fun k hk => h.2.2.2 ⟨k, Nat.lt_succ_of_le hk⟩⟩

theorem check_uniform {n : Nat} {v : Fin n → ℚ} {p : Fin n → Fin n → ℚ}
    (hmodel : Certified v p) {initial : Fin n → ℚ} {states : Nat → Fin n → ℚ}
    {times : Nat → ℚ} {dt eta : ℚ} {eps : Nat → ℚ} {N : Nat} {tol : ℚ}
    (h : check p initial states times dt eta eps N = true)
    (htol : radius eta eps N ≤ tol) :
    ∀ k, k ≤ N → Within (states k) (evolve p initial k) tol := by
  simp only [check, decide_eq_true_eq] at h
  exact uniform hmodel initial states eta eps N tol h.2.1
    (fun k hk => (h.2.2.1 ⟨k, hk⟩).2) (fun k hk => (h.2.2.1 ⟨k, hk⟩).1) htol

theorem real_bound {n : Nat} {p : Fin n → Fin n → ℚ} {initial row : Fin n → ℚ}
    {k : Nat} {e : ℚ} (h : Within row (evolve p initial k) e) :
    Within (fun i => (row i : ℝ))
      (evolve (fun i j => (p i j : ℝ)) (fun i => (initial i : ℝ)) k) (e : ℝ) := by
  intro i
  rw [← PCSReal.TransportTrace.cast_evolve]
  have hi := h i
  constructor
  · have hlo : ((-e : ℚ) : ℝ) ≤ ((row i - evolve p initial k i : ℚ) : ℝ) := by
      exact_mod_cast hi.1
    simpa only [Rat.cast_neg, Rat.cast_sub] using hlo
  · have hhi : ((row i - evolve p initial k i : ℚ) : ℝ) ≤ (e : ℝ) := by
      exact_mod_cast hi.2
    simpa only [Rat.cast_sub] using hhi

end PCSTraceEnvelope
