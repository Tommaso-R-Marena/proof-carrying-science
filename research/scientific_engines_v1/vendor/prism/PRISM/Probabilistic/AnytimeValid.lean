module

public import PRISM.Experiments.Policy

/-!
# Noisy experiments: anytime-valid certification under adaptive design

Each candidate model `m` assigns an exact rational outcome distribution
`lik m e : O → ℚ` to each experiment `e`.  An adaptive experimental procedure is a
`Policy E O` (decision tree): it chooses each experiment from the outcomes observed
so far, and *stops whenever it likes* (optional stopping is built in: the
stopping rule is the shape of the tree).  Under model `m` the probability of a
history `h = [(e₁,o₁),…,(e_t,o_t)]` is `∏ lik m eᵢ oᵢ`.

Fix a pre-declared prior/mixing weight `π` on models and let
`Q(h) = ∑ₘ π m · P_m(h)` be the mixture likelihood.  Model `m` is **rejected** at `h`
if `P_m(h) ≤ α · Q(h)` (i.e. the mixture e-value `Q(h)/P_m(h)` is at least `1/α`).

* `reject_at_stop_le`: for every adaptive procedure and every true model `m⋆`,
  `P_{m⋆}(m⋆ rejected when the procedure stops) ≤ α`.
* `reject_ever_le` (anytime validity): `P_{m⋆}(m⋆ rejected at *some* time) ≤ α`.
* `false_certification_le`: certifying a claim `C` once every model violating `C` has
  been rejected is wrong with probability at most `α`, whatever the true model.
* `posthoc_alternative_invalid`: rejecting with a *post-hoc maximized* alternative
  (`P_m(h) ≤ α · maxₘ' P_m'(h)`) is **not** valid — explicit counterexample.

These guarantees are probabilistic and are kept separate from the deterministic
certificates of the rest of PRISM.  The proofs are the finite-tree form of the
likelihood-ratio / Ville-type argument: the mixture likelihood is a martingale
under the tree, and rejection sets are bounded in mixture mass.
-/

@[expose] public section

namespace PRISM

universe u v w

variable {M : Type u} {E : Type v} {O : Type w}

/-- A finite noisy scientific problem with exact rational likelihoods. -/
structure NoisyProblem (M : Type u) (E : Type v) (O : Type w) [Fintype O] where
  lik : M → E → O → ℚ
  lik_nonneg : ∀ m e o, 0 ≤ lik m e o
  lik_sum : ∀ m e, ∑ o, lik m e o = 1

namespace NoisyProblem

variable [Fintype O] (N : NoisyProblem M E O)

/-- Probability of a history under model `m`. -/
def histProb (m : M) (h : List (E × O)) : ℚ := (h.map fun x => N.lik m x.1 x.2).prod

/-- Integrate a function of the terminal history over the leaves of an adaptive
procedure started at history `h` (the weight `w` already contains the probability). -/
def leafSum : Policy E O → (List (E × O) → ℚ) → List (E × O) → ℚ
  | .stop, w, h => w h
  | .test e f, w, h => ∑ o, leafSum (f o) w (h ++ [(e, o)])

variable {N}

lemma histProb_nil (m : M) : N.histProb m [] = 1 := by simp [histProb]

lemma histProb_snoc (m : M) (h : List (E × O)) (e : E) (o : O) :
    N.histProb m (h ++ [(e, o)]) = N.histProb m h * N.lik m e o := by
  simp [histProb, List.prod_append]

lemma histProb_nonneg (m : M) (h : List (E × O)) : 0 ≤ N.histProb m h := by
  unfold histProb
  apply List.prod_nonneg
  intro x hx
  obtain ⟨y, -, rfl⟩ := List.mem_map.1 hx
  exact N.lik_nonneg _ _ _

/-- Martingale weights: one more experiment preserves total weight. -/
def IsMartingale (w : List (E × O) → ℚ) : Prop := ∀ h e, ∑ o, w (h ++ [(e, o)]) = w h

lemma leafSum_martingale {w : List (E × O) → ℚ} (hw : IsMartingale w) (p : Policy E O) :
    ∀ h, leafSum p w h = w h := by
  induction p with
  | stop => intro h; rfl
  | test e f ih =>
    intro h
    simp only [leafSum, ih]
    exact hw h e

lemma leafSum_mono {w w' : List (E × O) → ℚ} (hle : ∀ h, w h ≤ w' h) (p : Policy E O) :
    ∀ h, leafSum p w h ≤ leafSum p w' h := by
  induction p with
  | stop => intro h; exact hle h
  | test e f ih =>
    intro h
    exact Finset.sum_le_sum fun o _ => ih o _

lemma leafSum_const_mul (c : ℚ) (w : List (E × O) → ℚ) (p : Policy E O) :
    ∀ h, leafSum p (fun h => c * w h) h = c * leafSum p w h := by
  induction p with
  | stop => intro h; rfl
  | test e f ih =>
    intro h
    simp only [leafSum, ih, Finset.mul_sum]

