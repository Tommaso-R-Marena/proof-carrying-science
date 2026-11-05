import PCS.V2.TranslationFixtures
import PCS.V2.TranslationJson

/-! Axiom audit of PCS Semantic Translation Contract v1 (printed on every build).
    Expected: only `propext`, `Classical.choice`, `Quot.sound` (or a subset); never `sorryAx`,
    `Lean.ofReduceBool` or a project axiom. -/

open PCS.V2.Semantic PCS.V2.Semantic.Fixtures

-- semantics and normalization
#print axioms Term.denote_hasSort
#print axioms Formula.toDB_denote
#print axioms SemanticClaim.normalize_denote
#print axioms alphaEquiv_denote_iff
-- explanation IR
#print axioms explanation_roundtrip
#print axioms explanationIR_preserves_semantics
#print axioms explanation_references_grounded
#print axioms explanation_references_complete
-- checker: exact characterisation, flagship, preservation
#print axioms translationAccepts_iff
#print axioms translation_acceptance_sound
#print axioms accepted_translation_preserves_meaning
#print axioms accepted_translation_preserves_meaning_typed
#print axioms accepted_explanation_means_interpretation
#print axioms accepted_translation_uses_only_grounded_symbols
#print axioms accepted_translation_has_no_unresolved_ambiguity
#print axioms accepted_translation_preserves_quantifiers
#print axioms accepted_translation_preserves_negation
#print axioms accepted_translation_preserves_assumptions
#print axioms accepted_translation_has_no_unexpected_free_variables
#print axioms accepted_translation_roundtrips
-- rejection theorems
#print axioms semantically_inequivalent_rejected
#print axioms unknown_symbol_rejected
#print axioms unresolved_ambiguity_rejected
#print axioms dropped_assumption_rejected
#print axioms added_assumption_rejected
#print axioms quantifier_change_rejected
#print axioms polarity_change_rejected
#print axioms shadowed_or_duplicate_grounding_rejected
#print axioms incorrect_symbol_identity_rejected
#print axioms forged_confirmation_rejected
#print axioms disallowed_axiom_rejected
#print axioms decision_ignores_model_metadata
-- authority, obligation graphs, proposers
#print axioms translation_authority_sound
#print axioms semanticChecker_sound
#print axioms translated_claim_graph_sound_memo
#print axioms untrusted_proposer_cannot_bypass_translation_authority
#print axioms no_strategy_forges_translation
-- wire format and executable front end
#print axioms decRequest_encRequest
#print axioms semanticCheck_accepted_iff
#print axioms semanticCheck_encRequest
-- fixtures (kernel `decide`)
#print axioms safety_accepted
#print axioms arith_interpretation_holds
#print axioms qOrder_rejected
#print axioms capture_codes
#print axioms explanationMismatch_code
#print axioms confidence_never_matters
