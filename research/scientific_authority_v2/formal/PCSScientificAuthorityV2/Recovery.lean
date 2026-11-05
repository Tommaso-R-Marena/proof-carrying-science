import PCSScientificAuthorityV2.Witness

namespace PCSScientificAuthorityV2

open PCSAuthorizationHistoryV1
open PCSScientificHistoryV1
open PCSScientificReceiver (Result ScopedScientificClaimHolds)

structure Authority where
  witness : Witness
  localState : State
  deriving DecidableEq, Repr

/-- Conservative serving rule: preparing a new event temporarily halts even
the old state. No positive from a local-only commit becomes witness-finalized. -/
def serve (a : Authority) : Option State :=
  if a.witness.pending = none ∧ a.localState = a.witness.committed then some a.localState else none

def localCommit (a : Authority) (e : Envelope) : Authority × Bool :=
  match a.witness.pending with
  | none => (a, false)
  | some p =>
    if p.before = a.witness.committed ∧ p.before = a.localState ∧ p.envelope = e then
      (⟨a.witness, commit a.localState e⟩, true)
    else (a, false)

def finalizeAuthority (a : Authority) (e : Envelope) : Authority :=
  ⟨(finalize a.witness e).1, a.localState⟩

theorem serve_checks (a : Authority) (s : State) (success : serve a = some s) :
    a.witness.pending = none ∧ a.localState = a.witness.committed ∧ s = a.witness.committed := by
  unfold serve at success
  split at success
  · rename_i eligible
    have hs : a.localState = s := Option.some.inj success
    exact ⟨eligible.1, eligible.2, hs.symm.trans eligible.2⟩
  · simp at success

theorem serve_requires_finalized_checkpoint (a : Authority) (s : State)
    (success : serve a = some s) : s = a.witness.committed :=
  (serve_checks a s success).2.2

theorem serving_artifact_scientific (root : Root) (verify : VerifySignature)
    (a : Authority) (s : State) (valid : WitnessInvariant root verify a.witness)
    (success : serve a = some s) :
    ∃ es, audit root verify es = some s ∧
      ∃ r, ScopedScientificClaimHolds s.incumbent r := by
  have bound := serve_requires_finalized_checkpoint a s success
  obtain ⟨es, checked⟩ := valid.checkedArchive
  rw [← bound] at checked
  exact ⟨es, checked, audited_incumbent_scientific root verify es s checked⟩

theorem pending_not_serving (a : Authority) (p : Prepared)
    (pending : a.witness.pending = some p) : serve a = none := by simp [serve, pending]

theorem localCommit_witness_unchanged (a : Authority) (e : Envelope) :
    (localCommit a e).1.witness = a.witness := by
  unfold localCommit
  split
  · rfl
  · split <;> rfl

theorem localCommit_checks (a : Authority) (e : Envelope)
    (accepted : (localCommit a e).2 = true) :
    ∃ p, a.witness.pending = some p ∧ p.before = a.witness.committed ∧
      p.before = a.localState ∧ p.envelope = e := by
  unfold localCommit at accepted
  split at accepted
  · simp at accepted
  · rename_i p hp
    split at accepted
    · rename_i checks
      exact ⟨p, hp, checks⟩
    · simp at accepted

theorem localCommit_state (a : Authority) (e : Envelope)
    (accepted : (localCommit a e).2 = true) :
    localCommit a e = (⟨a.witness, commit a.localState e⟩, true) := by
  obtain ⟨p, hp, hb, hl, he⟩ := localCommit_checks a e accepted
  have align : a.witness.committed = a.localState := hb.symm.trans hl
  simp [localCommit, hp, hb, align, he]

/-- A real local COMMIT alone cannot create a serving-eligible state. -/
theorem local_commit_without_finalization_not_serving (a : Authority) (e : Envelope)
    (accepted : (localCommit a e).2 = true) : serve (localCommit a e).1 = none := by
  obtain ⟨p, hp, _⟩ := localCommit_checks a e accepted
  apply pending_not_serving _ p
  rw [localCommit_witness_unchanged]
  exact hp

