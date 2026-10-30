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
set_option format.width 1000000
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

theorem uniform_error_exclusion (x : ι → κ → ℝ) (y : ι → ℝ) (floor ε : ℝ)
    (hl : ∀ c, floor ≤ loss x y c) (he : 0 ≤ ε)
    (hg : (Fintype.card ι : ℝ) * ε ^ 2 < floor) :
    ¬ (∃ c, ∀ i, |y i - prediction x c i| ≤ ε) := by
  rintro ⟨c, hc⟩
  have hs : loss x y c ≤ (Fintype.card ι : ℝ) * ε ^ 2 := by
    calc
      _ ≤ ∑ _i : ι, ε ^ 2 := by
        apply sum_le_sum
        intro i _
        have hh := (sq_le_sq₀ (abs_nonneg (y i - prediction x c i)) he).2 (hc i)
        simpa only [sq_abs] using hh
      _ = _ := by simp
  have hm := hl c
  linarith

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

theorem dual_gain_lower_bound (x : ι → κ → ℝ) (q a : κ → ℝ)
    (ha : ∀ i, |prediction x a i| ≤ 1) (v : ι → ℝ) (hv : Reproduces x v q) :
    dot q a ≤ ∑ i, |v i| := by
  have hh := response_perturbation_bound v (fun _ => 0) (prediction x a) 1
    (by simpa using ha)
  rw [reproduction_prediction x v q a hv] at hh
  have hb : |dot q a| ≤ ∑ i, |v i| := by simpa [dot] using hh
  exact (le_abs_self _).trans hb

theorem minimax_weights_optimal (x : ι → κ → ℝ) (w : ι → ℝ) (q a : κ → ℝ)
    (ha : ∀ i, |prediction x a i| ≤ 1) (heq : dot q a = ∑ i, |w i|) :
    ∀ v, Reproduces x v q → (∑ i, |w i|) ≤ ∑ i, |v i| := by
  intro v hv
  rw [← heq]
  exact dual_gain_lower_bound x q a ha v hv

theorem minimax_radius_lower_bound (x : ι → κ → ℝ) (y w : ι → ℝ) (q a : κ → ℝ)
    (ha : ∀ i, |prediction x a i| ≤ 1) (heq : dot q a = ∑ i, |w i|)
    (ε radius : ℝ) (he : 0 ≤ ε) (v : ι → ℝ) (hv : Reproduces x v q)
    (hr : ∀ z, (∀ i, |z i - y i| ≤ ε) → |dot v z - dot v y| ≤ radius) :
    ε * ∑ i, |w i| ≤ radius := by
  have hl := minimax_weights_optimal x w q a ha heq v hv
  have hu := (sharp_radius_iff v y ε radius he).1 hr
  exact (mul_le_mul_of_nonneg_left hl he).trans hu

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

def minimaxCheck {n p : Nat} (x : Fin n → Fin p → ℚ) (w : Fin n → ℚ)
    (q a : Fin p → ℚ) (gain : ℚ) : Bool :=
  decide (Reproduces x w q ∧ (∀ i, |prediction x a i| ≤ 1) ∧
    dot q a = gain ∧ (∑ i, |w i|) = gain)

theorem minimax_check_sound {n p : Nat} {x : Fin n → Fin p → ℚ} {w : Fin n → ℚ}
    {q a : Fin p → ℚ} {gain : ℚ} (h : minimaxCheck x w q a gain = true) :
    Reproduces (fun i j => (x i j : ℝ)) (fun i => (w i : ℝ)) (fun j => (q j : ℝ)) ∧
    (∀ i, |prediction (fun i j => (x i j : ℝ)) (fun j => (a j : ℝ)) i| ≤ 1) ∧
    dot (fun j => (q j : ℝ)) (fun j => (a j : ℝ)) = ∑ i, |(w i : ℝ)| := by
  have hq : Reproduces x w q ∧ (∀ i, |prediction x a i| ≤ 1) ∧
      dot q a = gain ∧ (∑ i, |w i|) = gain := of_decide_eq_true h
  refine ⟨?_, ?_, ?_⟩
  · intro j
    have hj := congrArg (fun q : ℚ => (q : ℝ)) (hq.1 j)
    simpa only [Rat.cast_sum, Rat.cast_mul] using hj
  · intro i
    have hi : ((|prediction x a i| : ℚ) : ℝ) ≤ 1 := by exact_mod_cast hq.2.1 i
    simpa only [prediction, Rat.cast_abs, Rat.cast_sum, Rat.cast_mul] using hi
  · have heq : dot q a = ∑ i, |w i| := hq.2.2.1.trans hq.2.2.2.symm
    have hc := congrArg (fun q : ℚ => (q : ℝ)) heq
    simpa only [dot, Rat.cast_sum, Rat.cast_mul, Rat.cast_abs] using hc

omit [Fintype ι] in
theorem any_estimator_radius_lower_bound (x : ι → κ → ℝ) (q a : κ → ℝ)
    (ha : ∀ i, |prediction x a i| ≤ 1) (ε radius : ℝ) (he : 0 ≤ ε)
    (estimator : (ι → ℝ) → ℝ)
    (hg : ∀ truth observed, (∀ i, |observed i - prediction x truth i| ≤ ε) →
      |estimator observed - dot q truth| ≤ radius) : ε * dot q a ≤ radius := by
  have hs (s : ℝ) (i : ι) : prediction x (fun j => s * a j) i =
      s * prediction x a i := by
    simp only [prediction, mul_sum]
    apply sum_congr rfl
    intro j _
    ring
  have hq (s : ℝ) : dot q (fun j => s * a j) = s * dot q a := by
    simp only [dot, mul_sum]
    apply sum_congr rfl
    intro j _
    ring
  have hm (s : ℝ) (hh : |s| ≤ ε) :
      ∀ i, |(0 : ℝ) - prediction x (fun j => s * a j) i| ≤ ε := by
    intro i
    rw [hs, zero_sub, abs_neg, abs_mul]
    calc
      _ ≤ |s| * 1 := mul_le_mul_of_nonneg_left (ha i) (abs_nonneg s)
      _ ≤ ε := by simpa using hh
  have hp := hg (fun j => ε * a j) (fun _ => 0)
    (hm ε (by simp [abs_of_nonneg he]))
  have hn := hg (fun j => -ε * a j) (fun _ => 0)
    (hm (-ε) (by simp [abs_of_nonneg he]))
  rw [hq] at hp hn
  have hp' := (abs_le.mp hp).1
  have hn' := (abs_le.mp hn).2
  linarith

theorem minimax_over_all_estimators_iff (x : ι → κ → ℝ) (w : ι → ℝ) (q a : κ → ℝ)
    (hw : Reproduces x w q) (ha : ∀ i, |prediction x a i| ≤ 1)
    (heq : dot q a = ∑ i, |w i|) (ε radius : ℝ) (he : 0 ≤ ε) :
    (∃ estimator : (ι → ℝ) → ℝ,
      ∀ truth observed, (∀ i, |observed i - prediction x truth i| ≤ ε) →
        |estimator observed - dot q truth| ≤ radius) ↔
      ε * ∑ i, |w i| ≤ radius := by
  constructor
  · rintro ⟨estimator, hg⟩
    rw [← heq]
    exact any_estimator_radius_lower_bound x q a ha ε radius he estimator hg
  · intro hr
    refine ⟨fun observed => dot w observed, ?_⟩
    intro truth observed hm
    exact (physical_enclosure x observed w q truth ε hw hm).trans hr

end PCSReal.Calibration
