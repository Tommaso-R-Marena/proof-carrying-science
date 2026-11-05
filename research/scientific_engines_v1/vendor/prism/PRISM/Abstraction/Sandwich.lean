module

public import PRISM.Identifiability.Impossibility

/-!
# Abstractions: the optimality sandwich and exact query-aware quotients

1. `optimality_sandwich`: if `K_lo ⊆ K ⊆ K_hi`, a policy succeeds on `K_hi` with
   worst-case cost `≤ B`, and every successful policy on `K_lo` costs `≥ B`, then the
   policy is globally minimax optimal on `K` and `value ε K = B` — although `K` itself
   is never inspected.
2. `value_image`: an *exact abstraction* (a map preserving observations, query and
   cost) preserves the optimal value; in particular the quotient of `K` by
   (observation signature, query value) is exact (`value_signatureQuotient`).
3. `signature_only_quotient_unsound`: merging models by observation signature alone
   (ignoring the query) is *not* exact.
-/

@[expose] public section

namespace PRISM

universe u v w u'

variable {M : Type u} {E : Type v} {O : Type w}

namespace Problem

variable {P : Problem M E O} [DecidableEq O]

/-- **Optimality sandwich (policy form).**  Inclusions `K_lo ⊆ K ⊆ K_hi`; a policy
succeeding on the over-approximation `K_hi` with cost `≤ B`; a lower bound `B` valid
for the under-approximation `K_lo`.  Then the policy succeeds on `K`, costs at most
`B` there, and no successful policy on `K` costs less than `B`. -/
theorem optimality_sandwich {ε : ℚ} {Klo K Khi : Finset M} (h₁ : Klo ⊆ K) (h₂ : K ⊆ Khi)
    {p : Policy E O} {B : ℚ≥0} (hp : P.Succeeds ε p Khi) (hc : P.CostLE p Khi B)
    (hlow : ∀ p' : Policy E O, P.Succeeds ε p' Klo → B ≤ P.worstCost p' Klo) :
    P.Succeeds ε p K ∧ P.CostLE p K B ∧
      ∀ p' : Policy E O, P.Succeeds ε p' K → B ≤ P.worstCost p' K := by
  refine ⟨succeeds_mono h₂ hp, costLE_mono h₂ hc, fun p' hp' => ?_⟩
  exact (hlow p' (succeeds_mono h₁ hp')).trans (Finset.sup_mono h₁)

/-- **Optimality sandwich (value form).**  Under the same hypotheses, with the
lower bound expressed through the value of the core, the exact optimal value of `K`
is `B`. -/
theorem value_eq_of_sandwich [Fintype E] {ε : ℚ} (hε : 0 ≤ ε) {Klo K Khi : Finset M}
    (h₁ : Klo ⊆ K) (h₂ : K ⊆ Khi) {p : Policy E O} {B : ℚ≥0}
    (hp : P.Succeeds ε p Khi) (hc : P.CostLE p Khi B) (hlow : (B : WithTop ℚ≥0) ≤ P.value ε Klo) :
    P.value ε K = B := by
  apply le_antisymm
  · exact (value_le_iff hε).2 ⟨p, succeeds_mono h₂ hp, costLE_mono h₂ hc⟩
  · exact hlow.trans (value_mono hε h₁)

/-- The sandwich inequalities `V(K_lo) ≤ V(K) ≤ V(K_hi)` (monotone abstraction). -/
theorem value_sandwich [Fintype E] {ε : ℚ} (hε : 0 ≤ ε) {Klo K Khi : Finset M}
    (h₁ : Klo ⊆ K) (h₂ : K ⊆ Khi) :
    P.value ε Klo ≤ P.value ε K ∧ P.value ε K ≤ P.value ε Khi :=
  ⟨value_mono hε h₁, value_mono hε h₂⟩

/-! ## Exact abstractions between model spaces -/

