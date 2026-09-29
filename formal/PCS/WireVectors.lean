import PCS.Wire

namespace PCS.WireVectors

open PCS
open PCS.Decision
open PCS.Wire
open PCS.Refinement
open PCS.Normalization

def pkpdPredicateCommitment : String :=
  "pcs-predicate-sha256:8cc9e0b74e7361040ed704b89f6753399f9c07573fe51198f0f093c6017f2c4c"

def pkpdWire : DecisionWire :=
  {
    source := {
      certificateSemanticHash :=
        "0fc13509d27c7b31e45ed9a841bfacddc9ca8a1a6c7e3a2af66e0b434cb36a8a"
      claimId := "C_PK_REPLAY"
    }
    context := [
      {
        id := "A_PK_MODEL"
        statement :=
          "The restricted one-compartment IV-bolus equation is the declared computational model; no claim of biological adequacy is made."
      }
    ]
    claim := {
      id := "C_PK_REPLAY"
      kind := ClaimKind.computational
      predicateCommitment := some pkpdPredicateCommitment
      requiredEvidence := ["E_PK_REPLAY"]
      assumptions := ["A_PK_MODEL"]
    }
    evidence := [
      {
        id := "E_PK_REPLAY"
        kind := EvidenceKind.computationalTest
        outcome := Outcome.pass
        predicateCommitment := some pkpdPredicateCommitment
      }
    ]
    recordedDecision := DecisionStatus.computational
  }

example : pkpdWire.source.claimId = pkpdWire.claim.id := by
  decide

example : evidenceIds pkpdWire = pkpdWire.claim.requiredEvidence := by
  decide

example :
    pkpdWire.evidence.head?.map (fun e => (decodeEvidence e).predicate) =
      some (decodeClaim pkpdWire.claim).predicate := by
  decide

example :
    decideClaim (decodeClaim pkpdWire.claim) (decodedEvidence pkpdWire) =
      DecisionStatus.computational := by
  decide

def pkpdWireWellFormed : WellFormed pkpdWire := by
  constructor
  · rfl
  · rfl
  · rfl
  · simp [UniqueEvidenceIds, decodedEvidence, decodeEvidence, pkpdWire]
  · simp [ContextCovers, decodedContext, decodeAssumption, decodeClaim, pkpdWire]
  · simp [RequiredEvidenceBound, requiredEvidenceFor, decodedEvidence,
      decodeEvidence, decodeClaim, decodePredicateCommitment, pkpdWire,
      pkpdPredicateCommitment]
  · decide

example :
    Assures
      (decodedContext pkpdWire)
      AssuranceLevel.computational
      (decodeClaim pkpdWire.claim)
      (decodedEvidence pkpdWire) := by
  exact wire_computational_sound pkpdWire pkpdWireWellFormed rfl

end PCS.WireVectors
