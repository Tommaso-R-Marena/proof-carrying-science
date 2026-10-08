import PCS.V2.GenericCounterexamples
import PCS.V2.Witnesses.WorkflowWitness

/-!
Audit surface for the generic-domain layer: a successful build prints the axiom
dependencies of every generic theorem, every witness theorem and every counterexample.
-/

-- Theorem 2: obligation graphs
#print axioms PCS.V2.ClaimGraph.root_assurance_sound
#print axioms PCS.V2.ClaimGraph.accepted_graph_facts
#print axioms PCS.V2.ClaimGraph.cycle_rejected
#print axioms PCS.V2.ClaimGraph.missing_child_rejected
#print axioms PCS.V2.ClaimGraph.duplicate_ids_rejected
#print axioms PCS.V2.ClaimGraph.unsupported_rejected
#print axioms PCS.V2.ClaimGraph.Checker.sumLeaf_sound
-- Theorem 1: generic domain adapters
#print axioms PCS.V2.DomainAdapter.pcsChecker_sound
#print axioms PCS.V2.DomainAdapter.domain_adapter_sound
-- Theorem 5: flagship (production and extended authority)
#print axioms PCS.V2.DomainAuthority.pcs_generic_domain_archive_acceptance_sound
#print axioms PCS.V2.DomainAuthority.pcs_generic_domain_archive_acceptance_sound_builtin
#print axioms PCS.V2.DomainAuthority.acceptArchiveWithCheckers_nil
#print axioms PCS.V2.DomainAuthority.authorityValid_builtin
#print axioms PCS.V2.DomainAuthority.pcs_extended_acceptance_sound
#print axioms PCS.V2.DomainAuthority.pcs_generic_domain_archive_acceptance_sound_with
#print axioms PCS.V2.DomainAuthority.pcs_generic_domain_archive_acceptance_sound_certified
-- Theorem 3: untrusted proposetÑPÐ€L@øó½œ…ªì