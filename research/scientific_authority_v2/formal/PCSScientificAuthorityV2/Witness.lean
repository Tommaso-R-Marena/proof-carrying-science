import PCSScientificAuthorityV2.Audit

/-!
One honest serial witness with durable-state continuity. PREPARE checks actual
science and authorization. FINALIZE commits only that exact prepared successor;
it does not attest that a remote SQLite transaction occurred. The abstract
actions are atomic; compiler, cryptography, networking, storage and crash mapping
are separate runtime obligations. A second cloned/compromised witness is outside
the serial-state assumption, not ruled out by an ordinary hash chain.
-/
namespace PCSScientificAuthorityV2

open PCSAuthorizationHistoryV1
open PCSScientificHistoryV1
open PCSScientificReceiver (Result ScopedScientificClaimHolds)

structure Prepared where
  before : State
  envelope : Envelope
  result : Result
  deriving DecidableEq, Repr

structure Witness where
  committed : State
  pending : Option Prepared
  deriving DecidableEq, Repr

def PendingSound (root : Root) (verify : VerifySignature) (w : Witness) : Prop :=
  ∀ p, w.pending = some p → p.before = w.committed ∧
    scientificTransition root verify w.committed p.envelope =
      (commit w.committed p.envelope, some p.result)

structure WitnessInvariant (root : Root) (verify : VerifySignature) (w : Witness) : Prop where
  checkedArchive : ∃ es, audit root verify es = some w.committed
  pendingSound : PendingSound root verify w

/-- Missing or false scientific genesis does not create a witness state. -/
def initializeWitness (root : Root) (verify : VerifySignature) : Option Witness :=
  (audit root verify []).map (fun s => ⟨s, none⟩)

def prepare (root : Root) (verify : VerifySignature) (w : Witness)
    (e : Envelope) : Witness × Bool :=
  match w.pending with
  | some p => if p.before = w.committed ∧ p.envelope = e then (w, true) else (w, false)
  | none =>
    match scientificTransition root verify w.committed e with
    | (_, none) => (w, false)
    | (_, some r) => (⟨w.committed, some ⟨w.committed, e, r⟩⟩, true)

/-- True means a new atomic finalization, not a cached idempotent RPC reply. -/
def finalize (w : Witness) (e : Envelope) : Witness × Bool :=
  match w.pending with
  | none => (w, false)
  | some p =>
    if p.before = w.committed ∧ p.envelope = e then (⟨commit w.committed e, none⟩, true)
    else (w, false)

theorem initialize_sound (root : Root) (verify : VerifySignature) (w : Witness)
    (success : initializeWitness root verify = some w) : WitnessInvariant root verify w := by
  unfold initializeWitness at success
  cases ha : audit root verify [] with
  | none => simp [ha] at success
  | some s =>
    simp only [ha, Option.map_some, Option.some.injEq] at success
    subst w
    exact ⟨⟨[], ha⟩, by intro p hp; simp at hp⟩

theorem prepare_committed_unchanged (root : Root) (verify : VerifySignature)
    (w : Witness) (e : Envelope) : (prepare root verify w e).1.committed = w.committed := by
  unfold prepare
  split
  · split <;> rfl
  · split <;> rfl

theorem prepare_rejected_unchanged (root : Root) (verify : VerifySignature)
    (w : Witness) (e : Envelope) (rejected : (prepare root verify w e).2 = false) :
    prepare root verify w e = (w, false) := by
  unfold prepare at rejected ⊢
  split
  · split <;> simp_all
  · split <;> simp_all

theorem prepare_preserves_invariant (root : Root) (verify : VerifySignature)
    (w : Witness) (e : Envelope) (valid : WitnessInvariant root verify w) :
    WitnessInvariant root verify (prepare root verify w e).1 := by
  refine ⟨?_, ?_⟩
  · rw [prepare_committed_unchanged]
    exact valid.checkedArchive
  · unfold prepare
    split
    · split <;> exact valid.pendingSound
    · rename_i empty
      cases hs : scientificTransition root verify w.committed e with
      | mk next result =>
        cases result with
        | none => simpa [hs] using valid.pendingSound
        | some r =>
          intro p hp
          have eq : (⟨w.committed, e, r⟩ : Prepared) = p := Option.some.inj hp
          subst p
          have hr : (scientificTransition root verify w.committed e).2 = some r := by rw [hs]
          exact ⟨rfl, (PCSScientificHistoryV1.accepted_sound root verify w.committed e r hr).state⟩

theorem finalize_checks (w : Witness) (e : Envelope)
    (accepted : (finalize w e).2 = true) :
    ∃ p, w.pending = some p ∧ p.before = w.committed ∧ p.envelope = e := by
  unfold finalize at accepted
  split at accepted
  · simp at accepted
  · rename_i p hp
    split at accepted
    · rename_i checks
      exact ⟨p, hp, checks.1, checks.2⟩
    · simp at accepted

theorem finalize_state (w : Witness) (e : Envelope)
    (accepted : (finalize w e).2 = true) :
    finalize w e = (⟨commit w.committed e, none⟩, true) := by
  obtain ⟨p, hp, hb, he⟩ := finalize_checks w e accepted
  simp [finalize, hp, hb, he]

theorem finalize_rejected_unchanged (w : Witness) (e : Envelope)
    (rejected : (finalize w e).2 = false) : finalize w e = (w, false) := by
  unfold finalize at rejected ⊢
  split
  · rfl
  · split <;> simp_all

