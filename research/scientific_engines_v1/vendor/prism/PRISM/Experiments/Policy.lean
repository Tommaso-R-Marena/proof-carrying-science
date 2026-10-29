module

public import PRISM.Inference.VersionSpace

/-!
# Adaptive experimental policies

An adaptive policy is a finite decision tree: either stop, or run experiment `e`
and continue with a sub-policy chosen as a function of the observed outcome.

Semantics: if the true mechanism is `m` and the current version space is `K`,
running experiment `e` produces outcome `obs m e` and the version space becomes the
cell `K(e, obs m e)`.  `terminal p m K` is the version space in which the policy
stops, and `pathCost p m` the cumulative cost along the path of `m`.  Because
these are defined for *every* model `m`, the results below hold under arbitrary
admissible sequences of observations.
-/

@[expose] public section

namespace PRISM

universe u v w

/-- Finite adaptive experimental strategies (decision trees). -/
inductive Policy (E : Type v) (O : Type w) : Type (max v w) where
  /-- Stop experimenting. -/
  | stop : Policy E O
  /-- Run experiment `e`, then continue with `next o` after observing `o`. -/
  | test (e : E) (next : O → Policy E O) : Policy E O

instance {E : Type v} {O : Type w} : Inhabited (Policy E O) := ⟨.stop⟩

variable {M : Type u} {E : Type v} {O : Type w}

namespace Problem

variable (P : Problem M E O)

/-- Cumulative cost of the experiments a policy runs when the truth is `m`. -/
def pathCost : Policy E O → M → ℚ≥0
  | .stop, _ => 0
  | .test e f, m => P.cost e + pathCost (f (P.obs m e)) m

/-- Number of experiments a policy runs when the truth is `m`. -/
def pathLength : Policy E O → M → ℕ
  | .stop, _ => 0
  | .test e f, m => 1 + pathLength (f (P.obs m e)) m

/-- Worst-case cumulative cost over the models in `K`. -/
def worstCost (p : Policy E O) (K : Finset M) : ℚ≥0 := K.sup (P.pathCost p)

/-- Every model of `K` incurs cost at most `B`. -/
def CostLE (p : Policy E O) (K : Finset M) (B : ℚ≥0) : Prop := ∀ m ∈ K, P.pathCost p m ≤ B

variable {P}

lemma costLE_iff {p : Policy E O} {K : Finset M} {B : ℚ≥0} :
    P.CostLE p K B ↔ P.worstCost p K ≤ B := by
  simp [CostLE, worstCost, Finset.sup_le_iff]

lemma costLE_worstCost (p : Policy E O) (K : Finset M) : P.CostLE p K (P.worstCost p K) :=
  costLE_iff.2 le_rfl

