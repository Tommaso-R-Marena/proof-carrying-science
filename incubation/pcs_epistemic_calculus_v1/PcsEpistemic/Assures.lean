import PcsEpistemic.Graph

/-!
The graded assurance judgment `Assures L C E`.

A claim at required class `L` is supported only when every required evidence
identifier is present and each cited evidence discharges at a class allowed by
the evidence lattice.
-/
set_option autoImplicit false

namespace PcsEpistemic

structure Assumption where
  id : Nat
  openStatus : Bool
  deriving DecidableEq, Repr

structure Context where
  assumptions : List Assumption
  deriving DecidableEq, Repr

/-- Evidence payload: identifier, class, and whether the checker accepted it. -/
structure EvidenceRecord where
  id : Nat
  cls : EvidenceClass
  accepted : Bool
  deriving DecidableEq, Repr

def EvidenceRecord.discharges (e : EvidenceRecord) (required : EvidenceClass) : Bool :=
  e.accepted && e.cls.le required

def findEvidence (E : List EvidenceRecord) (id : Nat) : Option EvidenceRecord :=
  E.find? (fun e => e.id = id)

/-- Executable support check for one claim against an evidence set. -/
def supportsClaim (claim : ClaimNode) (E : List EvidenceRecord) : Bool :=
  claim.requiredEvidence.all (fun eid =>
    match findEvidence E eid with
    | none => false
    | some e => e.discharges claim.requiredClass)

/-- Graded assurance predicate (context is retained for dialectic reporting). -/
def Assures (_Γ : Context) (L : EvidenceClass) (claim : ClaimNode) (E : List EvidenceRecord) : Prop :=
  claim.requiredClass = L ∧ supportsClaim claim E = true

theorem assures_requires_matching_class
    {Γ : Context} {L : EvidenceClass} {claim : ClaimNode} {E : List EvidenceRecord}
    (h : Assures Γ L claim E) : claim.requiredClass = L :=
  h.1

/-- Computational evidence alone cannot assure a formal claim. -/
theorem computational_cannot_assure_formal
    (Γ : Context) (claim : ClaimNode) (eid : Nat)
    (hcls : claim.requiredClass = .formal)
    (hreq : claim.requiredEvidence = [eid]) :
    ¬ Assures Γ .formal claim
        [{ id := eid, cls := .computational, accepted := true }] := by
  intro h
  have hs := h.2
  simp [supportsClaim, hreq, findEvidence, EvidenceRecord.discharges,
        EvidenceClass.le, hcls] at hs

/-- Missing required evidence blocks assurance. -/
theorem missing_evidence_blocks
    (Γ : Context) (claim : ClaimNode) (eid : Nat)
    (hreq : claim.requiredEvidence = [eid]) :
    ¬ Assures Γ claim.requiredClass claim [] := by
  intro h
  have hs := h.2
  simp [supportsClaim, hreq, findEvidence] at hs

/-- Accepted formal evidence assures a matching formal claim. -/
theorem formal_evidence_assures_formal
    (Γ : Context) (claim : ClaimNode) (eid : Nat)
    (hcls : claim.requiredClass = .formal)
    (hreq : claim.requiredEvidence = [eid]) :
    Assures Γ .formal claim
      [{ id := eid, cls := .formal, accepted := true }] := by
  refine ⟨hcls, ?_⟩
  simp [supportsClaim, hreq, findEvidence, EvidenceRecord.discharges, EvidenceClass.le, hcls]

end PcsEpistemic
