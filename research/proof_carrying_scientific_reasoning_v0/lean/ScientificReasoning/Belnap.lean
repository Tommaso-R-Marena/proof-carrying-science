import ScientificReasoning.Derivations
import ScientificReasoning.CheckCertificate
import ScientificReasoning.Contradictions

/-!
# Belnap FOUR semantics (truth/falsity components)

Encoding: subsets of `{T,F}`:
`none=∅`, `onlyTrue={T}`, `onlyFalse={F}`, `both={T,F}`.

Conjunction (standard):
`T ∈ a∧b ↔ T∈a ∧ T∈b`,  `F ∈ a∧b ↔ F∈a ∨ F∈b`.

**Counterexample to the previous table:** `both ∧ onlyFalse` must be `onlyFalse`
(has T? no; has F? yes), not `both`.
-/

namespace ScientificReasoning.Belnap

inductive TruthValue where
  | none
  | onlyTrue
  | onlyFalse
  | both
  deriving Repr, DecidableEq, Inhabited

def TruthValue.hasT : TruthValue → Bool
  | .onlyTrue | .both => true
  | .none | .onlyFalse => false

def TruthValue.hasF : TruthValue → Bool
  | .onlyFalse | .both => true
  | .none | .onlyTrue => false

def TruthValue.ofTF (t f : Bool) : TruthValue :=
  match t, f with
  | true,  false => .onlyTrue
  | false, true  => .onlyFalse
  | true,  true  => .both
  | false, false => .none

theorem ofTF_components (v : TruthValue) :
    TruthValue.ofTF v.hasT v.hasF = v := by
  cases v <;> decide

def TruthValue.neg : TruthValue → TruthValue
  | v => TruthValue.ofTF v.hasF v.hasT

/-- Standard Belnap conjunction via components. -/
def TruthValue.and (a b : TruthValue) : TruthValue :=
  TruthValue.ofTF (a.hasT && b.hasT) (a.hasF || b.hasF)

theorem and_hasT (a b : TruthValue) :
    (a.and b).hasT = (a.hasT && b.hasT) := by
  unfold TruthValue.and
  cases a.hasT <;> cases b.hasT <;> cases a.hasF <;> cases b.hasF <;> decide

theorem and_hasF (a b : TruthValue) :
    (a.and b).hasF = (a.hasF || b.hasF) := by
  unfold TruthValue.and
  cases a.hasT <;> cases b.hasT <;> cases a.hasF <;> cases b.hasF <;> decide

theorem and_comm (a b : TruthValue) : a.and b = b.and a := by
  unfold TruthValue.and
  cases a <;> cases b <;> decide

theorem and_assoc (a b c : TruthValue) : (a.and b).and c = a.and (b.and c) := by
  cases a <;> cases b <;> cases c <;> decide

theorem and_idem (a : TruthValue) : a.and a = a := by
  cases a <;> decide

/-- Concrete counterexample to the old (incorrect) table that mapped `both,_ ↦ both`. -/
theorem both_and_onlyFalse : TruthValue.both.and .onlyFalse = .onlyFalse := by
  decide

/-- Exhaustive 4×4 conjunction table (all 16 cells). -/
theorem and_truth_table :
    (TruthValue.none.and .none = .none) ∧
    (TruthValue.none.and .onlyTrue = .none) ∧
    (TruthValue.none.and .onlyFalse = .onlyFalse) ∧
    (TruthValue.none.and .both = .onlyFalse) ∧
    (TruthValue.onlyTrue.and .none = .none) ∧
    (TruthValue.onlyTrue.and .onlyTrue = .onlyTrue) ∧
    (TruthValue.onlyTrue.and .onlyFalse = .onlyFalse) ∧
    (TruthValue.onlyTrue.and .both = .both) ∧
    (TruthValue.onlyFalse.and .none = .onlyFalse) ∧
    (TruthValue.onlyFalse.and .onlyTrue = .onlyFalse) ∧
    (TruthValue.onlyFalse.and .onlyFalse = .onlyFalse) ∧
    (TruthValue.onlyFalse.and .both = .onlyFalse) ∧
    (TruthValue.both.and .none = .onlyFalse) ∧
    (TruthValue.both.and .onlyTrue = .both) ∧
    (TruthValue.both.and .onlyFalse = .onlyFalse) ∧
    (TruthValue.both.and .both = .both) := by
  decide

open ScientificReasoning

abbrev Assignment := PropId → TruthValue

def Formula.eval4 (σ : Assignment) : Formula → TruthValue
  | .atom i => σ i
  | .not φ => (Formula.eval4 σ φ).neg
  | .and φ ψ => (Formula.eval4 σ φ).and (Formula.eval4 σ ψ)

/-- Designated = contains Truth (approximation / support). -/
def designated (v : TruthValue) : Bool := v.hasT

theorem designated_and (a b : TruthValue) :
    designated (a.and b) = true ↔ designated a = true ∧ designated b = true := by
  simp [designated, and_hasT, Bool.and_eq_true]