lemma histProb_martingale (m : M) : IsMartingale (N.histProb m) := by
  intro h e
  simp only [histProb_snoc, ← Finset.mul_sum, N.lik_sum, mul_one]

/-- Under any adaptive procedure, the leaf probabilities of model `m` sum to one. -/
theorem leafSum_histProb (m : M) (p : Policy E O) : leafSum p (N.histProb m) [] = 1 := by
  rw [leafSum_martingale (histProb_martingale m), histProb_nil]

variable [Fintype M]

variable (N)

/-- Mixture likelihood with pre-declared weights `π`. -/
def mixProb (π : M → ℚ) (h : List (E × O)) : ℚ := ∑ m, π m * N.histProb m h

/-- Model `m` is rejected at history `h` at level `α`. -/
def Rejects (π : M → ℚ) (α : ℚ) (m : M) (h : List (E × O)) : Prop :=
  N.histProb m h ≤ α * N.mixProb π h

/-- Model `m` has been rejected at some prefix of `h` (including `h` itself). -/
def EverRejects (π : M → ℚ) (α : ℚ) (m : M) (h : List (E × O)) : Prop :=
  ∃ k ≤ h.length, N.Rejects π α m (h.take k)

variable {N}

/-- A pre-declared prior: nonnegative weights summing to one. -/
structure IsPrior (π : M → ℚ) : Prop where
  nonneg : ∀ m, 0 ≤ π m
  sum_one : ∑ m, π m = 1

lemma mixProb_martingale (π : M → ℚ) : IsMartingale (N.mixProb π) := by
  intro h e
  simp only [mixProb]
  rw [Finset.sum_comm]
  refine Finset.sum_congr rfl fun m _ => ?_
  rw [← Finset.mul_sum, histProb_martingale m h e]

lemma mixProb_nonneg {π : M → ℚ} (hπ : IsPrior π) (h : List (E × O)) : 0 ≤ N.mixProb π h :=
  Finset.sum_nonneg fun m _ => mul_nonneg (hπ.nonneg m) (histProb_nonneg m h)

lemma mixProb_nil {π : M → ℚ} (hπ : IsPrior π) : N.mixProb π [] = 1 := by
  simp [mixProb, histProb_nil, hπ.sum_one]

open Classical in
/-- **Validity at the stopping time.**  For every adaptive experimental procedure
(arbitrary data-dependent experiment choice and stopping) and every true model `m`,
the probability that `m` is rejected when the procedure stops is at most `α`. -/
theorem reject_at_stop_le {π : M → ℚ} (hπ : IsPrior π) {α : ℚ} (hα : 0 ≤ α) (m : M)
    (p : Policy E O) :
    leafSum p (fun h => if N.Rejects π α m h then N.histProb m h else 0) [] ≤ α := by
  have hle : ∀ h, (if N.Rejects π α m h then N.histProb m h else 0) ≤ α * N.mixProb π h := by
    intro h
    split_ifs with hr
    · exact hr
    · exact mul_nonneg hα (mixProb_nonneg hπ h)
  calc _ ≤ leafSum p (fun h => α * N.mixProb π h) [] := leafSum_mono hle p []
    _ = α * leafSum p (N.mixProb π) [] := leafSum_const_mul α _ p []
    _ = α := by rw [leafSum_martingale (mixProb_martingale π), mixProb_nil hπ, mul_one]

omit [Fintype O] in
private lemma take_snoc_cases (h : List (E × O)) (x : E × O) (k : ℕ)
    (hk : k ≤ (h ++ [x]).length) : (h ++ [x]).take k = h.take k ∨ k = h.length + 1 := by
  simp only [List.length_append, List.length_singleton] at hk
  rcases Nat.lt_or_ge k (h.length + 1) with hlt | hge
  · left
    rw [List.take_append_of_le_length (by omega)]
  · right; omega

