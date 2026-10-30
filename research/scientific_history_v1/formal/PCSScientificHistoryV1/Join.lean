import PCSScientificReceiver.Receiver
import PCSAuthorizationHistoryV1

/-!
Exact-byte scientific receiving joined to the existing serial history CAS.
The complete candidate is a canonical scientific bundle; auxiliary certificate
bytes are reserved and must be empty. Checker identity stays an abstract pinned
receiver configuration identity. No cryptographic, host, storage/crash, empirical
or improvement claim follows from this mathematical wrapper.
-/
namespace PCSScientificHistoryV1

open PCSAuthorizationHistoryV1
open PCSScientificReceiver (Result ScopedScientificClaimHolds)

def policyBytes : Bytes :=
  [80, 67, 83, 45, 83, 67, 73, 45, 72, 73, 83, 84, 79, 82, 89, 45, 86, 49]

/-- Check science from the exact signed candidate before any history commit. -/
def scientificTransition (root : Root) (verify : VerifySignature) (s : State)
    (e : Envelope) : State × Option Result :=
  if root.policy = policyBytes ∧ e.payload.certificate = [] then
    match PCSScientificReceiver.receive e.payload.candidate with
    | none => (s, none)
    | some r =>
      if (transition root verify s e).2 then ((transition root verify s e).1, some r)
      else (s, none)
  else (s, none)

theorem accepted_checks (root : Root) (verify : VerifySignature) (s : State)
    (e : Envelope) (r : Result) (h : (scientificTransition root verify s e).2 = some r) :
    root.policy = policyBytes ∧ e.payload.certificate = [] ∧
    PCSScientificReceiver.receive e.payload.candidate = some r ∧
    (transition root verify s e).2 = true := by
  unfold scientificTransition at h
  split at h
  · rename_i hp
    cases hs : PCSScientificReceiver.receive e.payload.candidate with
    | none => simp [hs] at h
    | some result =>
      simp only [hs] at h
      split at h
      · rename_i ht
        have hr := Option.some.inj h
        subst result
        exact ⟨hp.1, hp.2, rfl, ht⟩
      · simp at h
  · simp at h

/-- The accepted result denotes precisely the candidate bound into both signed
payload checks, and the committed state contains precisely that byte string. -/
structure AcceptedFacts (root : Root) (verify : VerifySignature) (s : State)
    (e : Envelope) (r : Result) : Prop where
  policy : root.policy = policyBytes
  reservedEmpty : e.payload.certificate = []
  science : ScopedScientificClaimHolds e.payload.candidate r
  historyAccepted : (transition root verify s e).2 = true
  state : scientificTransition root verify s e = (commit s e, some r)
  incumbent : (scientificTransition root verify s e).1.incumbent = e.payload.candidate
  history : (scientificTransition root verify s e).1.history = s.history ++ [e]
  generation : (scientificTransition root verify s e).1.generation = s.generation + 1
  scope : e.payload.authority = root.authority ∧ e.payload.witness = root.witness ∧
    e.payload.policy = root.policy ∧ e.payload.checker = root.checker

theorem accepted_sound (root : Root) (verify : VerifySignature) (s : State)
    (e : Envelope) (r : Result) (h : (scientificTransition root verify s e).2 = some r) :
    AcceptedFacts root verify s e r := by
  obtain ⟨hp, hc, hs, ht⟩ := accepted_checks root verify s e r h
  have stateEq : scientificTransition root verify s e = (commit s e, some r) := by
    simp [scientificTransition, hp, hc, hs, accepted_state root verify s e ht]
  refine ⟨hp, hc, PCSScientificReceiver.verifiedWireSound _ _ hs, ht, stateEq,
    ?_, ?_, ?_, accepted_scope_pinned root verify s e ht⟩
  all_goals simp [stateEq, commit]

