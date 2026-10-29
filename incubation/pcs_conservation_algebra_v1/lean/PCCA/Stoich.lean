import Mathlib.Algebra.Order.BigOperators.Ring.Finset
import Mathlib.Data.Rat.BigOperators
import Mathlib.Data.Rat.Cast.Order
import Mathlib.Data.Real.Basic
import Mathlib.Tactic.Ring

/-!
# Proof-carrying conservation algebra

Universal stoichiometric conservation laws for finite reaction networks.

A row vector `γ` of the stoichiometric matrix `S` is a conservation law when
`γ · S = 0`. Every stoichiometric update `x ↦ x + S ξ` then preserves the
linear pool `γ · x`, for an arbitrary firing vector `ξ` and for every natural
number of successive updates.

These are exact matrix theorems over any field. Continuum ODE flows,
floating-point arithmetic, empirical biology and package authority are not
inferred.
-/
set_option autoImplicit false
set_option linter.unusedSectionVars false

namespace PCCA.Stoich

open Finset

variable {σ ρ K : Type*} [Fintype σ] [Fintype ρ] [Field K]

/-- Stoichiometric change of species `s` under reaction `r`. -/
abbrev Matrix (σ ρ K : Type*) := σ → ρ → K

/-- Linear conservation pool evaluated on a concentration state. -/
def pool (γ state : σ → K) : K := ∑ s, γ s * state s

/-- `γ` is a conservation law for `S` when it annihilates every reaction column. -/
def ConservationLaw (γ : σ → K) (S : Matrix σ ρ K) : Prop :=
  ∀ r, ∑ s, γ s * S s r = 0

/-- One stoichiometric firing: `x' = x + S ξ`. -/
def fire (S : Matrix σ ρ K) (ξ : ρ → K) (x : σ → K) (s : σ) : K :=
  x s + ∑ r, S s r * ξ r

/-- Iterate stoichiometric firings. Each step may use a different firing vector. -/
def evolve (S : Matrix σ ρ K) (ξs : Nat → ρ → K) (initial : σ → K) : Nat → σ → K
  | 0 => initial
  | n + 1 => fire S (ξs n) (evolve S ξs initial n)

/-- Uniform firing schedule (same ξ every step). -/
def evolveUniform (S : Matrix σ ρ K) (ξ : ρ → K) (initial : σ → K) : Nat → σ → K :=
  evolve S (fun _ => ξ) initial

/-- One stoichiometric step preserves every conservation pool. -/
theorem conserved_step (γ : σ → K) (S : Matrix σ ρ K) (h : ConservationLaw γ S)
    (ξ : ρ → K) (x : σ → K) : pool γ (fire S ξ x) = pool γ x := by
  unfold pool fire
  have hsum : (∑ s, γ s * ∑ r, S s r * ξ r) = 0 := by
    simp_rw [mul_sum]
    rw [sum_comm]
    apply sum_eq_zero
    intro r _
    calc (∑ s, γ s * (S s r * ξ r))
        = (∑ s, γ s * S s r) * ξ r := by
            rw [sum_mul]; apply sum_congr rfl; intro s _; ring
        _ = 0 * ξ r := by rw [h r]
        _ = 0 := by simp
  calc (∑ s, γ s * (x s + ∑ r, S s r * ξ r))
      = (∑ s, γ s * x s) + (∑ s, γ s * ∑ r, S s r * ξ r) := by
          simp_rw [mul_add, sum_add_distrib]
      _ = (∑ s, γ s * x s) + 0 := by rw [hsum]
      _ = ∑ s, γ s * x s := by simp

/-- Every finite sequence of stoichiometric firings preserves the pool. -/
theorem conserved_all_times (γ : σ → K) (S : Matrix σ ρ K) (h : ConservationLaw γ S)
    (ξs : Nat → ρ → K) (x : σ → K) (n : Nat) :
    pool γ (evolve S ξs x n) = pool γ x := by
  induction n with
  | zero => rfl
  | succ n ih =>
    calc pool γ (evolve S ξs x (n + 1))
        = pool γ (fire S (ξs n) (evolve S ξs x n)) := rfl
      _ = pool γ (evolve S ξs x n) := conserved_step γ S h (ξs n) _
      _ = pool γ x := ih

theorem conserved_uniform (γ : σ → K) (S : Matrix σ ρ K) (h : ConservationLaw γ S)
    (ξ : ρ → K) (x : σ → K) (n : Nat) :
    pool γ (evolveUniform S ξ x n) = pool γ x :=
  conserved_all_times γ S h (fun _ => ξ) x n

/-- Zero firing leaves the state unchanged. -/
theorem fire_zero (S : Matrix σ ρ K) (x : σ → K) (s : σ) :
    fire S (fun _ => 0) x s = x s := by
  simp [fire]

/-- The zero pool is always a conservation law. -/
theorem conservation_zero (S : Matrix σ ρ K) : ConservationLaw (fun _ : σ => (0 : K)) S := by
  intro r; simp

