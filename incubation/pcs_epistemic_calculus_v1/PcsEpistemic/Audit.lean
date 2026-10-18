import PcsEpistemic.Controls

/-!
Axiom inventory anchors for principal theorems.

Approved transitive axioms for this incubation library: `propext`,
`Classical.choice`, `Quot.sound` (or fewer).
-/
set_option autoImplicit false

namespace PcsEpistemic.Audit

open PcsEpistemic

#print axioms no_computational_to_formal
#print axioms no_provenance_to_formal
#print axioms formal_covers_computational
#print axioms computational_cannot_assure_formal
#print axioms missing_evidence_blocks
#print axioms formal_evidence_assures_formal
#print axioms compose_assures
#print axioms compose_independent_support
#print axioms nonimpact_requires_completeness
#print axioms hidden_dependency_blocks_world_nonimpact
#print axioms affected_evidence_must_replay
#print axioms claimsRequiring_covers
#print axioms claim_requiring_affected_evidence_is_affected
#print axioms distinguishing_not_unanimous
#print axioms dispute_preserved_if_still_split
#print axioms ensemble_impact_covers_singleton
#print axioms agreement_core_singleton
#print axioms Controls.control_no_computational_to_formal
#print axioms Controls.control_formal_evidence_accepts
#print axioms Controls.control_computational_rejects_formal
#print axioms Controls.control_missing_evidence

end PcsEpistemic.Audit