lemma costLE_mono {p : Policy E O} {K K' : Finset M} {B : ℚ≥0} (h : K ⊆ K')
    (hc : P.CostLE p K' B) : P.CostLE p K B := fun m hm => hc m (h hm)

variable [DecidableEq O]
variable (P)

/-- The version space in which policy `p` stops when the truth is `m`. -/
def terminal : Policy E O → M → Finset M → Finset M
  | .stop, _, K => K
  | .test e f, m, K => terminal (f (P.obs m e)) m (P.cell K e (P.obs m e))

/-- A policy *succeeds* on `K` at tolerance `ε` if, whatever the true model in `K`,
the final version space has query width at most `ε`. -/
def Succeeds (ε : ℚ) (p : Policy E O) (K : Finset M) : Prop :=
  ∀ m ∈ K, P.width (P.terminal p m K) ≤ ε

/-- `p` only ever runs experiments that are informative at the version space where
they are run. -/
def OnlyInformative : Policy E O → Finset M → Prop
  | .stop, _ => True
  | .test e f, K => P.Informative K e ∧ ∀ o ∈ P.outcomes K e, OnlyInformative (f o) (P.cell K e o)

variable {P}

lemma terminal_subset (p : Policy E O) (m : M) (K : Finset M) : P.terminal p m K ⊆ K := by
  induction p generalizing K with
  | stop => exact subset_rfl
  | test e f ih => exact (ih _ _).trans (P.cell_subset _ _ _)

lemma mem_terminal_self (p : Policy E O) {m : M} {K : Finset M} (hm : m ∈ K) :
    m ∈ P.terminal p m K := by
  induction p generalizing K with
  | stop => exact hm
  | test e f ih => exact ih _ ((P.mem_cell).2 ⟨hm, rfl⟩)

lemma terminal_mono (p : Policy E O) (m : M) {K K' : Finset M} (h : K ⊆ K') :
    P.terminal p m K ⊆ P.terminal p m K' := by
  induction p generalizing K K' with
  | stop => exact h
  | test e f ih => exact ih _ (P.cell_mono h _ _)

/-- Success is inherited by sub-version-spaces. -/
lemma succeeds_mono {ε : ℚ} {p : Policy E O} {K K' : Finset M} (h : K ⊆ K')
    (hs : P.Succeeds ε p K') : P.Succeeds ε p K :=
  fun m hm => (P.width_mono (terminal_mono p m h)).trans (hs m (h hm))

lemma succeeds_stop_iff {ε : ℚ} {K : Finset M} (hε : 0 ≤ ε) :
    P.Succeeds ε .stop K ↔ P.width K ≤ ε := by
  constructor
  · intro h
    by_cases hK : K.Nonempty
    · obtain ⟨m, hm⟩ := hK; exact h m hm
    · rw [Finset.not_nonempty_iff_eq_empty.1 hK, width_empty]; exact hε
  · intro h m _; exact h

lemma succeeds_child {ε : ℚ} {e : E} {f : O → Policy E O} {K : Finset M}
    (h : P.Succeeds ε (.test e f) K) (o : O) : P.Succeeds ε (f o) (P.cell K e o) := by
  intro m hm
  have ho := ((P.mem_cell).1 hm).2
  have := h m ((P.mem_cell).1 hm).1
  simp only [terminal, ho] at this
  exact this

lemma succeeds_test_iff {ε : ℚ} {e : E} {f : O → Policy E O} {K : Finset M} :
    P.Succeeds ε (.test e f) K ↔ ∀ o ∈ P.outcomes K e, P.Succeeds ε (f o) (P.cell K e o) := by
  refine ⟨fun h o _ => succeeds_child h o, fun h m hm => ?_⟩
  have := h (P.obs m e) ((P.mem_outcomes).2 ⟨m, hm, rfl⟩) m ((P.mem_cell).2 ⟨hm, rfl⟩)
  simpa [terminal] using this

lemma costLE_child {e : E} {f : O → Policy E O} {K : Finset M} {B : ℚ≥0}
    (h : P.CostLE (.test e f) K B) (o : O) :
    P.CostLE (f o) (P.cell K e o) (B - P.cost e) := by
  intro m hm
  have ho := ((P.mem_cell).1 hm).2
  have := h m ((P.mem_cell).1 hm).1
  simp only [pathCost, ho] at this
  exact le_tsub_of_add_le_left this

omit [DecidableEq O] in
lemma cost_le_of_costLE_test {e : E} {f : O → Policy E O} {K : Finset M} {B : ℚ≥0}
    (h : P.CostLE (.test e f) K B) {m : M} (hm : m ∈ K) : P.cost e ≤ B := by
  have := h m hm
  simp only [pathCost] at this
  exact le_of_add_le_left this

/-- **Termination**: a policy that only runs informative experiments performs fewer
than `|K|` experiments on every admissible path. -/
theorem pathLength_lt_card {p : Policy E O} {K : Finset M} (hp : P.OnlyInformative p K)
    {m : M} (hm : m ∈ K) : P.pathLength p m < K.card := by
  induction p generalizing K with
  | stop => simp only [pathLength]; exact Finset.card_pos.2 ⟨m, hm⟩
  | test e f ih =>
    obtain ⟨hi, hrest⟩ := hp
    have ho : P.obs m e ∈ P.outcomes K e := (P.mem_outcomes).2 ⟨m, hm, rfl⟩
    have := ih (P.obs m e) (hrest _ ho) ((P.mem_cell).2 ⟨hm, rfl⟩)
    have := P.card_cell_lt_of_informative hi (P.obs m e)
    simp only [pathLength]
    omega

end Problem

end PRISM
