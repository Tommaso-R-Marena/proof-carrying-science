import Mathlib.Algebra.Order.BigOperators.Ring.Finset
import Mathlib.Data.Rat.BigOperators
import Mathlib.Data.Rat.Cast.Order
import Mathlib.Data.Real.Basic
import Mathlib.Tactic.Linarith
import Mathlib.Tactic.NormNum
import Mathlib.Tactic.Ring

/-!
Universal discrete transport invariants for a nonnegative row-stochastic matrix
with positive invariant cell volumes. These are mathematical matrix contracts;
no continuum, parser, Python-runtime or empirical correspondence is inferred.
-/
set_option autoImplicit false

namespace PCSReal.Transport

open Finset

variable {ι K : Type*} [Fintype ι]
  [Field K] [LinearOrder K] [IsStrictOrderedRing K]

structure Certified (volume : ι → K) (matrix : ι → ι → K) : Prop where
  volume_pos : ∀ i, 0 < volume i
  nonnegative : ∀ i j, 0 ≤ matrix i j
  row_sum : ∀ i, ∑ j, matrix i j = 1
  invariant_volume : ∀ j, ∑ i, volume i * matrix i j = volume j


omit [IsStrictOrderedRing K] in
/-- Detailed balance and row stochasticity imply volume invariance. Symmetric
    exchange discretizations can use this sufficient condition. -/
theorem of_detailed_balance (v : ι → K) (p : ι → ι → K)
    (hv : ∀ i, 0 < v i) (hp : ∀ i j, 0 ≤ p i j)
    (hr : ∀ i, ∑ j, p i j = 1)
    (hb : ∀ i j, v i * p i j = v j * p j i) : Certified v p := by
  refine ⟨hv, hp, hr, ?_⟩
  intro j
  calc (∑ i, v i * p i j) = ∑ i, v j * p j i := sum_congr rfl fun i _ => hb i j
       _ = v j := by rw [← mul_sum, hr]; simp

def step (matrix : ι → ι → K) (state : ι → K) (i : ι) : K :=
  ∑ j, matrix i j * state j

def amount (volume state : ι → K) : K := ∑ i, volume i * state i

def quadratic (volume state : ι → K) : K := ∑ i, volume i * state i ^ 2

def evolve (matrix : ι → ι → K) (initial : ι → K) : Nat → ι → K
  | 0 => initial
  | n + 1 => step matrix (evolve matrix initial n)

theorem step_lower {v : ι → K} {p : ι → ι → K} (h : Certified v p)
    (x : ι → K) (lo : K) (hx : ∀ i, lo ≤ x i) (i : ι) : lo ≤ step p x i := by
  calc lo = ∑ j, p i j * lo := by rw [← sum_mul, h.row_sum]; simp
       _ ≤ step p x i := sum_le_sum fun j _ => mul_le_mul_of_nonneg_left (hx j) (h.nonnegative i j)

theorem step_upper {v : ι → K} {p : ι → ι → K} (h : Certified v p)
    (x : ι → K) (hi : K) (hx : ∀ i, x i ≤ hi) (i : ι) : step p x i ≤ hi := by
  calc step p x i ≤ ∑ j, p i j * hi :=
         sum_le_sum fun j _ => mul_le_mul_of_nonneg_left (hx j) (h.nonnegative i j)
       _ = hi := by rw [← sum_mul, h.row_sum]; simp

theorem step_nonnegative {v : ι → K} {p : ι → ι → K} (h : Certified v p)
    (x : ι → K) (hx : ∀ i, 0 ≤ x i) (i : ι) : 0 ≤ step p x i :=
  step_lower h x 0 hx i

omit [IsStrictOrderedRing K] in
theorem amount_step {v : ι → K} {p : ι → ι → K} (h : Certified v p)
    (x : ι → K) : amount v (step p x) = amount v x := by
  unfold amount step
  simp_rw [mul_sum]
  rw [sum_comm]
  apply sum_congr rfl
  intro j _
  calc (∑ i, v i * (p i j * x j)) = (∑ i, v i * p i j) * x j := by
         rw [sum_mul]; apply sum_congr rfl; intro i _; ring
       _ = v j * x j := by rw [h.invariant_volume]

theorem row_quadratic_bound {v : ι → K} {p : ι → ι → K} (h : Certified v p)
    (x : ι → K) (i : ι) : (step p x i) ^ 2 ≤ ∑ j, p i j * x j ^ 2 := by
  let m := step p x i
  have hn : 0 ≤ ∑ j, p i j * (x j - m) ^ 2 :=
    sum_nonneg fun j _ => mul_nonneg (h.nonnegative i j) (sq_nonneg _)
  have hid : (∑ j, p i j * (x j - m) ^ 2) =
      (∑ j, p i j * x j ^ 2) - (2 * m) * (∑ j, p i j * x j) +
        m ^ 2 * (∑ j, p i j) := by
    calc (∑ j, p i j * (x j - m) ^ 2) =
        ∑ j, (p i j * x j ^ 2 - (2 * m) * (p i j * x j) + m ^ 2 * p i j) := by
          apply sum_congr rfl; intro j _; ring
         _ = _ := by rw [sum_add_distrib, sum_sub_distrib, ← mul_sum, ← mul_sum]
  rw [hid, h.row_sum] at hn
  change 0 ≤ (∑ j, p i j * x j ^ 2) - (2 * m) * m + m ^ 2 * 1 at hn
  change m ^ 2 ≤ _
  nlinarith