def Entails4 (Γ : Context) (φ : Formula) : Prop :=
  ∀ σ, (∀ p ∈ Γ.premises, designated (Formula.eval4 σ p.formula) = true) →
    designated (Formula.eval4 σ φ) = true

/-- Semantic soundness for the supported ND fragment w.r.t. Entails4. -/
theorem derives_entails4
    (Γ : Context) (S : Support) (a : Authority) (φ : Formula)
    (h : Derives Γ S a φ) :
    Entails4 Γ φ := by
  induction h with
  | hyp p hp =>
      intro σ hsat
      exact hsat p hp
  | andI S T a b φ ψ hφ hψ ihφ ihψ =>
      intro σ hsat
      have h1 := ihφ σ hsat
      have h2 := ihψ σ hsat
      have := (designated_and (Formula.eval4 σ φ) (Formula.eval4 σ ψ)).2 ⟨h1, h2⟩
      simpa [Formula.eval4] using this
  | andE1 S a φ ψ hand ih =>
      intro σ hsat
      have h := ih σ hsat
      have := (designated_and (Formula.eval4 σ φ) (Formula.eval4 σ ψ)).1 (by
        simpa [Formula.eval4] using h)
      exact this.1
  | andE2 S a φ ψ hand ih =>
      intro σ hsat
      have h := ih σ hsat
      have := (designated_and (Formula.eval4 σ φ) (Formula.eval4 σ ψ)).1 (by
        simpa [Formula.eval4] using h)
      exact this.2

/-- Accepted structured certificates entail4 their conclusions. -/
theorem checkCertificate_entails4
    (c : StructuredCertificate) (j : VerifiedJudgment)
    (h : checkCertificate c = some j) :
    Entails4 c.toContext j.formula :=
  derives_entails4 _ _ _ _ (checkCertificate_sound c j h)

def σ_demo : Assignment
  | 0 => .both
  | 2 => .onlyTrue
  | _ => .none

theorem demo_premises_designated_atom99_not :
    designated (Formula.eval4 σ_demo (Formula.atom 0)) = true ∧
    designated (Formula.eval4 σ_demo (Formula.not (Formula.atom 0))) = true ∧
    designated (Formula.eval4 σ_demo (Formula.atom 2)) = true ∧
    designated (Formula.eval4 σ_demo (Formula.atom 99)) = false := by
  decide

/-- Entails4 does not explode for this inconsistent-designating assignment on atom 99. -/
theorem not_entails4_atom99_from_demo_assignment :
    designated (Formula.eval4 σ_demo (Formula.atom 99)) = false := by
  decide

theorem demoΓ_designated_under_σ_demo :
    ∀ p ∈ demoΓ.premises, designated (Formula.eval4 σ_demo p.formula) = true := by
  intro p hp
  simp [demoΓ, p0, p1, p2] at hp
  rcases hp with (rfl | rfl | rfl)
  · -- atom 0 under σ_demo = both
    decide
  · -- not atom 0 under σ_demo = both
    decide
  · -- atom 2 under σ_demo = onlyTrue
    decide

/-- **Break fix (semantic):** Entails4 does *not* yield unrelated atom 99 from demoΓ,
    while classical `Entails` does (`classical_entails_atom99_demoΓ`). -/
theorem not_entails4_atom99_demoΓ : ¬ Entails4 demoΓ (Formula.atom 99) := by
  intro h
  have := h σ_demo demoΓ_designated_under_σ_demo
  simp [Formula.eval4, σ_demo, designated, TruthValue.hasT] at this

/-- Accepted certificates only get Entails4 — not classical explosion. -/
theorem checkCertificate_entails4_not_classical_explosion
    (c : StructuredCertificate) (j : VerifiedJudgment)
    (h : checkCertificate c = some j)
    (hctx : c.toContext = demoΓ)
    (hform : j.formula = Formula.atom 99) : False := by
  have he4 := checkCertificate_entails4 c j h
  rw [hctx, hform] at he4
  exact not_entails4_atom99_demoΓ he4

theorem traceValid_implies_entails4
    (c : StructuredCertificate) (h : c.traceValid) :
    ∃ j, checkCertificate c = some j ∧ Entails4 c.toContext j.formula := by
  obtain ⟨j, hj⟩ := h
  exact ⟨j, hj, checkCertificate_entails4 c j hj⟩

end ScientificReasoning.Belnap

#print axioms ScientificReasoning.Belnap.and_truth_table
#print axioms ScientificReasoning.Belnap.both_and_onlyFalse
#print axioms ScientificReasoning.Belnap.derives_entails4
#print axioms ScientificReasoning.Belnap.checkCertificate_entails4
#print axioms ScientificReasoning.Belnap.designated_and
#print axioms ScientificReasoning.Belnap.not_entails4_atom99_demoΓ
#print axioms ScientificReasoning.Belnap.checkCertificate_entails4_not_classical_explosion
#print axioms ScientificReasoning.Belnap.traceValid_implies_entails4
