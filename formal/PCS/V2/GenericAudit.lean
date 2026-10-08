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
-- Theorem 3: untrusted proposer
#print axioms PCS.V2.Proposer.loop_output_checked
#print axioms PCS.V2.Proposer.untrusted_proposer_cannot_forge_assurance
#print axioms PCS.V2.Proposer.no_strategy_forges
#print axioms PCS.V2.Proposer.stochastic_proposer_sound
#print axioms PCS.V2.Proposer.untrusted_proposer_archive_sound
-- Theorem 4: workflow refinement
#print axioms PCS.V2.WorkflowRefinement.pipeline_refines
#print axioms PCS.V2.WorkflowRefinement.pipeline_total
#print axioms PCS.V2.Witnesses.WorkflowWitness.evaluator_sound
-- witnesses
#print axioms PCS.V2.Witnesses.registry_valid
#print axioms PCS.V2.Witnesses.Biology.bioAdapter_sound
#print axioms PCS.V2.Witnesses.Biology.bio_archive_sound
#print axioms PCS.V2.Witnesses.AISafety.aiAdapter_sound
#print axioms PCS.V2.Witnesses.AISafety.ai_archive_sound
#print axioms PCS.V2.Witnesses.MLEval.mlAdapter_sound
#print axioms PCS.V2.Witnesses.MLEval.ml_archive_sound
#print axioms PCS.V2.Witnesses.Instances.bio_assurance
#print axioms PCS.V2.Witnesses.Instances.ai_assurance
#print axioms PCS.V2.Witnesses.Instances.bioGraph_accepted
#print axioms PCS.V2.Witnesses.Instances.aiGraph_accepted
#print axioms PCS.V2.Witnesses.Instances.mlGraph_accepted
-- counterexamples / falsification
#print axioms PCS.V2.GenericCounterexamples.cyclic_rejected
#print axioms PCS.V2.GenericCounterexamples.missing_leaf_rejected
#print axioms PCS.V2.GenericCounterexamples.duplicate_rejected
#print axioms PCS.V2.GenericCounterexamples.unsupported_node_rejected
#print axioms PCS.V2.GenericCounterexamples.wrong_root_rejected
#print axioms PCS.V2.GenericCounterexamples.swapped_artifact_rejected
#print axioms PCS.V2.GenericCounterexamples.failed_evidence_rejected
#print axioms PCS.V2.GenericCounterexamples.unrequired_evidence_rejected
#print axioms PCS.V2.GenericCounterexamples.weaker_leaf_rejected
#print axioms PCS.V2.GenericCounterexamples.adversary_gets_nothing
#print axioms PCS.V2.GenericCounterexamples.rule_soundness_necessary
#print axioms PCS.V2.GenericCounterexamples.leaf_soundness_necessary
#print axioms PCS.V2.GenericCounterexamples.trusting_reports_unsound
#print axioms PCS.V2.GenericCounterexamples.lossy_compile_unsound
#print axioms PCS.V2.GenericCounterexamples.duplicate_tag_shadowing
