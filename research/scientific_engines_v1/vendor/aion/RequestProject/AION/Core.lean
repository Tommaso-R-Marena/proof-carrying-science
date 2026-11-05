module

public import Mathlib

/-!
# AION core: jump models, hitting probabilities, generators

A *jump model* on a (possibly countably infinite) state type `S` has finitely many
transition channels `r : ι` (the reactions).  Channel `r` fires at rate
`rate r x ≥ 0` in state `x` and moves the state to `next r x`.
This is exactly the data of a continuous-time Markov chain whose (formal) generator is

  `(L g)(x) = ∑ r, rate r x * (g (next r x) - g x)`.

## What "hitting probability" means here

For a target set `B` and a taboo (avoid) set `A`, `hitN M A B n x` is defined by
first-step analysis of the embedded jump chain: the probability that, starting
from `x`, the jump chain enters `B` within `n` jumps without first entering `A`.
States with total rate `0` (not in `B`) are absorbing and never reach `B`.
`hitProb M A B x = ⨆ n, hitN M A B n x` is the probability of *ever* reaching
`B` before `A`.

For the minimal (possibly explosive) continuous-time chain this is
`P_x(τ_B < τ_A, τ_B < ζ)` with `ζ` the explosion time, because the event depends
only on the sequence of visited states.  Hence no nonexplosion assumption is
needed for the hitting-probability theorems.  The path-space reading of `hitN`
(an explicit sum over finite reaction sequences) is proved in `AION.PathSemantics`.
-/

@[expose] public section

open scoped BigOperators
open Classical

namespace AION

/-- A finite-channel jump model on state type `S`. -/
structure JumpModel (S : Type*) (ι : Type*) [Fintype ι] where
  /-- propensity / rate of channel `r` at state `x` -/
  rate : ι → S → ℝ
  rate_nonneg : ∀ r x, 0 ≤ rate r x
  /-- target state after channel `r` fires at `x` -/
  next : ι → S → S

namespace JumpModel

variable {S : Type*} {ι : Type*} [Fintype ι] (M : JumpModel S ι)

/-- Total exit rate. -/
noncomputable def totalRate (x : S) : ℝ := ∑ r, M.rate r x

lemma totalRate_nonneg (x : S) : 0 ≤ M.totalRate x :=
  Finset.sum_nonneg (fun r _ => M.rate_nonneg r x)

/-- The (formal) generator applied to `g` at `x`. -/
noncomputable def gen (g : S → ℝ) (x : S) : ℝ :=
  ∑ r, M.rate r x * (g (M.next r x) - g x)

/-- Unnormalised one-step flux `∑ r, rate r x * g (next r x)`. -/
noncomputable def flux (g : S → ℝ) (x : S) : ℝ :=
  ∑ r, M.rate r x * g (M.next r x)

lemma gen_eq_flux_sub (g : S → ℝ) (x : S) :
    M.gen g x = M.flux g x - M.totalRate x * g x := by
  simp only [gen, flux, totalRate, mul_sub, Finset.sum_sub_distrib, Finset.sum_mul]

lemma flux_mono {f g : S → ℝ} (h : ∀ y, f y ≤ g y) (x : S) : M.flux f x ≤ M.flux g x :=
  Finset.sum_le_sum (fun r _ => mul_le_mul_of_nonneg_left (h _) (M.rate_nonneg r x))

lemma flux_nonneg {f : S → ℝ} (h : ∀ y, 0 ≤ f y) (x : S) : 0 ≤ M.flux f x :=
  Finset.sum_nonneg (fun r _ => mul_nonneg (M.rate_nonneg r x) (h _))

lemma flux_add (f g : S → ℝ) (x : S) :
    M.flux (fun y => f y + g y) x = M.flux f x + M.flux g x := by
  simp only [flux, mul_add, Finset.sum_add_distrib]

lemma flux_smul (c : ℝ) (f : S → ℝ) (x : S) :
    M.flux (fun y => c * f y) x = c * M.flux f x := by
  simp only [flux, Finset.mul_sum]; exact Finset.sum_congr rfl (fun _ _ => by ring)

lemma flux_const (c : ℝ) (x : S) : M.flux (fun _ => c) x = c * M.totalRate x := by
  simp only [flux, totalRate, Finset.mul_sum]; exact Finset.sum_congr rfl (fun _ _ => by ring)

