import PCS.WireCodec
import PCS.WireVectors

namespace PCS.WireCodecVectors

open PCS
open PCS.Wire
open PCS.WireVectors
open PCS.WireCodec

def rawPkpdWire : RawDecisionWire :=
  {
    wireFormat := expectedWireFormat
    source := {
      specVersion := expectedSpecVersion
      checkerVersion := expectedCheckerVersion
      certificateSemanticHash :=
        "0fc13509d27c7b31e45ed9a841bfacddc9ca8a1a6c7e3a2af66e0b434cb36a8a"
      claimId := "C_PK_REPLAY"
    }
    context := pkpdWire.context
    claim := {
      id := "C_PK_REPLAY"
      kind := "computational"
      predicateCommitment := some pkpdPredicateCommitment
      requiredEvidence := ["E_PK_REPLAY"]
      assumptions := ["A_PK_MODEL"]
    }
    evidence := [
      {
        id := "E_PK_REPLAY"
        kind := "computational_test"
        outcome := "PASS"
        predicateCommitment := some pkpdPredicateCommitment
      }
    ]
    decision := "COMPUTATIONALLY_SUPPORTED"
    invariants := {
      uniqueEvidenceIds := true
      requiredIdsUnique := true
      allRequiredEvidencePresent := true
      contextCovers := true
      requiredEvidenceBound := true
    }
    wireSemanticHash :=
      "c5d3da1f6296a62e3affe9f7d43c3c8d50f51b0b99f75da459ca613d0e5580a7"
  }

example : decodeRawWire rawPkpdWire = some pkpdWire := by
  rfl

def badVersionWire : RawDecisionWire :=
  { rawPkpdWire with wireFormat := "pcs-normalized-decision-v999" }

example : decodeRawWire badVersionWire = none := by
  decide

def badEvidenceKindWire : RawDecisionWire :=
  {
    rawPkpdWire with
    evidence := [
      {
        id := "E_PK_REPLAY"
        kind := "magic_evidence"
        outcome := "PASS"
        predicateCommitment := some pkpdPredicateCommitment
      }
    ]
  }

example : decodeRawWire badEvidenceKindWire = none := by
  decide

end PCS.WireCodecVectors