variable {N : Type u'} [DecidableEq N]

/-- `f : M → N` is an exact abstraction from problem `P` to problem `Q` if it
preserves every observation, the query and the costs. -/
structure IsExactAbstraction (P : Problem M E O) (Q : Problem N E O) (f : M → N) : Prop where
  obs : ∀ m e, Q.obs (f m) e = P.obs m e
  q : ∀ m, Q.q (f m) = P.q m
  cost : ∀ e, Q.cost e = P.cost e

variable {Q : Problem N E O} {f : M → N}

omit [DecidableEq O] in
lemma IsExactAbstraction.width_image (hf : IsExactAbstraction P Q f) (K : Finset M) :
    Q.width (K.image f) = P.width K := by
  by_cases hK : K.Nonempty
  · have hK' : (K.image f).Nonempty := Finset.image_nonempty.2 hK
    simp only [width, hK, hK', dite_true, Finset.sup'_image, Finset.inf'_image]
    have : Q.q ∘ f = P.q := funext hf.q
    simp only [this]
  · have : K = ∅ := Finset.not_nonempty_iff_eq_empty.1 hK
    subst this; simp [width]

lemma IsExactAbstraction.cell_image (hf : IsExactAbstraction P Q f) (K : Finset M) (e : E)
    (o : O) : Q.cell (K.image f) e o = (P.cell K e o).image f := by
  simp only [cell, Finset.filter_image, hf.obs]

lemma IsExactAbstraction.terminal_image (hf : IsExactAbstraction P Q f) (p : Policy E O)
    (m : M) (K : Finset M) : Q.terminal p (f m) (K.image f) = (P.terminal p m K).image f := by
  induction p generalizing K with
  | stop => rfl
  | test e g ih => simp only [terminal, hf.obs, hf.cell_image, ih]

omit [DecidableEq O] [DecidableEq N] in
lemma IsExactAbstraction.pathCost_eq (hf : IsExactAbstraction P Q f) (p : Policy E O)
    (m : M) : Q.pathCost p (f m) = P.pathCost p m := by
  induction p with
  | stop => rfl
  | test e g ih => simp only [pathCost, hf.obs, hf.cost, ih]

lemma IsExactAbstraction.succeeds_iff (hf : IsExactAbstraction P Q f) {ε : ℚ}
    (p : Policy E O) (K : Finset M) : Q.Succeeds ε p (K.image f) ↔ P.Succeeds ε p K := by
  simp only [Succeeds, Finset.forall_mem_image, hf.terminal_image, hf.width_image]

omit [DecidableEq O] in
lemma IsExactAbstraction.costLE_iff (hf : IsExactAbstraction P Q f)
    (p : Policy E O) (K : Finset M) (B : ℚ≥0) : Q.CostLE p (K.image f) B ↔ P.CostLE p K B := by
  simp only [CostLE, Finset.forall_mem_image, hf.pathCost_eq]

/-- **Exact abstraction theorem.**  Exact abstractions preserve the minimax optimal
experimental value (and, by `succeeds_iff`/`costLE_iff`, transport optimal policies
in both directions). -/
theorem IsExactAbstraction.value_image [Fintype E] (hf : IsExactAbstraction P Q f) {ε : ℚ}
    (hε : 0 ≤ ε) (K : Finset M) : Q.value ε (K.image f) = P.value ε K := by
  have key : ∀ v : ℚ≥0, Q.value ε (K.image f) ≤ v ↔ P.value ε K ≤ v := by
    intro v
    rw [value_le_iff hε, value_le_iff hε]
    simp only [hf.succeeds_iff, hf.costLE_iff]
  rcases eq_or_ne (P.value ε K) ⊤ with h | h
  · rw [h]
    by_contra hne
    obtain ⟨v, hv⟩ := WithTop.ne_top_iff_exists.1 hne
    have := (key v).1 hv.symm.le
    rw [h] at this; simp at this
  · obtain ⟨v, hv⟩ := WithTop.ne_top_iff_exists.1 h
    rw [← hv]
    apply le_antisymm ((key v).2 hv.symm.le)
    rcases eq_or_ne (Q.value ε (K.image f)) ⊤ with h' | h'
    · rw [h']; exact le_top
    obtain ⟨w, hw⟩ := WithTop.ne_top_iff_exists.1 h'
    rw [← hw]
    have := (key w).1 hw.symm.le
    rw [← hv] at this
    exact this

/-- The canonical query-aware quotient problem on (signature, query value) pairs. -/
def signatureQuotient (P : Problem M E O) : Problem ((E → O) × ℚ) E O where
  obs n e := n.1 e
  q n := n.2
  cost := P.cost

/-- The quotient map `m ↦ (obs m, q m)`. -/
def sigMap (P : Problem M E O) (m : M) : (E → O) × ℚ := (P.obs m, P.q m)

omit [DecidableEq O] in
lemma sigMap_isExactAbstraction (P : Problem M E O) :
    IsExactAbstraction P P.signatureQuotient P.sigMap :=
  ⟨fun _ _ => rfl, fun _ => rfl, fun _ => rfl⟩

/-- **Exact query-aware quotient**: collapsing models with identical observation
signature *and* identical query value preserves the optimal experimental value. -/
theorem value_signatureQuotient [Fintype E] [DecidableEq (E → O)] {ε : ℚ} (hε : 0 ≤ ε)
    (K : Finset M) : P.signatureQuotient.value ε (K.image P.sigMap) = P.value ε K :=
  (sigMap_isExactAbstraction P).value_image hε K

end Problem

/-- **Negative result: signature-only quotients are unsound.**  Merging models with
identical observation signatures but different query values changes the optimal
value: here the concrete problem is impossible (`⊤`) while the merged problem is
already solved (`0`). -/
theorem signature_only_quotient_unsound :
    ∃ (P : Problem Bool Unit Unit) (Q : Problem Unit Unit Unit) (f : Bool → Unit),
      (∀ m e, Q.obs (f m) e = P.obs m e) ∧ (∀ e, Q.cost e = P.cost e) ∧
      P.value 0 {false, true} = ⊤ ∧ Q.value 0 (({false, true} : Finset Bool).image f) = 0 := by
  refine ⟨⟨fun _ _ => (), fun b => if b then 1 else 0, fun _ => 1⟩,
    ⟨fun _ _ => (), fun _ => 0, fun _ => 1⟩, fun _ => (), fun _ _ => rfl, fun _ => rfl, ?_, ?_⟩
  · refine (Problem.value_eq_top_iff le_rfl).2 ?_
    intro p
    exact Problem.impossibility (m₁ := true) (m₂ := false) (by simp) (by simp)
      (fun _ => rfl) (by norm_num) p
  · apply Problem.value_of_width_le
    simp [Problem.width]

end PRISM
