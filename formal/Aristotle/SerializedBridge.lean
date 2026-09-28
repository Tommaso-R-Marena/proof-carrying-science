import PCS.Normalized

namespace PCS.Aristotle.SerializedBridge

open PCS.Decision
open PCS.Refinement
open PCS.Normalized

/-
These obligations become straightforward after DecisionExtraction.lean is solved.
They deliberately start from Normalized.DecisionInput rather than raw JSON.

Raw serialized bytes -> strict JSON -> schema-valid object -> replayed normalized
DecisionInput remains a separate executable/refinement boundary.
-/

theorem normalized_computational_sound
    (input : DecisionInput)
    (h : decide input = DecisionStatus.computational) :
    Assures input.Γ AssuranceLevel.computational input.claim input.evidence := by
  sorry

theorem normalized_formal_sound
    (input : DecisionInput)
    (h : decide input = DecisionStatus.formal) :
    Assures input.Γ AssuranceLevel.formal input.claim input.evidence := by
  sorry

theorem normalized_empirical_sound
    (input : DecisionInput)
    (h : decide input = DecisionStatus.empirical) :
    Assures input.Γ AssuranceLevel.empirical input.claim input.evidence := by
  sorry

theorem normalized_mixed_sound
    (input : DecisionInput)
    (h : decide input = DecisionStatus.mixed) :
    Assures input.Γ AssuranceLevel.mixed input.claim input.evidence := by
  sorry

end PCS.Aristotle.SerializedBridge
