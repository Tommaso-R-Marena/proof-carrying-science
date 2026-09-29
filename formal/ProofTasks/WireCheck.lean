import PCS.WireCheck
import PCS.WireVectors

/-!
The finite wire-checker bridge has been promoted to the production module
`PCS.WireCheck`. This file re-states the promoted theorems verbatim so that
`lake env lean ProofTasks/WireCheck.lean` still type-checks the staged targets.
-/

namespace PCS.ProofTasks.WireCheck

open PCS
open PCS.Decision
open PCS.Refinement
open PCS.Normalization
open PCS.Wire
open PCS.WireCheck

example {w : DecisionWire} (h : (evidenceIds w).Nodup) :
    UniqueEvidenceIds (decodedEvidence w) :=
  decodedEvidence_unique_of_wire_ids_nodup h

example {w : DecisionWire} (h : contextIds w = w.claim.assumptions) :
    ContextCovers (decodedContext w) (decodeClaim w.claim) :=
  contextCovers_of_exact_context_scope h

example {w : DecisionWire}
    (h : ∀ e ∈ w.evidence,
      e.predicateCommitment = w.claim.predicateCommitment) :
    RequiredEvidenceBound (decodeClaim w.claim) (decodedEvidence w) :=
  requiredEvidenceBound_of_commitments h

example {w : DecisionWire} (h : wireCheck w = true) : WellFormed w :=
  wireCheck_sound h

/-- The frozen PK/PD wire vector passes the Boolean checker by evaluation. -/
example : wireCheck PCS.WireVectors.pkpdWire = true := by decide

/-- Tampering the recorded decision is rejected by the Boolean checker. -/
example :
    wireCheck { PCS.WireVectors.pkpdWire with
      recordedDecision := PCS.Decision.DecisionStatus.formal } = false := by
  decide

end PCS.ProofTasks.WireCheck
