import PCS.V2.ProofGatedSelfImprovement
import PCS.V2.ProofGatedSymbolic
import PCS.V2.ProofGatedArtifacts
import PCS.V2.ProofGatedPromotion
import PCS.V2.ProofGatedInference
import PCS.V2.ProofGatedMultilayer
import PCS.V2.ProofGatedGeneric
import PCS.V2.ProofGatedWide
import PCS.V2.ProofGatedDeep
import PCS.V2.ProofGatedCodec
import PCS.V2.ProofGatedV1Analysis
import PCS.V2.ProofGatedNetArtifacts
import PCS.V2.ProofGatedLimits

/-!
# Replayed trusted-kernel dependency inventory (research only)

This file intentionally prints the axioms of the *specific* headline claims.
CI rejects if Lean reports `sorryAx`. This does not establish real-world
artifact fidelity or immutable deployment.
-/

#print axioms PCS.V2.ProofGatedSelfImprovement.accept_sound
#print axioms PCS.V2.ProofGatedSelfImprovement.accepted_preserves
#print axioms PCS.V2.ProofGatedSelfImprovement.accepted_expands
#print axioms PCS.V2.ProofGatedSelfImprovement.trace_length_bound
#print axioms PCS.V2.ProofGatedSelfImprovement.arbitrary_strategies_preserve
#print axioms PCS.V2.ProofGatedSelfImprovement.arbitrary_strategies_nonincrease
#print axioms PCS.V2.ProofGatedSelfImprovement.same_target_ood_regression
#print axioms PCS.V2.ProofGatedArtifacts.decode_canonical
#print axioms PCS.V2.ProofGatedArtifacts.decode_bounded
#print axioms PCS.V2.ProofGatedArtifacts.acceptWire_sound
#print axioms PCS.V2.ProofGatedSymbolic.add_zero_rewrite
#print axioms PCS.V2.ProofGatedSymbolic.multiply_one_rewrite
#print axioms PCS.V2.ProofGatedSymbolic.rewrites_compose

#print axioms PCS.V2.ProofGatedPromotion.commit_sound
#print axioms PCS.V2.ProofGatedPromotion.commit_requires_genuine_improvement
#print axioms PCS.V2.ProofGatedPromotion.stale_generation_cannot_commit
#print axioms PCS.V2.ProofGatedPromotion.substituted_active_cannot_commit
#print axioms PCS.V2.ProofGatedPromotion.gatedCommit_monotone_generation

#print axioms PCS.V2.ProofGatedInference.infer_sound
#print axioms PCS.V2.ProofGatedInference.infer_canonical
#print axioms PCS.V2.ProofGatedInference.committed_inference_preserves_correct_cases
#print axioms PCS.V2.ProofGatedInference.committed_inference_exact_artifact

#print axioms PCS.V2.ProofGatedMultilayer.accept_sound
#print axioms PCS.V2.ProofGatedMultilayer.accepted_preserves
#print axioms PCS.V2.ProofGatedMultilayer.accepted_expands
#print axioms PCS.V2.ProofGatedMultilayer.trace_length_bound
#print axioms PCS.V2.ProofGatedMultilayer.arbitrary_proposers_preserve
#print axioms PCS.V2.ProofGatedMultilayer.arbitrary_proposers_nonincrease
#print axioms PCS.V2.ProofGatedMultilayer.swapHidden_semantics
#print axioms PCS.V2.ProofGatedMultilayer.two_generations_certified
#print axioms PCS.V2.ProofGatedMultilayer.complete_terminal

/-! ## v4 additions (generic gate, width-n / deep networks, codec, refinement, limits) -/

