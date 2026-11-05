module

public import PRISM.Optimality.Bellman

/-!
# Observational equivalence, impossibility, and exact identifiability

* `obsEquiv_mem_terminal`: no adaptive policy ever separates observationally
  equivalent models.
* `impossibility`: two observationally equivalent admissible models whose query
  values differ by more than `ε` make every adaptive strategy fail.
* `identifiable_iff`: a successful finite adaptive strategy exists **iff** every
  observational-equivalence class inside `K` has query width at most `ε`.
* `impossibilityCert_complete`: hence impossibility always has a *two-model*
  certificate, checkable in `O(|E|)` observation comparisons, without enumerating
  any strategies.
-/

@[expose] public section

namespace PRISM

universe u v w

variable {M : Type u} {E : Type v} {O : Type w}

/-- The nonadaptive policy running a fixed list of experiments. -/
def Policy.testAll : List E → Policy E O
  | [] => .stop
  | e :: l => .test e (fun _ => Policy.testAll l)

namespace Problem

variable (P : Problem M E O)

/-- Observational equivalence: identical predictions for every permitted experiment. -/
def ObsEquiv (m₁ m₂ : M) : Prop := ∀ e, P.obs m₁ e = P.obs m₂ e

variable {P} [DecidableEq O]

omit [DecidableEq O] in
lemma obsEquiv_symm {m₁ m₂ : M} (h : P.ObsEquiv m₁ m₂) : P.ObsEquiv m₂ m₁ :=
  fun e => (h e).symm

/-- No adaptive policy, however it chooses experiments based on earlier outcomes,
separates two observationally equivalent models. -/
theorem obsEquiv_mem_terminal (p : Policy E O) {m₁ m₂ : M} {K : Finset M}
    (h₂ : m₂ ∈ K) (h : P.ObsEquiv m₁ m₂) : m₂ ∈ P.terminal p m₁ K := by
  induction p generalizing K with
  | stop => exact h₂
  | test e f ih => exact ih _ ((P.mem_cell).2 ⟨h₂, (h e).symm⟩)

/-- **Impossibility theorem.**  If two admissible models are observationally
equivalent but their query values differ by more than `ε`, then *no* finite adaptive
strategy using the permitted deterministic experiments guarantees final width `≤ ε`. -/
theorem impossibility {ε : ℚ} {K : Finset M} {m₁ m₂ : M} (h₁ : m₁ ∈ K) (h₂ : m₂ ∈ K)
    (h : P.ObsEquiv m₁ m₂) (hgap : ε < P.q m₁ - P.q m₂) (p : Policy E O) :
    ¬ P.Succeeds ε p K := by
  intro hs
  have hw := hs m₁ h₁
  have := P.sub_le_width (mem_terminal_self p h₁) (obsEquiv_mem_terminal p h₂ h)
  linarith

lemma terminal_testAll (l : List E) (m : M) (K : Finset M) :
    P.terminal (Policy.testAll l) m K = K.filter (fun m' => ∀ e ∈ l, P.obs m' e = P.obs m e) := by
  induction l generalizing K with
  | nil => simp [Policy.testAll, terminal]
  | cons e l ih =>
    simp only [Policy.testAll, terminal, ih]
    ext x
    simp only [Finset.mem_filter, mem_cell, List.mem_cons, forall_eq_or_imp]
    tauto

/-- **Exact characterization of finite identifiability at tolerance `ε`.**
A successful finite adaptive strategy exists iff every pair of observationally
equivalent admissible models has query values within `ε`, i.e. iff every
observational-equivalence class of `K` has width `≤ ε`.  (Sufficiency is witnessed
by the nonadaptive strategy running every experiment once.) -/
theorem identifiable_iff [Fintype E] {ε : ℚ} (hε : 0 ≤ ε) {K : Finset M} :
    (∃ p : Policy E O, P.Succeeds ε p K) ↔
      ∀ m₁ ∈ K, ∀ m₂ ∈ K, P.ObsEquiv m₁ m₂ → P.q m₁ - P.q m₂ ≤ ε := by
  constructor
  · rintro ⟨p, hp⟩ m₁ h₁ m₂ h₂ h
    by_contra hc
    exact impossibility h₁ h₂ h (lt_of_not_ge hc) p hp
  · intro H
    classical
    refine ⟨Policy.testAll (O := O) Finset.univ.toList, fun m _ => ?_⟩
    rw [terminal_testAll, P.width_le_iff hε]
    intro a ha b hb
    simp only [Finset.mem_filter, Finset.mem_toList, Finset.mem_univ, true_implies] at ha hb
    exact H a ha.1 b hb.1 (fun e => (ha.2 e).trans (hb.2 e).symm)