open Classical in
private lemma ever_aux {π : M → ℚ} (hπ : IsPrior π) {α : ℚ} (hα : 0 ≤ α) (m : M)
    (p : Policy E O) : ∀ h : List (E × O),
      (N.Rejects π α m h ∨ ∀ k ≤ h.length, ¬ N.Rejects π α m (h.take k)) →
      leafSum p (fun h' => if N.EverRejects π α m h' then N.histProb m h' else 0) h ≤
        α * N.mixProb π h := by
  induction p with
  | stop =>
    intro h hcase
    simp only [leafSum]
    split_ifs with hev
    · rcases hcase with hr | hno
      · exact hr
      · obtain ⟨k, hk, hr⟩ := hev
        exact absurd hr (hno k hk)
    · exact mul_nonneg hα (mixProb_nonneg hπ h)
  | test e f ih =>
    intro h hcase
    rcases hcase with hr | hno
    · -- already rejected: every leaf below counts, total mass `P_m(h)`
      have hev : ∀ (q : Policy E O) (h' : List (E × O)), h <+: h' →
          leafSum q (fun h' => if N.EverRejects π α m h' then N.histProb m h' else 0) h' =
            N.histProb m h' := by
        intro q
        induction q with
        | stop =>
          intro h' hpre
          simp only [leafSum]
          rw [if_pos]
          obtain ⟨t, rfl⟩ := hpre
          exact ⟨h.length, by simp, by simpa using hr⟩
        | test e' f' ih' =>
          intro h' hpre
          simp only [leafSum]
          rw [Finset.sum_congr rfl fun o _ => ih' o _ (hpre.trans (List.prefix_append _ _))]
          exact histProb_martingale m h' e'
      rw [hev (.test e f) h (List.prefix_refl h)]
      exact hr
    · simp only [leafSum]
      calc ∑ o, leafSum (f o) (fun h' => if N.EverRejects π α m h' then N.histProb m h' else 0)
              (h ++ [(e, o)])
          ≤ ∑ o, α * N.mixProb π (h ++ [(e, o)]) := by
            refine Finset.sum_le_sum fun o _ => ih o _ ?_
            by_cases hro : N.Rejects π α m (h ++ [(e, o)])
            · exact Or.inl hro
            · right
              intro k hk
              rcases take_snoc_cases h (e, o) k hk with h1 | h1
              · rw [h1, List.take_eq_take_min]
                exact hno _ (min_le_right _ _)
              · subst h1
                rw [List.take_of_length_le (by simp)]
                exact hro
        _ = α * N.mixProb π h := by rw [← Finset.mul_sum, mixProb_martingale π h e]

open Classical in
/-- **Anytime validity.**  For every adaptive experimental procedure and every true
model `m`, the probability that `m` is *ever* rejected along the observed history is
at most `α`.  In particular optional stopping and data-dependent experiment choice
cannot inflate the error. -/
theorem reject_ever_le {π : M → ℚ} (hπ : IsPrior π) {α : ℚ} (hα : 0 ≤ α) (m : M)
    (p : Policy E O) :
    leafSum p (fun h => if N.EverRejects π α m h then N.histProb m h else 0) [] ≤ α := by
  have := ever_aux hπ hα m p [] (by
    by_cases hr : N.Rejects π α m []
    · exact Or.inl hr
    · right; intro k _; simpa using hr)
  rwa [mixProb_nil hπ, mul_one] at this

open Classical in
/-- **Bounded false-certification probability.**  The procedure certifies a claim
`C` at history `h` when every model violating `C` has been rejected at some point.
If the true model `m⋆` violates `C`, the probability of (wrongly) certifying `C` is at
most `α`, for every adaptive design and stopping rule. -/
theorem false_certification_le {π : M → ℚ} (hπ : IsPrior π) {α : ℚ} (hα : 0 ≤ α)
    (C : M → Prop) {mstar : M} (hC : ¬ C mstar) (p : Policy E O) :
    leafSum p (fun h => if (∀ m, ¬ C m → N.EverRejects π α m h) then N.histProb mstar h else 0) []
      ≤ α := by
  refine le_trans (leafSum_mono (fun h => ?_) p []) (reject_ever_le (N := N) hπ hα mstar p)
  split_ifs with h1 h2
  · exact le_rfl
  · exact absurd (h1 mstar hC) h2
  · exact histProb_nonneg mstar h
  · exact le_rfl

end NoisyProblem

/-- Three coin models: fair (`0`), always-heads (`1`), always-tails (`2`). -/
def coinTable : Fin 3 → Fin 2 → ℚ := ![![1 / 2, 1 / 2], ![1, 0], ![0, 1]]

/-- The noisy coin problem used in `posthoc_alternative_invalid`. -/
def coinProblem : NoisyProblem (Fin 3) Unit (Fin 2) where
  lik m _ o := coinTable m o
  lik_nonneg := by decide +kernel
  lik_sum := by intro m _; fin_cases m <;> norm_num [coinTable, Fin.sum_univ_two]

/-- **Negative result: post-hoc maximized alternatives are invalid.**  Rejecting the
true model when `P_m(h) ≤ α · max_{m'} P_{m'}(h)` (a generalized likelihood ratio
with the alternative chosen after seeing the data, without a pre-declared mixture)
can exceed level `α`: with a fair coin as the truth and the two deterministic coins
as alternatives, one flip at `α = 1/2` rejects the truth with probability `1 > α`. -/
theorem posthoc_alternative_invalid :
    NoisyProblem.leafSum (.test () (fun _ => .stop)) (fun h => if coinProblem.histProb 0 h ≤
        (1 / 2 : ℚ) * (Finset.univ.sup' Finset.univ_nonempty fun m => coinProblem.histProb m h)
      then coinProblem.histProb 0 h else 0) [] = 1 := by
  decide +kernel

end PRISM
