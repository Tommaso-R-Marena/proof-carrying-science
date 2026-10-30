module

public import PRISM.Certificates.Adversary

/-!
# The independent executable certificate checker

The untrusted search engine (Python, solvers, heuristics, learned models) emits
*certificates*.  The functions in this file are **executable Boolean checkers**
written in Lean; each comes with a soundness theorem stating precisely what a
`true` answer guarantees.  The checker never trusts any number reported by the
search engine: policies are re-simulated on every model, bounds re-evaluated and
adversary tables re-validated entry by entry.

Every checker below is an ordinary structurally recursive / `decide`-based Lean
function (no `implemented_by`, no `unsafe`, no `native_decide`), so concrete
certificates can be checked by the Lean kernel itself via `decide`.
-/

@[expose] public section

namespace PRISM

universe u v w

variable {M : Type u} {E : Type v} {O : Type w}

namespace Problem

variable [DecidableEq M] [DecidableEq O] (P : Problem M E O)

instance (ε : ℚ) (p : Policy E O) (K : Finset M) : Decidable (P.Succeeds ε p K) := by
  unfold Succeeds; infer_instance

instance (p : Policy E O) (K : Finset M) (B : ℚ≥0) : Decidable (P.CostLE p K B) := by
  unfold CostLE; infer_instance

/-! ## Upper-bound certificates: explicit policies -/

/-- Check that a policy succeeds on `K` with worst-case cost at most `B`, by
simulating it on every model of `K`. -/
def checkPolicy (ε : ℚ) (p : Policy E O) (K : Finset M) (B : ℚ≥0) : Bool :=
  decide (P.Succeeds ε p K ∧ P.CostLE p K B)

variable {P}

omit [DecidableEq M] in
theorem checkPolicy_sound {ε : ℚ} {p : Policy E O} {K : Finset M} {B : ℚ≥0}
    (h : P.checkPolicy ε p K B = true) : P.Succeeds ε p K ∧ P.CostLE p K B :=
  of_decide_eq_true h

omit [DecidableEq M] in
theorem checkPolicy_complete {ε : ℚ} {p : Policy E O} {K : Finset M} {B : ℚ≥0}
    (h : P.Succeeds ε p K ∧ P.CostLE p K B) : P.checkPolicy ε p K B = true :=
  decide_eq_true h

/-! ## Lower-bound certificates: adversary tables -/

/-- Lookup in an adversary table (first matching entry; `0` if absent). -/
def lbOf (cert : List (Finset M × ℚ≥0)) (S : Finset M) : ℚ≥0 :=
  match cert.find? (fun x => decide (x.1 = S)) with
  | some x => x.2
  | none => 0

variable [Fintype E]
variable (P)

/-- Local validity condition of one adversary-table entry. -/
def EntryOK (ε : ℚ) (cert : List (Finset M × ℚ≥0)) (S : Finset M) : Prop :=
  lbOf cert S = 0 ∨
    (ε < P.width S ∧ ∀ e : E, ∃ o ∈ P.outcomes S e, lbOf cert S ≤ P.cost e + lbOf cert (P.cell S e o))

instance (ε : ℚ) (cert : List (Finset M × ℚ≥0)) (S : Finset M) :
    Decidable (P.EntryOK ε cert S) := by
  unfold EntryOK; infer_instance

/-- Check an adversary table entry by entry. -/
def checkAdversary (ε : ℚ) (cert : List (Finset M × ℚ≥0)) : Bool :=
  cert.all fun x => decide (P.EntryOK ε cert x.1)

variable {P}

theorem checkAdversary_sound {ε : ℚ} {cert : List (Finset M × ℚ≥0)}
    (h : P.checkAdversary ε cert = true) : P.IsAdversary ε (lbOf cert) := by
  intro S
  have hS := h
  unfold checkAdversary at hS
  rw [List.all_eq_true] at hS
  cases hf : cert.find? (fun x => decide (x.1 = S)) with
  | none => left; simp [lbOf, hf]
  | some x =>
    have hx := List.mem_of_find?_eq_some hf
    have hxS : x.1 = S := by simpa using List.find?_some hf
    have := of_decide_eq_true (hS x hx)
    rw [hxS] at this
    exact this

/-! ## Exact-optimality certificates (the optimality sandwich) -/