omit [DecidableEq O] in
/-- Running a fixed list of experiments costs the sum of their costs. -/
theorem pathCost_testAll (l : List E) (m : M) :
    P.pathCost (Policy.testAll (O := O) l) m = (l.map P.cost).sum := by
  induction l with
  | nil => rfl
  | cons e l ih => simp [Policy.testAll, pathCost, ih]

/-- A nonadaptive design fails as soon as two admissible models agree on all its
experiments but differ in query value by more than `ε`. -/
theorem testAll_fails {ε : ℚ} {l : List E} {K : Finset M} {m₁ m₂ : M} (h₁ : m₁ ∈ K)
    (h₂ : m₂ ∈ K) (hag : ∀ e ∈ l, P.obs m₂ e = P.obs m₁ e) (hgap : ε < P.q m₁ - P.q m₂) :
    ¬ P.Succeeds ε (Policy.testAll l) K := by
  intro hs
  have hw := hs m₁ h₁
  have hm₂ : m₂ ∈ P.terminal (Policy.testAll l) m₁ K := by
    rw [terminal_testAll]; exact Finset.mem_filter.2 ⟨h₂, hag⟩
  have := P.sub_le_width (mem_terminal_self _ h₁) hm₂
  linarith

/-- Identifiability in terms of the Bellman value. -/
theorem value_ne_top_iff [Fintype E] {ε : ℚ} (hε : 0 ≤ ε) {K : Finset M} :
    P.value ε K ≠ ⊤ ↔ ∀ m₁ ∈ K, ∀ m₂ ∈ K, P.ObsEquiv m₁ m₂ → P.q m₁ - P.q m₂ ≤ ε := by
  rw [← identifiable_iff hε, Ne, value_eq_top_iff hε]
  push_neg
  rfl

/-- A compact impossibility certificate: two admissible, observationally equivalent
models whose query values differ by more than `ε`. -/
structure ImpossibilityCert (P : Problem M E O) (ε : ℚ) (K : Finset M) where
  m₁ : M
  m₂ : M
  mem₁ : m₁ ∈ K
  mem₂ : m₂ ∈ K
  equiv : P.ObsEquiv m₁ m₂
  gap : ε < P.q m₁ - P.q m₂

/-- Soundness of impossibility certificates. -/
theorem ImpossibilityCert.sound [Fintype E] {ε : ℚ} (hε : 0 ≤ ε) {K : Finset M}
    (c : ImpossibilityCert P ε K) :
    (∀ p : Policy E O, ¬ P.Succeeds ε p K) ∧ P.value ε K = ⊤ :=
  ⟨impossibility c.mem₁ c.mem₂ c.equiv c.gap,
    (value_eq_top_iff hε).2 (impossibility c.mem₁ c.mem₂ c.equiv c.gap)⟩

/-- **Completeness of two-model impossibility certificates**: whenever no adaptive
strategy can succeed, a two-model certificate exists.  No enumeration of strategies
is ever needed to certify impossibility. -/
theorem impossibilityCert_complete [Fintype E] {ε : ℚ} (hε : 0 ≤ ε) {K : Finset M}
    (h : ∀ p : Policy E O, ¬ P.Succeeds ε p K) : Nonempty (ImpossibilityCert P ε K) := by
  have : ¬ ∀ m₁ ∈ K, ∀ m₂ ∈ K, P.ObsEquiv m₁ m₂ → P.q m₁ - P.q m₂ ≤ ε := by
    rw [← identifiable_iff hε]; rintro ⟨p, hp⟩; exact h p hp
  push_neg at this
  obtain ⟨m₁, h₁, m₂, h₂, he, hg⟩ := this
  exact ⟨⟨m₁, m₂, h₁, h₂, he, hg⟩⟩

end Problem

end PRISM
