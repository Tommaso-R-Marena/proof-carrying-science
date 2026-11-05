import Mathlib.Probability.Moments.SubGaussian
import Mathlib.Analysis.SpecificLimits.Basic

/-!
# Statistical gates for adaptive model selection (Mathlib library)

Probability space `(Ω, μ)`, `μ` a probability measure.

**Observations.**  At generation `k`, each candidate `c` from a finite, *pre-registered*
candidate set `cands k` is compared with the incumbent on `n k` sampled tasks.  The paired
observation for task `i` is a single bounded random variable `D k c i ∈ [a, b]` — the
difference of independently kernel-verified solve indicators (`[-1, 1]`) or of bounded costs
— so correlation between the two policies *within* a task is absorbed by pairing, and multiple
seeds of one task are averaged into that one observation (never counted as independent tasks).

**Sampling assumption.**  For fixed `k, c`, the task observations `(D k c i)_i` are mutually
independent (`iIndepFun`) with common mean `m k c` (the true improvement).

**Stopping/selection rule.**  The selected candidate `sel k ω` may depend arbitrarily on all
data (adaptive selection, any stopping time over generations); promotion at generation `k`
requires the paired mean to reach `m₀ + ε k`.

* `paired_improvement_bound` — Hoeffding bound for the paired mean (any bounded range).
* `adaptive_promotion_error_budget` — the probability that *any* generation promotes *any*
  candidate whose true improvement is `≤ 0` is at most `∑ₖ |cands k| · exp(−n ε² / 2 …)`.
* `anytime_selection_valid` — with a summable allocation (e.g. `δ / 2^(k+1)`), the probability
  of any erroneous superiority promotion, over all generations, is at most `δ`.
-/

open MeasureTheory ProbabilityTheory Real
open scoped ENNReal NNReal

namespace PCSStatistics

variable {Ω : Type*} [MeasurableSpace Ω] {μ : Measure Ω} [IsProbabilityMeasure μ]

/-- **Paired improvement bound** (Hoeffding, observations in `[a, b]`). -/
theorem paired_improvement_bound {n : ℕ} (hn : 0 < n) (D : ℕ → Ω → ℝ) (m a b : ℝ)
    (hmeas : ∀ i, Measurable (D i)) (hind : iIndepFun D μ)
    (hb : ∀ i, ∀ᵐ ω ∂μ, D i ω ∈ Set.Icc a b) (hm : ∀ i, μ[D i] = m) {ε : ℝ} (hε : 0 ≤ ε) :
    μ.real {ω | m + ε ≤ (∑ i ∈ Finset.range n, D i ω) / n} ≤
      exp (-(n * ε ^ 2) / (2 * ((‖b - a‖₊ / 2) ^ 2 : ℝ≥0))) := by
  set Y : ℕ → Ω → ℝ := fun i ω => D i ω - μ[D i]
  have hY : iIndepFun Y μ := by
    have := hind.comp (fun i (x : ℝ) => x - μ[D i]) (fun i => measurable_id.sub_const _)
    exact this
  have hsub : ∀ i < n, HasSubgaussianMGF (Y i) ((‖b - a‖₊ / 2) ^ 2) μ := fun i _ =>
    hasSubgaussianMGF_of_mem_Icc (hmeas i).aemeasurable (hb i)
  have hH := HasSubgaussianMGF.measure_sum_range_ge_le_of_iIndepFun hY hsub (ε := n * ε) (by positivity)
  have hnpos : (0 : ℝ) < n := by exact_mod_cast hn
  have hset : {ω | m + ε ≤ (∑ i ∈ Finset.range n, D i ω) / n} =
      {ω | (n : ℝ) * ε ≤ ∑ i ∈ Finset.range n, Y i ω} := by
    ext ω
    simp only [Set.mem_setOf_eq, Y, hm, Finset.sum_sub_distrib, Finset.sum_const,
      Finset.card_range, nsmul_eq_mul]
    rw [le_div_iff₀ hnpos]
    constructor <;> intro h <;> nlinarith
  rw [hset]
  refine hH.trans (le_of_eq ?_)
  congr 1
  field_simp