/-- Probability of reaching `B` within `n` jumps without first entering `A`
(first-step analysis of the embedded jump chain).  `B` takes priority over `A`. -/
noncomputable def hitN (A B : Set S) : ℕ → S → ℝ
  | 0, x => if x ∈ B then 1 else 0
  | n + 1, x =>
      if x ∈ B then 1
      else if x ∈ A then 0
      else if M.totalRate x = 0 then 0
      else M.flux (hitN A B n) x / M.totalRate x

variable {M}

lemma hitN_nonneg (A B : Set S) : ∀ n x, 0 ≤ M.hitN A B n x
  | 0, x => by unfold hitN; split_ifs <;> norm_num
  | n + 1, x => by
      unfold hitN
      split_ifs
      · norm_num
      · norm_num
      · norm_num
      · exact div_nonneg (M.flux_nonneg (hitN_nonneg A B n) x) (M.totalRate_nonneg x)

lemma hitN_le_one (A B : Set S) : ∀ n x, M.hitN A B n x ≤ 1
  | 0, x => by unfold hitN; split_ifs <;> norm_num
  | n + 1, x => by
      unfold hitN
      split_ifs with h1 h2 h3
      · norm_num
      · norm_num
      · norm_num
      · have hpos : 0 < M.totalRate x := lt_of_le_of_ne (M.totalRate_nonneg x) (Ne.symm h3)
        rw [div_le_one hpos]
        calc M.flux (M.hitN A B n) x ≤ M.flux (fun _ => (1:ℝ)) x :=
              M.flux_mono (hitN_le_one A B n) x
          _ = M.totalRate x := by rw [flux_const]; ring

lemma hitN_mono_succ (A B : Set S) : ∀ n x, M.hitN A B n x ≤ M.hitN A B (n + 1) x
  | 0, x => by
      rw [hitN, hitN]
      split_ifs
      · exact le_rfl
      · exact le_rfl
      · exact le_rfl
      · exact div_nonneg (M.flux_nonneg (hitN_nonneg A B 0) x) (M.totalRate_nonneg x)
  | n + 1, x => by
      rw [hitN, hitN]
      split_ifs with h1 h2 h3
      · exact le_rfl
      · exact le_rfl
      · exact le_rfl
      · have hpos : 0 < M.totalRate x := lt_of_le_of_ne (M.totalRate_nonneg x) (Ne.symm h3)
        exact div_le_div_of_nonneg_right (M.flux_mono (hitN_mono_succ A B n) x) hpos.le

lemma hitN_mono (A B : Set S) (x : S) : Monotone (fun n => M.hitN A B n x) :=
  monotone_nat_of_le_succ (fun n => hitN_mono_succ A B n x)

variable (M)

/-- Probability that the jump chain started at `x` ever enters `B` before `A`. -/
noncomputable def hitProb (A B : Set S) (x : S) : ℝ := ⨆ n, M.hitN A B n x

variable {M}

lemma hitN_bddAbove (A B : Set S) (x : S) : BddAbove (Set.range fun n => M.hitN A B n x) :=
  ⟨1, by rintro _ ⟨n, rfl⟩; exact hitN_le_one A B n x⟩

lemma hitN_le_hitProb (A B : Set S) (n : ℕ) (x : S) : M.hitN A B n x ≤ M.hitProb A B x :=
  le_ciSup (hitN_bddAbove A B x) n

lemma hitProb_nonneg (A B : Set S) (x : S) : 0 ≤ M.hitProb A B x :=
  le_trans (hitN_nonneg A B 0 x) (hitN_le_hitProb A B 0 x)

lemma hitProb_le_one (A B : Set S) (x : S) : M.hitProb A B x ≤ 1 :=
  ciSup_le (fun n => hitN_le_one A B n x)

lemma hitProb_le_of_forall {A B : Set S} {x : S} {c : ℝ} (h : ∀ n, M.hitN A B n x ≤ c) :
    M.hitProb A B x ≤ c := ciSup_le h

lemma tendsto_hitN (A B : Set S) (x : S) :
    Filter.Tendsto (fun n => M.hitN A B n x) Filter.atTop (nhds (M.hitProb A B x)) :=
  tendsto_atTop_ciSup (hitN_mono A B x) (hitN_bddAbove A B x)

end JumpModel
end AION