-- Generic gate over an arbitrary exact model family
#print axioms PCS.V2.ProofGatedGeneric.accept_iff_admissible
#print axioms PCS.V2.ProofGatedGeneric.accept_trans
#print axioms PCS.V2.ProofGatedGeneric.accept_irrefl
#print axioms PCS.V2.ProofGatedGeneric.loss_eq_zero_iff
#print axioms PCS.V2.ProofGatedGeneric.perfect_valid_always_accepted
#print axioms PCS.V2.ProofGatedGeneric.trace_length_bound
#print axioms PCS.V2.ProofGatedGeneric.trace_valid
#print axioms PCS.V2.ProofGatedGeneric.trace_strict_gain
#print axioms PCS.V2.ProofGatedGeneric.no_long_trace
#print axioms PCS.V2.ProofGatedGeneric.runSched_preserves
#print axioms PCS.V2.ProofGatedGeneric.runSched_valid
#print axioms PCS.V2.ProofGatedGeneric.runSched_count_bound
#print axioms PCS.V2.ProofGatedGeneric.runSched_certified
#print axioms PCS.V2.ProofGatedGeneric.runSched_frozen_of_perfect

-- Parameterized-width networks
#print axioms PCS.V2.ProofGatedWide.predict_perm
#print axioms PCS.V2.ProofGatedWide.predict_insert_dead
#print axioms PCS.V2.ProofGatedWide.predict_prune_dead
#print axioms PCS.V2.ProofGatedWide.predict_merge
#print axioms PCS.V2.ProofGatedWide.predict_rescale
#print axioms PCS.V2.ProofGatedWide.valid_perm
#print axioms PCS.V2.ProofGatedWide.accept_congr_candidate
#print axioms PCS.V2.ProofGatedWide.accept_congr_incumbent
#print axioms PCS.V2.ProofGatedWide.accept_perm_invariant
#print axioms PCS.V2.ProofGatedWide.predict_ofTiny
#print axioms PCS.V2.ProofGatedWide.accept_ofTiny
#print axioms PCS.V2.ProofGatedWide.tiny_accept_eq
#print axioms PCS.V2.ProofGatedWide.neuron_accept_eq
#print axioms PCS.V2.ProofGatedWide.predict_ofNeuron
#print axioms PCS.V2.ProofGatedWide.wide_three_generations
#print axioms PCS.V2.ProofGatedWide.wide_losses
#print axioms PCS.V2.ProofGatedWide.gen3_exact
#print axioms PCS.V2.ProofGatedWide.regressive_blocked
#print axioms PCS.V2.ProofGatedWide.outOfRange_blocked
#print axioms PCS.V2.ProofGatedWide.overWidth_blocked
#print axioms PCS.V2.ProofGatedWide.permuted_gen3_accepted

-- Arbitrary-depth networks
#print axioms PCS.V2.ProofGatedDeep.predict_ofWide
#print axioms PCS.V2.ProofGatedDeep.predict_deepen
#print axioms PCS.V2.ProofGatedDeep.predict_deepen_ofWide
#print axioms PCS.V2.ProofGatedDeep.deep_two_generations
#print axioms PCS.V2.ProofGatedDeep.dFull_exact
#print axioms PCS.V2.ProofGatedDeep.dIllShaped_blocked
#print axioms PCS.V2.ProofGatedDeep.dTooDeep_blocked

-- Verified canonical codec (PGSI2)
#print axioms PCS.V2.ProofGatedCodec.parseNat_renderNat
#print axioms PCS.V2.ProofGatedCodec.parseInt_renderInt
#print axioms PCS.V2.ProofGatedCodec.parseInt_eq_some_iff
#print axioms PCS.V2.ProofGatedCodec.renderInt_injective
#print axioms PCS.V2.ProofGatedCodec.noncanonical_rejected
#print axioms PCS.V2.ProofGatedCodec.splitFields_joinFields
#print axioms PCS.V2.ProofGatedCodec.joinFields_splitFields
#print axioms PCS.V2.ProofGatedCodec.decodeInts_encodeInts
#print axioms PCS.V2.ProofGatedCodec.decodeInts_canonical
#print axioms PCS.V2.ProofGatedCodec.toString_ofNat_toList
#print axioms PCS.V2.ProofGatedCodec.toString_toList_of_append_spec

