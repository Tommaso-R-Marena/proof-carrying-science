module

public import PRISM.Abstraction.Sandwich

/-!
# Adversary (lower-bound) certificates

An *adversary certificate* is a map `lb : Finset M → ℚ≥0` such that every version
space `S` with `lb S > 0` is not yet solved (`ε < W(S)`) and, for every experiment
`e`, some feasible outcome `o` keeps the adversary's claim alive:
`lb S ≤ c(e) + lb (S(e,o))`.

* `adversary_sound`: any successful policy on `S` has worst-case cost `≥ lb S`.
* `adversary_complete`: for every `B ≤ value ε S₀` there is an adversary certificate
  with `lb S₀ = B`.  Adversary certificates are therefore a **complete proof system**
  for lower bounds on minimax experimental cost: no enumeration of policies is ever
  needed, and only version spaces on which `lb` is positive need to be listed.

These are the lower half of the optimality sandwich.
-/

@[expose] public section

namespace PRISM

universe u v w

variable {M : Type u} {E : Type v} {O : Type w}

namespace Problem

variable [DecidableEq O] (P : Problem M E O)

/-- Validity of an adversary certificate at tolerance `ε`. -/
def IsAdversary (ε : ℚ) (lb : Finset M → ℚ≥0) : Prop :=
  ∀ S : Finset M, lb S = 0 ∨
    (ε < P.width S ∧ ∀ e : E, ∃ o ∈ P.outcomes S e, lb S ≤ P.cost e + lb (P.cell S e o))

variable {P}

/-- **Soundness of adversary certificates.** -/
theorem adversary_sound {ε : ℚ} (hε : 0 ≤ ε) {lb : Finset M → ℚ≥0} (hA : P.IsAdversary ε lb)
    (p : Policy E O) : ∀ (S : Finset M) (B : ℚ≥0), P.Succeeds ε p S → P.CostLE p S B → lb S ≤ B := by
  induction p with
  | stop =>
    intro S B hs _
    rcases hA S with h | ⟨hw, -⟩
    · rw [h]; exact zero_le B
    · exact absurd ((succeeds_stop_iff hε).1 hs) (not_le.2 hw)
  | test e f ih =>
    intro S B hs hc
    rcases hA S with h | ⟨hw, hall⟩
    · rw [h]; exact zero_le B
    obtain ⟨o, ho, hlb⟩ := hall e
    obtain ⟨m, hm⟩ := P.cell_nonempty_of_mem_outcomes ho
    have hce : P.cost e ≤ B := cost_le_of_costLE_test hc ((P.mem_cell).1 hm).1
    have := ih o _ _ (succeeds_child hs o) (costLE_child hc o)
    calc lb S ≤ P.cost e + lb (P.cell S e o) := hlb
      _ ≤ P.cost e + (B - P.cost e) := add_le_add_right this _
      _ = B := add_tsub_cancel_of_le hce

/-- Adversary certificates bound the exact value from below. -/
theorem adversary_le_value [Fintype E] {ε : ℚ} (hε : 0 ≤ ε) {lb : Finset M → ℚ≥0}
    (hA : P.IsAdversary ε lb) (S : Finset M) : (lb S : WithTop ℚ≥0) ≤ P.value ε S := by
  rcases eq_or_ne (P.value ε S) ⊤ with h | h
  · rw [h]; exact le_top
  obtain ⟨v, hv⟩ := WithTop.ne_top_iff_exists.1 h
  obtain ⟨p, hp, hc⟩ := (value_le_iff hε).1 hv.symm.le
  rw [← hv]
  exact WithTop.coe_le_coe.2 (adversary_sound hε hA p S v hp hc)

/-- The canonical adversary: the exact value truncated at `B`. -/
def truncValue [Fintype E] (P : Problem M E O) (ε : ℚ) (B : ℚ≥0) (S : Finset M) : ℚ≥0 :=
  (min (P.value ε S) (B : WithTop ℚ≥0)).untop
    (ne_top_of_le_ne_top WithTop.coe_ne_top (min_le_right _ _))

lemma coe_truncValue [Fintype E] (ε : ℚ) (B : ℚ≥0) (S : Finset M) :
    (P.truncValue ε B S : WithTop ℚ≥0) = min (P.value ε S) B := by
  simp [truncValue]

