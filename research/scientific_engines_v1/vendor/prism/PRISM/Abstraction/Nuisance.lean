module

public import PRISM.Abstraction.Sandwich

/-!
# Nuisance-factor elimination (a compositional exactness theorem)

Suppose the model space factors as `A × Z`. The query depends only on the
`A`-component. Every experiment is either *relevant* (its outcome depends only on
`a`) or *nuisance* (its outcome depends only on `z`). Then for any version space of
product form `KA ×ˢ KZ` with `z₀ ∈ KZ`:

`value ε (KA ×ˢ KZ) = value ε (KA ×ˢ {z₀})`

(`value_prod_eq_section`). An optimal policy for the single section is optimal
for the whole product (`section_policy_lifts`). In particular the optimal cost,
an optimal policy, and hence the size of an optimality certificate do not depend
on `|KZ|`. This is the structure behind the lesion benchmark family.

This is **not** an instance of `IsExactAbstraction`: the projection
`(a, z) ↦ a` does not preserve the outcomes of nuisance experiments. The proof
instead uses the fact that only-informative policies on a section never run
nuisance experiments (`exists_optimal_onlyInformative`), and simulates such a
policy on the product.
-/

@[expose] public section

namespace PRISM

universe u v w u'

variable {A : Type u} {Z : Type u'} {E : Type v} {O : Type w}

namespace Problem

variable [DecidableEq A] [DecidableEq O] {P : Problem (A × Z) E O}

/-- Every experiment is relevant (outcome independent of `z`) or nuisance
(outcome independent of `a`). -/
def SplitsExperiments (P : Problem (A × Z) E O) : Prop :=
  ∀ e, (∀ a z z', P.obs (a, z) e = P.obs (a, z') e) ∨ (∀ a a' z, P.obs (a, z) e = P.obs (a', z) e)

/-- The query depends only on the `A`-component. -/
def QueryOnFirst (P : Problem (A × Z) E O) : Prop := ∀ a z z', P.q (a, z) = P.q (a, z')

/-- Lift a version space to the product with the nuisance set `KZ`. -/
def liftZ (S : Finset (A × Z)) (KZ : Finset Z) : Finset (A × Z) := S.image Prod.fst ×ˢ KZ

lemma mem_liftZ {S : Finset (A × Z)} {KZ : Finset Z} {z₀ : Z} (hS : ∀ x ∈ S, x.2 = z₀)
    {a : A} {z : Z} : (a, z) ∈ liftZ S KZ ↔ (a, z₀) ∈ S ∧ z ∈ KZ := by
  simp only [liftZ, Finset.mem_product, Finset.mem_image]
  constructor
  · rintro ⟨⟨x, hx, rfl⟩, hz⟩
    refine ⟨?_, hz⟩
    have := hS x hx
    rcases x with ⟨a', z'⟩
    simp only at this
    subst this
    exact hx
  · rintro ⟨h, hz⟩
    exact ⟨⟨(a, z₀), h, rfl⟩, hz⟩

omit [DecidableEq A] [DecidableEq O] in
/-- On a section (all `z`-components equal), an informative experiment is relevant. -/
lemma relevant_of_informative (hsp : P.SplitsExperiments) {S : Finset (A × Z)} {z₀ : Z}
    (hS : ∀ x ∈ S, x.2 = z₀) {e : E} (hinf : P.Informative S e) :
    ∀ a z z', P.obs (a, z) e = P.obs (a, z') e := by
  rcases hsp e with h | h
  · exact h
  · exfalso
    obtain ⟨x, hx, y, hy, hxy⟩ := hinf
    rcases x with ⟨a, zx⟩
    rcases y with ⟨b, zy⟩
    have h1 : zx = z₀ := hS _ hx
    have h2 : zy = z₀ := hS _ hy
    rw [h1, h2] at hxy
    exact hxy (h a b z₀)