-- Original PGSI1 format: core-library analysis
#print axioms PCS.V2.ProofGatedV1Analysis.splitOn_pipe
#print axioms PCS.V2.ProofGatedV1Analysis.encode_splitOn
#print axioms PCS.V2.ProofGatedV1Analysis.parseComponentsLegacy_encodeLegacy
#print axioms PCS.V2.ProofGatedV1Analysis.decode_encode_of_bounded_of_core
#print axioms PCS.V2.ProofGatedV1Analysis.coreIntContract_of
#print axioms PCS.V2.ProofGatedV1Analysis.decode_encode_of_bounded_nonneg
#print axioms PCS.V2.ProofGatedV1Analysis.encode_injective_of_bounded_of_core
#print axioms PCS.V2.ProofGatedV1Analysis.encode_injective_nonneg
#print axioms PCS.V2.ProofGatedV1Analysis.decode_sound_unconditional
#print axioms PCS.V2.ProofGatedV1Analysis.encode_eq_encodeLegacy_of_nonneg
#print axioms PCS.V2.ProofGatedV1Analysis.encode_eq_encodeLegacy_of_append_spec
#print axioms PCS.V2.ProofGatedV1Analysis.decode_encodeLegacy_of_append_spec
-- Verified PGSI1 artifact path (unconditional Priority A)
#print axioms PCS.V2.ProofGatedArtifacts.parseComponents_encode
#print axioms PCS.V2.ProofGatedArtifacts.decode_encode_of_bounded
#print axioms PCS.V2.ProofGatedArtifacts.encode_injective
#print axioms PCS.V2.ProofGatedArtifacts.decode_eq_some_iff
#print axioms PCS.V2.ProofGatedArtifacts.decode_eq_none_of_invalid
#print axioms PCS.V2.ProofGatedArtifacts.encode_examples
#print axioms PCS.V2.ProofGatedArtifacts.decode_rejection_examples
#print axioms PCS.V2.ProofGatedArtifacts.decode_acceptance_examples
#print axioms PCS.V2.ProofGatedInference.infer_encode
#print axioms PCS.V2.ProofGatedInference.infer_eq_some_iff

-- Versioned network artifacts, promotion and inference
#print axioms PCS.V2.ProofGatedNetArtifacts.decode_encode
#print axioms PCS.V2.ProofGatedNetArtifacts.decode_iff
#print axioms PCS.V2.ProofGatedNetArtifacts.encode_injective
#print axioms PCS.V2.ProofGatedNetArtifacts.infer_encode
#print axioms PCS.V2.ProofGatedNetArtifacts.acceptWire_iff
#print axioms PCS.V2.ProofGatedNetArtifacts.acceptWire_encode
#print axioms PCS.V2.ProofGatedNetArtifacts.commit_refines
#print axioms PCS.V2.ProofGatedNetArtifacts.commit_complete
#print axioms PCS.V2.ProofGatedNetArtifacts.runCommits_invariant
#print axioms PCS.V2.ProofGatedNetArtifacts.three_commits
#print axioms PCS.V2.ProofGatedNetArtifacts.gen3_wire
#print axioms PCS.V2.ProofGatedNetArtifacts.boundary_fixtures

-- Limits
#print axioms PCS.V2.ProofGatedLimits.gated_run_stabilizes
#print axioms PCS.V2.ProofGatedLimits.blind_extension_accepted
#print axioms PCS.V2.ProofGatedLimits.multilayer_ood_regression
#print axioms PCS.V2.ProofGatedLimits.gate_cannot_separate
#print axioms PCS.V2.ProofGatedLimits.blind_extensions_of_gen3
#print axioms PCS.V2.ProofGatedLimits.local_trap
#print axioms PCS.V2.ProofGatedLimits.local_proposer_frozen