theorem rejected_unchanged (root : Root) (verify : VerifySignature) (s : State)
    (e : Envelope) (h : (scientificTransition root verify s e).2 = none) :
    scientificTransition root verify s e = (s, none) := by
  unfold scientificTransition at h ⊢
  split
  · cases hs : PCSScientificReceiver.receive e.payload.candidate with
    | none => simp
    | some r =>
      simp only [hs] at h ⊢
      split <;> simp_all
  · rfl

theorem wrong_policy_rejects (root : Root) (verify : VerifySignature) (s : State)
    (e : Envelope) (h : root.policy ≠ policyBytes) :
    scientificTransition root verify s e = (s, none) := by simp [scientificTransition, h]

theorem auxiliary_certificate_rejects (root : Root) (verify : VerifySignature) (s : State)
    (e : Envelope) (h : e.payload.certificate ≠ []) :
    scientificTransition root verify s e = (s, none) := by simp [scientificTransition, h]

theorem false_science_rejects (root : Root) (verify : VerifySignature) (s : State)
    (e : Envelope) (h : PCSScientificReceiver.receive e.payload.candidate = none) :
    scientificTransition root verify s e = (s, none) := by simp [scientificTransition, h]

theorem history_failure_rejects (root : Root) (verify : VerifySignature) (s : State)
    (e : Envelope) (h : (transition root verify s e).2 = false) :
    scientificTransition root verify s e = (s, none) := by
  unfold scientificTransition
  split <;> simp_all
  split <;> simp_all

theorem accepted_authenticated (root : Root) (verify : VerifySignature)
    (Authenticated : Bytes → Payload → Prop)
    (signatureSound : ∀ key payload signature,
      verify key payload signature = true → Authenticated key payload)
    (s : State) (e : Envelope) (r : Result)
    (h : (scientificTransition root verify s e).2 = some r) :
    Authenticated root.authority e.payload ∧ Authenticated root.witness e.payload :=
  PCSAuthorizationHistoryV1.accepted_authenticated root verify Authenticated signatureSound
    s e (accepted_sound root verify s e r h).historyAccepted

/-- This invariant concerns checked exact bytes, not scientific model adequacy. -/
def Checked (raw : Bytes) : Prop := ∃ r, PCSScientificReceiver.receive raw = some r

def ScientificHistory (s : State) : Prop :=
  ∀ e ∈ s.history, e.payload.certificate = [] ∧ Checked e.payload.candidate

theorem preserves_scientific_history (root : Root) (verify : VerifySignature)
    (s : State) (e : Envelope) (h : ScientificHistory s) :
    ScientificHistory (scientificTransition root verify s e).1 := by
  cases hr : (scientificTransition root verify s e).2 with
  | none => rw [rejected_unchanged root verify s e hr]; exact h
  | some r =>
    have facts := accepted_sound root verify s e r hr
    intro old hm
    rw [facts.history] at hm
    rcases List.mem_append.mp hm with hold | hnew
    · exact h old hold
    · have he : old = e := by simpa using hnew
      subst old
      exact ⟨facts.reservedEmpty, ⟨r, (accepted_checks root verify s e r hr).2.2.1⟩⟩

theorem preserves_incumbent_science (root : Root) (verify : VerifySignature)
    (s : State) (e : Envelope) (h : Checked s.incumbent) :
    Checked (scientificTransition root verify s e).1.incumbent := by
  cases hr : (scientificTransition root verify s e).2 with
  | none => rw [rejected_unchanged root verify s e hr]; exact h
  | some r =>
    rw [(accepted_sound root verify s e r hr).incumbent]
    exact ⟨r, (accepted_checks root verify s e r hr).2.2.1⟩

def run (root : Root) (verify : VerifySignature) : State → List Envelope → State
  | s, [] => s
  | s, e :: es => run root verify (scientificTransition root verify s e).1 es

theorem run_scientific (root : Root) (verify : VerifySignature) (s : State)
    (es : List Envelope) (history : ScientificHistory s) (incumbent : Checked s.incumbent) :
    ScientificHistory (run root verify s es) ∧ Checked (run root verify s es).incumbent := by
  induction es generalizing s with
  | nil => exact ⟨history, incumbent⟩
  | cons e es ih =>
    exact ih _ (preserves_scientific_history root verify s e history)
      (preserves_incumbent_science root verify s e incumbent)

