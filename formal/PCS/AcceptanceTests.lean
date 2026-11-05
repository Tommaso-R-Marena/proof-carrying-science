import PCS.DecisionVectors
import PCS.Normalized

namespace PCS.AcceptanceTests

open PCS.Decision

/-- Extra evidence that is not required by the claim must not poison the claim. -/
example :
    decideClaim
      (PCS.DecisionVectors.mkClaim ClaimKind.computational ["E"])
      [ PCS.DecisionVectors.mkEvidence "E" EvidenceKind.computationalTest Outcome.pass
      , PCS.DecisionVectors.mkEvidence "UNRELATED" EvidenceKind.computationalTest Outcome.fail ] =
      DecisionStatus.computational := by
  decide

/-- If one of several required evidence IDs is missing, the claim remains OPEN. -/
example :
    decideClaim
      (PCS.DecisionVectors.mkClaim ClaimKind.computational ["E1", "E2"])
      [PCS.DecisionVectors.mkEvidence "E1" EvidenceKind.computationalTest Outcome.pass] =
      DecisionStatus.open_ := by
  decide

/-- A required failure dominates another passing required evidence object. -/
example :
    decideClaim
      (PCS.DecisionVectors.mkClaim ClaimKind.computational ["E1", "E2"])
      [ PCS.DecisionVectors.mkEvidence "E1" EvidenceKind.computationalTest Outcome.pass
      , PCS.DecisionVectors.mkEvidence "E2" EvidenceKind.formalProof Outcome.fail ] =
      DecisionStatus.failed := by
  decide

/-- UNVERIFIED required evidence keeps an otherwise passing claim OPEN. -/
example :
    decideClaim
      (PCS.DecisionVectors.mkClaim ClaimKind.computational ["E1", "E2"])
      [ PCS.DecisionVectors.mkEvidence "E1" EvidenceKind.computationalTest Outcome.pass
      , PCS.DecisionVectors.mkEvidence "E2" EvidenceKind.formalProof Outcome.unverified ] =
      DecisionStatus.open_ := by
  decide

/-- No required evidence means OPEN even when unrelated passing evidence exists. -/
example :
    decideClaim
      (PCS.DecisionVectors.mkClaim ClaimKind.computational [])
      [PCS.DecisionVectors.mkEvidence "E" EvidenceKind.computationalTest Outcome.pass] =
      DecisionStatus.open_ := by
  decide

/-- A formal claim is deliberately strict: every required item must be a formal proof. -/
example :
    decideClaim
      (PCS.DecisionVectors.mkClaim ClaimKind.formal ["F", "C"])
      [ PCS.DecisionVectors.mkEvidence "F" EvidenceKind.formalProof Outcome.pass
      , PCS.DecisionVectors.mkEvidence "C" EvidenceKind.computationalTest Outcome.pass ] =
      DecisionStatus.open_ := by
  decide

/-- Statistical validation is an accepted empirical evidence class. -/
example :
    decideClaim
      (PCS.DecisionVectors.mkClaim ClaimKind.empirical ["S"])
      [PCS.DecisionVectors.mkEvidence "S" EvidenceKind.statisticalValidation Outcome.pass] =
      DecisionStatus.empirical := by
  decide

/-- A formal proof alone does not silently promote an empirical claim. -/
example :
    decideClaim
      (PCS.DecisionVectors.mkClaim ClaimKind.empirical ["F"])
      [PCS.DecisionVectors.mkEvidence "F" EvidenceKind.formalProof Outcome.pass] =
      DecisionStatus.open_ := by
  decide

/-- Mixed assurance requires both a formal correctness role and an empirical role. -/
example :
    decideClaim
      (PCS.DecisionVectors.mkClaim ClaimKind.mixed ["F", "V"])
      [ PCS.DecisionVectors.mkEvidence "F" EvidenceKind.formalProof Outcome.pass
      , PCS.DecisionVectors.mkEvidence "V" EvidenceKind.empiricalValidation Outcome.pass ] =
      DecisionStatus.mixed := by
  decide

/-- Formal + computational evidence is insufficient for mixed assurance. -/
example :
    decideClaim
      (PCS.DecisionVectors.mkClaim ClaimKind.mixed ["F", "C"])
      [ PCS.DecisionVectors.mkEvidence "F" EvidenceKind.formalProof Outcome.pass
      , PCS.DecisionVectors.mkEvidence "C" EvidenceKind.computationalTest Outcome.pass ] =
      DecisionStatus.open_ := by
  decide

/-- Stronger formal evidence may discharge a computational claim. -/
example :
    decideClaim
      (PCS.DecisionVectors.mkClaim ClaimKind.computational ["F"])
      [PCS.DecisionVectors.mkEvidence "F" EvidenceKind.formalProof Outcome.pass] =
      DecisionStatus.computational := by
  decide

/-- Empirical/statistical evidence alone must not discharge a computational claim. -/
example :
    decideClaim
      (PCS.DecisionVectors.mkClaim ClaimKind.computational ["V"])
      [PCS.DecisionVectors.mkEvidence "V" EvidenceKind.statisticalValidation Outcome.pass] =
      DecisionStatus.open_ := by
  decide

end PCS.AcceptanceTests