/-- **Completeness of adversary certificates.**  Every true lower bound
`B ≤ value ε S₀` is witnessed by an adversary certificate. -/
theorem adversary_complete [Fintype E] {ε : ℚ} (hε : 0 ≤ ε) (B : ℚ≥0) :
    P.IsAdversary ε (P.truncValue ε B) := by
  intro S
  by_cases hw : P.width S ≤ ε
  · left
    have := coe_truncValue (P := P) ε B S
    rw [value_of_width_le hw] at this
    have h0 : (min (0 : WithTop ℚ≥0) (B : WithTop ℚ≥0)) = ((0 : ℚ≥0) : WithTop ℚ≥0) :=
      min_eq_left (WithTop.coe_le_coe.2 (zero_le B))
    rw [h0] at this
    exact_mod_cast this
  right
  have hε' : ε < P.width S := lt_of_not_ge hw
  have hne : S.Nonempty := by
    by_contra h
    rw [Finset.not_nonempty_iff_eq_empty.1 h, width_empty] at hw
    exact hw hε
  refine ⟨hε', fun e => ?_⟩
  have hout : (P.outcomes S e).Nonempty := Finset.image_nonempty.2 hne
  by_cases hi : P.Informative S e
  · -- pick the worst outcome
    obtain ⟨o, ho, hmax⟩ := Finset.exists_mem_eq_sup _ hout (fun o => P.value ε (P.cell S e o))
    refine ⟨o, ho, ?_⟩
    have hval : P.value ε S ≤ P.cost e + P.value ε (P.cell S e o) := by
      rw [value_of_not_width_le hw]
      refine (Finset.inf_le (Finset.mem_filter.2 ⟨Finset.mem_univ e, hi⟩)).trans ?_
      simp only [backup, hmax, le_refl]
    rw [← WithTop.coe_le_coe, WithTop.coe_add, coe_truncValue, coe_truncValue]
    rcases le_total (P.value ε (P.cell S e o)) B with h | h
    · rw [min_eq_left h]
      exact (min_le_left _ _).trans hval
    · rw [min_eq_right h]
      calc min (P.value ε S) (B : WithTop ℚ≥0) ≤ B := min_le_right _ _
        _ ≤ (P.cost e : WithTop ℚ≥0) + B := le_add_self
  · obtain ⟨m, hm⟩ := hne
    refine ⟨P.obs m e, (P.mem_outcomes).2 ⟨m, hm, rfl⟩, ?_⟩
    rw [P.cell_eq_of_not_informative hi hm]
    exact le_add_self

lemma truncValue_eq [Fintype E] {ε : ℚ} {B : ℚ≥0} {S : Finset M}
    (h : (B : WithTop ℚ≥0) ≤ P.value ε S) : P.truncValue ε B S = B := by
  have := coe_truncValue (P := P) ε B S
  rw [min_eq_right h] at this
  exact_mod_cast this

/-- Lower bounds on the value are exactly those witnessed by adversary certificates. -/
theorem le_value_iff_adversary [Fintype E] {ε : ℚ} (hε : 0 ≤ ε) {S : Finset M} {B : ℚ≥0} :
    (B : WithTop ℚ≥0) ≤ P.value ε S ↔ ∃ lb, P.IsAdversary ε lb ∧ lb S = B := by
  constructor
  · intro h
    exact ⟨P.truncValue ε B, adversary_complete hε B, truncValue_eq h⟩
  · rintro ⟨lb, hA, rfl⟩
    exact adversary_le_value hε hA S

end Problem

end PRISM

namespace PRISM.Problem

variable {M : Type*} {E : Type*} {O : Type*} [DecidableEq O] {P : Problem M E O}

/-- **Lower bound for policies forced to start with a given experiment.**  If a
policy starts with `e` and succeeds on `K` with cost `≤ B`, then for every feasible
outcome `o` and every adversary certificate, `c(e) + lb(K(e,o)) ≤ B`.  Used to
certify that a particular first move (e.g. the greedy choice) is suboptimal. -/
theorem adversary_test_bound {ε : ℚ} (hε : 0 ≤ ε) {lb : Finset M → ℚ≥0}
    (hA : P.IsAdversary ε lb) {e : E} {f : O → Policy E O} {K : Finset M} {B : ℚ≥0}
    (hs : P.Succeeds ε (.test e f) K) (hc : P.CostLE (.test e f) K B) {o : O}
    (ho : o ∈ P.outcomes K e) : P.cost e + lb (P.cell K e o) ≤ B := by
  obtain ⟨m, hm⟩ := P.cell_nonempty_of_mem_outcomes ho
  have hce : P.cost e ≤ B := cost_le_of_costLE_test hc ((P.mem_cell).1 hm).1
  have := adversary_sound hε hA (f o) _ _ (succeeds_child hs o) (costLE_child hc o)
  calc P.cost e + lb (P.cell K e o) ≤ P.cost e + (B - P.cost e) := add_le_add_right this _
    _ = B := add_tsub_cancel_of_le hce

end PRISM.Problem