/-- Specialisation to solve-indicator differences in `[-1, 1]`: `exp (−n ε² / 2)`. -/
theorem paired_success_bound {n : ℕ} (hn : 0 < n) (D : ℕ → Ω → ℝ) (m : ℝ)
    (hmeas : ∀ i, Measurable (D i)) (hind : iIndepFun D μ)
    (hb : ∀ i, ∀ᵐ ω ∂μ, D i ω ∈ Set.Icc (-1) 1) (hm : ∀ i, μ[D i] = m) {ε : ℝ} (hε : 0 ≤ ε) :
    μ.real {ω | m + ε ≤ (∑ i ∈ Finset.range n, D i ω) / n} ≤ exp (-(n * ε ^ 2) / 2) := by
  have := paired_improvement_bound hn D m (-1) 1 hmeas hind hb hm hε
  refine this.trans (le_of_eq ?_)
  congr 1
  have : ((‖(1 : ℝ) - -1‖₊ / 2) ^ 2 : ℝ≥0) = 1 := by
    have h2 : ‖(1 : ℝ) - -1‖₊ = 2 := by
      ext; simp [Real.norm_eq_abs]; norm_num
    rw [h2]; norm_num
  rw [this]; simp

/-- The experiment specification of adaptive generations. -/
structure GateSpec (Ω C : Type*) [MeasurableSpace Ω] where
  n : ℕ → ℕ
  cands : ℕ → Finset C
  D : ℕ → C → ℕ → Ω → ℝ
  mean : ℕ → C → ℝ
  ε : ℕ → ℝ

namespace GateSpec

variable {C : Type*} (G : GateSpec Ω C)

/-- Paired sample mean of candidate `c` at generation `k`. -/
noncomputable def sampleMean (k : ℕ) (c : C) (ω : Ω) : ℝ :=
  (∑ i ∈ Finset.range (G.n k), G.D k c i ω) / G.n k

/-- Promotion of `c` at generation `k`. -/
def Promotes (k : ℕ) (c : C) (ω : Ω) : Prop := G.ε k ≤ G.sampleMean k c ω

/-- The hypotheses connecting the theorem to the experiment state machine: fresh, bounded,
independent paired observations for every pre-registered candidate. -/
structure Valid (μ : Measure Ω) : Prop where
  npos : ∀ k, 0 < G.n k
  epos : ∀ k, 0 ≤ G.ε k
  meas : ∀ k c i, Measurable (G.D k c i)
  indep : ∀ k c, iIndepFun (G.D k c) μ
  bounded : ∀ k c i, ∀ᵐ ω ∂μ, G.D k c i ω ∈ Set.Icc (-1) 1
  mean_eq : ∀ k c i, μ[G.D k c i] = G.mean k c

/-- Probability that generation `k` erroneously promotes some candidate. -/
theorem generation_error (hG : G.Valid μ) (k : ℕ) :
    μ {ω | ∃ c ∈ G.cands k, G.mean k c ≤ 0 ∧ G.Promotes k c ω} ≤
      ∑ c ∈ G.cands k, ENNReal.ofReal (exp (-(G.n k * G.ε k ^ 2) / 2)) := by
  have hsub : {ω | ∃ c ∈ G.cands k, G.mean k c ≤ 0 ∧ G.Promotes k c ω} ⊆
      ⋃ c ∈ G.cands k, {ω | G.mean k c ≤ 0 ∧ G.Promotes k c ω} := by
    intro ω ⟨c, hc, h⟩; exact Set.mem_biUnion hc h
  refine (measure_mono hsub).trans ((measure_biUnion_finset_le _ _).trans ?_)
  refine Finset.sum_le_sum fun c _ => ?_
  by_cases hm : G.mean k c ≤ 0
  · have hb := paired_success_bound (hG.npos k) (G.D k c) (G.mean k c) (hG.meas k c)
      (hG.indep k c) (hG.bounded k c) (hG.mean_eq k c) (ε := G.ε k - G.mean k c) (by
        have := hG.epos k; linarith)
    have hsub2 : {ω | G.mean k c ≤ 0 ∧ G.Promotes k c ω} ⊆
        {ω | G.mean k c + (G.ε k - G.mean k c) ≤ (∑ i ∈ Finset.range (G.n k), G.D k c i ω) / G.n k} := by
      intro ω ⟨_, hp⟩
      simp only [Set.mem_setOf_eq, add_sub_cancel]
      exact hp
    refine (measure_mono hsub2).trans ?_
    rw [← ofReal_measureReal]
    refine ENNReal.ofReal_le_ofReal (hb.trans ?_)
    apply exp_le_exp.mpr
    have hn : (0 : ℝ) ≤ G.n k := by positivity
    have he := hG.epos k
    have : G.ε k ^ 2 ≤ (G.ε k - G.mean k c) ^ 2 := by nlinarith
    have := mul_le_mul_of_nonneg_left this hn
    linarith
  · have : {ω | G.mean k c ≤ 0 ∧ G.Promotes k c ω} = ∅ := by
      ext ω; simp only [Set.mem_setOf_eq, Set.mem_empty_iff_false, iff_false, not_and]
      intro h; exact absurd h hm
    rw [this, measure_empty]; exact zero_le _

