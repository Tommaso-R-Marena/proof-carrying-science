import PcsEpistemic.Controls
import PcsEpistemic.Laws

/-!
Axiom inventory anchors for principal theorems.

Approved transitive axioms: `propext`, `Classical.choice`, `Quot.sound` (or fewer).
This incubation currently uses only `propext` and/or `Quot.sound`.
-/
set_option autoImplicit false

namespace PcsEpistemic.Audit

open PcsEpistemic

#print axioms no_computational_to_formal
#print axioms no_provenance_to_formal
#print axioms formal_covers_computational
#print axioms le_antisymm
#print axioms le_trans
#print axioms computational_incomparable_empirical
#print axioms formal_incomparable_empirical
#print axioms provenance_discharges_only_self
#print axioms meet_formal_empirical_collapses
#print axioms computational_cannot_assure_formal
#print axioms missing_evidence_blocks
#print axioms formal_evidence_assures_formal
#print axioms rejected_evidence_blocks
#print axioms empty_requirements_supported
#print axioms formal_evidence_assures_computational
#print axioms empirical_cannot_assure_formal
#print axioms compose_assures
#print axioms compose_independent_support
#print axioms nonimpact_requires_completeness
#print axioms hidden_dependency_blocks_world_nonimpact
#print axioms incomplete_never_endorses
#print axioms claimsRequiring_covers
#print axioms claim_requiring_affected_evidence_is_affected
#print axioms distinguishing_not_unanimous
#print axioms dispute_preserved_if_still_split
#print axioms agreement_core_empty_ensemble
#print axioms agreement_dispute_disjoint
#print axioms unanimous_not_distinguishing
#print axioms agreement_core_subset_candidates
#print axioms dispute_frontier_subset_candidates
#print axioms Controls.control_no_computational_to_formal
#print axioms Controls.control_formal_evidence_accepts
#print axioms Controls.control_computational_rejects_formal
#print axioms Controls.control_missing_evidence
#print axioms Controls.control_rejected_blocks_formal
#print axioms Controls.control_agreement_dispute_disjoint
#print axioms Controls.control_incomplete_never_endorses

end PcsEpistemic.Audit
