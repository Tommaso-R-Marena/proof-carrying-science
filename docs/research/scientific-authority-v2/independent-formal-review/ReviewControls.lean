import PCSScientificAuthorityV2

/-!
Independent model controls. `oracle` is deliberately a symbolic signature
callback, NOT cryptography and NOT a claimed real authorization. Science always
uses the actual unchanged receiver. Controls isolate hypotheses that cannot be
omitted from the author's safety statements.
-/
namespace PCSAuthorityV2IndependentReview
open PCSAuthorizationHistoryV1 PCSScientificHistoryV1 PCSScientificReceiver
open PCSScientificAuthorityV2

def oracle : VerifySignature := fun _ _ _ => true

def first : Envelope :=
  { sampleEnvelope with payload := { sampleEnvelope.payload with eventId := [200] } }
def second : Envelope :=
  { sampleEnvelope with payload := { sampleEnvelope.payload with eventId := [201] } }

abbrev s0 := PCSAuthorizationHistoryV1.initial sampleRoot

theorem oracle_initializes :
    initializeWitness sampleRoot oracle = some sampleInitialWitness := by
  have hp : sampleRoot.policy = policyBytes := rfl
  simp [initializeWitness, audit, hp, sample_genesis_receive, auditFrom, sampleInitialWitness]

theorem first_checked :
    scientificTransition sampleRoot oracle s0 first =
      (commit s0 first, some (resultOfContract codecSample)) := by
  have history : (transition sampleRoot oracle s0 first).2 = true := by decide +kernel
  have received : receive first.payload.candidate = some (resultOfContract codecSample) :=
    sample_science_accepts
  have hp : sampleRoot.policy = policyBytes := rfl
  have hc : first.payload.certificate = [] := rfl
  simp [scientificTransition, hp, hc, received, accepted_state sampleRoot oracle s0 first history]

theorem second_checked :
    scientificTransition sampleRoot oracle s0 second =
      (commit s0 second, some (resultOfContract codecSample)) := by
  have history : (transition sampleRoot oracle s0 second).2 = true := by decide +kernel
  have received : receive second.payload.candidate = some (resultOfContract codecSample) :=
    sample_science_accepts
  have hp : sampleRoot.policy = policyBytes := rfl
  have hc : second.payload.certificate = [] := rfl
  simp [scientificTransition, hp, hc, received, accepted_state sampleRoot oracle s0 second history]

def pendingFirst : Witness :=
  ⟨s0, some ⟨s0, first, resultOfContract codecSample⟩⟩
def pendingSecond : Witness :=
  ⟨s0, some ⟨s0, second, resultOfContract codecSample⟩⟩

theorem honest_prepare_first : prepare sampleRoot oracle sampleInitialWitness first =
    (pendingFirst, true) := by simp [prepare, sampleInitialWitness, first_checked, pendingFirst]
theorem honest_prepare_second : prepare sampleRoot oracle sampleInitialWitness second =
    (pendingSecond, true) := by simp [prepare, sampleInitialWitness, second_checked, pendingSecond]

/-- Cloning a checked witness state permits both incompatible branch commits.
This is excluded by the author's single durable state-continuity hypothesis. -/
theorem cloned_witnesses_can_diverge :
    (finalize pendingFirst first).2 = true ∧
    (finalize pendingSecond second).2 = true ∧
    (finalize pendingFirst first).1.committed ≠
      (finalize pendingSecond second).1.committed := by
  refine ⟨by simp [finalize, pendingFirst], by simp [finalize, pendingSecond], ?_⟩
  intro eq
  have tips := congrArg (fun w => w.tip) eq
  simp [finalize, pendingFirst, pendingSecond, commit, first, second] at tips

/-- With one retained state, the same incompatible second successor rejects. -/
theorem retained_witness_rejects_conflict :
    finalize (finalize pendingFirst first).1 second =
      ((finalize pendingFirst first).1, false) := by
  have initialValid := initialize_sound sampleRoot oracle sampleInitialWitness oracle_initializes
  have preparedValid := prepare_preserves_invariant sampleRoot oracle sampleInitialWitness first initialValid
  rw [honest_prepare_first] at preparedValid
  have accepted : (finalize pendingFirst first).2 = true := by simp [finalize, pendingFirst]
  have sameGeneration : second.payload.expectedGeneration = first.payload.expectedGeneration := rfl
  simpa [witnessRun] using no_conflicting_finalization_later sampleRoot oracle pendingFirst first second
    preparedValid accepted sameGeneration []

def fakeState : State := ⟨0, [], [], []⟩

/-- Serving's structural test alone does not establish science. -/
theorem uninitialized_equal_state_serves :
    serve ⟨⟨fakeState, none⟩, fakeState⟩ = some fakeState := by simp [serve]
theorem uninitialized_served_artifact_is_invalid : receive fakeState.incumbent = none := by
  apply PCSScientificReceiver.malformed_rejects
  decide +kernel

def badEnvelope : Envelope :=
  { first with payload := { first.payload with candidate := [] } }
def forgedPending : Witness :=
  ⟨s0, some ⟨s0, badEnvelope, resultOfContract codecSample⟩⟩

/-- finalize's science claim needs PendingSound/checked initialization. -/
theorem forged_pending_can_finalize : (finalize forgedPending badEnvelope).2 = true := by
  simp [finalize, forgedPending]
theorem forged_pending_result_invalid :
    receive (finalize forgedPending badEnvelope).1.committed.incumbent = none := by
  have malformed : receive ([] : Bytes) = none := by
    apply PCSScientificReceiver.malformed_rejects
    decide +kernel
  simpa [finalize, forgedPending, commit, badEnvelope] using malformed

/-- Unlike bare finalize, recovery actually rechecks science, even for a forged
witness that claims the invalid candidate has already been finalized. -/
theorem recovery_refuses_invalid_archive (w : Witness) :
    recover sampleRoot oracle w [badEnvelope] = none := by
  apply recovery_invalid_archive_rejects
  have hp : sampleRoot.policy = policyBytes := rfl
  have malformed : receive badEnvelope.payload.candidate = none := by
    apply PCSScientificReceiver.malformed_rejects
    decide +kernel
  have rejected := false_science_rejects sampleRoot oracle s0 badEnvelope malformed
  simp [audit, hp, sample_genesis_receive, auditFrom, rejected]

/-- A valid first entry cannot hide a rejected later entry. -/
theorem successful_prefix_does_not_hide_bad_suffix :
    audit sampleRoot oracle [first, badEnvelope] = none := by
  have hp : sampleRoot.policy = policyBytes := rfl
  have malformed : receive badEnvelope.payload.candidate = none := by
    apply PCSScientificReceiver.malformed_rejects
    decide +kernel
  have rejected := false_science_rejects sampleRoot oracle (commit s0 first) badEnvelope malformed
  simp [audit, hp, sample_genesis_receive, auditFrom, first_checked, rejected]

/-- A live pending record halts even an otherwise matching old state. Safety is
conservative; this is not a liveness or availability theorem. -/
theorem pending_blocks_old_checked_state : serve ⟨pendingFirst, s0⟩ = none := by
  simp [serve, pendingFirst]

end PCSAuthorityV2IndependentReview

open Lean Elab Command
run_cmd do
  for (name, info) in (← getEnv).constants.toList do
    match info with
    | .thmInfo _ =>
      if "PCSAuthorityV2IndependentReview.".isPrefixOf name.toString then
        elabCommand (← `(#check $(mkIdent name)))
        elabCommand (← `(#print axioms $(mkIdent name)))
    | _ => pure ()
