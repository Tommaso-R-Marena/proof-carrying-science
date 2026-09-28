/-!
Proof-Carrying Science: minimal assurance kernel.

This module intentionally depends only on Lean core. It separates evidence classes,
makes the assumption context explicit, and requires accepted evidence to be PASS,
explicitly required by the claim, and bound to the same machine-readable predicate.

The intended judgment is:

  Γ ; E ⊢ C @ L

represented by `Assures Γ L C E`.
-/

namespace PCS

inductive ClaimKind
  | formal
  | computational
  | empirical
  | mixed
  deriving DecidableEq, Repr

inductive EvidenceKind
  | formalProof
  | computationalTest
  | statisticalValidation
  | empiricalValidation
  | provenance
  deriving DecidableEq, Repr

inductive Outcome
  | pass
  | fail
  | unverified
  deriving DecidableEq, Repr

inductive Predicate
  | opaque (tag : String)
  | csvDisjoint (leftArtifact rightArtifact key : String)
  | reactionBalanced (signature : String)
  | unitsCompatible (leftUnit rightUnit : String)
  | pkpdContract (modelArtifact : String)
  | pkpdReferenceMatch (modelArtifact outputArtifact : String)
  deriving DecidableEq, Repr

structure Assumption where
  id : String
  statement : String := ""
  deriving DecidableEq, Repr

structure Evidence where
  id : String
  kind : EvidenceKind
  outcome : Outcome
  predicate : Option Predicate := none
  deriving DecidableEq, Repr

structure Claim where
  id : String
  kind : ClaimKind
  predicate : Option Predicate := none
  requiredEvidence : List String := []
  assumptions : List String := []
  deriving DecidableEq, Repr

/-- Every assumption ID named by the claim must occur in the explicit context Γ. -/
def ContextCovers (Γ : List Assumption) (c : Claim) : Prop :=
  ∀ aid, aid ∈ c.assumptions → ∃ a, a ∈ Γ ∧ a.id = aid

/-- Evidence is bound to a claim only if the claim explicitly requires its ID and the
    evidence is about the same machine-readable predicate. -/
def BoundTo (e : Evidence) (c : Claim) : Prop :=
  e.id ∈ c.requiredEvidence ∧ e.predicate = c.predicate

inductive AssuranceLevel
  | formal
  | computational
  | empirical
  | mixed
  deriving DecidableEq, Repr

/--
The trusted logical judgment `Γ ; E ⊢ C @ L`.
Every constructor explicitly carries context coverage and PASS evidence.
-/
inductive Assures : List Assumption → AssuranceLevel → Claim → List Evidence → Prop
  | formal {Γ : List Assumption} {c : Claim} {es : List Evidence} (e : Evidence)
      (member : e ∈ es)
      (context : ContextCovers Γ c)
      (claimKind : c.kind = ClaimKind.formal)
      (evidenceKind : e.kind = EvidenceKind.formalProof)
      (passed : e.outcome = Outcome.pass)
      (bound : BoundTo e c) : Assures Γ AssuranceLevel.formal c es
  | computational {Γ : List Assumption} {c : Claim} {es : List Evidence} (e : Evidence)
      (member : e ∈ es)
      (context : ContextCovers Γ c)
      (claimKind : c.kind = ClaimKind.computational)
      (evidenceKind : e.kind = EvidenceKind.computationalTest ∨
                      e.kind = EvidenceKind.formalProof)
      (passed : e.outcome = Outcome.pass)
      (bound : BoundTo e c) : Assures Γ AssuranceLevel.computational c es
  | empirical {Γ : List Assumption} {c : Claim} {es : List Evidence} (e : Evidence)
      (member : e ∈ es)
      (context : ContextCovers Γ c)
      (claimKind : c.kind = ClaimKind.empirical)
      (evidenceKind : e.kind = EvidenceKind.empiricalValidation ∨
                      e.kind = EvidenceKind.statisticalValidation)
      (passed : e.outcome = Outcome.pass)
      (bound : BoundTo e c) : Assures Γ AssuranceLevel.empirical c es
  | mixed {Γ : List Assumption} {c : Claim} {es : List Evidence}
      (correctness empiricalEvidence : Evidence)
      (correctnessMember : correctness ∈ es)
      (empiricalMember : empiricalEvidence ∈ es)
      (context : ContextCovers Γ c)
      (claimKind : c.kind = ClaimKind.mixed)
      (correctnessKind : correctness.kind = EvidenceKind.formalProof)
      (empiricalKind : empiricalEvidence.kind = EvidenceKind.empiricalValidation ∨
                       empiricalEvidence.kind = EvidenceKind.statisticalValidation)
      (correctnessPassed : correctness.outcome = Outcome.pass)
      (empiricalPassed : empiricalEvidence.outcome = Outcome.pass)
      (correctnessBound : BoundTo correctness c)
      (empiricalBound : BoundTo empiricalEvidence c) : Assures Γ AssuranceLevel.mixed c es

