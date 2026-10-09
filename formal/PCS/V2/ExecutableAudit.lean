import PCS.V2.ExecutableAuthority
import PCS.V2.ExternalWorld
import PCS.V2.DistributedContributors
import PCS.V2.ClaimGraphMemo
import PCS.V2.Witnesses.AISafetyCampaign
import PCS.V2.Witnesses.AISafetyDeployment

/-!
Audit surface for the executable AI-safety assurance layer: a successful build prints the
axiom dependencies of every major result added for the executable authority, the golden
AI-safety archive, distributed contributors, the external-world bridge and the memoized
graph checker.
-/

-- Priority 1: executable certified authority
#print axioms PCS.V2.DomainAuthority.executableAuthority_eq
#print axioms PCS.V2.DomainAuthority.executableAuthority_refines_certifiedAuthority
#print axioms PCS.V2.DomainAuthority.executableAuthorityEntries_refines_certifiedAuthority
#print axioms PCS.V2.DomainAuthority.executableAuthorityWith_dup
#print axioms PCS.V2.DomainAuthority.executableAuthorityWith_builtin
#print axioms PCS.V2.DomainAuthority.executableAuthorityWith_nil
#print axioms PCS.V2.DomainAuthority.buildRegistry_dup_none
#print axioms PCS.V2.DomainAuthority.buildRegistry_builtin_none
#print axioms PCS.V2.DomainAuthority.executor_builtin_unchanged
#print axioms PCS.V2.DomainAuthority.executor_unhandled_unchanged
#print axioms PCS.V2.DomainAuthority.executor_unknown_fail_closed
#print axioms PCS.V2.DomainAuthority.executableAuthority_sound
#print axioms PCS.V2.DomainAuthority.executableAuthority_domain_sound
-- Priority 2/3: golden AI-safety archive and adversarial campaign
#print axioms PCS.V2.Witnesses.AISafetyCampaign.golden_claim_decodes
#print axioms PCS.V2.Witnesses.AISafetyCampaign.golden_trace_safe
#print axioms PCS.V2.Witnesses.AISafetyCampaign.golden_checker_passes
#print axioms PCS.V2.Witnesses.AISafetyCampaign.golden_graph_accepted
#print axioms PCS.V2.Witnesses.AISafetyCampaign.aiSafetyGoldenArchive_domain_sound
#print axioms PCS.V2.Witnesses.AISafetyCampaign.aiSafetyGoldenArchive_deployed_safe
#print axioms PCS.V2.Witnesses.AISafetyCampaign.replay_mismatch_rejects
#print axioms PCS.V2.Witnesses.AISafetyCampaign.unknown_tag_no_leaf
#print axioms PCS.V2.Witnesses.AISafetyCampaign.duplicate_registry_fails_closed
#print axioms PCS.V2.Witnesses.AISafetyCampaign.forbidden_trace_checker_fails
#print axioms PCS.V2.Witnesses.AISafetyCampaign.over_budget_checker_fails
#print axioms PCS.V2.Witnesses.AISafetyCampaign.graph_attacks_rejected
#print axioms PCS.V2.Witnesses.AISafetyCampaign.wrong_decoder_rejected
#print axioms PCS.V2.Witnesses.AISafetyCampaign.golden_distributed_protocol
-- Priority 4: distributed contributors
#print axioms PCS.V2.DistributedContributors.run_invariant
#print axioms PCS.V2.DistributedContributors.unverified_leaf_rejected
#print axioms PCS.V2.DistributedContributors.no_overwrite
#print axioms PCS.V2.DistributedContributors.committed_persistent
#print axioms PCS.V2.DistributedContributors.committed_provenance
#print axioms PCS.V2.DistributedContributors.committed_ids_nodup
#print axioms PCS.V2.DistributedContributors.committed_children_earlier
#print axioms PCS.V2.DistributedContributors.run_accepts_sound
#print axioms PCS.V2.DistributedContributors.accepted_root_claim_fixed
#print axioms PCS.V2.DistributedContributors.accepted_contributions_cannot_forge_assurance
#print axioms PCS.V2.DistributedContributors.accepted_conclusion_order_independent
#print axioms PCS.V2.DistributedContributors.coalition_is_submission_list
#print axioms PCS.V2.DistributedContributors.execution_provenance
#print axioms PCS.V2.DistributedContributors.squatting_blocks_liveness
#print axioms PCS.V2.DistributedContributors.pcs_distributed_domain_sound
#print axioms PCS.V2.DistributedContributors.protocol_graph_accepted
-- Priority 5: external-world bridge
#print axioms PCS.V2.DomainAdapter.external_world_transfer_sound
#print axioms PCS.V2.DomainAdapter.false_external_world_not_corresponding
#print axioms PCS.V2.DomainAuthority.archive_external_world_transfer_sound
#print axioms PCS.V2.Witnesses.AISafety.committed_safe_deployed_unsafe
-- Priority 6: memoized obligation-graph checker
#print axioms PCS.V2.ClaimGraph.checkGraph_iff
#print axioms PCS.V2.ClaimGraph.checkGraphMemo_eq
#print axioms PCS.V2.ClaimGraph.root_assurance_sound_memo
#print axioms PCS.V2.ClaimGraph.memo_rejects_id_collision
#print axioms PCS.V2.ClaimGraph.memo_rejects_cycle
#print axioms PCS.V2.ClaimGraph.memo_rejects_missing