/-- Simulation lemma: an only-informative policy on a section behaves identically
on the lifted product version space. -/
theorem terminal_liftZ (hsp : P.SplitsExperiments) (KZ : Finset Z) (z₀ : Z) (p : Policy E O) :
    ∀ S : Finset (A × Z), (∀ x ∈ S, x.2 = z₀) → P.OnlyInformative p S →
      ∀ a z, (a, z₀) ∈ S →
        P.terminal p (a, z) (liftZ S KZ) = liftZ (P.terminal p (a, z₀) S) KZ ∧
        P.pathCost p (a, z) = P.pathCost p (a, z₀) := by
  induction p with
  | stop => intro S _ _ a z _; simp [terminal, pathCost]
  | test e f ih =>
    intro S hS hp a z ha
    obtain ⟨hinf, hch⟩ := hp
    have hrel := relevant_of_informative hsp hS hinf
    have hobs : P.obs (a, z) e = P.obs (a, z₀) e := hrel a z z₀
    set o := P.obs (a, z₀) e with ho
    have hcellS : ∀ x ∈ P.cell S e o, x.2 = z₀ := fun x hx => hS x (P.cell_subset S e o hx)
    have hcell : P.cell (liftZ S KZ) e o = liftZ (P.cell S e o) KZ := by
      ext ⟨a', z'⟩
      rw [mem_cell, mem_liftZ hS, mem_liftZ hcellS, mem_cell]
      constructor
      · rintro ⟨⟨h1, h2⟩, h3⟩
        exact ⟨⟨h1, by rw [← h3, hrel a' z' z₀]⟩, h2⟩
      · rintro ⟨⟨h1, h3⟩, h2⟩
        exact ⟨⟨h1, h2⟩, by rw [hrel a' z' z₀, h3]⟩
    have hmem : (a, z₀) ∈ P.cell S e o := (P.mem_cell).2 ⟨ha, rfl⟩
    have hout : o ∈ P.outcomes S e := (P.mem_outcomes).2 ⟨(a, z₀), ha, rfl⟩
    obtain ⟨ih1, ih2⟩ := ih o (P.cell S e o) hcellS (hch o hout) a z hmem
    refine ⟨?_, ?_⟩
    · simp only [terminal]
      rw [hobs, ← ho, hcell, ih1]
    · simp only [pathCost]
      rw [hobs, ← ho, ih2]

