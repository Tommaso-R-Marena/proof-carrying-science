import Mathlib.Data.List.Basic
import Mathlib.Tactic

/-!
# Isolated authenticated authorization-history core

This is a pure serial transition model, separate from every existing authority.
The receiver pins its root and its current committed state independently of the
proposer. Signature verification is an explicit receiver-controlled parameter;
authenticity theorems state its soundness assumption. Both authority and witness
must verify the same complete structured payload. No cryptographic implementation,
canonical event-byte codec, hash collision resistance, storage persistence,
concurrent-replica consensus, crash recovery or protected host is established.

Event IDs are opaque, fresh link labels, not cryptographic commitments. The model
retains exact signed envelopes and proves append-only extension. It does not infer
history authenticity from an ordinary hash, and it cannot protect a substituted
trusted root/state. Only committed atomic transitions are modeled; the
receipt-before-HEAD protocol and liveness remain separate obligations. Generation
rollback is rejected; an expressly authorized later-generation model may reuse
older model bytes. Policy rotation and checker upgrades are outside this v1 core.
Candidate/certificate bytes and checker identity are bound, but the scientific
checker is not executed here. Signature origin alone does not establish model
validity or governance approval: an authorization interpretation requires the
explicit verifier-soundness premise to assert that authorization predicate.
-/
namespace PCSAuthorizationHistoryV1

abbrev Bytes := List UInt8

structure Root where
  authority : Bytes
  witness : Bytes
  policy : Bytes
  checker : Bytes
  genesisId : Bytes
  genesisIncumbent : Bytes
  genesisGeneration : Nat
  deriving DecidableEq, Repr

/-- Exact candidate/certificate bytes, CAS expectations, predecessor and all
pinned scopes are part of what both signatures authenticate. -/
structure Payload where
  authority : Bytes
  witness : Bytes
  policy : Bytes
  checker : Bytes
  previousId : Bytes
  eventId : Bytes
  expectedGeneration : Nat
  nextGeneration : Nat
  expectedIncumbent : Bytes
  candidate : Bytes
  certificate : Bytes
  deriving DecidableEq, Repr

structure Envelope where
  payload : Payload
  authoritySignature : Bytes
  witnessSignature : Bytes
  deriving DecidableEq, Repr

structure State where
  generation : Nat
  incumbent : Bytes
  tip : Bytes
  history : List Envelope
  deriving DecidableEq, Repr

def initial (root : Root) : State :=
  ⟨root.genesisGeneration, root.genesisIncumbent, root.genesisId, []⟩

abbrev VerifySignature := Bytes → Payload → Bytes → Bool

/-- Admission depends on receiver-controlled state/root, never on an anchor or
policy selected by the request. Both signatures cover this exact payload. -/
def Admissible (root : Root) (verify : VerifySignature) (s : State) (e : Envelope) : Prop :=
  e.payload.authority = root.authority ∧
  e.payload.witness = root.witness ∧
  e.payload.policy = root.policy ∧
  e.payload.checker = root.checker ∧
  e.payload.expectedGeneration = s.generation ∧
  e.payload.nextGeneration = s.generation + 1 ∧
  e.payload.expectedIncumbent = s.incumbent ∧
  e.payload.previousId = s.tip ∧
  e.payload.eventId ≠ root.genesisId ∧
  (∀ old ∈ s.history, old.payload.eventId ≠ e.payload.eventId) ∧
  verify root.authority e.payload e.authoritySignature = true ∧
  verify root.witness e.payload e.witnessSignature = true

instance (root : Root) (verify : VerifySignature) (s : State) (e : Envelope) :
    Decidable (Admissible root verify s e) := by
  unfold Admissible
  infer_instance

def commit (s : State) (e : Envelope) : State :=
  ⟨s.generation + 1, e.payload.candidate, e.payload.eventId, s.history ++ [e]⟩

/-- One abstract atomic CAS linearization point. Rejection changes no state. -/
def transition (root : Root) (verify : VerifySignature) (s : State) (e : Envelope) :
    State × Bool :=
  if Admissible root verify s e then (commit s e, true) else (s, false)

theorem accepted_iff (root : Root) (verify : VerifySignature) (s : State) (e : Envelope) :
    (transition root verify s e).2 = true ↔ Admissible root verify s e := by
  unfold transition
  split <;> simp_all

theorem accepted_state (root : Root) (verify : VerifySignature) (s : State) (e : Envelope)
    (h : (transition root verify s e).2 = true) :
    transition root verify s e = (commit s e, true) := by
  simp [transition, (accepted_iff root verify s e).mp h]

