import PCSScientificHistoryV1

/-!
Rejecting, complete scientific-history replay. Unlike a transition runner that
silently ignores rejected inputs, every supplied envelope must pass the existing
scientific and authorization checks. Genesis is also received from exact bytes.
Signatures are explicit abstract verifier calls; the scientific decoder/decision
is the actual unchanged receiver. No historical occurrence is inferred.
-/
namespace PCSScientificAuthorityV2

open PCSAuthorizationHistoryV1
open PCSScientificHistoryV1
open PCSScientificReceiver (Result ScopedScientificClaimHolds)

def auditFrom (root : Root) (verify : VerifySignature) :
    State → List Envelope → Option State
  | s, [] => some s
  | s, e :: es =>
    match scientificTransition root verify s e with
    | (_, none) => none
    | (next, some _) => auditFrom root verify next es

/-- No initial scientific-validity hypothesis is accepted from the producer. -/
def audit (root : Root) (verify : VerifySignature) (es : List Envelope) : Option State :=
  if root.policy = policyBytes then
    match PCSScientificReceiver.receive root.genesisIncumbent with
    | none => none
    | some _ => auditFrom root verify (initial root) es
  else none

def ScopedHistory (root : Root) (s : State) : Prop :=
  ∀ e ∈ s.history, e.payload.authority = root.authority ∧
    e.payload.witness = root.witness ∧ e.payload.policy = root.policy ∧
    e.payload.checker = root.checker

def lastArtifact : Bytes → List Envelope → Bytes
  | genesis, [] => genesis
  | _, e :: es => lastArtifact e.payload.candidate es

structure HistoryInvariant (root : Root) (verify : VerifySignature) (s : State) : Prop where
  science : ScientificHistory s
  incumbent : Checked s.incumbent
  authenticated : AuthenticatedHistory root verify s
  linked : LinkedHistory root.genesisId s.history s.tip
  count : s.generation = root.genesisGeneration + s.history.length
  scopePinned : ScopedHistory root s

theorem initial_invariant (root : Root) (verify : VerifySignature)
    (checked : Checked root.genesisIncumbent) : HistoryInvariant root verify (initial root) := by
  refine ⟨?_, checked, ?_, LinkedHistory.genesis _, ?_, ?_⟩
  · intro e he
    simp [initial] at he
  · intro e he
    simp [initial] at he
  · simp [initial]
  · intro e he
    simp [initial] at he

theorem transition_preserves_scope (root : Root) (verify : VerifySignature)
    (s : State) (e : Envelope) (scopePinned : ScopedHistory root s) :
    ScopedHistory root (scientificTransition root verify s e).1 := by
  cases ht : (scientificTransition root verify s e).2 with
  | none => rw [PCSScientificHistoryV1.rejected_unchanged root verify s e ht]; exact scopePinned
  | some r =>
    have facts := PCSScientificHistoryV1.accepted_sound root verify s e r ht
    intro old member
    rw [facts.history] at member
    rcases List.mem_append.mp member with previous | latest
    · exact scopePinned old previous
    · have eq : old = e := by simpa using latest
      subst old
      exact facts.scope

theorem transition_preserves_invariant (root : Root) (verify : VerifySignature)
    (s : State) (e : Envelope) (h : HistoryInvariant root verify s) :
    HistoryInvariant root verify (scientificTransition root verify s e).1 := by
  have old := preserves_history_invariants root verify s e h.authenticated h.linked
  refine ⟨preserves_scientific_history root verify s e h.science,
    preserves_incumbent_science root verify s e h.incumbent, old.1, old.2, ?_,
    transition_preserves_scope root verify s e h.scopePinned⟩
  cases hr : (scientificTransition root verify s e).2 with
  | none => rw [PCSScientificHistoryV1.rejected_unchanged root verify s e hr]; exact h.count
  | some r =>
    have facts := PCSScientificHistoryV1.accepted_sound root verify s e r hr
    rw [facts.generation, facts.history]
    simp only [List.length_append, List.length_singleton]
    have count := h.count
    omega

