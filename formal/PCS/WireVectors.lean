import PCS.Wire

namespace PCS.WireVectors

open PCS
open PCS.Decision
open PCS.Wire

def pkpdPredicateCommitment : String :=
  "pcs-predicate-sha256:8cc9e0b74e7361040ed704b89f6753399f9c07573fe51198f0f093c6017f2c4c"

def pkpdWire : DecisionWire :=
  {
    source := {
      certificateSemanticHash :=
        "345cf0e67ece949156d0ce7a5e35b4dbc4d22dc87855fcb7f76fea3ee9bf628a"
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
    (decodeClaim pkpdWire.claim).predicate =
      (decodeEvidence pkpdWire.evidence.head!).predicate := by
  decide

example :
    decideClaim (decodeClaim pkpdWire.claim) (decodedEvidence pkpdWire) =
      DecisionStatus.computational := by
  decide

end PCS.WireVectors
