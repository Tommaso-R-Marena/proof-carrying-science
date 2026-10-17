import PCS.V2.ProofGatedSelfImprovement
import PCS.V2.ProofGatedSymbolic
import PCS.V2.ProofGatedArtifacts
import PCS.V2.ProofGatedPromotion
import PCS.V2.ProofGatedInference

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
