import PCSEpistemic.Theorems
import PCSEpistemic.Controls

/-!
# Axiom audit for epistemic lattice theorems
-/

open PCSEpistemic PCSEpistemic.Controls

#print axioms empirical_requires_falsifier
#print axioms computational_requires_falsifier
#print axioms formal_may_omit_falsifier
#print axioms provenance_may_omit_falsifier
#print axioms classCompatible_iff
#print axioms depJoin_unsound_cons
#print axioms depJoin_refuted_only
#print axioms depJoin_supported_pair
#print axioms depJoin_open_blocks
#print axioms empty_empirical_package_unsound
#print axioms evalClaim_falsifier_refutes
#print axioms evidenceFor_wrong_class
#print axioms literal_matches_known
#print axioms claim_empirical_wellFormed
#print axioms good_claim_supported
#print axioms falsified_claim_refuted
#print axioms promotion_claim_open
#print axioms incomplete_claim_open
#print axioms dependent_reopens_when_premise_refuted
#print axioms dependent_supported_when_premise_supported
#print axioms unfalsifiable_not_wellFormed
#print axioms empty_empirical_package_unsound_control
#print axioms good_package_structurally_sound