/-- **Adaptive promotion error budget.** Over all generations, the probability that any
pre-registered candidate with non-positive true improvement is promoted is at most the sum of
the per-generation Hoeffding terms. -/
theorem adaptive_promotion_error_budget (hG : G.Valid μ) :
    μ {ω | ∃ k, ∃ c ∈ G.cands k, G.mean k c ≤ 0 ∧ G.Promotes k c ω} ≤
      ∑' k, ∑ c ∈ G.cands k, ENNReal.ofReal (exp (-(G.n k * G.ε k ^ 2) / 2)) := by
  have hsub : {ω | ∃ k, ∃ c ∈ G.cands k, G.mean k c ≤ 0 ∧ G.Promotes k c ω} ⊆
      ⋃ k, {ω | ∃ c ∈ G.cands k, G.mean k c ≤ 0 ∧ G.Promotes k c ω} := by
    intro ω ⟨k, h⟩; exact Set.mem_iUnion.2 ⟨k, h⟩
  refine (measure_mono hsub).trans ((measure_iUnion_le _).trans ?_)
  exact ENNReal.tsum_le_tsum fun k => G.generation_error hG k

/-- **Anytime-valid selection.** If the per-generation allocation `δₖ` bounds the Hoeffding
terms and `∑ δₖ ≤ δ`, then for *every* adaptive selection rule the probability of any
erroneous superiority promotion is at most `δ`. -/
theorem anytime_selection_valid (hG : G.Valid μ) (δk : ℕ → ℝ≥0∞) (δ : ℝ≥0∞)
    (halloc : ∀ k, ∑ c ∈ G.cands k, ENNReal.ofReal (exp (-(G.n k * G.ε k ^ 2) / 2)) ≤ δk k)
    (hsum : ∑' k, δk k ≤ δ) (sel : ℕ → Ω → C) (hsel : ∀ k ω, sel k ω ∈ G.cands k) :
    μ {ω | ∃ k, G.mean k (sel k ω) ≤ 0 ∧ G.Promotes k (sel k ω) ω} ≤ δ := by
  have hsub : {ω | ∃ k, G.mean k (sel k ω) ≤ 0 ∧ G.Promotes k (sel k ω) ω} ⊆
      {ω | ∃ k, ∃ c ∈ G.cands k, G.mean k c ≤ 0 ∧ G.Promotes k c ω} := by
    intro ω ⟨k, h⟩; exact ⟨k, sel k ω, hsel k ω, h⟩
  refine (measure_mono hsub).trans ((G.adaptive_promotion_error_budget hG).trans ?_)
  exact (ENNReal.tsum_le_tsum halloc).trans hsum

end GateSpec

/-- The geometric allocation `δ / 2^(k+1)` sums to `δ`. -/
theorem geometric_allocation (δ : ℝ≥0∞) : ∑' k : ℕ, δ / 2 ^ (k + 1) = δ := by
  simp_rw [div_eq_mul_inv, ENNReal.tsum_mul_left]
  have : ∑' k : ℕ, ((2 : ℝ≥0∞) ^ (k + 1))⁻¹ = 1 := by
    simp_rw [ENNReal.inv_pow]
    rw [ENNReal.tsum_geometric_add_one, ENNReal.one_sub_inv_two, inv_inv]
    exact ENNReal.inv_mul_cancel (by norm_num) (by norm_num)
  rw [this, mul_one]

/-- Threshold choice making the Hoeffding term at most `δₖ` for `|cands k|` candidates:
`ε = sqrt (2 log (|C| / δₖ) / n)`. -/
theorem threshold_sufficient (n : ℕ) (hn : 0 < n) (N : ℕ) (hN : 0 < N) (δk : ℝ) (hδ : 0 < δk)
    (hδ1 : δk ≤ N) :
    (N : ℝ) * exp (-(n * (Real.sqrt (2 * Real.log (N / δk) / n)) ^ 2) / 2) ≤ δk := by
  have hnr : (0 : ℝ) < n := by exact_mod_cast hn
  have hNr : (0 : ℝ) < N := by exact_mod_cast hN
  have hlog : 0 ≤ Real.log (N / δk) := Real.log_nonneg (by rw [le_div_iff₀ hδ]; linarith)
  rw [Real.sq_sqrt (by positivity)]
  have : -(n * (2 * Real.log (N / δk) / n)) / 2 = -Real.log (N / δk) := by field_simp
  rw [this, Real.exp_neg, Real.exp_log (by positivity)]
  rw [inv_div, mul_div_assoc', mul_comm, mul_div_assoc, div_self hNr.ne', mul_one]

end PCSStatistics