/-- An exact-optimality certificate: a policy (upper bound), a claimed optimal cost,
a small *core* sub-version-space and an adversary table on it (lower bound). -/
structure OptCert (M : Type u) (E : Type v) (O : Type w) where
  policy : Policy E O
  bound : ℚ≥0
  core : Finset M
  adversary : List (Finset M × ℚ≥0)

variable (P)

/-- Check an exact-optimality certificate for an explicitly given version space `K`. -/
def checkOptimal (ε : ℚ) (K : Finset M) (c : OptCert M E O) : Bool :=
  decide (c.core ⊆ K) && P.checkPolicy ε c.policy K c.bound &&
    P.checkAdversary ε c.adversary && decide (c.bound ≤ lbOf c.adversary c.core)

/-- Check the parts of a sandwich certificate that do not mention the (possibly
implicit, never enumerated) true version space: the policy on an over-approximation
`Khi` and the adversary on the core. -/
def checkSandwich (ε : ℚ) (Khi : Finset M) (c : OptCert M E O) : Bool :=
  P.checkPolicy ε c.policy Khi c.bound &&
    P.checkAdversary ε c.adversary && decide (c.bound ≤ lbOf c.adversary c.core)

variable {P}

/-- **Soundness of the sandwich checker.**  For *any* version space `K` with
`core ⊆ K ⊆ Khi`, an accepted certificate proves that its policy is globally minimax
optimal on `K` with exact optimal cost `bound`.  `K` itself is never inspected. -/
theorem checkSandwich_sound {ε : ℚ} (hε : 0 ≤ ε) {Khi K : Finset M} {c : OptCert M E O}
    (h : P.checkSandwich ε Khi c = true) (h₁ : c.core ⊆ K) (h₂ : K ⊆ Khi) :
    P.Succeeds ε c.policy K ∧ P.worstCost c.policy K = c.bound ∧
      (∀ p : Policy E O, P.Succeeds ε p K → c.bound ≤ P.worstCost p K) ∧
      P.value ε K = c.bound := by
  simp only [checkSandwich, Bool.and_eq_true, decide_eq_true_eq] at h
  obtain ⟨⟨hp, ha⟩, hb⟩ := h
  obtain ⟨hs, hc⟩ := checkPolicy_sound hp
  have hA := checkAdversary_sound ha
  have hlow : ∀ p : Policy E O, P.Succeeds ε p c.core → c.bound ≤ P.worstCost p c.core :=
    fun p hp' => hb.trans (adversary_sound hε hA p _ _ hp' (costLE_worstCost p _))
  obtain ⟨hsK, hcK, hopt⟩ := optimality_sandwich h₁ h₂ hs hc hlow
  refine ⟨hsK, le_antisymm (costLE_iff.1 hcK) (hopt _ hsK), hopt, ?_⟩
  exact value_eq_of_sandwich hε h₁ h₂ hs hc
    ((WithTop.coe_le_coe.2 hb).trans (adversary_le_value hε hA _))

/-- **Soundness of the explicit optimality checker.** -/
theorem checkOptimal_sound {ε : ℚ} (hε : 0 ≤ ε) {K : Finset M} {c : OptCert M E O}
    (h : P.checkOptimal ε K c = true) :
    P.Succeeds ε c.policy K ∧ P.worstCost c.policy K = c.bound ∧
      (∀ p : Policy E O, P.Succeeds ε p K → c.bound ≤ P.worstCost p K) ∧
      P.value ε K = c.bound := by
  simp only [checkOptimal, Bool.and_eq_true, decide_eq_true_eq] at h
  obtain ⟨⟨⟨hcore, hp⟩, ha⟩, hb⟩ := h
  refine checkSandwich_sound hε (Khi := K) ?_ hcore subset_rfl
  simp [checkSandwich, hp, ha, hb]

omit [DecidableEq M] in
/-- **Completeness of exact-optimality certificates**: whenever `value ε K = v` is
finite, an accepted certificate exists (with core `K`; smaller cores are an
optimization, not a requirement). Its adversary is a *function*; the table form is
complete whenever the table lists every sub-version-space with positive truncated
value. -/
theorem optimal_certificate_exists {ε : ℚ} (hε : 0 ≤ ε) {K : Finset M} {v : ℚ≥0}
    (hv : P.value ε K = v) :
    ∃ (p : Policy E O) (lb : Finset M → ℚ≥0), P.checkPolicy ε p K v = true ∧
      P.IsAdversary ε lb ∧ v ≤ lb K := by
  obtain ⟨⟨p, hs, hw, -⟩, -⟩ := value_optimal hε hv
  refine ⟨p, P.truncValue ε v, checkPolicy_complete ⟨hs, costLE_iff.2 hw.le⟩,
    adversary_complete hε v, (truncValue_eq hv.symm.le).symm.le⟩

