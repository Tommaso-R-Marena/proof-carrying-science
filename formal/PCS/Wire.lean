import PCS.SerializedBridge
import PCS.Normalization

namespace PCS.Wire

open PCS
open PCS.Decision
open PCS.Refinement
open PCS.Normalized
open PCS.Normalization
open PCS.SerializedBridge

/-- Version of the deliberately small claim-scoped normalized wire format. -/
inductive WireVersion
  | v1
  deriving DecidableEq, Repr

/-- Source metadata retained across the executable -> formal boundary. -/
structure WireSource where
  certificateSemanticHash : String
  claimId : String
  deriving DecidableEq, Repr

structure WireAssumption where
  id : String
  statement : String := ""
  deriving DecidableEq, Repr

/--
The full Python predicate is SHA-256 committed before crossing the wire boundary.
Lean only needs exact identity for the decision/soundness layer, so the digest is
represented as an opaque predicate tag rather than projecting away domain fields.
-/
abbrev PredicateCommitment := String

structure WireEvidence where
  id : String
  kind : EvidenceKind
  outcome : Outcome
  predicateCommitment : Option PredicateCommitment := none
  deriving DecidableEq, Repr

structure WireClaim where
  id : String
  kind : ClaimKind
  predicateCommitment : Option PredicateCommitment := none
  requiredEvidence : List String := []
  assumptions : List String := []
  deriving DecidableEq, Repr

structure DecisionWire where
  version : WireVersion := WireVersion.v1
  source : WireSource
  context : List WireAssumption
  claim : WireClaim
  evidence : List WireEvidence
  recordedDecision : DecisionStatus
  deriving DecidableEq, Repr

def decodePredicateCommitment : Option PredicateCommitment → Option Predicate
  | none => none
  | some tag => some (Predicate.opaque tag)

def decodeAssumption (a : WireAssumption) : Assumption :=
  { id := a.id, statement := a.statement }

def decodeEvidence (e : WireEvidence) : Evidence :=
  {
    id := e.id
    kind := e.kind
    outcome := e.outcome
    predicate := decodePredicateCommitment e.predicateCommitment
  }

def decodeClaim (c : WireClaim) : Claim :=
  {
    id := c.id
    kind := c.kind
    predicate := decodePredicateCommitment c.predicateCommitment
    requiredEvidence := c.requiredEvidence
    assumptions := c.assumptions
  }

def decodedContext (w : DecisionWire) : List Assumption :=
  w.context.map decodeAssumption

def decodedEvidence (w : DecisionWire) : List Evidence :=
  w.evidence.map decodeEvidence

def evidenceIds (w : DecisionWire) : List String :=
  w.evidence.map (fun e => e.id)

def contextIds (w : DecisionWire) : List String :=
  w.context.map (fun a => a.id)

/--
Well-formedness facts that must be established by the executable decoder/
normalizer before the typed wire state may enter the machine-checked decision
bridge.

The JSON parser and SHA-256 implementation are intentionally not hidden here:
they are the remaining lower refinement boundary.
-/
structure WellFormed (w : DecisionWire) : Prop where
  sourceClaim : w.source.claimId = w.claim.id
  exactEvidenceScope : evidenceIds w = w.claim.requiredEvidence
  exactContextScope : contextIds w = w.claim.assumptions
  uniqueEvidenceIds : UniqueEvidenceIds (decodedEvidence w)
  context : ContextCovers (decodedContext w) (decodeClaim w.claim)
  binding : RequiredEvidenceBound (decodeClaim w.claim) (decodedEvidence w)
  decision :
    decideClaim (decodeClaim w.claim) (decodedEvidence w) = w.recordedDecision

/-- Decode a well-formed wire state into the already machine-checked normalized input. -/
def toDecisionInput (w : DecisionWire) (h : WellFormed w) : DecisionInput where
  version := NormalizedVersion.v1
  Γ := decodedContext w
  claim := decodeClaim w.claim
  evidence := decodedEvidence w
  uniqueEvidenceIds := h.uniqueEvidenceIds
  context := h.context
  binding := h.binding

theorem source_claim_identity {w : DecisionWire} (h : WellFormed w) :
    w.source.claimId = (toDecisionInput w h).claim.id := by
  simpa [toDecisionInput, decodeClaim] using h.sourceClaim

theorem exact_context_scope_preserved {w : DecisionWire} (h : WellFormed w) :
    contextIds w = (toDecisionInput w h).claim.assumptions := by
  simpa [toDecisionInput, decodeClaim] using h.exactContextScope

theorem decoded_decision_matches_recorded
    (w : DecisionWire) (h : WellFormed w) :
    decide (toDecisionInput w h) = w.recordedDecision := by
  simpa [decide, toDecisionInput] using h.decision

/-- Exact predicate-commitment equality is preserved by decoding. -/
theorem predicate_commitment_eq_preserved
    {a b : Option PredicateCommitment}
    (h : a = b) :
    decodePredicateCommitment a = decodePredicateCommitment b := by
  exact congrArg decodePredicateCommitment h

theorem wire_computational_sound
    (w : DecisionWire) (h : WellFormed w)
    (accepted : w.recordedDecision = DecisionStatus.computational) :
    Assures
      (decodedContext w)
      AssuranceLevel.computational
      (decodeClaim w.claim)
      (decodedEvidence w) := by
  apply normalized_computational_sound (toDecisionInput w h)
  exact (decoded_decision_matches_recorded w h).trans accepted

theorem wire_formal_sound
    (w : DecisionWire) (h : WellFormed w)
    (accepted : w.recordedDecision = DecisionStatus.formal) :
    Assures
      (decodedContext w)
      AssuranceLevel.formal
      (decodeClaim w.claim)
      (decodedEvidence w) := by
  apply normalized_formal_sound (toDecisionInput w h)
  exact (decoded_decision_matches_recorded w h).trans accepted

theorem wire_empirical_sound
    (w : DecisionWire) (h : WellFormed w)
    (accepted : w.recordedDecision = DecisionStatus.empirical) :
    Assures
      (decodedContext w)
      AssuranceLevel.empirical
      (decodeClaim w.claim)
      (decodedEvidence w) := by
  apply normalized_empirical_sound (toDecisionInput w h)
  exact (decoded_decision_matches_recorded w h).trans accepted

theorem wire_mixed_sound
    (w : DecisionWire) (h : WellFormed w)
    (accepted : w.recordedDecision = DecisionStatus.mixed) :
    Assures
      (decodedContext w)
      AssuranceLevel.mixed
      (decodeClaim w.claim)
      (decodedEvidence w) := by
  apply normalized_mixed_sound (toDecisionInput w h)
  exact (decoded_decision_matches_recorded w h).trans accepted

end PCS.Wire