theorem finalize_prepared_science (root : Root) (verify : VerifySignature)
    (w : Witness) (e : Envelope) (valid : WitnessInvariant root verify w)
    (accepted : (finalize w e).2 = true) :
    ∃ r, scientificTransition root verify w.committed e = (commit w.committed e, some r) ∧
      ScopedScientificClaimHolds e.payload.candidate r := by
  obtain ⟨p, hp, _, he⟩ := finalize_checks w e accepted
  have checked := (valid.pendingSound p hp).2
  rw [he] at checked
  have hr : (scientificTransition root verify w.committed e).2 = some p.result := by rw [checked]
  exact ⟨p.result, checked, (PCSScientificHistoryV1.accepted_sound root verify _ e _ hr).science⟩

theorem finalize_preserves_invariant (root : Root) (verify : VerifySignature)
    (w : Witness) (e : Envelope) (valid : WitnessInvariant root verify w) :
    WitnessInvariant root verify (finalize w e).1 := by
  cases ht : (finalize w e).2 with
  | false => rw [finalize_rejected_unchanged w e ht]; exact valid
  | true =>
    rw [finalize_state w e ht]
    obtain ⟨es, archive⟩ := valid.checkedArchive
    obtain ⟨r, hs, _⟩ := finalize_prepared_science root verify w e valid ht
    have hr : (scientificTransition root verify w.committed e).2 = some r := by rw [hs]
    exact ⟨⟨es ++ [e], audit_append_accepted root verify es w.committed e r archive hr⟩,
      by intro p hp; simp at hp⟩

theorem finalize_generation (w : Witness) (e : Envelope)
    (accepted : (finalize w e).2 = true) :
    (finalize w e).1.committed.generation = w.committed.generation + 1 := by
  simp [finalize_state w e accepted, commit]

theorem finalize_generation_monotone (w : Witness) (e : Envelope) :
    w.committed.generation ≤ (finalize w e).1.committed.generation := by
  cases ht : (finalize w e).2 with
  | false => rw [finalize_rejected_unchanged w e ht]
  | true => rw [finalize_generation w e ht]; omega

theorem finalize_stale_rejected (root : Root) (verify : VerifySignature)
    (w : Witness) (e : Envelope) (valid : WitnessInvariant root verify w)
    (stale : e.payload.expectedGeneration ≠ w.committed.generation) :
    finalize w e = (w, false) := by
  cases ht : (finalize w e).2 with
  | false => exact finalize_rejected_unchanged w e ht
  | true =>
    obtain ⟨r, hs, _⟩ := finalize_prepared_science root verify w e valid ht
    have hr : (scientificTransition root verify w.committed e).2 = some r := by rw [hs]
    have history := (PCSScientificHistoryV1.accepted_sound root verify _ e _ hr).historyAccepted
    exact False.elim (stale (accepted_cas root verify _ e history).1)

inductive WitnessAction where
  | prepare (envelope : Envelope)
  | finalize (envelope : Envelope)

def witnessStep (root : Root) (verify : VerifySignature) (w : Witness)
    (action : WitnessAction) : Witness :=
  match action with
  | .prepare e => (prepare root verify w e).1
  | .finalize e => (finalize w e).1

def witnessRun (root : Root) (verify : VerifySignature) : Witness → List WitnessAction → Witness
  | w, [] => w
  | w, a :: as => witnessRun root verify (witnessStep root verify w a) as

theorem witnessStep_invariant (root : Root) (verify : VerifySignature)
    (w : Witness) (a : WitnessAction) (valid : WitnessInvariant root verify w) :
    WitnessInvariant root verify (witnessStep root verify w a) := by
  cases a with
  | prepare e => exact prepare_preserves_invariant root verify w e valid
  | finalize e => exact finalize_preserves_invariant root verify w e valid

theorem witnessRun_invariant (root : Root) (verify : VerifySignature)
    (w : Witness) (actions : List WitnessAction) (valid : WitnessInvariant root verify w) :
    WitnessInvariant root verify (witnessRun root verify w actions) := by
  induction actions generalizing w with
  | nil => exact valid
  | cons a as ih => exact ih _ (witnessStep_invariant root verify w a valid)

theorem witnessRun_generation_monotone (root : Root) (verify : VerifySignature)
    (w : Witness) (actions : List WitnessAction) :
    w.committed.generation ≤ (witnessRun root verify w actions).committed.generation := by
  induction actions generalizing w with
  | nil => exact le_rfl
  | cons a as ih =>
    have step : w.committed.generation ≤ (witnessStep root verify w a).committed.generation := by
      cases a with
      | prepare e => rw [witnessStep, prepare_committed_unchanged]
      | finalize e => exact finalize_generation_monotone w e
    exact le_trans step (ih _)

/-- One honest durable serial witness cannot finalize a conflicting successor
from the already consumed predecessor, even after arbitrary later requests. -/
theorem no_conflicting_finalization_later (root : Root) (verify : VerifySignature)
    (w : Witness) (first second : Envelope) (valid : WitnessInvariant root verify w)
    (accepted : (finalize w first).2 = true)
    (samePredecessorGeneration : second.payload.expectedGeneration = first.payload.expectedGeneration)
    (later : List WitnessAction) :
    let after := witnessRun root verify (finalize w first).1 later
    finalize after second = (after, false) := by
  dsimp only
  have inv := witnessRun_invariant root verify (finalize w first).1 later
    (finalize_preserves_invariant root verify w first valid)
  apply finalize_stale_rejected root verify _ second inv
  obtain ⟨r, hs, _⟩ := finalize_prepared_science root verify w first valid accepted
  have hr : (scientificTransition root verify w.committed first).2 = some r := by rw [hs]
  have hg := (accepted_cas root verify w.committed first
    (PCSScientificHistoryV1.accepted_sound root verify _ first _ hr).historyAccepted).1
  have monotone := witnessRun_generation_monotone root verify (finalize w first).1 later
  rw [finalize_generation w first accepted] at monotone
  omega

end PCSScientificAuthorityV2
