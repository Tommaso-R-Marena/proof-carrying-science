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
        "345cf0e67ece949156d0ce7a5e35b4dbc4d22dc87855fcb7f76fea3ee9bf628a"
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
      "f414d613bd01e6507d35c75e65f374a8db061438a16321064bb06c8fd45fc253"
  }

example : decodeRawWire rawPkpdWire = some pkpdWire := by
  decide

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
