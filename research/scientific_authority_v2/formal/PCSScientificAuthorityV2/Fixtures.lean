import PCSScientificAuthorityV2.Recovery

/-!
Kernel nonvacuity and countermodels. The finite symbolic signature allowlist is
not a real cryptographic implementation or an execution attestation. The actual
scientific receiver is reused; runtime Ed25519/Lean tests are separate evidence.
-/
namespace PCSScientificAuthorityV2

open PCSAuthorizationHistoryV1
open PCSScientificHistoryV1
open PCSScientificReceiver

theorem sample_genesis_receive :
    receive sampleRoot.genesisIncumbent = some (resultOfContract codecSample) :=
  sample_science_accepts

theorem sample_empty_audit :
    audit sampleRoot sampleVerify [] = some (PCSAuthorizationHistoryV1.initial sampleRoot) := by
  have hp : sampleRoot.policy = policyBytes := rfl
  simp only [audit, hp, ↓reduceIte, sample_genesis_receive, auditFrom]

theorem sample_complete_audit :
    audit sampleRoot sampleVerify [sampleEnvelope] =
      some (commit (PCSAuthorizationHistoryV1.initial sampleRoot) sampleEnvelope) := by
  have hs : (scientificTransition sampleRoot sampleVerify (PCSAuthorizationHistoryV1.initial sampleRoot)
      sampleEnvelope).2 = some (resultOfContract codecSample) := by
    rw [sample_commits_checked_science]
  exact audit_append_accepted sampleRoot sampleVerify [] (PCSAuthorizationHistoryV1.initial sampleRoot)
    sampleEnvelope _ sample_empty_audit hs

theorem sample_duplicate_history_rejects :
    audit sampleRoot sampleVerify [sampleEnvelope, sampleEnvelope] = none := by
  have hs : (scientificTransition sampleRoot sampleVerify (PCSAuthorizationHistoryV1.initial sampleRoot)
      sampleEnvelope).2 = some (resultOfContract codecSample) := by
    rw [sample_commits_checked_science]
  have stale := accepted_never_replayed sampleRoot sampleVerify (PCSAuthorizationHistoryV1.initial sampleRoot)
    sampleEnvelope _ hs []
  simp only [PCSScientificHistoryV1.run] at stale
  rw [sample_commits_checked_science] at stale
  have hp : sampleRoot.policy = policyBytes := rfl
  simp [audit, hp, sample_genesis_receive, auditFrom,
    sample_commits_checked_science, stale]

theorem sample_valid_current_invalid_old_rejects :
    audit sampleRoot sampleVerify
      [{ sampleEnvelope with payload := { sampleEnvelope.payload with candidate := [] } },
       sampleEnvelope] = none := by
  have hs := sample_false_science_unchanged
  have hp : sampleRoot.policy = policyBytes := rfl
  simp [audit, hp, sample_genesis_receive, auditFrom, hs]

def sampleInitialWitness : Witness := ⟨PCSAuthorizationHistoryV1.initial sampleRoot, none⟩
def samplePrepared : Prepared :=
  ⟨PCSAuthorizationHistoryV1.initial sampleRoot, sampleEnvelope, resultOfContract codecSample⟩
def samplePendingWitness : Witness := ⟨PCSAuthorizationHistoryV1.initial sampleRoot, some samplePrepared⟩
def sampleFinalWitness : Witness := ⟨commit (PCSAuthorizationHistoryV1.initial sampleRoot) sampleEnvelope, none⟩

theorem sample_initialize :
    initializeWitness sampleRoot sampleVerify = some sampleInitialWitness := by
  simp [initializeWitness, sample_empty_audit, sampleInitialWitness]

theorem sample_prepare :
    prepare sampleRoot sampleVerify sampleInitialWitness sampleEnvelope =
      (samplePendingWitness, true) := by
  simp [prepare, sampleInitialWitness, sample_commits_checked_science,
    samplePendingWitness, samplePrepared]

theorem sample_pending_cannot_serve :
    serve ⟨samplePendingWitness, PCSAuthorizationHistoryV1.initial sampleRoot⟩ = none := by
  apply pending_not_serving _ samplePrepared
  rfl