omit [DecidableEq O] in
/-- Lifting preserves "width ≤ ε" when the query depends only on `a` and `KZ ≠ ∅`. -/
lemma width_liftZ_le_iff (hq : P.QueryOnFirst) {S : Finset (A × Z)} {KZ : Finset Z} {z₀ : Z}
    (hS : ∀ x ∈ S, x.2 = z₀) (hKZ : KZ.Nonempty) {ε : ℚ} (hε : 0 ≤ ε) :
    P.width (liftZ S KZ) ≤ ε ↔ P.width S ≤ ε := by
  rw [P.width_le_iff hε, P.width_le_iff hε]
  obtain ⟨zz, hzz⟩ := hKZ
  constructor
  · intro h x hx y hy
    rcases x with ⟨a, zx⟩
    rcases y with ⟨b, zy⟩
    have h1 : zx = z₀ := hS _ hx
    have h2 : zy = z₀ := hS _ hy
    rw [h1] at hx ⊢
    rw [h2] at hy ⊢
    have := h (a, zz) ((mem_liftZ hS).2 ⟨hx, hzz⟩) (b, zz) ((mem_liftZ hS).2 ⟨hy, hzz⟩)
    rwa [hq a zz z₀, hq b zz z₀] at this
  · rintro h ⟨a, z⟩ hx ⟨b, z'⟩ hy
    rw [mem_liftZ hS] at hx hy
    have := h _ hx.1 _ hy.1
    rwa [hq a z z₀, hq b z' z₀]

/-- **Policy lifting.** An only-informative policy that succeeds on the section
`KA ×ˢ {z₀}` with cost bound `B` also succeeds on `KA ×ˢ KZ` with the same cost
bound, for every `KZ ∋ z₀`. -/
theorem section_policy_lifts (hsp : P.SplitsExperiments) (hq : P.QueryOnFirst)
    {ε : ℚ} (hε : 0 ≤ ε) {KA : Finset A} {KZ : Finset Z} {z₀ : Z} (hz₀ : z₀ ∈ KZ)
    {p : Policy E O} {B : ℚ≥0} (hp : P.OnlyInformative p (KA ×ˢ {z₀}))
    (hs : P.Succeeds ε p (KA ×ˢ {z₀})) (hc : P.CostLE p (KA ×ˢ {z₀}) B) :
    P.Succeeds ε p (KA ×ˢ KZ) ∧ P.CostLE p (KA ×ˢ KZ) B := by
  have hS : ∀ x ∈ KA ×ˢ ({z₀} : Finset Z), x.2 = z₀ := by
    intro x hx
    simpa using (Finset.mem_product.1 hx).2
  have hlift : liftZ (KA ×ˢ {z₀}) KZ = KA ×ˢ KZ := by
    ext ⟨a, z⟩
    rw [mem_liftZ hS]
    simp
  have hsec : ∀ {a z}, (a, z) ∈ KA ×ˢ KZ → (a, z₀) ∈ KA ×ˢ ({z₀} : Finset Z) := by
    intro a z h
    simpa using (Finset.mem_product.1 h).1
  refine ⟨?_, ?_⟩
  · rintro ⟨a, z⟩ hm
    obtain ⟨h1, -⟩ := terminal_liftZ hsp KZ z₀ p _ hS hp a z (hsec hm)
    rw [← hlift, h1]
    have hT : ∀ x ∈ P.terminal p (a, z₀) (KA ×ˢ {z₀}), x.2 = z₀ :=
      fun x hx => hS x (terminal_subset p _ _ hx)
    exact (width_liftZ_le_iff hq hT ⟨z₀, hz₀⟩ hε).2 (hs _ (hsec hm))
  · rintro ⟨a, z⟩ hm
    obtain ⟨-, h2⟩ := terminal_liftZ hsp KZ z₀ p _ hS hp a z (hsec hm)
    rw [h2]
    exact hc _ (hsec hm)

/-- **Nuisance-factor elimination.** Under `SplitsExperiments` and `QueryOnFirst`,
the exact minimax value on a product version space equals the value on any single
nuisance section. -/
theorem value_prod_eq_section [Fintype E] (hsp : P.SplitsExperiments) (hq : P.QueryOnFirst)
    {ε : ℚ} (hε : 0 ≤ ε) (KA : Finset A) {KZ : Finset Z} {z₀ : Z} (hz₀ : z₀ ∈ KZ) :
    P.value ε (KA ×ˢ KZ) = P.value ε (KA ×ˢ {z₀}) := by
  apply le_antisymm
  · cases hv : P.value ε (KA ×ˢ {z₀}) with
    | top => exact le_top
    | coe v =>
      obtain ⟨⟨p, hs, hcost, hp⟩, -⟩ := P.value_optimal hε hv
      have hc : P.CostLE p (KA ×ˢ {z₀}) v := by
        rw [costLE_iff, hcost]
      obtain ⟨hs', hc'⟩ := section_policy_lifts hsp hq hε hz₀ hp hs hc
      exact (P.value_le_iff hε).2 ⟨p, hs', hc'⟩
  · apply P.value_mono hε
    intro x hx
    rw [Finset.mem_product] at hx ⊢
    exact ⟨hx.1, by rw [Finset.mem_singleton.1 hx.2]; exact hz₀⟩

/-- **The splitting hypothesis cannot be dropped.** If an experiment mixes the
factors (here: it reports `a xor z`), the query is identifiable on a single
nuisance section but not on the product. -/
theorem nuisance_mixing_counterexample :
    ∃ P : Problem (Bool × Bool) Unit Bool, P.QueryOnFirst ∧
      P.value 0 (Finset.univ ×ˢ Finset.univ) = ⊤ ∧
      P.value 0 (Finset.univ ×ˢ {false}) ≠ ⊤ := by
  refine ⟨⟨fun m _ => xor m.1 m.2, fun m => if m.1 then 1 else 0, fun _ => 1⟩, ?_, ?_, ?_⟩
  · intro a z z'
    rfl
  · refine (value_eq_top_iff le_rfl).2 fun p => ?_
    exact impossibility (m₁ := (true, true)) (m₂ := (false, false)) (by simp) (by simp)
      (fun _ => rfl) (by norm_num) p
  · refine (value_ne_top_iff le_rfl).2 ?_
    rintro ⟨a, z⟩ h1 ⟨b, z'⟩ h2 heq
    simp only [Finset.mem_product, Finset.mem_univ, Finset.mem_singleton, true_and] at h1 h2
    subst h1 h2
    have := heq ()
    cases a <;> cases b <;> simp_all

end Problem

end PRISM
