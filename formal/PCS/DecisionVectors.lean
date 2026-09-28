import PCS.Decision

namespace PCS.DecisionVectors

open PCS.Decision

def mkClaim (kind : ClaimKind) (required : List String) : Claim where
  id := "C"
  kind := kind
  requiredEvidence := required

def mkEvidence (id : String) (kind : EvidenceKind) (outcome : Outcome) : Evidence where
  id := id
  kind := kind
  outcome := outcome

example :
    decideClaim (mkClaim ClaimKind.computational ["E"]) [] =
      DecisionStatus.open_ := by
  decide

example :
    decideClaim
      (mkClaim ClaimKind.computational ["E"])
      [mkEvidence "E" EvidenceKind.computationalTest Outcome.unverified] =
      DecisionStatus.open_ := by
  decide

example :
    decideClaim
      (mkClaim ClaimKind.computational ["E"])
      [mkEvidence "E" EvidenceKind.computationalTest Outcome.fail] =
      DecisionStatus.failed := by
  decide

example :
    decideClaim
      (mkClaim ClaimKind.computational ["E"])
      [mkEvidence "E" EvidenceKind.computationalTest Outcome.pass] =
      DecisionStatus.computational := by
  decide

example :
    decideClaim
      (mkClaim ClaimKind.formal ["E"])
      [mkEvidence "E" EvidenceKind.formalProof Outcome.pass] =
      DecisionStatus.formal := by
  decide

example :
    decideClaim
      (mkClaim ClaimKind.formal ["E"])
      [mkEvidence "E" EvidenceKind.computationalTest Outcome.pass] =
      DecisionStatus.open_ := by
  decide

example :
    decideClaim
      (mkClaim ClaimKind.empirical ["E"])
      [mkEvidence "E" EvidenceKind.empiricalValidation Outcome.pass] =
      DecisionStatus.empirical := by
  decide

example :
    decideClaim
      (mkClaim ClaimKind.empirical ["E"])
      [mkEvidence "E" EvidenceKind.statisticalValidation Outcome.pass] =
      DecisionStatus.empirical := by
  decide

example :
    decideClaim
      (mkClaim ClaimKind.mixed ["F", "V"])
      [ mkEvidence "F" EvidenceKind.formalProof Outcome.pass
      , mkEvidence "V" EvidenceKind.statisticalValidation Outcome.pass ] =
      DecisionStatus.mixed := by
  decide

example :
    decideClaim
      (mkClaim ClaimKind.mixed ["F"])
      [mkEvidence "F" EvidenceKind.formalProof Outcome.pass] =
      DecisionStatus.open_ := by
  decide

/-- This is the cross-language case that required aligning the logical kernel:
    a formal proof may discharge a computational claim as stronger evidence. -/
example :
    decideClaim
      (mkClaim ClaimKind.computational ["F"])
      [mkEvidence "F" EvidenceKind.formalProof Outcome.pass] =
      DecisionStatus.computational := by
  decide

end PCS.DecisionVectors
