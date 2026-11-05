import PCS.V2.ProofGatedRobust
import PCS.V2.ProofGatedStrongGate
import PCS.V2.ProofGatedDeepCert
import PCS.V2.ProofGatedStrongArtifacts

/-! Axiom audit for the interval-robustness checker (`ProofGatedRobust`), the unified
strong gate (`ProofGatedStrongGate`), the deep certificate checker (`ProofGatedDeepCert`)
and the strong-gate artifacts (`ProofGatedStrongArtifacts`). Every theorem declared in
these four modules is listed. Expected: only `propext`, `Classical.choice`,
`Quot.sound`; no `sorryAx`, no `Lean.ofReduceBool`, no `Lean.trustCompiler`. -/

-- PCS.V2.ProofGatedRobust
#print axioms PCS.V2.ProofGatedRobust.abs_le_endpoints
#print axioms PCS.V2.ProofGatedRobust.inIv_iff
#print axioms PCS.V2.ProofGatedRobust.probes_in_interval
#print axioms PCS.V2.ProofGatedRobust.probes_length
#print axioms PCS.V2.ProofGatedRobust.probe_dominates
#print axioms PCS.V2.ProofGatedRobust.le_maxOver
#print axioms PCS.V2.ProofGatedRobust.maxOver_attained
#print axioms PCS.V2.ProofGatedRobust.maxOver_le_iff
#print axioms PCS.V2.ProofGatedRobust.errProbes_length
#print axioms PCS.V2.ProofGatedRobust.errAt_secondDiff
#print axioms PCS.V2.ProofGatedRobust.errAt_le_probe
#print axioms PCS.V2.ProofGatedRobust.errAt_le_maxAbsErr
#print axioms PCS.V2.ProofGatedRobust.maxAbsErr_attained
#print axioms PCS.V2.ProofGatedRobust.maxAbsErr_isMax
#print axioms PCS.V2.ProofGatedRobust.maxAbsErr_le_iff
#print axioms PCS.V2.ProofGatedRobust.checkErrBound_iff
#print axioms PCS.V2.ProofGatedRobust.findErrViolation_sound
#print axioms PCS.V2.ProofGatedRobust.findErrViolation_complete
#print axioms PCS.V2.ProofGatedRobust.findErrViolation_none_iff
#print axioms PCS.V2.ProofGatedRobust.robustB_iff
#print axioms PCS.V2.ProofGatedRobust.robustB_iff_pointwise
#print axioms PCS.V2.ProofGatedRobust.findRobustViolation_sound
#print axioms PCS.V2.ProofGatedRobust.findRobustViolation_none_iff
#print axioms PCS.V2.ProofGatedRobust.maxAbsErr_congr
#print axioms PCS.V2.ProofGatedRobust.robustB_trans

-- PCS.V2.ProofGatedStrongGate
#print axioms PCS.V2.ProofGatedStrongGate.acceptStrong_iff
#print axioms PCS.V2.ProofGatedStrongGate.acceptStrong_sound
#print axioms PCS.V2.ProofGatedStrongGate.acceptStrong_complete
#print axioms PCS.V2.ProofGatedStrongGate.acceptStrong_acceptNF
#print axioms PCS.V2.ProofGatedStrongGate.acceptStrong_maxAbsErr
#print axioms PCS.V2.ProofGatedStrongGate.acceptStrong_irrefl
#print axioms PCS.V2.ProofGatedStrongGate.acceptStrong_congr_candidate
#print axioms PCS.V2.ProofGatedStrongGate.acceptStrong_congr_incumbent
#print axioms PCS.V2.ProofGatedStrongGate.acceptStrong_perm_invariant
#print axioms PCS.V2.ProofGatedStrongGate.strongTrace_noForget
#print axioms PCS.V2.ProofGatedStrongGate.strongTrace_robust
#print axioms PCS.V2.ProofGatedStrongGate.strongTrace_maxAbsErr
#print axioms PCS.V2.ProofGatedStrongGate.strongTrace_loss
#print axioms PCS.V2.ProofGatedStrongGate.strongTrace_length_le_loss
#print axioms PCS.V2.ProofGatedStrongGate.strongTrace_valid
#print axioms PCS.V2.ProofGatedStrongGate.strongTrace_corpus
#print axioms PCS.V2.ProofGatedStrongGate.no_long_strongTrace
#print axioms PCS.V2.ProofGatedStrongGate.strongTrace_append
#print axioms PCS.V2.ProofGatedStrongGate.runStrong_trace
#print axioms PCS.V2.ProofGatedStrongGate.countStrong_le_loss
#print axioms PCS.V2.ProofGatedStrongGate.runStrong_guarantees
#print axioms PCS.V2.ProofGatedStrongGate.specNarrow_corpusSpec
#print axioms PCS.V2.ProofGatedStrongGate.growth_chain_errors
#print axioms PCS.V2.ProofGatedStrongGate.growth_chain_narrow
#print axioms PCS.V2.ProofGatedStrongGate.growth_step1_rejected_mid
#print axioms PCS.V2.ProofGatedStrongGate.robust_chain_wide
#print axioms PCS.V2.ProofGatedStrongGate.robust_chain_wide_values
#print axioms PCS.V2.ProofGatedStrongGate.robust_chain_wide_guarantee
#print axioms PCS.V2.ProofGatedStrongGate.blindForget_only_B
#print axioms PCS.V2.ProofGatedStrongGate.ood_only_C
#print axioms PCS.V2.ProofGatedStrongGate.noProgress_only_A
#print axioms PCS.V2.ProofGatedStrongGate.gen3_strong_terminal

