import Mathlib.Data.Real.Basic
import Mathlib.Data.Rat.BigOperators
import Mathlib.Algebra.Order.BigOperators.Ring.Finset
import Mathlib.Tactic.Linarith
import Mathlib.Tactic.NormNum
import Mathlib.Tactic.Ring

/-! Exact finite regression and sharp response-perturbation certificates.
These results concern declared numeric arrays. They do not establish a physical
model, measurement precision, predictor accuracy, or statistical coverage. -/
set_option autoImplicit false
namespace PCSReal.Calibration
open Finset

variable {ι κ : Type*} [Fintype ι] [Fintype κ]

def prediction {K : Type*} [Semiring K] (x : ι → κ → K) (b : κ → K) (i : ι) : K :=
  ∑ j, x i j * b j

def loss {K : Type*} [Ring K] (x : ι → κ → K) (y : ι → K) (b : κ → K) : K :=
  ∑ i, (y i - prediction x b i) ^ 2

abbrev Normal {K : Type*} [Ring K] (x : ι → κ → K) (y : ι → K) (b : κ → K) : Prop :=
  ∀ j, ∑ i, x i j * (y i - prediction x b i) = 0

def dot {K : Type*} [Semiring K] (w y : ι → K) : K := ∑ i, w i * y i

abbrev Reproduces {K : Type*} [Semiring K] (x : ι → κ → K) (w : ι → K) (q : κ → K) : Prop :=
  ∀ j, ∑ i, w i * x i j = q j

theorem normal_orthogonal (x : ι → κ → ℝ) (y : ι → ℝ) (b c : κ → ℝ)
    (h : Normal x y b) :
    ∑ i, (y i - prediction x b i) * (prediction x c i - prediction x b i) = 0 := by
  have hp (i : ι) : prediction x c i - prediction x b i =
      ∑ j, x i j * (c j - b j) := by
    simp [prediction, mul_sub, sum_sub_distrib]
  simp_rw [hp, mul_sum]
  rw [sum_comm]
  calc
    _ = ∑ j, (c j - b j) * ∑ i, x i j * (y i - prediction x b i) := by
      apply sum_congr rfl
      intro j _
      rw [mul_sum]
      apply sum_congr rfl
      intro i _
      ring
    _ = 0 := by simp [h]

theorem loss_decomposition (x : ι → κ → ℝ) (y : ι → ℝ) (b c : κ → ℝ)
    (h : Normal x y b) :
    loss x y c = loss x y b + ∑ i, (prediction x c i - prediction x b i) ^ 2 := by
  have he : loss x y c = loss x y b +
      (∑ i, (prediction x c i - prediction x b i) ^ 2) -
      2 * ∑ i, (y i - prediction x b i) * (prediction x c i - prediction x b i) := by
    simp only [loss, mul_sum, ← sum_add_distrib, ← sum_sub_distrib]
    apply sum_congr rfl
    intro i _
    ring
  rw [normal_orthogonal x y b c h, mul_zero, sub_zero] at he
  exact he

theorem global_minimum (x : ι → κ → ℝ) (y : ι → ℝ) (b : κ → ℝ)
    (h : Normal x y b) : ∀ c, loss x y b ≤ loss x y c := by
  intro c
  rw [loss_decomposition x y b c h]
  exact le_add_of_nonneg_right (sum_nonneg (fun _ _ => sq_nonneg _))

theorem model_exclusion (x : ι → κ → ℝ) (y : ι → ℝ) (b : κ → ℝ)
    (h : Normal x y b) (threshold : ℝ) (ht : threshold < loss x y b) :
    ∀ c, threshold < loss x y c := by
  intro c
  exact ht.trans_le (global_minimum x y b h c)

theorem reproduction_prediction (x : ι → κ → ℝ) (w : ι → ℝ) (q b : κ → ℝ)
    (h : Reproduces x w q) : dot w (prediction x b) = dot q b := by
  simp only [dot, prediction, mul_sum]
  rw [sum_comm]
  apply sum_congr rfl
  intro j _
  calc
    _ = (∑ i, w i * x i j) * b j := by
      rw [sum_mul]
      apply sum_congr rfl
      intro i _
      ring
    _ = q j * b j := by rw [h j]

theorem dual_prediction (x : ι → κ → ℝ) (y w : ι → ℝ) (q b d : κ → ℝ)
    (hn : Normal x y b) (hr : Reproduces x w q)
    (hs : ∀ i, w i = prediction x d i) : dot w y = dot q b := by
  have hz : ∑ i, w i * (y i - prediction x b i) = 0 := by
    simp_rw [hs, prediction, sum_mul]
    rw [sum_comm]
    calc
      _ = ∑ j, d j * ∑ i, x i j * (y i - prediction x b i) := by
        apply sum_congr rfl
        intro j _
        rw [mul_sum]
        apply sum_congr rfl
        intro i _
        dsimp [prediction]
        ring
      _ = 0 := by simp [hn]
  have hd : dot w y - dot w (prediction x b) = 0 := by
    simpa only [dot, ← sum_sub_distrib, ← mul_sub] using hz
  rw [reproduction_prediction x w q b hr] at hd
  linarith