theorem rejected_unchanged (root : Root) (verify : VerifySignature) (s : State) (e : Envelope)
    (h : (transition root verify s e).2 = false) :
    transition root verify s e = (s, false) := by
  unfold transition at h ⊢
  split <;> simp_all

theorem reject_of_inadmissible (root : Root) (verify : VerifySignature)
    (s : State) (e : Envelope) (h : ¬ Admissible root verify s e) :
    transition root verify s e = (s, false) := by simp [transition, h]

/-- Unforgeability/authentication is a stated assumption about the actual
receiver-controlled verifier, not a theorem about an ordinary digest. -/
theorem accepted_authenticated (root : Root) (verify : VerifySignature)
    (Authenticated : Bytes → Payload → Prop)
    (signatureSound : ∀ key payload signature,
      verify key payload signature = true → Authenticated key payload)
    (s : State) (e : Envelope) (h : (transition root verify s e).2 = true) :
    Authenticated root.authority e.payload ∧ Authenticated root.witness e.payload := by
  have ha := (accepted_iff root verify s e).mp h
  rcases ha with ⟨_, _, _, _, _, _, _, _, _, _, hs, hw⟩
  exact ⟨signatureSound _ _ _ hs, signatureSound _ _ _ hw⟩

theorem accepted_scope_pinned (root : Root) (verify : VerifySignature)
    (s : State) (e : Envelope) (h : (transition root verify s e).2 = true) :
    e.payload.authority = root.authority ∧ e.payload.witness = root.witness ∧
    e.payload.policy = root.policy ∧ e.payload.checker = root.checker := by
  have ha := (accepted_iff root verify s e).mp h
  exact ⟨ha.1, ha.2.1, ha.2.2.1, ha.2.2.2.1⟩

theorem accepted_cas (root : Root) (verify : VerifySignature)
    (s : State) (e : Envelope) (h : (transition root verify s e).2 = true) :
    e.payload.expectedGeneration = s.generation ∧
    e.payload.nextGeneration = s.generation + 1 ∧
    e.payload.expectedIncumbent = s.incumbent ∧ e.payload.previousId = s.tip := by
  rcases (accepted_iff root verify s e).mp h with
    ⟨_, _, _, _, hg, hn, hi, hp, _, _, _, _⟩
  exact ⟨hg, hn, hi, hp⟩

theorem stale_generation_rejected (root : Root) (verify : VerifySignature)
    (s : State) (e : Envelope) (stale : e.payload.expectedGeneration ≠ s.generation) :
    transition root verify s e = (s, false) := by
  apply reject_of_inadmissible
  intro h
  exact stale h.2.2.2.2.1

theorem generation_rollback_rejected (root : Root) (verify : VerifySignature)
    (s : State) (e : Envelope) (rollback : e.payload.nextGeneration ≤ s.generation) :
    transition root verify s e = (s, false) := by
  apply reject_of_inadmissible
  intro h
  have hn := h.2.2.2.2.2.1
  omega

theorem wrong_incumbent_rejected (root : Root) (verify : VerifySignature)
    (s : State) (e : Envelope) (wrong : e.payload.expectedIncumbent ≠ s.incumbent) :
    transition root verify s e = (s, false) := by
  apply reject_of_inadmissible
  intro h
  exact wrong h.2.2.2.2.2.2.1

theorem wrong_predecessor_rejected (root : Root) (verify : VerifySignature)
    (s : State) (e : Envelope) (wrong : e.payload.previousId ≠ s.tip) :
    transition root verify s e = (s, false) := by
  apply reject_of_inadmissible
  intro h
  exact wrong h.2.2.2.2.2.2.2.1

theorem duplicate_eventId_rejected (root : Root) (verify : VerifySignature)
    (s : State) (e old : Envelope) (mem : old ∈ s.history)
    (duplicate : old.payload.eventId = e.payload.eventId) :
    transition root verify s e = (s, false) := by
  apply reject_of_inadmissible
  intro h
  exact h.2.2.2.2.2.2.2.2.2.1 old mem duplicate

theorem generation_monotone (root : Root) (verify : VerifySignature)
    (s : State) (e : Envelope) :
    s.generation ≤ (transition root verify s e).1.generation := by
  unfold transition
  split <;> simp [commit]

theorem history_extension (root : Root) (verify : VerifySignature)
    (s : State) (e : Envelope) :
    ∃ suffix, (transition root verify s e).1.history = s.history ++ suffix := by
  unfold transition
  split
  · exact ⟨[e], rfl⟩
  · exact ⟨[], (List.append_nil _).symm⟩