-- PCS.V2.ProofGatedDeepCert
#print axioms PCS.V2.ProofGatedDeepCert.dot_affv
#print axioms PCS.V2.ProofGatedDeepCert.affv_zero
#print axioms PCS.V2.ProofGatedDeepCert.between_of_affine
#print axioms PCS.V2.ProofGatedDeepCert.neuronStep_spec
#print axioms PCS.V2.ProofGatedDeepCert.neuronStep_one
#print axioms PCS.V2.ProofGatedDeepCert.layerStep_spec
#print axioms PCS.V2.ProofGatedDeepCert.layerStep_one
#print axioms PCS.V2.ProofGatedDeepCert.hiddenStep_spec
#print axioms PCS.V2.ProofGatedDeepCert.hiddenStep_one
#print axioms PCS.V2.ProofGatedDeepCert.cellCoeffs_spec
#print axioms PCS.V2.ProofGatedDeepCert.cellOK_affine
#print axioms PCS.V2.ProofGatedDeepCert.cellOK_succ
#print axioms PCS.V2.ProofGatedDeepCert.affine_abs_le
#print axioms PCS.V2.ProofGatedDeepCert.affine_secondDiff
#print axioms PCS.V2.ProofGatedDeepCert.chainOK_cons
#print axioms PCS.V2.ProofGatedDeepCert.chain_in_range
#print axioms PCS.V2.ProofGatedDeepCert.cell_dominates
#print axioms PCS.V2.ProofGatedDeepCert.chain_dominates
#print axioms PCS.V2.ProofGatedDeepCert.certMaxErr_isMax
#print axioms PCS.V2.ProofGatedDeepCert.certErrBound_iff
#print axioms PCS.V2.ProofGatedDeepCert.enumCert_ok
#print axioms PCS.V2.ProofGatedDeepCert.cert_exists
#print axioms PCS.V2.ProofGatedDeepCert.cert_must_contain
#print axioms PCS.V2.ProofGatedDeepCert.deepRobustCert_sound
#print axioms PCS.V2.ProofGatedDeepCert.deepRobustCert_complete
#print axioms PCS.V2.ProofGatedDeepCert.acceptDeepCert_sound
#print axioms PCS.V2.ProofGatedDeepCert.dFull_cert
#print axioms PCS.V2.ProofGatedDeepCert.dFull_bad_cert
#print axioms PCS.V2.ProofGatedDeepCert.sawtooth_all_kinks
#print axioms PCS.V2.ProofGatedDeepCert.saw6_cert_contains_all

-- PCS.V2.ProofGatedStrongArtifacts
#print axioms PCS.V2.ProofGatedStrongArtifacts.strongAdmissible_valid
#print axioms PCS.V2.ProofGatedStrongArtifacts.acceptStrongWire_iff
#print axioms PCS.V2.ProofGatedStrongArtifacts.acceptStrongWire_encode
#print axioms PCS.V2.ProofGatedStrongArtifacts.acceptStrongWire_noncanonical
#print axioms PCS.V2.ProofGatedStrongArtifacts.commitS_refines
#print axioms PCS.V2.ProofGatedStrongArtifacts.commitS_complete
#print axioms PCS.V2.ProofGatedStrongArtifacts.staleS_rejected
#print axioms PCS.V2.ProofGatedStrongArtifacts.substitutedS_rejected
#print axioms PCS.V2.ProofGatedStrongArtifacts.runCommitsS_invariant
#print axioms PCS.V2.ProofGatedStrongArtifacts.served_error_le
#print axioms PCS.V2.ProofGatedStrongArtifacts.served_noForget
#print axioms PCS.V2.ProofGatedStrongArtifacts.chain_wires
#print axioms PCS.V2.ProofGatedStrongArtifacts.three_strong_commits
#print axioms PCS.V2.ProofGatedStrongArtifacts.ood_wire_rejected