theorem auditFrom_sound (root : Root) (verify : VerifySignature)
    (s final : State) (es : List Envelope)
    (start : HistoryInvariant root verify s) (success : auditFrom root verify s es = some final) :
    HistoryInvariant root verify final ∧ final.history = s.history ++ es := by
  induction es generalizing s with
  | nil =>
    have eq : s = final := Option.some.inj success
    subst final
    exact ⟨start, by simp⟩
  | cons e es ih =>
    cases ht : scientificTransition root verify s e with
    | mk next result =>
      cases result with
      | none => simp [auditFrom, ht] at success
      | some r =>
        have hr : (scientificTransition root verify s e).2 = some r := by rw [ht]
        have hs : (scientificTransition root verify s e).1 = next := by rw [ht]
        have nextInvariant := transition_preserves_invariant root verify s e start
        rw [hs] at nextInvariant
        have tail : auditFrom root verify next es = some final := by
          simpa [auditFrom, ht] using success
        obtain ⟨valid, history⟩ := ih next nextInvariant tail
        have hf := (PCSScientificHistoryV1.accepted_sound root verify s e r hr).history
        rw [hs] at hf
        refine ⟨valid, ?_⟩
        rw [history, hf]
        simp [List.append_assoc]

theorem auditFrom_final_incumbent (root : Root) (verify : VerifySignature)
    (s final : State) (es : List Envelope) (success : auditFrom root verify s es = some final) :
    final.incumbent = lastArtifact s.incumbent es := by
  induction es generalizing s with
  | nil =>
    have eq : s = final := Option.some.inj success
    subst final
    rfl
  | cons e es ih =>
    cases ht : scientificTransition root verify s e with
    | mk next result =>
      cases result with
      | none => simp [auditFrom, ht] at success
      | some r =>
        have hr : (scientificTransition root verify s e).2 = some r := by rw [ht]
        have hs : (scientificTransition root verify s e).1 = next := by rw [ht]
        have tail : auditFrom root verify next es = some final := by
          simpa [auditFrom, ht] using success
        have incumbent := (PCSScientificHistoryV1.accepted_sound root verify s e r hr).incumbent
        rw [hs] at incumbent
        simpa [lastArtifact, incumbent] using ih next tail

structure CompleteAuditFacts (root : Root) (verify : VerifySignature)
    (es : List Envelope) (final : State) : Prop where
  policy : root.policy = policyBytes
  genesis : ∃ r, PCSScientificReceiver.receive root.genesisIncumbent = some r ∧
    ScopedScientificClaimHolds root.genesisIncumbent r
  invariant : HistoryInvariant root verify final
  exactHistory : final.history = es
  generation : final.generation = root.genesisGeneration + es.length
  finalIncumbent : final.incumbent = lastArtifact root.genesisIncumbent es

/-- Actual checked-genesis/list-auditor soundness, with no opaque premise that
the old history is already scientifically valid. -/
theorem audit_sound (root : Root) (verify : VerifySignature) (es : List Envelope)
    (final : State) (success : audit root verify es = some final) :
    CompleteAuditFacts root verify es final := by
  unfold audit at success
  split at success
  · rename_i hp
    cases hg : PCSScientificReceiver.receive root.genesisIncumbent with
    | none => simp [hg] at success
    | some r =>
      have tail : auditFrom root verify (initial root) es = some final := by
        simpa [hg] using success
      have valid := auditFrom_sound root verify (initial root) final es
        (initial_invariant root verify ⟨r, hg⟩) tail
      have exactHistory : final.history = es := by simpa [initial] using valid.2
      exact ⟨hp, ⟨r, hg, PCSScientificReceiver.verifiedWireSound _ _ hg⟩,
        valid.1, exactHistory, by simpa [exactHistory] using valid.1.count,
        by simpa [initial] using auditFrom_final_incumbent root verify (initial root) final es tail⟩
  · simp at success

