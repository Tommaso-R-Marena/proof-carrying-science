module

public import RequestProject.AION.Core

/-!
# Path-space semantics of `hitN`

We make explicit that `hitN A B n x` is a genuine probability of an explicit event
under an explicit probability measure on finite reaction sequences.

The *stopped embedded jump chain* chooses reaction `r` at state `x` with probability
`rate r x / totalRate x`, and stays put (choosing a dummy reaction uniformly) once it
is stopped, i.e. once it is in `B`, in `A`, or in a state with zero total rate.
`pathWeight n x rs` is the probability of the reaction sequence `rs : Fin n → ι`,
`pathHits n x rs` is the event "the trajectory visits `B` within `n` jumps" (it can
only do so before visiting `A`, because `A` is absorbing for the stopped chain).

* `sum_pathWeight` : the weights form a probability distribution on `Fin n → ι`.
* `hitN_eq_path_sum` : `hitN A B n x = ∑_{rs} pathWeight n x rs · 1[pathHits n x rs]`.

Together with `hitProb = ⨆ n, hitN n` this identifies `hitProb` with the probability
that the (embedded) Markov chain ever reaches `B` before `A`, by continuity of
probability along the increasing events "hit within `n` jumps".
-/

@[expose] public section

open scoped BigOperators
open Classical

namespace AION
namespace JumpModel

variable {S : Type*} {ι : Type*} [Fintype ι] [Nonempty ι] (M : JumpModel S ι) (A B : Set S)

/-- Stopped states. -/
def stopped (x : S) : Prop := x ∈ B ∨ x ∈ A ∨ M.totalRate x = 0

/-- Transition probability of the stopped embedded chain. -/
noncomputable def q (r : ι) (x : S) : ℝ :=
  if M.stopped A B x then 1 / (Fintype.card ι : ℝ) else M.rate r x / M.totalRate x

/-- One step of the stopped embedded chain. -/
noncomputable def step (r : ι) (x : S) : S := if M.stopped A B x then x else M.next r x

/-- Probability of a reaction sequence. -/
noncomputable def pathWeight : (n : ℕ) → S → (Fin n → ι) → ℝ
  | 0, _, _ => 1
  | n + 1, x, rs => M.q A B (rs 0) x * pathWeight n (M.step A B (rs 0) x) (Fin.tail rs)

/-- The trajectory driven by `rs` visits `B` within `n` jumps. -/
def pathHits : (n : ℕ) → S → (Fin n → ι) → Prop
  | 0, x, _ => x ∈ B
  | n + 1, x, rs => x ∈ B ∨ pathHits n (M.step A B (rs 0) x) (Fin.tail rs)

omit [Nonempty ι] in
lemma sum_fin_succ_fun {n : ℕ} (F : (Fin (n + 1) → ι) → ℝ) :
    ∑ f, F f = ∑ r, ∑ g : Fin n → ι, F (Fin.cons r g) := by
  rw [← (Fin.consEquiv (fun _ : Fin (n + 1) => ι)).sum_comp, Fintype.sum_prod_type]
  rfl

lemma sum_q (x : S) : ∑ r, M.q A B r x = 1 := by
  unfold q
  by_cases h : M.stopped A B x
  · simp only [h, if_true, Finset.sum_const, Finset.card_univ, nsmul_eq_mul]
    have : (Fintype.card ι : ℝ) ≠ 0 := by exact_mod_cast Fintype.card_ne_zero
    field_simp
  · simp only [h, if_false]
    have hne : M.totalRate x ≠ 0 := fun h0 => h (Or.inr (Or.inr h0))
    rw [← Finset.sum_div]
    exact div_self hne

/-- The path weights are a probability distribution. -/
theorem sum_pathWeight : ∀ (n : ℕ) (x : S), ∑ rs : Fin n → ι, M.pathWeight A B n x rs = 1
  | 0, x => by simp [pathWeight]
  | n + 1, x => by
      rw [sum_fin_succ_fun]
      simp only [pathWeight, Fin.cons_zero, Fin.tail_cons]
      simp_rw [← Finset.mul_sum, sum_pathWeight n]
      simp [sum_q]

omit [Nonempty ι] in
lemma hitN_stopped_not_B {x : S} (hs : M.stopped A B x) (hB : x ∉ B) :
    ∀ n, M.hitN A B n x = 0
  | 0 => by simp [hitN, hB]
  | n + 1 => by
      simp only [hitN, hB, if_false]
      rcases hs with h | h | h
      · exact absurd h hB
      · simp [h]
      · split_ifs <;> simp_all

/-- **Path-space semantics.** -/
theorem hitN_eq_path_sum : ∀ (n : ℕ) (x : S),
    M.hitN A B n x =
      ∑ rs : Fin n → ι, M.pathWeight A B n x rs * (if M.pathHits A B n x rs then 1 else 0)
  | 0, x => by simp [hitN, pathWeight, pathHits]
  | n + 1, x => by
      rw [sum_fin_succ_fun]
      simp only [pathWeight, pathHits, Fin.cons_zero, Fin.tail_cons]
      by_cases hB : x ∈ B
      · simp only [hB, true_or, if_true, mul_one]
        have : M.hitN A B (n + 1) x = 1 := by simp [hitN, hB]
        rw [this]
        simp_rw [← Finset.mul_sum, sum_pathWeight]
        simp [sum_q]
      · simp only [hB, false_or]
        by_cases hs : M.stopped A B x
        · rw [hitN_stopped_not_B M A B hs hB]
          have hstep : ∀ r, M.step A B r x = x := fun r => by simp [step, hs]
          simp_rw [hstep, mul_assoc, ← Finset.mul_sum, ← hitN_eq_path_sum n x,
            hitN_stopped_not_B M A B hs hB]
          simp
        · have hA : x ∉ A := fun h => hs (Or.inr (Or.inl h))
          have hne : M.totalRate x ≠ 0 := fun h0 => hs (Or.inr (Or.inr h0))
          have hstep : ∀ r, M.step A B r x = M.next r x := fun r => by simp [step, hs]
          have hq : ∀ r, M.q A B r x = M.rate r x / M.totalRate x := fun r => by simp [q, hs]
          simp_rw [hstep, hq, mul_assoc, ← Finset.mul_sum, ← hitN_eq_path_sum n]
          simp only [hitN, hB, hA, hne, if_false, flux, Finset.sum_div]
          exact Finset.sum_congr rfl (fun r _ => by ring)

end JumpModel
end AION