theorem quadratic_step {v : ι → K} {p : ι → ι → K} (h : Certified v p)
    (x : ι → K) : quadratic v (step p x) ≤ quadratic v x := by
  calc quadratic v (step p x) ≤ ∑ i, v i * (∑ j, p i j * x j ^ 2) := by
         exact sum_le_sum fun i _ => mul_le_mul_of_nonneg_left (row_quadratic_bound h x i) (h.volume_pos i).le
       _ = quadratic v x := by
         unfold quadratic
         simp_rw [mul_sum]
         rw [sum_comm]
         apply sum_congr rfl
         intro j _
         calc (∑ i, v i * (p i j * x j ^ 2)) = (∑ i, v i * p i j) * x j ^ 2 := by
                rw [sum_mul]; apply sum_congr rfl; intro i _; ring
              _ = v j * x j ^ 2 := by rw [h.invariant_volume]

omit [IsStrictOrderedRing K] in
theorem amount_all_times {v : ι → K} {p : ι → ι → K} (h : Certified v p)
    (x : ι → K) (n : Nat) : amount v (evolve p x n) = amount v x := by
  induction n with
  | zero => rfl
  | succ n ih => exact (amount_step h _).trans ih

theorem bounds_all_times {v : ι → K} {p : ι → ι → K} (h : Certified v p)
    (x : ι → K) (lo hi : K) (hx : ∀ i, lo ≤ x i ∧ x i ≤ hi) (n : Nat) :
    ∀ i, lo ≤ evolve p x n i ∧ evolve p x n i ≤ hi := by
  induction n with
  | zero => exact hx
  | succ n ih => exact fun i => ⟨step_lower h _ lo (fun j => (ih j).1) i,
                                 step_upper h _ hi (fun j => (ih j).2) i⟩


theorem nonnegative_all_times {v : ι → K} {p : ι → ι → K} (h : Certified v p)
    (x : ι → K) (hx : ∀ i, 0 ≤ x i) (n : Nat) : ∀ i, 0 ≤ evolve p x n i := by
  induction n with
  | zero => exact hx
  | succ n ih => exact step_nonnegative h _ ih

theorem quadratic_all_times {v : ι → K} {p : ι → ι → K} (h : Certified v p)
    (x : ι → K) (n : Nat) : quadratic v (evolve p x n) ≤ quadratic v x := by
  induction n with
  | zero => exact le_rfl
  | succ n ih => exact (quadratic_step h _).trans ih

theorem all_times_contract {v : ι → K} {p : ι → ι → K} (h : Certified v p)
    (x : ι → K) (lo hi : K) (hx : ∀ i, lo ≤ x i ∧ x i ≤ hi) (n : Nat) :
    amount v (evolve p x n) = amount v x ∧
    (∀ i, lo ≤ evolve p x n i ∧ evolve p x n i ≤ hi) ∧
    quadratic v (evolve p x (n + 1)) ≤ quadratic v (evolve p x n) ∧
    quadratic v (evolve p x n) ≤ quadratic v x :=
  ⟨amount_all_times h x n, bounds_all_times h x lo hi hx n,
    quadratic_step h _, quadratic_all_times h x n⟩

/-- Finite exact-rational data check. No native code reduction is used. -/
def check {n : Nat} (v : Fin n → ℚ) (p : Fin n → Fin n → ℚ) : Bool :=
  decide ((∀ i, 0 < v i) ∧ (∀ i j, 0 ≤ p i j) ∧
    (∀ i, ∑ j, p i j = 1) ∧ (∀ j, ∑ i, v i * p i j = v j))

theorem check_sound {n : Nat} {v : Fin n → ℚ} {p : Fin n → Fin n → ℚ}
    (h : check v p = true) : Certified v p := by
  simp only [check, decide_eq_true_eq] at h
  exact ⟨h.1, h.2.1, h.2.2.1, h.2.2.2⟩

theorem rational_certificate_real {n : Nat} {v : Fin n → ℚ} {p : Fin n → Fin n → ℚ}
    (h : check v p = true) : Certified (fun i => (v i : ℝ)) (fun i j => (p i j : ℝ)) := by
  have c := check_sound h
  constructor
  · intro i; exact_mod_cast c.volume_pos i
  · intro i j; exact_mod_cast c.nonnegative i j
  · intro i; exact_mod_cast c.row_sum i
  · intro j; exact_mod_cast c.invariant_volume j

end PCSReal.Transport
