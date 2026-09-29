import PCS.Wire

namespace PCS.WireCodec

open PCS
open PCS.Decision
open PCS.Wire

def expectedWireFormat : String := "pcs-normalized-decision-v1"
def expectedSpecVersion : String := "pcs-0.5"
def expectedCheckerVersion : String := "pcs-python-kernel/0.5.0"

structure RawSource where
  specVersion : String
  checkerVersion : String
  certificateSemanticHash : String
  claimId : String
  deriving DecidableEq, Repr

structure RawClaim where
  id : String
  kind : String
  predicateCommitment : Option String := none
  requiredEvidence : List String := []
  assumptions : List String := []
  deriving DecidableEq, Repr

structure RawEvidence where
  id : String
  kind : String
  outcome : String
  predicateCommitment : Option String := none
  deriving DecidableEq, Repr

structure RawDecisionWire where
  wireFormat : String
  source : RawSource
  context : List WireAssumption
  claim : RawClaim
  evidence : List RawEvidence
  decision : String
  wireSemanticHash : String
  deriving DecidableEq, Repr

def decodeClaimKind : String → Option ClaimKind
  | "formal" => some ClaimKind.formal
  | "computational" => some ClaimKind.computational
  | "empirical" => some ClaimKind.empirical
  | "mixed" => some ClaimKind.mixed
  | _ => none

def decodeEvidenceKind : String → Option EvidenceKind
  | "formal_proof" => some EvidenceKind.formalProof
  | "computational_test" => some EvidenceKind.computationalTest
  | "statistical_validation" => some EvidenceKind.statisticalValidation
  | "empirical_validation" => some EvidenceKind.empiricalValidation
  | "provenance" => some EvidenceKind.provenance
  | _ => none

def decodeOutcome : String → Option Outcome
  | "PASS" => some Outcome.pass
  | "FAIL" => some Outcome.fail
  | "UNVERIFIED" => some Outcome.unverified
  | _ => none

def decodeDecisionStatus : String → Option DecisionStatus
  | "FORMALLY_VERIFIED_UNDER_ASSUMPTIONS" => some DecisionStatus.formal
  | "COMPUTATIONALLY_SUPPORTED" => some DecisionStatus.computational
  | "EMPIRICALLY_VALIDATED_WITHIN_SCOPE" => some DecisionStatus.empirical
  | "MIXED_SUPPORT_UNDER_ASSUMPTIONS" => some DecisionStatus.mixed
  | "OPEN" => some DecisionStatus.open_
  | "FALSIFIED_OR_CHECK_FAILED" => some DecisionStatus.failed
  | _ => none

def decodeClaim (raw : RawClaim) : Option WireClaim := do
  let kind ← decodeClaimKind raw.kind
  pure {
    id := raw.id
    kind := kind
    predicateCommitment := raw.predicateCommitment
    requiredEvidence := raw.requiredEvidence
    assumptions := raw.assumptions
  }

def decodeEvidence (raw : RawEvidence) : Option WireEvidence := do
  let kind ← decodeEvidenceKind raw.kind
  let outcome ← decodeOutcome raw.outcome
  pure {
    id := raw.id
    kind := kind
    outcome := outcome
    predicateCommitment := raw.predicateCommitment
  }

def decodeEvidenceList : List RawEvidence → Option (List WireEvidence)
  | [] => some []
  | x :: xs => do
      let head ← decodeEvidence x
      let tail ← decodeEvidenceList xs
      pure (head :: tail)

def decodeRawWire (raw : RawDecisionWire) : Option DecisionWire := do
  if raw.wireFormat != expectedWireFormat then none
  else if raw.source.specVersion != expectedSpecVersion then none
  else if raw.source.checkerVersion != expectedCheckerVersion then none
  else
    let claim ← decodeClaim raw.claim
    let evidence ← decodeEvidenceList raw.evidence
    let decision ← decodeDecisionStatus raw.decision
    pure {
      version := WireVersion.v1
      source := {
        certificateSemanticHash := raw.source.certificateSemanticHash
        claimId := raw.source.claimId
      }
      context := raw.context
      claim := claim
      evidence := evidence
      recordedDecision := decision
    }

theorem decodeClaimKind_computational :
    decodeClaimKind "computational" = some ClaimKind.computational := rfl

theorem decodeEvidenceKind_computationalTest :
    decodeEvidenceKind "computational_test" = some EvidenceKind.computationalTest := rfl

theorem decodeOutcome_pass :
    decodeOutcome "PASS" = some Outcome.pass := rfl

theorem decodeDecisionStatus_computational :
    decodeDecisionStatus "COMPUTATIONALLY_SUPPORTED" =
      some DecisionStatus.computational := rfl

theorem unknown_claim_kind_rejected :
    decodeClaimKind "unknown" = none := rfl

theorem unknown_evidence_kind_rejected :
    decodeEvidenceKind "unknown" = none := rfl

theorem unknown_outcome_rejected :
    decodeOutcome "MAYBE" = none := rfl

theorem unknown_decision_rejected :
    decodeDecisionStatus "ACCEPTED" = none := rfl

end PCS.WireCodec
