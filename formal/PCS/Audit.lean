import PCS.Core
import PCS.Decision
import PCS.Refinement
import PCS.Normalized
import PCS.Normalization
import PCS.DecisionExtraction
import PCS.SerializedBridge
import PCS.Wire
import PCS.WireVectors
import PCS.PKPD
import PCS.DecisionVectors
import PCS.AcceptanceTests

/-!
Audit surface for the PCS formal kernel.

A successful build prints the axiom dependencies of the main assurance,
decision-extraction, normalization, and normalized-state soundness theorems.
-/

#print axioms PCS.formal_assurance_has_checked_formal_proof
#print axioms PCS.computational_assurance_is_predicate_bound
#print axioms PCS.computational_assurance_has_correctness_evidence
#print axioms PCS.computational_assurance_cannot_use_unverified
#print axioms PCS.empirical_assurance_requires_empirical_class
#print axioms PCS.mixed_assurance_requires_both_classes
#print axioms PCS.assurance_context_is_explicit

#print axioms PCS.Decision.computationalEvidenceAccepts_sound
#print axioms PCS.Decision.formalEvidenceAccepts_sound

#print axioms PCS.Refinement.mem_requiredEvidenceFor_iff
#print axioms PCS.Refinement.boundTo_of_required
#print axioms PCS.Refinement.computational_witness_sound
#print axioms PCS.Refinement.formal_witness_sound
#print axioms PCS.Refinement.empirical_witness_sound
#print axioms PCS.Refinement.mixed_witness_sound
#print axioms PCS.Refinement.computational_claim_sound
#print axioms PCS.Refinement.formal_claim_sound
#print axioms PCS.Refinement.empirical_claim_sound
#print axioms PCS.Refinement.mixed_claim_sound

#print axioms PCS.Normalized.context_available
#print axioms PCS.Normalized.binding_available
#print axioms PCS.Normalized.evidence_ids_unique

#print axioms PCS.Normalization.uniqueEvidenceIds_implies_required_unambiguous
#print axioms PCS.Normalization.selected_evidence_id_required
#print axioms PCS.Normalization.selected_evidence_in_source
#print axioms PCS.Normalization.no_missingRequiredEvidence_has_witness

#print axioms PCS.DecisionExtraction.decideClaim_computational_extract
#print axioms PCS.DecisionExtraction.decideClaim_formal_extract
#print axioms PCS.DecisionExtraction.decideClaim_empirical_extract
#print axioms PCS.DecisionExtraction.decideClaim_mixed_extract
#print axioms PCS.DecisionExtraction.decideClaim_computational_sound
#print axioms PCS.DecisionExtraction.decideClaim_formal_sound
#print axioms PCS.DecisionExtraction.decideClaim_empirical_sound
#print axioms PCS.DecisionExtraction.decideClaim_mixed_sound

#print axioms PCS.SerializedBridge.normalized_computational_sound
#print axioms PCS.SerializedBridge.normalized_formal_sound
#print axioms PCS.SerializedBridge.normalized_empirical_sound
#print axioms PCS.SerializedBridge.normalized_mixed_sound

#print axioms PCS.PKPD.canonical_pk_units_valid
#print axioms PCS.PKPD.canonical_pd_units_valid


#print axioms PCS.Wire.source_claim_identity
#print axioms PCS.Wire.decoded_decision_matches_recorded
#print axioms PCS.Wire.predicate_commitment_eq_preserved
#print axioms PCS.Wire.wire_computational_sound
#print axioms PCS.Wire.wire_formal_sound
#print axioms PCS.Wire.wire_empirical_sound
#print axioms PCS.Wire.wire_mixed_sound