def run (root : Root) (verify : VerifySignature) : State → List Envelope → State
  | s, [] => s
  | s, e :: es => run root verify (transition root verify s e).1 es

theorem run_generation_monotone (root : Root) (verify : VerifySignature)
    (s : State) (es : List Envelope) : s.generation ≤ (run root verify s es).generation := by
  induction es generalizing s with
  | nil => exact le_rfl
  | cons e es ih => exact le_trans (generation_monotone root verify s e) (ih _)

theorem run_history_extension (root : Root) (verify : VerifySignature)
    (s : State) (es : List Envelope) :
    ∃ suffix, (run root verify s es).history = s.history ++ suffix := by
  induction es generalizing s with
  | nil => exact ⟨[], (List.append_nil _).symm⟩
  | cons e es ih =>
    obtain ⟨first, hf⟩ := history_extension root verify s e
    obtain ⟨rest, hr⟩ := ih (transition root verify s e).1
    exact ⟨first ++ rest, by simpa [run, hf, List.append_assoc] using hr⟩

/-- Once accepted, the same signed event cannot be accepted again at any later
point on this serial committed chain, even after arbitrary other requests. -/
theorem accepted_never_replayed (root : Root) (verify : VerifySignature)
    (s : State) (e : Envelope) (accepted : (transition root verify s e).2 = true)
    (later : List Envelope) :
    let after := run root verify (transition root verify s e).1 later
    transition root verify after e = (after, false) := by
  dsimp only
  apply stale_generation_rejected
  have hg := (accepted_cas root verify s e accepted).1
  have hm := run_generation_monotone root verify (transition root verify s e).1 later
  rw [accepted_state root verify s e accepted] at hm ⊢
  simp only [commit] at hm ⊢
  omega

/-- This is serial CAS safety, not a consensus/non-equivocation theorem for two
independent replicas started from the same root and state. -/
theorem same_generation_conflict_rejected (root : Root) (verify : VerifySignature)
    (s : State) (first second : Envelope)
    (accepted : (transition root verify s first).2 = true)
    (sameGeneration : second.payload.expectedGeneration = first.payload.expectedGeneration) :
    transition root verify (transition root verify s first).1 second =
      ((transition root verify s first).1, false) := by
  apply stale_generation_rejected
  have hg := (accepted_cas root verify s first accepted).1
  rw [accepted_state root verify s first accepted]
  simp only [commit]
  omega

/-- Every stored envelope in a generated history passed both pinned checks. -/
def AuthenticatedHistory (root : Root) (verify : VerifySignature) (s : State) : Prop :=
  ∀ e ∈ s.history,
    verify root.authority e.payload e.authoritySignature = true ∧
    verify root.witness e.payload e.witnessSignature = true

theorem transition_preserves_authentication (root : Root) (verify : VerifySignature)
    (s : State) (e : Envelope) (h : AuthenticatedHistory root verify s) :
    AuthenticatedHistory root verify (transition root verify s e).1 := by
  unfold transition
  split
  · rename_i ha
    intro old hm
    simp only [commit, List.mem_append, List.mem_singleton] at hm
    rcases hm with hm | rfl
    · exact h old hm
    · exact ha.2.2.2.2.2.2.2.2.2.2
  · exact h

theorem run_authenticated (root : Root) (verify : VerifySignature)
    (es : List Envelope) : AuthenticatedHistory root verify (run root verify (initial root) es) := by
  have general : ∀ es s, AuthenticatedHistory root verify s →
      AuthenticatedHistory root verify (run root verify s es) := by
    intro es
    induction es with
    | nil => intro s h; exact h
    | cons e es ih =>
      intro s h
      exact ih _ (transition_preserves_authentication root verify s e h)
  apply general
  intro e he
  simp [initial] at he

/-- Exact predecessor links from genesis to the current committed tip. No hash
collision assumption is needed because the entire envelope list is retained. -/
inductive LinkedHistory : Bytes → List Envelope → Bytes → Prop
  | genesis (tip : Bytes) : LinkedHistory tip [] tip
  | append {start tip : Bytes} {history : List Envelope} (e : Envelope) :
      LinkedHistory start history tip → e.payload.previousId = tip →
      LinkedHistory start (history ++ [e]) e.payload.eventId

theorem transition_preserves_links (root : Root) (verify : VerifySignature)
    (s : State) (e : Envelope)
    (h : LinkedHistory root.genesisId s.history s.tip) :
    LinkedHistory root.genesisId (transition root verify s e).1.history
      (transition root verify s e).1.tip := by
  unfold transition
  split
  · rename_i ha
    exact LinkedHistory.append e h ha.2.2.2.2.2.2.2.1
  · exact h

