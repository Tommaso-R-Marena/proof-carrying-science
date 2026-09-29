import PCS.Core
import PCS.Decision
import PCS.Refinement
import PCS.Normalized
import PCS.PKPD
import PCS.DecisionVectors
import PCS.AcceptanceTests

/-!
Audit surface for the PCS formal kernel.

These commands are intentionally kept in source so a successful Lean build reports
the axiom dependencies of the main soundness/refinement statements. After Aristotle
closes the staged obligations, add the promoted direct decision/normalized bridge
theorems here as well.
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

#print axioms PCS.PKPD.canonical_pk_units_valid
#print axioms PCS.PKPD.canonical_pd_units_valid