theorem audited_entry_scientific (root : Root) (verify : VerifySignature)
    (es : List Envelope) (final : State) (success : audit root verify es = some final)
    (e : Envelope) (member : e ∈ es) :
    e.payload.certificate = [] ∧ ∃ r, ScopedScientificClaimHolds e.payload.candidate r := by
  have facts := audit_sound root verify es final success
  have checked := facts.invariant.science e (by simpa [facts.exactHistory] using member)
  obtain ⟨r, hr⟩ := checked.2
  exact ⟨checked.1, r, PCSScientificReceiver.verifiedWireSound _ _ hr⟩

theorem audited_incumbent_scientific (root : Root) (verify : VerifySignature)
    (es : List Envelope) (final : State) (success : audit root verify es = some final) :
    ∃ r, ScopedScientificClaimHolds final.incumbent r := by
  obtain ⟨r, hr⟩ := (audit_sound root verify es final success).invariant.incumbent
  exact ⟨r, PCSScientificReceiver.verifiedWireSound _ _ hr⟩

theorem audited_signatures_authenticated (root : Root) (verify : VerifySignature)
    (Authenticated : Bytes → Payload → Prop)
    (signatureSound : ∀ key payload signature,
      verify key payload signature = true → Authenticated key payload)
    (es : List Envelope) (final : State) (success : audit root verify es = some final)
    (e : Envelope) (member : e ∈ es) :
    Authenticated root.authority e.payload ∧ Authenticated root.witness e.payload := by
  have facts := audit_sound root verify es final success
  have checked := facts.invariant.authenticated e (by simpa [facts.exactHistory] using member)
  exact ⟨signatureSound _ _ _ checked.1, signatureSound _ _ _ checked.2⟩

theorem wrong_audit_policy_rejects (root : Root) (verify : VerifySignature)
    (es : List Envelope) (wrong : root.policy ≠ policyBytes) : audit root verify es = none := by
  simp [audit, wrong]

theorem invalid_genesis_rejects (root : Root) (verify : VerifySignature)
    (es : List Envelope) (bad : PCSScientificReceiver.receive root.genesisIncumbent = none) :
    audit root verify es = none := by simp [audit, bad]

theorem rejected_entry_stops_audit (root : Root) (verify : VerifySignature)
    (s : State) (e : Envelope) (es : List Envelope)
    (bad : (scientificTransition root verify s e).2 = none) :
    auditFrom root verify s (e :: es) = none := by
  rw [auditFrom, PCSScientificHistoryV1.rejected_unchanged root verify s e bad]

theorem auditFrom_append (root : Root) (verify : VerifySignature)
    (s : State) (front back : List Envelope) :
    auditFrom root verify s (front ++ back) =
      (auditFrom root verify s front).bind (fun next => auditFrom root verify next back) := by
  induction front generalizing s with
  | nil => rfl
  | cons e es ih =>
    cases ht : scientificTransition root verify s e with
    | mk next result =>
      cases result <;> simp [auditFrom, ht, ih]

theorem audit_append_accepted (root : Root) (verify : VerifySignature)
    (es : List Envelope) (s : State) (e : Envelope) (r : Result)
    (success : audit root verify es = some s)
    (accepted : (scientificTransition root verify s e).2 = some r) :
    audit root verify (es ++ [e]) = some (commit s e) := by
  have facts := audit_sound root verify es s success
  obtain ⟨genesis, hg, _⟩ := facts.genesis
  have hp := facts.policy
  have hs := (PCSScientificHistoryV1.accepted_sound root verify s e r accepted).state
  simp only [audit, hp, ↓reduceIte, hg] at success ⊢
  rw [auditFrom_append, success]
  simp [auditFrom, hs]

end PCSScientificAuthorityV2