theorem formal_assurance_has_checked_formal_proof
    {Γ : List Assumption} {c : Claim} {es : List Evidence}
    (h : Assures Γ AssuranceLevel.formal c es) :
    ∃ e, e ∈ es ∧ e.kind = EvidenceKind.formalProof ∧ e.outcome = Outcome.pass := by
  cases h with
  | formal e member _ _ evidenceKind passed _ =>
      exact ⟨e, member, evidenceKind, passed⟩

theorem computational_assurance_is_predicate_bound
    {Γ : List Assumption} {c : Claim} {es : List Evidence}
    (h : Assures Γ AssuranceLevel.computational c es) :
    ∃ e, e ∈ es ∧ e.id ∈ c.requiredEvidence ∧ e.predicate = c.predicate := by
  cases h with
  | computational e member _ _ _ _ bound =>
      exact ⟨e, member, bound.1, bound.2⟩

theorem computational_assurance_has_correctness_evidence
    {Γ : List Assumption} {c : Claim} {es : List Evidence}
    (h : Assures Γ AssuranceLevel.computational c es) :
    ∃ e, e ∈ es ∧
      (e.kind = EvidenceKind.computationalTest ∨
       e.kind = EvidenceKind.formalProof) ∧
      e.outcome = Outcome.pass := by
  cases h with
  | computational e member _ _ evidenceKind passed _ =>
      exact ⟨e, member, evidenceKind, passed⟩

theorem computational_assurance_cannot_use_unverified
    {Γ : List Assumption} {c : Claim} {es : List Evidence}
    (h : Assures Γ AssuranceLevel.computational c es) :
    ∃ e, e ∈ es ∧ e.outcome = Outcome.pass := by
  cases h with
  | computational e member _ _ _ passed _ =>
      exact ⟨e, member, passed⟩

theorem empirical_assurance_requires_empirical_class
    {Γ : List Assumption} {c : Claim} {es : List Evidence}
    (h : Assures Γ AssuranceLevel.empirical c es) :
    ∃ e, e ∈ es ∧
      (e.kind = EvidenceKind.empiricalValidation ∨ e.kind = EvidenceKind.statisticalValidation) ∧
      e.outcome = Outcome.pass := by
  cases h with
  | empirical e member _ _ evidenceKind passed _ =>
      exact ⟨e, member, evidenceKind, passed⟩

theorem mixed_assurance_requires_both_classes
    {Γ : List Assumption} {c : Claim} {es : List Evidence}
    (h : Assures Γ AssuranceLevel.mixed c es) :
    ∃ correctness empiricalEvidence,
      correctness ∈ es ∧ empiricalEvidence ∈ es ∧
      correctness.kind = EvidenceKind.formalProof ∧
      (empiricalEvidence.kind = EvidenceKind.empiricalValidation ∨
       empiricalEvidence.kind = EvidenceKind.statisticalValidation) ∧
      correctness.outcome = Outcome.pass ∧ empiricalEvidence.outcome = Outcome.pass := by
  cases h with
  | mixed correctness empiricalEvidence cm em _ _ ck ek cp ep _ _ =>
      exact ⟨correctness, empiricalEvidence, cm, em, ck, ek, cp, ep⟩

theorem assurance_context_is_explicit
    {Γ : List Assumption} {L : AssuranceLevel} {c : Claim} {es : List Evidence}
    (h : Assures Γ L c es) : ContextCovers Γ c := by
  cases h with
  | formal _ _ context _ _ _ _ => exact context
  | computational _ _ context _ _ _ _ => exact context
  | empirical _ _ context _ _ _ _ => exact context
  | mixed _ _ _ _ context _ _ _ _ _ _ _ => exact context

end PCS
