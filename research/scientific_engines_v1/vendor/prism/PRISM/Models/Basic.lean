module

public import Mathlib

/-!
# PRISM — core finite deterministic model

A *problem* consists of a type of candidate mechanistic models `M`, a type of
permitted experiments `E`, a type of observable outcomes `O`, a deterministic
observation map `obs : M → E → O`, an exact rational query `q : M → ℚ`, and a
nonnegative rational experiment cost `cost : E → ℚ≥0`.

Nonnegativity of costs is enforced by the type `ℚ≥0`; negative-cost inputs are
rejected at the serialization boundary (see `docs/TRUST_BOUNDARIES.md`).

Version spaces (sets of models still admissible) are `Finset M`.
-/

@[expose] public section

namespace PRISM

universe u v w

/-- A finite deterministic scientific problem. -/
structure Problem (M : Type u) (E : Type v) (O : Type w) where
  /-- The outcome model `m` predicts for experiment `e`. -/
  obs : M → E → O
  /-- The exact rational scientific query. -/
  q : M → ℚ
  /-- The nonnegative cost of running an experiment. -/
  cost : E → ℚ≥0

variable {M : Type u} {E : Type v} {O : Type w}

namespace Problem

section Width

variable (P : Problem M E O)

/-- Lower query bound `L(K)` (only meaningful for nonempty `K`). -/
def lower (K : Finset M) (h : K.Nonempty) : ℚ := K.inf' h P.q

/-- Upper query bound `U(K)`. -/
def upper (K : Finset M) (h : K.Nonempty) : ℚ := K.sup' h P.q

/-- Query width `W(K) = U(K) - L(K)`, with the convention `W(∅) = 0`. -/
def width (K : Finset M) : ℚ :=
  if h : K.Nonempty then K.sup' h P.q - K.inf' h P.q else 0

lemma width_empty : P.width ∅ = 0 := by simp [width]

lemma width_of_nonempty {K : Finset M} (h : K.Nonempty) :
    P.width K = P.upper K h - P.lower K h := by
  simp [width, h, upper, lower]

lemma width_nonneg (K : Finset M) : 0 ≤ P.width K := by
  unfold width
  split_ifs with h
  · obtain ⟨m, hm⟩ := h
    have := Finset.inf'_le P.q hm
    have := Finset.le_sup' P.q hm
    linarith
  · rfl

/-- Any two members of `K` differ in query value by at most the width. -/
lemma sub_le_width {K : Finset M} {a b : M} (ha : a ∈ K) (hb : b ∈ K) :
    P.q a - P.q b ≤ P.width K := by
  have h : K.Nonempty := ⟨a, ha⟩
  simp only [width, h, dite_true]
  have := Finset.inf'_le P.q hb
  have := Finset.le_sup' P.q ha
  linarith

/-- The width is at most `ε` iff all pairwise query differences are at most `ε`
(for `ε ≥ 0`). -/
lemma width_le_iff {K : Finset M} {ε : ℚ} (hε : 0 ≤ ε) :
    P.width K ≤ ε ↔ ∀ a ∈ K, ∀ b ∈ K, P.q a - P.q b ≤ ε := by
  constructor
  · intro h a ha b hb
    exact (P.sub_le_width ha hb).trans h
  · intro h
    by_cases hK : K.Nonempty
    · obtain ⟨a, ha, hsa⟩ := Finset.exists_mem_eq_sup' hK P.q
      obtain ⟨b, hb, hib⟩ := Finset.exists_mem_eq_inf' hK P.q
      simp only [width, hK, dite_true, hsa, hib]
      exact h a ha b hb
    · simp [width, hK, hε]

lemma width_mono {K K' : Finset M} (h : K ⊆ K') : P.width K ≤ P.width K' := by
  by_cases hK : K.Nonempty
  · obtain ⟨a, ha, hsa⟩ := Finset.exists_mem_eq_sup' hK P.q
    obtain ⟨b, hb, hib⟩ := Finset.exists_mem_eq_inf' hK P.q
    simp only [width, hK, dite_true, hsa, hib]
    exact P.sub_le_width (h ha) (h hb)
  · simp only [width, hK, dite_false]
    exact P.width_nonneg K'

end Width

section Cells

variable [DecidableEq O] (P : Problem M E O)

/-- `K(e,o)`: the models of `K` that predict outcome `o` for experiment `e`. -/
def cell (K : Finset M) (e : E) (o : O) : Finset M :=
  K.filter (fun m => P.obs m e = o)

/-- The outcomes of `e` that at least one model of `K` predicts
(the *feasible* outcomes). -/
def outcomes (K : Finset M) (e : E) : Finset O := K.image (fun m => P.obs m e)

/-- Experiment `e` is *informative* on `K` if two models of `K` disagree on it. -/
def Informative (K : Finset M) (e : E) : Prop :=
  ∃ a ∈ K, ∃ b ∈ K, P.obs a e ≠ P.obs b e

instance (K : Finset M) (e : E) : Decidable (P.Informative K e) := by
  unfold Informative; infer_instance

lemma cell_subset (K : Finset M) (e : E) (o : O) : P.cell K e o ⊆ K :=
  Finset.filter_subset _ _

lemma mem_cell {K : Finset M} {e : E} {o : O} {m : M} :
    m ∈ P.cell K e o ↔ m ∈ K ∧ P.obs m e = o := Finset.mem_filter

lemma mem_outcomes {K : Finset M} {e : E} {o : O} :
    o ∈ P.outcomes K e ↔ ∃ m ∈ K, P.obs m e = o := Finset.mem_image

lemma cell_nonempty_of_mem_outcomes {K : Finset M} {e : E} {o : O}
    (h : o ∈ P.outcomes K e) : (P.cell K e o).Nonempty := by
  obtain ⟨m, hm, rfl⟩ := Finset.mem_image.mp h
  exact ⟨m, (P.mem_cell).2 ⟨hm, rfl⟩⟩

/-- An informative experiment strictly shrinks every cell (termination of planning). -/
lemma cell_ssubset_of_informative {K : Finset M} {e : E} (h : P.Informative K e) (o : O) :
    P.cell K e o ⊂ K := by
  obtain ⟨a, ha, b, hb, hab⟩ := h
  refine (Finset.ssubset_iff_of_subset (P.cell_subset K e o)).2 ?_
  by_cases hao : P.obs a e = o
  · exact ⟨b, hb, fun hb' => hab (hao.trans ((P.mem_cell).1 hb').2.symm)⟩
  · exact ⟨a, ha, fun ha' => hao ((P.mem_cell).1 ha').2⟩

lemma card_cell_lt_of_informative {K : Finset M} {e : E} (h : P.Informative K e) (o : O) :
    (P.cell K e o).card < K.card :=
  Finset.card_lt_card (P.cell_ssubset_of_informative h o)

/-- An uninformative experiment leaves the version space unchanged on every
feasible outcome: it provides no information. -/
lemma cell_eq_of_not_informative {K : Finset M} {e : E} (h : ¬ P.Informative K e)
    {m : M} (hm : m ∈ K) : P.cell K e (P.obs m e) = K := by
  ext x
  simp only [mem_cell, and_iff_left_iff_imp]
  intro hx
  by_contra hne
  exact h ⟨x, hx, m, hm, hne⟩

lemma cell_mono {K K' : Finset M} (h : K ⊆ K') (e : E) (o : O) :
    P.cell K e o ⊆ P.cell K' e o := Finset.filter_subset_filter _ h

end Cells

end Problem

end PRISM