theorem witness_finalize_does_not_assert_local_commit (a : Authority) (e : Envelope) :
    (finalizeAuthority a e).localState = a.localState := rfl

/-- Distinct durable systems may disagree after a crash. Final witness state
does not silently overwrite or authorize the mismatching local state. -/
theorem mismatched_local_checkpoint_not_serving (a : Authority)
    (different : a.localState ≠ a.witness.committed) : serve a = none := by
  simp [serve, different]

/-- Recovery only installs an actual complete audit exactly matching the pinned
durable witness's finalized state. Pending resolution belongs to the protocol;
recovery cannot finalize it or invent a signed envelope. -/
def recover (root : Root) (verify : VerifySignature) (w : Witness)
    (archive : List Envelope) : Option Authority := do
  let s ← audit root verify archive
  if s = w.committed ∧ w.pending = none then some ⟨w, s⟩ else none

structure RecoveryFacts (root : Root) (verify : VerifySignature) (w : Witness)
    (archive : List Envelope) (a : Authority) : Prop where
  exactWitness : a.witness = w
  noPending : w.pending = none
  checked : audit root verify archive = some a.localState
  checkpoint : a.localState = w.committed
  serve : serve a = some a.localState
  scientific : CompleteAuditFacts root verify archive a.localState

theorem recovery_sound (root : Root) (verify : VerifySignature) (w : Witness)
    (archive : List Envelope) (a : Authority)
    (success : recover root verify w archive = some a) :
    RecoveryFacts root verify w archive a := by
  unfold recover at success
  cases ha : audit root verify archive with
  | none => simp [ha] at success
  | some s =>
    simp only [ha, bind, Option.bind] at success
    split at success
    · rename_i checks
      have eq : (⟨w, s⟩ : Authority) = a := Option.some.inj success
      subst a
      exact ⟨rfl, checks.2, ha, checks.1,
        by simp [serve, checks.1, checks.2], audit_sound root verify archive s ha⟩
    · simp at success

theorem recovery_invalid_archive_rejects (root : Root) (verify : VerifySignature)
    (w : Witness) (archive : List Envelope) (bad : audit root verify archive = none) :
    recover root verify w archive = none := by simp [recover, bad]

theorem recovery_pending_rejects (root : Root) (verify : VerifySignature)
    (w : Witness) (archive : List Envelope) (pending : w.pending ≠ none) :
    recover root verify w archive = none := by
  unfold recover
  cases ha : audit root verify archive <;> simp [pending]

theorem recovery_wrong_checkpoint_rejects (root : Root) (verify : VerifySignature)
    (w : Witness) (archive : List Envelope) (s : State)
    (checked : audit root verify archive = some s) (wrong : s ≠ w.committed) :
    recover root verify w archive = none := by simp [recover, checked, wrong]

theorem recovered_history_not_invented (root : Root) (verify : VerifySignature)
    (w : Witness) (archive : List Envelope) (a : Authority)
    (success : recover root verify w archive = some a) : a.localState.history = archive :=
  (recovery_sound root verify w archive a success).scientific.exactHistory

/-- Closed pure-model serving theorem: a checked initialization and actual
prepare/finalize trace establish the invariant rather than receiving it as an
unexplained premise. Honest retention of that witness state is essential. -/
theorem initialized_trace_serving_scientific (root : Root) (verify : VerifySignature)
    (start : Witness) (initialized : initializeWitness root verify = some start)
    (actions : List WitnessAction) (localState served : State)
    (eligible : serve ⟨witnessRun root verify start actions, localState⟩ = some served) :
    ∃ archive, audit root verify archive = some served ∧
      ∃ r, ScopedScientificClaimHolds served.incumbent r := by
  apply serving_artifact_scientific root verify _ served _ eligible
  exact witnessRun_invariant root verify start actions (initialize_sound root verify start initialized)

end PCSScientificAuthorityV2