theorem sample_local_commit :
    localCommit ⟨samplePendingWitness, PCSAuthorizationHistoryV1.initial sampleRoot⟩ sampleEnvelope =
      (⟨samplePendingWitness, commit (PCSAuthorizationHistoryV1.initial sampleRoot) sampleEnvelope⟩, true) := by
  simp [localCommit, samplePendingWitness, samplePrepared]

theorem sample_local_commit_cannot_serve :
    serve ⟨samplePendingWitness, commit (PCSAuthorizationHistoryV1.initial sampleRoot) sampleEnvelope⟩ = none := by
  apply pending_not_serving _ samplePrepared
  rfl

theorem sample_finalize : finalize samplePendingWitness sampleEnvelope =
    (sampleFinalWitness, true) := by
  simp [finalize, samplePendingWitness, samplePrepared, sampleFinalWitness]

theorem sample_final_can_serve :
    serve ⟨sampleFinalWitness, commit (PCSAuthorizationHistoryV1.initial sampleRoot) sampleEnvelope⟩ =
      some (commit (PCSAuthorizationHistoryV1.initial sampleRoot) sampleEnvelope) := by
  simp [serve, sampleFinalWitness]

theorem sample_rollback_local_cannot_serve :
    serve ⟨sampleFinalWitness, PCSAuthorizationHistoryV1.initial sampleRoot⟩ = none := by
  apply mismatched_local_checkpoint_not_serving
  intro equal
  have hg := congrArg State.generation equal
  simp [sampleFinalWitness, PCSAuthorizationHistoryV1.initial, commit] at hg

theorem sample_recovery_exact_archive :
    recover sampleRoot sampleVerify sampleFinalWitness [sampleEnvelope] =
      some ⟨sampleFinalWitness, commit (PCSAuthorizationHistoryV1.initial sampleRoot) sampleEnvelope⟩ := by
  simp [recover, sample_complete_audit, sampleFinalWitness]

theorem sample_recovery_missing_event_rejects :
    recover sampleRoot sampleVerify sampleFinalWitness [] = none := by
  apply recovery_wrong_checkpoint_rejects _ _ _ _ _ sample_empty_audit
  intro equal
  have hg := congrArg State.generation equal
  simp [sampleFinalWitness, PCSAuthorizationHistoryV1.initial, commit] at hg

theorem sample_invalid_genesis_rejects :
    audit { sampleRoot with genesisIncumbent := [] } sampleVerify [] = none := by
  apply invalid_genesis_rejects
  apply PCSScientificReceiver.malformed_rejects
  decide +kernel

/-- A self-consistency checker without an independently retained root accepts
two distinct authority/checker bootstraps for the same valid genesis. This is a
restricted substitution countermodel, not a cryptographic break. -/
def replacedRoot : Root :=
  { sampleRoot with authority := [91], witness := [92], checker := [93], genesisId := [94] }

theorem simultaneous_root_replacement_countermodel :
    replacedRoot ≠ sampleRoot ∧
    audit sampleRoot sampleVerify [] = some (PCSAuthorizationHistoryV1.initial sampleRoot) ∧
    audit replacedRoot sampleVerify [] = some (PCSAuthorizationHistoryV1.initial replacedRoot) := by
  refine ⟨?_, sample_empty_audit, ?_⟩
  · intro equal
    have different : replacedRoot.authority ≠ sampleRoot.authority := by decide +kernel
    exact different (congrArg Root.authority equal)
  · have hg : receive replacedRoot.genesisIncumbent = some (resultOfContract codecSample) :=
      sample_genesis_receive
    have hp : replacedRoot.policy = policyBytes := rfl
    simp only [audit, hp, ↓reduceIte, hg, auditFrom]

/-- Unsupported empirical adequacy can be false while the actual scientific
auditor succeeds. Mathematical acceptance carries no extra empirical predicate. -/
theorem mathematical_acceptance_not_empirical :
    ∃ (EmpiricallyAdequate : Bytes → Prop) (s : State),
      audit sampleRoot sampleVerify [sampleEnvelope] = some s ∧
      ¬ EmpiricallyAdequate s.incumbent := by
  exact ⟨fun _ => False, _, sample_complete_audit, fun h => h⟩

end PCSScientificAuthorityV2