theorem run_linked (root : Root) (verify : VerifySignature) (es : List Envelope) :
    LinkedHistory root.genesisId (run root verify (initial root) es).history
      (run root verify (initial root) es).tip := by
  have general : ∀ es s, LinkedHistory root.genesisId s.history s.tip →
      LinkedHistory root.genesisId (run root verify s es).history
        (run root verify s es).tip := by
    intro es
    induction es with
    | nil => intro s h; exact h
    | cons e es ih =>
      intro s h
      exact ih _ (transition_preserves_links root verify s e h)
  exact general es (initial root) (LinkedHistory.genesis root.genesisId)

/-- The generation is exactly genesis plus the number of committed envelopes;
rejections neither consume a generation nor appear as invented commits. -/
theorem run_generation_counts_commits (root : Root) (verify : VerifySignature)
    (es : List Envelope) :
    (run root verify (initial root) es).generation =
      root.genesisGeneration + (run root verify (initial root) es).history.length := by
  have general : ∀ es s, s.generation = root.genesisGeneration + s.history.length →
      (run root verify s es).generation =
        root.genesisGeneration + (run root verify s es).history.length := by
    intro es
    induction es with
    | nil => intro s h; exact h
    | cons e es ih =>
      intro s h
      apply ih
      unfold transition
      split <;> simp_all [commit, List.length_append, Nat.add_assoc]
  exact general es (initial root) (by simp [initial])

theorem run_authenticated_of_verifier_sound (root : Root) (verify : VerifySignature)
    (Authenticated : Bytes → Payload → Prop)
    (signatureSound : ∀ key payload signature,
      verify key payload signature = true → Authenticated key payload)
    (es : List Envelope) (e : Envelope)
    (mem : e ∈ (run root verify (initial root) es).history) :
    Authenticated root.authority e.payload ∧ Authenticated root.witness e.payload := by
  have checked := run_authenticated root verify es e mem
  exact ⟨signatureSound _ _ _ checked.1, signatureSound _ _ _ checked.2⟩

/-- Symbolic finite fixture, not a cryptographic verifier implementation. -/
def fixtureRoot : Root := ⟨[1], [2], [3], [4], [0], [10], 0⟩

def fixturePayload : Payload :=
  ⟨[1], [2], [3], [4], [0], [5], 0, 1, [10], [11], [12]⟩

def fixtureEnvelope : Envelope := ⟨fixturePayload, [21], [22]⟩

/-- Exact finite allowlist for nonvacuity tests only. -/
def fixtureVerify (key : Bytes) (payload : Payload) (signature : Bytes) : Bool :=
  decide (payload = fixturePayload ∧
    ((key = [1] ∧ signature = [21]) ∨ (key = [2] ∧ signature = [22])))

theorem fixture_accepts :
    transition fixtureRoot fixtureVerify (initial fixtureRoot) fixtureEnvelope =
      (commit (initial fixtureRoot) fixtureEnvelope, true) := by decide +kernel

theorem fixture_replay_rejects :
    transition fixtureRoot fixtureVerify (commit (initial fixtureRoot) fixtureEnvelope)
      fixtureEnvelope = (commit (initial fixtureRoot) fixtureEnvelope, false) := by decide +kernel

theorem fixture_missing_witness_rejects :
    transition fixtureRoot fixtureVerify (initial fixtureRoot)
      { fixtureEnvelope with witnessSignature := [] } = (initial fixtureRoot, false) := by
  decide +kernel

theorem fixture_substituted_policy_rejects :
    transition fixtureRoot fixtureVerify (initial fixtureRoot)
      { fixtureEnvelope with payload := { fixturePayload with policy := [99] } } =
      (initial fixtureRoot, false) := by decide +kernel

#print axioms accepted_authenticated
#print axioms accepted_scope_pinned
#print axioms accepted_cas
#print axioms rejected_unchanged
#print axioms generation_rollback_rejected
#print axioms run_generation_monotone
#print axioms run_history_extension
#print axioms accepted_never_replayed
#print axioms same_generation_conflict_rejected
#print axioms run_authenticated
#print axioms run_linked
#print axioms run_generation_counts_commits
#print axioms run_authenticated_of_verifier_sound
#print axioms fixture_accepts
#print axioms fixture_replay_rejects
#print axioms fixture_missing_witness_rejects
#print axioms fixture_substituted_policy_rejects

end PCSAuthorizationHistoryV1