theorem run_generation_monotone (root : Root) (verify : VerifySignature) (s : State)
    (es : List Envelope) : s.generation ≤ (run root verify s es).generation := by
  induction es generalizing s with
  | nil => exact le_rfl
  | cons e es ih =>
    have step : s.generation ≤ (scientificTransition root verify s e).1.generation := by
      cases hr : (scientificTransition root verify s e).2 with
      | none => rw [rejected_unchanged root verify s e hr]
      | some r => rw [(accepted_sound root verify s e r hr).generation]; omega
    exact le_trans step (ih _)

theorem accepted_never_replayed (root : Root) (verify : VerifySignature)
    (s : State) (e : Envelope) (r : Result)
    (h : (scientificTransition root verify s e).2 = some r) (later : List Envelope) :
    let after := run root verify (scientificTransition root verify s e).1 later
    scientificTransition root verify after e = (after, none) := by
  dsimp only
  apply history_failure_rejects
  have hg := (accepted_cas root verify s e (accepted_sound root verify s e r h).historyAccepted).1
  have hm := run_generation_monotone root verify (scientificTransition root verify s e).1 later
  rw [(accepted_sound root verify s e r h).generation] at hm
  have stale : e.payload.expectedGeneration ≠
      (run root verify (scientificTransition root verify s e).1 later).generation := by omega
  rw [stale_generation_rejected root verify _ e stale]

theorem malformed_rejects (root : Root) (verify : VerifySignature) (s : State)
    (e : Envelope) (h : PCSScientificReceiver.decode e.payload.candidate = none) :
    scientificTransition root verify s e = (s, none) :=
  false_science_rejects root verify s e (PCSScientificReceiver.malformed_rejects _ h)

theorem signature_failure_rejects (root : Root) (verify : VerifySignature) (s : State)
    (e : Envelope)
    (h : verify root.authority e.payload e.authoritySignature = false ∨
      verify root.witness e.payload e.witnessSignature = false) :
    scientificTransition root verify s e = (s, none) := by
  apply history_failure_rejects
  have bad : ¬ Admissible root verify s e := by
    intro ha
    rcases ha with ⟨_, _, _, _, _, _, _, _, _, _, auth, witness⟩
    rcases h with h | h <;> simp_all
  rw [reject_of_inadmissible root verify s e bad]

theorem initial_run_scientific (root : Root) (verify : VerifySignature)
    (es : List Envelope) (genesis : Checked root.genesisIncumbent) :
    ScientificHistory (run root verify (initial root) es) ∧
      Checked (run root verify (initial root) es).incumbent := by
  apply run_scientific root verify (initial root) es
  · intro e he
    simp [initial] at he
  · exact genesis

/-- The wrapper preserves the original history's authentication/link invariants;
science rejection cannot manufacture a history transition. -/
theorem preserves_history_invariants (root : Root) (verify : VerifySignature)
    (s : State) (e : Envelope) (auth : AuthenticatedHistory root verify s)
    (links : LinkedHistory root.genesisId s.history s.tip) :
    AuthenticatedHistory root verify (scientificTransition root verify s e).1 ∧
    LinkedHistory root.genesisId (scientificTransition root verify s e).1.history
      (scientificTransition root verify s e).1.tip := by
  cases hr : (scientificTransition root verify s e).2 with
  | none => rw [rejected_unchanged root verify s e hr]; exact ⟨auth, links⟩
  | some r =>
    have facts := accepted_sound root verify s e r hr
    have hs : (transition root verify s e).1 = commit s e :=
      congrArg Prod.fst (accepted_state root verify s e facts.historyAccepted)
    simp only [facts.state, hs.symm]
    exact ⟨transition_preserves_authentication root verify s e auth,
      transition_preserves_links root verify s e links⟩

end PCSScientificHistoryV1
