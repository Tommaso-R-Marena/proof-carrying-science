import Std

/-! Research calculus for joining evidence at an exact subject. A subject identifies
a version of the source, its formal interpretation, assumptions and inputs. Evidence
providers must check those bindings. Lean makes no authenticity assumption for them. -/
namespace PCSResearch.Admission

inductive Kind where
  | proposed | typed | sourceReviewed | modelChecked | observed
  deriving DecidableEq, Repr

structure Receipt (S : Type) where
  subject : S
  kind : Kind
  deriving DecidableEq

/-- A scoped interpretation of each piece of evidence, supplied by the application. -/
structure Meaning (S : Type) where
  typed : S → Prop
  sourceReviewed : S → Prop
  modelChecked : S → Prop
  observed : S → Prop

def Meaning.interpret (m : Meaning S) (r : Receipt S) : Prop :=
  match r.kind with
  | .proposed => True
  | .typed => m.typed r.subject
  | .sourceReviewed => m.sourceReviewed r.subject
  | .modelChecked => m.modelChecked r.subject
  | .observed => m.observed r.subject

/-- These are two different conclusions about one subject. -/
inductive Conclusion where
  | interpretedResult | recordedObservation
  deriving DecidableEq, Repr

def requires : Conclusion → List Kind
  | .interpretedResult => [.sourceReviewed, .modelChecked]
  | .recordedObservation => [.observed]

def admits [DecidableEq S] (rs : List (Receipt S)) (s : S) (c : Conclusion) : Bool :=
  (requires c).all fun k => rs.contains ⟨s, k⟩

theorem exactSupport [DecidableEq S] (rs : List (Receipt S)) (s : S) (c : Conclusion) :
    admits rs s c = true ↔ ∀ k ∈ requires c, (⟨s, k⟩ : Receipt S) ∈ rs := by
  simp [admits]

/-- Policy soundness for every meaning compatible with the checked evidence. -/
theorem sound [DecidableEq S] (rs : List (Receipt S)) (s : S) (c : Conclusion)
    (m : Meaning S) (verified : ∀ r ∈ rs, m.interpret r) (h : admits rs s c = true) :
    match c with
    | .interpretedResult => m.sourceReviewed s ∧ m.modelChecked s
    | .recordedObservation => m.observed s := by
  have support := (exactSupport rs s c).mp h
  cases c with
  | interpretedResult =>
    exact ⟨verified ⟨s, .sourceReviewed⟩ (support _ (by decide)),
           verified ⟨s, .modelChecked⟩ (support _ (by decide))⟩
  | recordedObservation =>
    exact verified ⟨s, .observed⟩ (support _ (by decide))

theorem restrict [DecidableEq S] (small large : List (Receipt S)) (s : S)
    (c : Conclusion) (sub : ∀ r ∈ small, r ∈ large) :
    admits small s c = true → admits large s c = true := by
  intro h
  exact (exactSupport large s c).mpr fun k hk =>
    sub _ ((exactSupport small s c).mp h k hk)

/-- Counterinterpretation built from the evidence alone. Every supplied receipt
holds in this interpretation, including when the subject type has infinitely many values. -/
def leastMeaning (rs : List (Receipt S)) : Meaning S where
  typed s := ⟨s, .typed⟩ ∈ rs
  sourceReviewed s := ⟨s, .sourceReviewed⟩ ∈ rs
  modelChecked s := ⟨s, .modelChecked⟩ ∈ rs
  observed s := ⟨s, .observed⟩ ∈ rs

theorem compatibleLeast (rs : List (Receipt S)) : ∀ r ∈ rs, (leastMeaning rs).interpret r := by
  rintro ⟨s,k⟩ h
  cases k <;> simp_all [Meaning.interpret, leastMeaning]

/-- Completeness is relative to these rules: if a proposed conclusion is true in
every interpretation compatible with the receipts, these receipts suffice for admission. -/
theorem complete [DecidableEq S] (rs : List (Receipt S)) (s : S) (c : Conclusion)
    (h : ∀ m : Meaning S, (∀ r ∈ rs, m.interpret r) →
      match c with
      | .interpretedResult => m.sourceReviewed s ∧ m.modelChecked s
      | .recordedObservation => m.observed s) : admits rs s c = true := by
  have needed := h (leastMeaning rs) (compatibleLeast rs)
  apply (exactSupport rs s c).mpr
  intro k hk
  cases c with
  | interpretedResult =>
    simp [requires] at hk
    rcases hk with rfl | rfl
    · exact needed.1
    · exact needed.2
  | recordedObservation =>
    simp [requires] at hk
    subst k
    exact needed

-- Executable witnesses for cross-subject substitution and missing interpretation.
example : admits [⟨0, .sourceReviewed⟩, ⟨1, .modelChecked⟩] 0 .interpretedResult = false := by decide
example : admits [⟨0, .typed⟩, ⟨0, .modelChecked⟩, ⟨0, .observed⟩] 0 .interpretedResult = false := by decide
example : admits [⟨0, .sourceReviewed⟩, ⟨0, .modelChecked⟩] 0 .recordedObservation = false := by decide

#print axioms sound
#print axioms complete
#print axioms restrict
end PCSResearch.Admission
