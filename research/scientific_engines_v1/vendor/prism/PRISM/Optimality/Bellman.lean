module

public import PRISM.Experiments.Policy

/-!
# The exact minimax experiment-cost value and Bellman optimality

`value ε K : WithTop ℚ≥0` is defined *by* the Bellman recursion

* `value ε K = 0` if `W(K) ≤ ε`;
* otherwise `value ε K = min_{e informative on K} (c(e) + max_{o feasible} value ε K(e,o))`,
  with `min ∅ = ⊤` (impossibility).

The recursion terminates because informative experiments strictly shrink every
cell.  We then *prove* that this recursively computed number is exactly the
minimax optimal worst-case cost over all successful adaptive policies
(`value_le_iff`, `value_optimal`), so dynamic programming is justified rather than
assumed.
-/

@[expose] public section

namespace PRISM

universe u v w

variable {M : Type u} {E : Type v} {O : Type w}

namespace Problem

variable [DecidableEq O] [Fintype E] (P : Problem M E O)

/-- The Bellman value: exact minimax worst-case experimental cost (`⊤` = impossible). -/
def value (ε : ℚ) (K : Finset M) : WithTop ℚ≥0 :=
  if P.width K ≤ ε then 0 else
    (Finset.univ.filter (P.Informative K)).attach.inf fun e =>
      (P.cost e.1 : WithTop ℚ≥0) + (P.outcomes K e.1).attach.sup fun o =>
        value ε (P.cell K e.1 o.1)
termination_by K.card
decreasing_by exact P.card_cell_lt_of_informative (Finset.mem_filter.1 e.2).2 _

/-- The one-step Bellman backup of experiment `e` at `K`. -/
def backup (ε : ℚ) (K : Finset M) (e : E) : WithTop ℚ≥0 :=
  (P.cost e : WithTop ℚ≥0) + (P.outcomes K e).sup fun o => P.value ε (P.cell K e o)

variable {P}

/-- **Bellman recurrence** (target already met). -/
theorem value_of_width_le {ε : ℚ} {K : Finset M} (h : P.width K ≤ ε) : P.value ε K = 0 := by
  rw [value, if_pos h]

/-- **Bellman recurrence** (target not met): minimum over informative experiments of
cost plus worst feasible outcome. -/
theorem value_of_not_width_le {ε : ℚ} {K : Finset M} (h : ¬ P.width K ≤ ε) :
    P.value ε K = (Finset.univ.filter (P.Informative K)).inf (P.backup ε K) := by
  rw [value, if_neg h, ← Finset.inf_attach (Finset.univ.filter (P.Informative K)) (P.backup ε K)]
  congr 1
  funext e
  simp only [backup]
  congr 1
  exact Finset.sup_attach (P.outcomes K e.1) (fun o => P.value ε (P.cell K e.1 o))

private lemma coe_add_tsub_le {a B : ℚ≥0} (ha : a ≤ B) (S : WithTop ℚ≥0)
    (hS : S ≤ ((B - a : ℚ≥0) : WithTop ℚ≥0)) : (a : WithTop ℚ≥0) + S ≤ B := by
  calc (a : WithTop ℚ≥0) + S ≤ (a : WithTop ℚ≥0) + ((B - a : ℚ≥0) : WithTop ℚ≥0) :=
        add_le_add_right hS _
    _ = ((a + (B - a) : ℚ≥0) : WithTop ℚ≥0) := by norm_cast
    _ = B := by rw [add_tsub_cancel_of_le ha]

/-- **Lower bound (no policy beats the value).**  If an adaptive policy succeeds on
`K` with worst-case cost at most `B`, then `value ε K ≤ B`. -/
theorem value_le_of_succeeds {ε : ℚ} (hε : 0 ≤ ε) (p : Policy E O) :
    ∀ (K : Finset M) (B : ℚ≥0), P.Succeeds ε p K → P.CostLE p K B → P.value ε K ≤ B := by
  induction p with
  | stop =>
    intro K B hs _
    rw [value_of_width_le ((succeeds_stop_iff hε).1 hs)]
    exact WithTop.coe_le_coe.2 (zero_le B)
  | test e f ih =>
    intro K B hs hc
    by_cases hw : P.width K ≤ ε
    · rw [value_of_width_le hw]; exact WithTop.coe_le_coe.2 (zero_le B)
    have hK : K.Nonempty := by
      by_contra hK
      rw [Finset.not_nonempty_iff_eq_empty.1 hK, width_empty] at hw
      exact hw hε
    obtain ⟨m₀, hm₀⟩ := hK
    have hce : P.cost e ≤ B := cost_le_of_costLE_test hc hm₀
    by_cases hi : P.Informative K e
    · rw [value_of_not_width_le hw]
      refine (Finset.inf_le (Finset.mem_filter.2 ⟨Finset.mem_univ e, hi⟩)).trans ?_
      apply coe_add_tsub_le hce
      refine Finset.sup_le fun o ho => ?_
      exact ih o _ _ (succeeds_child hs o) (costLE_child hc o)
    · have hcell := P.cell_eq_of_not_informative hi hm₀
      have h1 := succeeds_child hs (P.obs m₀ e)
      have h2 := costLE_child hc (P.obs m₀ e)
      rw [hcell] at h1 h2
      exact (ih _ K _ h1 h2).trans (WithTop.coe_le_coe.2 tsub_le_self)