/-! ## Impossibility, bounds, countermodel and certification checkers -/

variable (P)

/-- Check a two-model impossibility certificate. -/
def checkImpossible (ε : ℚ) (K : Finset M) (m₁ m₂ : M) : Bool :=
  decide (m₁ ∈ K ∧ m₂ ∈ K ∧ (∀ e, P.obs m₁ e = P.obs m₂ e) ∧ ε < P.q m₁ - P.q m₂)

variable {P}

theorem checkImpossible_sound {ε : ℚ} (hε : 0 ≤ ε) {K : Finset M} {m₁ m₂ : M}
    (h : P.checkImpossible ε K m₁ m₂ = true) :
    (∀ p : Policy E O, ¬ P.Succeeds ε p K) ∧ P.value ε K = ⊤ := by
  obtain ⟨h₁, h₂, he, hg⟩ := of_decide_eq_true h
  exact ImpossibilityCert.sound hε ⟨m₁, m₂, h₁, h₂, he, hg⟩

end Problem

namespace Problem

variable [DecidableEq M] (P : Problem M E O)

/-- Check a sharp-bounds certificate `[lo, hi]` with attaining witnesses. -/
def checkBounds (K : Finset M) (lo hi : ℚ) (mlo mhi : M) : Bool :=
  decide (mlo ∈ K ∧ mhi ∈ K ∧ P.q mlo = lo ∧ P.q mhi = hi ∧ ∀ m ∈ K, lo ≤ P.q m ∧ P.q m ≤ hi)

variable {P}

/-- **Soundness of the bounds checker**: the certified interval is exactly
`[L(K), U(K)]` (sound *and* sharp). -/
theorem checkBounds_sound {K : Finset M} {lo hi : ℚ} {mlo mhi : M}
    (h : P.checkBounds K lo hi mlo mhi = true) :
    ∃ hK : K.Nonempty, P.lower K hK = lo ∧ P.upper K hK = hi := by
  obtain ⟨h₁, h₂, h₃, h₄, h₅⟩ := of_decide_eq_true h
  refine ⟨⟨mlo, h₁⟩, le_antisymm ?_ ?_, le_antisymm ?_ ?_⟩
  · exact h₃ ▸ Finset.inf'_le _ h₁
  · exact Finset.le_inf' _ _ fun m hm => (h₅ m hm).1
  · exact Finset.sup'_le _ _ fun m hm => (h₅ m hm).2
  · exact h₄ ▸ Finset.le_sup' _ h₂

/-- Check an explicit countermodel to a universal claim. -/
def checkCountermodel (K : Finset M) (C : M → Prop) [DecidablePred C] (m : M) : Bool :=
  decide (m ∈ K ∧ ¬ C m)

theorem checkCountermodel_sound {K : Finset M} {C : M → Prop} [DecidablePred C] {m : M}
    (h : checkCountermodel K C m = true) : ¬ ∀ m' ∈ K, C m' := by
  obtain ⟨h₁, h₂⟩ := of_decide_eq_true h
  exact fun H => h₂ (H m h₁)

/-- Check certification of a universal claim; refuses empty version spaces. -/
def checkCertified (K : Finset M) (C : M → Prop) [DecidablePred C] : Bool :=
  decide (K.Nonempty ∧ ∀ m ∈ K, C m)

omit [DecidableEq M] in
theorem checkCertified_sound {K : Finset M} {C : M → Prop} [DecidablePred C]
    (h : checkCertified K C = true) : K.Nonempty ∧ ∀ m ∈ K, C m := of_decide_eq_true h

/-- Check inconsistency (empty version space). -/
def checkInconsistent (K : Finset M) : Bool := decide (K = ∅)

theorem checkInconsistent_sound {K : Finset M} (h : checkInconsistent K = true) : K = ∅ :=
  of_decide_eq_true h

end Problem

end PRISM
