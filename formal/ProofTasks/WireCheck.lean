import PCS.Wire

namespace PCS.ProofTasks.WireCheck

open PCS
open PCS.Decision
open PCS.Refinement
open PCS.Normalization
open PCS.Wire

def contextIds (w : DecisionWire) : List String :=
  w.context.map (fun a => a.id)

def idsUnique (w : DecisionWire) : Bool :=
  decide (evidenceIds w).Nodup

def exactContextScope (w : DecisionWire) : Bool :=
  contextIds w == w.claim.assumptions

def evidenceCommitmentsBound (w : DecisionWire) : Bool :=
  w.evidence.all (fun e =>
    e.predicateCommitment == w.claim.predicateCommitment)

def wireCheck (w : DecisionWire) : Bool :=
  (w.source.claimId == w.claim.id) &&
  (evidenceIds w == w.claim.requiredEvidence) &&
  idsUnique w &&
  exactContextScope w &&
  evidenceCommitmentsBound w &&
  (decideClaim (decodeClaim w.claim) (decodedEvidence w) ==
    w.recordedDecision)

/--
A no-duplicate-ID fact about the wire evidence list is enough to establish the
strong uniqueness field required by the normalized decision input.
-/
theorem decodedEvidence_unique_of_wire_ids_nodup
    {w : DecisionWire}
    (h : (evidenceIds w).Nodup) :
    UniqueEvidenceIds (decodedEvidence w) := by
  sorry

/-- Exact claim-scoped context IDs imply the kernel's explicit context coverage. -/
theorem contextCovers_of_exact_context_scope
    {w : DecisionWire}
    (h : contextIds w = w.claim.assumptions) :
    ContextCovers (decodedContext w) (decodeClaim w.claim) := by
  sorry

/--
If every wire evidence object has the same full predicate commitment as the
claim, the decoded required evidence is predicate-bound in the Lean kernel.
-/
theorem requiredEvidenceBound_of_commitments
    {w : DecisionWire}
    (h : ∀ e ∈ w.evidence,
      e.predicateCommitment = w.claim.predicateCommitment) :
    RequiredEvidenceBound (decodeClaim w.claim) (decodedEvidence w) := by
  sorry

/-- A successful finite Boolean wire check constructs the typed formal invariant. -/
theorem wireCheck_sound
    {w : DecisionWire}
    (h : wireCheck w = true) :
    WellFormed w := by
  sorry

theorem wireCheck_computational_sound
    (w : DecisionWire)
    (checked : wireCheck w = true)
    (accepted : w.recordedDecision = DecisionStatus.computational) :
    Assures
      (decodedContext w)
      AssuranceLevel.computational
      (decodeClaim w.claim)
      (decodedEvidence w) := by
  exact wire_computational_sound w (wireCheck_sound checked) accepted

theorem wireCheck_formal_sound
    (w : DecisionWire)
    (checked : wireCheck w = true)
    (accepted : w.recordedDecision = DecisionStatus.formal) :
    Assures
      (decodedContext w)
      AssuranceLevel.formal
      (decodeClaim w.claim)
      (decodedEvidence w) := by
  exact wire_formal_sound w (wireCheck_sound checked) accepted

theorem wireCheck_empirical_sound
    (w : DecisionWire)
    (checked : wireCheck w = true)
    (accepted : w.recordedDecision = DecisionStatus.empirical) :
    Assures
      (decodedContext w)
      AssuranceLevel.empirical
      (decodeClaim w.claim)
      (decodedEvidence w) := by
  exact wire_empirical_sound w (wireCheck_sound checked) accepted

theorem wireCheck_mixed_sound
    (w : DecisionWire)
    (checked : wireCheck w = true)
    (accepted : w.recordedDecision = DecisionStatus.mixed) :
    Assures
      (decodedContext w)
      AssuranceLevel.mixed
      (decodeClaim w.claim)
      (decodedEvidence w) := by
  exact wire_mixed_sound w (wireCheck_sound checked) accepted

end PCS.ProofTasks.WireCheck