theorem response_perturbation_bound (w y z : ι → ℝ) (ε : ℝ)
    (h : ∀ i, |z i - y i| ≤ ε) :
    |dot w z - dot w y| ≤ ε * ∑ i, |w i| := by
  have hd : dot w z - dot w y = ∑ i, w i * (z i - y i) := by
    simp only [dot, mul_sub, sum_sub_distrib]
  rw [hd]
  calc
    _ ≤ ∑ i, |w i * (z i - y i)| := abs_sum_le_sum_abs _ _
    _ ≤ ∑ i, |w i| * ε := by
      apply sum_le_sum
      intro i _
      rw [abs_mul]
      exact mul_le_mul_of_nonneg_left (h i) (abs_nonneg _)
    _ = ε * ∑ i, |w i| := by simp [mul_sum, mul_comm]

theorem sharp_perturbation_attained (w y : ι → ℝ) (ε : ℝ) (he : 0 ≤ ε) :
    ∃ z, (∀ i, |z i - y i| ≤ ε) ∧
      dot w z - dot w y = ε * ∑ i, |w i| := by
  let z := fun i => y i + if 0 ≤ w i then ε else -ε
  refine ⟨z, ?_, ?_⟩
  · intro i
    dsimp [z]
    split_ifs <;> simp [abs_of_nonneg he]
  · simp only [dot, ← sum_sub_distrib, mul_sum]
    apply sum_congr rfl
    intro i _
    dsimp [z]
    split_ifs with hi
    · rw [abs_of_nonneg hi]; ring
    · rw [abs_of_neg (lt_of_not_ge hi)]; ring

theorem sharp_radius_iff (w y : ι → ℝ) (ε radius : ℝ) (he : 0 ≤ ε) :
    (∀ z, (∀ i, |z i - y i| ≤ ε) → |dot w z - dot w y| ≤ radius) ↔
      ε * ∑ i, |w i| ≤ radius := by
  constructor
  · intro h
    obtain ⟨z, hz, hv⟩ := sharp_perturbation_attained w y ε he
    have hh := h z hz
    rw [hv, abs_of_nonneg (mul_nonneg he (sum_nonneg (fun _ _ => abs_nonneg _)))] at hh
    exact hh
  · intro h z hz
    exact (response_perturbation_bound w y z ε hz).trans h

theorem physical_enclosure (x : ι → κ → ℝ) (y w : ι → ℝ) (q truth : κ → ℝ)
    (ε : ℝ) (hr : Reproduces x w q)
    (hm : ∀ i, |y i - prediction x truth i| ≤ ε) :
    |dot w y - dot q truth| ≤ ε * ∑ i, |w i| := by
  rw [← reproduction_prediction x w q truth hr]
  exact response_perturbation_bound w (prediction x truth) y ε hm

def fitCheck {n p : Nat} (x : Fin n → Fin p → ℚ) (y : Fin n → ℚ) (b : Fin p → ℚ) : Bool :=
  decide (Normal x y b)

theorem fit_check_sound {n p : Nat} {x : Fin n → Fin p → ℚ}
    {y : Fin n → ℚ} {b : Fin p → ℚ} (h : fitCheck x y b = true) :
    Normal (fun i j => (x i j : ℝ)) (fun i => (y i : ℝ)) (fun j => (b j : ℝ)) := by
  have hq : Normal x y b := of_decide_eq_true h
  intro j
  have hj := congrArg (fun q : ℚ => (q : ℝ)) (hq j)
  simpa only [prediction, Rat.cast_sum, Rat.cast_mul, Rat.cast_sub, Rat.cast_zero] using hj

theorem cast_loss {n p : Nat} (x : Fin n → Fin p → ℚ)
    (y : Fin n → ℚ) (b : Fin p → ℚ) :
    ((loss x y b : ℚ) : ℝ) =
      loss (fun i j => (x i j : ℝ)) (fun i => (y i : ℝ)) (fun j => (b j : ℝ)) := by
  simp only [loss, prediction, Rat.cast_sum, Rat.cast_pow, Rat.cast_sub, Rat.cast_mul]

def dualCheck {n p : Nat} (x : Fin n → Fin p → ℚ) (w : Fin n → ℚ)
    (q d : Fin p → ℚ) : Bool :=
  decide (Reproduces x w q ∧ ∀ i, w i = prediction x d i)

theorem dual_check_sound {n p : Nat} {x : Fin n → Fin p → ℚ} {w : Fin n → ℚ}
    {q d : Fin p → ℚ} (h : dualCheck x w q d = true) :
    Reproduces (fun i j => (x i j : ℝ)) (fun i => (w i : ℝ)) (fun j => (q j : ℝ)) ∧
      ∀ i, (w i : ℝ) = prediction (fun i j => (x i j : ℝ)) (fun j => (d j : ℝ)) i := by
  have hq : Reproduces x w q ∧ ∀ i, w i = prediction x d i := of_decide_eq_true h
  constructor
  · intro j
    have hj := congrArg (fun q : ℚ => (q : ℝ)) (hq.1 j)
    simpa only [Rat.cast_sum, Rat.cast_mul] using hj
  · intro i
    have hi := congrArg (fun q : ℚ => (q : ℝ)) (hq.2 i)
    simpa only [prediction, Rat.cast_sum, Rat.cast_mul] using hi

end PCSReal.Calibration