/-- **Upper bound (the value is attained).**  If `value ε K ≤ v` then there is a
successful adaptive policy with worst-case cost at most `v`, which moreover runs
only informative experiments. -/
theorem exists_policy_of_value_le {ε : ℚ} (hε : 0 ≤ ε) :
    ∀ (n : ℕ) (K : Finset M), K.card = n → ∀ v : ℚ≥0, P.value ε K ≤ v →
      ∃ p : Policy E O, P.Succeeds ε p K ∧ P.CostLE p K v ∧ P.OnlyInformative p K := by
  intro n
  induction n using Nat.strong_induction_on with
  | _ n ih =>
  intro K hn v hv
  by_cases hw : P.width K ≤ ε
  · exact ⟨.stop, (succeeds_stop_iff hε).2 hw, fun _ _ => zero_le v, trivial⟩
  rw [value_of_not_width_le hw] at hv
  obtain ⟨e, he, hev⟩ := (Finset.inf_le_iff (WithTop.coe_lt_top v)).1 hv
  have hi : P.Informative K e := (Finset.mem_filter.1 he).2
  simp only [backup] at hev
  -- split the bound
  set S := (P.outcomes K e).sup fun o => P.value ε (P.cell K e o) with hSdef
  have hS : S ≠ ⊤ := by
    intro h; rw [h] at hev; simp at hev
  obtain ⟨s, hs⟩ := WithTop.ne_top_iff_exists.1 hS
  rw [← hs] at hev
  have hev' : P.cost e + s ≤ v := by exact_mod_cast hev
  have hce : P.cost e ≤ v := le_of_add_le_left hev'
  have hsv : s ≤ v - P.cost e := le_tsub_of_add_le_left hev'
  have H : ∀ o ∈ P.outcomes K e, ∃ p : Policy E O, P.Succeeds ε p (P.cell K e o) ∧
      P.CostLE p (P.cell K e o) (v - P.cost e) ∧ P.OnlyInformative p (P.cell K e o) := by
    intro o ho
    have hle : P.value ε (P.cell K e o) ≤ ((v - P.cost e : ℚ≥0) : WithTop ℚ≥0) := by
      calc P.value ε (P.cell K e o) ≤ S := Finset.le_sup (f := fun o => P.value ε (P.cell K e o)) ho
        _ = s := hs.symm
        _ ≤ _ := WithTop.coe_le_coe.2 hsv
    exact ih _ (hn ▸ P.card_cell_lt_of_informative hi o) _ rfl _ hle
  choose! g hg using H
  refine ⟨.test e g, ?_, ?_, ?_⟩
  · exact succeeds_test_iff.2 fun o ho => (hg o ho).1
  · intro m hm
    have ho : P.obs m e ∈ P.outcomes K e := (P.mem_outcomes).2 ⟨m, hm, rfl⟩
    have := (hg _ ho).2.1 m ((P.mem_cell).2 ⟨hm, rfl⟩)
    simp only [pathCost]
    calc P.cost e + P.pathCost (g (P.obs m e)) m ≤ P.cost e + (v - P.cost e) :=
          add_le_add_right this _
      _ = v := add_tsub_cancel_of_le hce
  · exact ⟨hi, fun o ho => (hg o ho).2.2⟩

/-- **Exact minimax characterization.**  For every `v`,
`value ε K ≤ v` iff some successful adaptive policy has worst-case cost `≤ v`. -/
theorem value_le_iff {ε : ℚ} (hε : 0 ≤ ε) {K : Finset M} {v : ℚ≥0} :
    P.value ε K ≤ v ↔ ∃ p : Policy E O, P.Succeeds ε p K ∧ P.CostLE p K v := by
  constructor
  · intro h
    obtain ⟨p, h1, h2, -⟩ := exists_policy_of_value_le hε _ K rfl v h
    exact ⟨p, h1, h2⟩
  · rintro ⟨p, h1, h2⟩
    exact value_le_of_succeeds hε p K v h1 h2

/-- **Global minimax optimality.**  If `value ε K = v` (finite), then an adaptive
policy achieving worst-case cost `v` exists, and *no* successful adaptive policy
achieves worst-case cost below `v`. -/
theorem value_optimal {ε : ℚ} (hε : 0 ≤ ε) {K : Finset M} {v : ℚ≥0}
    (hv : P.value ε K = v) :
    (∃ p : Policy E O, P.Succeeds ε p K ∧ P.worstCost p K = v ∧ P.OnlyInformative p K) ∧
    ∀ p : Policy E O, P.Succeeds ε p K → v ≤ P.worstCost p K := by
  have hlow : ∀ p : Policy E O, P.Succeeds ε p K → v ≤ P.worstCost p K := by
    intro p hp
    have := value_le_of_succeeds hε p K _ hp (costLE_worstCost p K)
    rw [hv] at this
    exact_mod_cast this
  refine ⟨?_, hlow⟩
  obtain ⟨p, h1, h2, h3⟩ := exists_policy_of_value_le hε _ K rfl v hv.le
  exact ⟨p, h1, le_antisymm (costLE_iff.1 h2) (hlow p h1), h3⟩