theorem conservation_add (γ δ : σ → K) (S : Matrix σ ρ K)
    (hγ : ConservationLaw γ S) (hδ : ConservationLaw δ S) :
    ConservationLaw (fun s => γ s + δ s) S := by
  intro r
  calc (∑ s, (γ s + δ s) * S s r)
      = (∑ s, γ s * S s r) + (∑ s, δ s * S s r) := by
          simp_rw [add_mul, sum_add_distrib]
      _ = 0 + 0 := by rw [hγ r, hδ r]
      _ = 0 := by simp

theorem conservation_smul (a : K) (γ : σ → K) (S : Matrix σ ρ K)
    (hγ : ConservationLaw γ S) : ConservationLaw (fun s => a * γ s) S := by
  intro r
  calc (∑ s, (a * γ s) * S s r)
      = a * ∑ s, γ s * S s r := by
          simp_rw [mul_assoc, ← mul_sum]
      _ = a * 0 := by rw [hγ r]
      _ = 0 := by simp

/-- Exact rational finite check: every reaction column is annihilated by γ. -/
def check {nSpec nRxn : Nat}
    (γ : Fin nSpec → ℚ) (S : Fin nSpec → Fin nRxn → ℚ) : Bool :=
  decide (∀ r, ∑ s, γ s * S s r = 0)

theorem check_sound {nSpec nRxn : Nat}
    {γ : Fin nSpec → ℚ} {S : Fin nSpec → Fin nRxn → ℚ}
    (h : check γ S = true) : ConservationLaw γ S := by
  simp only [check, decide_eq_true_eq] at h
  exact h

theorem rational_certificate_real {nSpec nRxn : Nat}
    {γ : Fin nSpec → ℚ} {S : Fin nSpec → Fin nRxn → ℚ}
    (h : check γ S = true) :
    ConservationLaw (fun s => (γ s : ℝ)) (fun s r => (S s r : ℝ)) := by
  have c := check_sound h
  intro r
  simpa using (by exact_mod_cast (c r) : (∑ s : Fin nSpec, (γ s : ℝ) * (S s r : ℝ)) = 0)

/-- Finite trajectory: consecutive states differ by declared stoichiometric fires. -/
def TrajectorySound {nSpec nRxn nSteps : Nat}
    (S : Fin nSpec → Fin nRxn → ℚ)
    (ξs : Fin nSteps → Fin nRxn → ℚ)
    (xs : Fin (nSteps + 1) → Fin nSpec → ℚ) : Prop :=
  ∀ k : Fin nSteps,
    xs ⟨k.val + 1, by omega⟩ = fire S (ξs k) (xs ⟨k.val, by omega⟩)

theorem trajectory_preserves_pool {nSpec nRxn nSteps : Nat}
    (γ : Fin nSpec → ℚ) (S : Fin nSpec → Fin nRxn → ℚ)
    (h : ConservationLaw γ S)
    (ξs : Fin nSteps → Fin nRxn → ℚ)
    (xs : Fin (nSteps + 1) → Fin nSpec → ℚ)
    (hsound : TrajectorySound S ξs xs)
    (k : Fin (nSteps + 1)) :
    pool γ (xs k) = pool γ (xs 0) := by
  induction k using Fin.induction with
  | zero => rfl
  | succ k ih =>
    have step := hsound k
    calc pool γ (xs ⟨k.val + 1, by omega⟩)
        = pool γ (fire S (ξs k) (xs ⟨k.val, by omega⟩)) := by rw [step]
      _ = pool γ (xs ⟨k.val, by omega⟩) := conserved_step γ S h _ _
      _ = pool γ (xs 0) := ih

/-- Independent Boolean trajectory check (exact rationals). -/
def checkTrajectory {nSpec nRxn nSteps : Nat}
    (S : Fin nSpec → Fin nRxn → ℚ)
    (ξs : Fin nSteps → Fin nRxn → ℚ)
    (xs : Fin (nSteps + 1) → Fin nSpec → ℚ) : Bool :=
  decide (∀ k : Fin nSteps,
    xs ⟨k.val + 1, by omega⟩ = fire S (ξs k) (xs ⟨k.val, by omega⟩))

theorem checkTrajectory_sound {nSpec nRxn nSteps : Nat}
    {S : Fin nSpec → Fin nRxn → ℚ}
    {ξs : Fin nSteps → Fin nRxn → ℚ}
    {xs : Fin (nSteps + 1) → Fin nSpec → ℚ}
    (h : checkTrajectory S ξs xs = true) : TrajectorySound S ξs xs := by
  simpa [checkTrajectory, TrajectorySound, decide_eq_true_eq] using h

theorem checkTrajectory_preserves {nSpec nRxn nSteps : Nat}
    {γ : Fin nSpec → ℚ} {S : Fin nSpec → Fin nRxn → ℚ}
    (hγ : check γ S = true)
    {ξs : Fin nSteps → Fin nRxn → ℚ}
    {xs : Fin (nSteps + 1) → Fin nSpec → ℚ}
    (htraj : checkTrajectory S ξs xs = true)
    (k : Fin (nSteps + 1)) :
    pool γ (xs k) = pool γ (xs 0) :=
  trajectory_preserves_pool γ S (check_sound hγ) ξs xs
    (checkTrajectory_sound htraj) k

end PCCA.Stoich
