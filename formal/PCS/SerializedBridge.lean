import PCS.Normalized
import PCS.DecisionExtraction

namespace PCS.SerializedBridge

open PCS.Decision
open PCS.Refinement
open PCS.Normalized
open PCS.DecisionExtraction

/--
Soundness bridge from a normalized, replayed decision input into the logical
assurance judgment. Raw serialized bytes, strict JSON/schema validation, and
evidence replay remain a separate executable/refinement boundary.
-/
theorem normalized_computational_sound
    (input : DecisionInput)
    (h : decide input = DecisionStatus.computational) :
    Assures input.Γ AssuranceLevel.computational input.claim input.evidence := by
  exact decideClaim_computational_sound input.context input.binding h

theorem normalized_formal_sound
    (input : DecisionInput)
    (h : decide input = DecisionStatus.formal) :
    Assures input.Γ AssuranceLevel.formal input.claim input.evidence := by
  exact decideClaim_formal_sound input.context input.binding h

theorem normalized_empirical_sound
    (input : DecisionInput)
    (h : decide input = DecisionStatus.empirical) :
    Assures input.Γ AssuranceLevel.empirical input.claim input.evidence := by
  exact decideClaim_empirical_sound input.context input.binding h

theorem normalized_mixed_sound
    (input : DecisionInput)
    (h : decide input = DecisionStatus.mixed) :
    Assures input.Γ AssuranceLevel.mixed input.claim input.evidence := by
  exact decideClaim_mixed_sound input.context input.binding h

end PCS.SerializedBridge