/-- **Impossibility ⇔ infinite value.** -/
theorem value_eq_top_iff {ε : ℚ} (hε : 0 ≤ ε) {K : Finset M} :
    P.value ε K = ⊤ ↔ ∀ p : Policy E O, ¬ P.Succeeds ε p K := by
  constructor
  · intro h p hp
    have := value_le_of_succeeds hε p K _ hp (costLE_worstCost p K)
    rw [h] at this
    exact absurd this (by simp)
  · intro h
    by_contra hne
    obtain ⟨v, hv⟩ := WithTop.ne_top_iff_exists.1 hne
    obtain ⟨p, hp, -⟩ := (value_le_iff hε).1 hv.symm.le
    exact h p hp

/-- **Any minimizer of the Bellman backup starts an optimal policy** (tie-breaking is
irrelevant): if experiment `e` has backup `≤ v`, there is a successful policy that
starts with `e` and has worst-case cost `≤ v`. -/
theorem exists_policy_test_of_backup_le {ε : ℚ} (hε : 0 ≤ ε) {K : Finset M} {e : E}
    {v : ℚ≥0} (h : P.backup ε K e ≤ v) :
    ∃ f : O → Policy E O, P.Succeeds ε (.test e f) K ∧ P.CostLE (.test e f) K v := by
  simp only [backup] at h
  set S := (P.outcomes K e).sup fun o => P.value ε (P.cell K e o) with hSdef
  have hS : S ≠ ⊤ := by
    intro h'; rw [h'] at h; simp at h
  obtain ⟨s, hs⟩ := WithTop.ne_top_iff_exists.1 hS
  rw [← hs] at h
  have h' : P.cost e + s ≤ v := by exact_mod_cast h
  have hce : P.cost e ≤ v := le_of_add_le_left h'
  have hsv : s ≤ v - P.cost e := le_tsub_of_add_le_left h'
  have H : ∀ o ∈ P.outcomes K e, ∃ p : Policy E O, P.Succeeds ε p (P.cell K e o) ∧
      P.CostLE p (P.cell K e o) (v - P.cost e) := by
    intro o ho
    apply (value_le_iff hε).1
    calc P.value ε (P.cell K e o) ≤ S := Finset.le_sup (f := fun o => P.value ε (P.cell K e o)) ho
      _ = s := hs.symm
      _ ≤ _ := WithTop.coe_le_coe.2 hsv
  choose! g hg using H
  refine ⟨g, succeeds_test_iff.2 fun o ho => (hg o ho).1, ?_⟩
  intro m hm
  have ho : P.obs m e ∈ P.outcomes K e := (P.mem_outcomes).2 ⟨m, hm, rfl⟩
  have := (hg _ ho).2 m ((P.mem_cell).2 ⟨hm, rfl⟩)
  simp only [pathCost]
  calc P.cost e + P.pathCost (g (P.obs m e)) m ≤ P.cost e + (v - P.cost e) :=
        add_le_add_right this _
    _ = v := add_tsub_cancel_of_le hce

/-- **Uninformative experiments are useless**: the optimal value is always attained
by a policy that never runs an uninformative experiment (see
`exists_policy_of_value_le`); in particular deleting all uninformative experiments
from consideration never increases the optimal cost. -/
theorem exists_optimal_onlyInformative {ε : ℚ} (hε : 0 ≤ ε) {K : Finset M}
    (p : Policy E O) (hp : P.Succeeds ε p K) :
    ∃ p' : Policy E O, P.Succeeds ε p' K ∧ P.OnlyInformative p' K ∧
      P.worstCost p' K ≤ P.worstCost p K := by
  obtain ⟨p', h1, h2, h3⟩ := exists_policy_of_value_le hε _ K rfl _
    (value_le_of_succeeds hε p K _ hp (costLE_worstCost p K))
  exact ⟨p', h1, h3, costLE_iff.1 h2⟩

/-- **Monotonicity of the value** in the version space: more admissible models can
never make the experimental problem cheaper. -/
theorem value_mono {ε : ℚ} (hε : 0 ≤ ε) {K K' : Finset M} (h : K ⊆ K') :
    P.value ε K ≤ P.value ε K' := by
  rcases eq_or_ne (P.value ε K') ⊤ with htop | hne
  · rw [htop]; exact le_top
  obtain ⟨v, hv⟩ := WithTop.ne_top_iff_exists.1 hne
  obtain ⟨p, hp, hc⟩ := (value_le_iff hε).1 hv.symm.le
  rw [← hv]
  exact (value_le_iff hε).2 ⟨p, succeeds_mono h hp, costLE_mono h hc⟩

end Problem

end PRISM
