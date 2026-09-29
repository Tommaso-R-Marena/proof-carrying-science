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
        "b1f03d0f97df1e257cc00da492b91bf0f31df2f5b9562938d058df060c57d13e"
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
    wireSemanticHash :=
      "8ad40ede070c1dfb6846dd334eb5cb08d622233feb149eb7875ec432878ef188"
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
