import PCS.V2.ReceiptAuthorityV3

/-!
# PCS v3 — the state-aware semantic translation decision

`decideV3` is the production decision of Semantic Intelligence v3.  It reuses, unchanged, v2's
core gates and proof-carrying semantic analysis (`semanticAnalysis`: normal forms, checked
equivalence certificates, verified countermodels) and replaces the stateless v1 receipt gates by
the stateful envelope phase of `PCS.V2.Semantic.V3.receiptPhase`.

`stepV3` is the authority's state transition: it returns the decision together with the new
ledger, which differs from the old one **only** on `CERTIFIED_TRANSLATION`, and then exactly by
the request's nonces (atomic consume; a failed request consumes nothing).

Legacy v1 receipts (`Request.confirmation/elaboration/proof`) are **rejected** in v3 mode: the
v3 authority never treats a stateless receipt as evidence.  (`pcs-semantic-check` without
`--v3` still runs v1/v2; those modes are documented as non-production in the v3 report.)
-/

set_option autoImplicit false

namespace PCS.V2.Semantic.V3

open PCS.V2.Json PCS.V2.Semantic PCS.V2.Semantic.Ledger

/-! ## Legacy receipts -/

def legacyDiagnostics (req : Request) : List Diagnostic :=
  (match req.confirmation with
    | some _ => [⟨.confirmationNotVerified, "confirmation",
        "stateless v1 confirmation receipt is not accepted by the v3 authority (use a receipt envelope)"⟩]
    | none => []) ++
  (match req.elaboration with
    | some _ => [⟨.elaborationNotVerified, "elaboration",
        "stateless v1 elaboration receipt is not accepted by the v3 authority (use a receipt envelope)"⟩]
    | none => []) ++
  (match req.proof with
    | some _ => [⟨.proofNotVerified, "proof",
        "stateless v1 proof receipt is not accepted by the v3 authority (use a receipt envelope)"⟩]
    | none => [])

/-- No stateless v1 receipt is present. -/
def NoLegacyReceipts (req : Request) : Prop :=
  req.confirmation = none ∧ req.elaboration = none ∧ req.proof = none

theorem legacyDiagnostics_nil (req : Request) :
    legacyDiagnostics req = [] ↔ NoLegacyReceipts req := by
  unfold legacyDiagnostics NoLegacyReceipts
  cases req.confirmation <;> cases req.elaboration <;> cases req.proof <;> simp

/-! ## Outcomes and decisions -/

/-- v3 outcome classes.  Only `certifiedTranslation` is an acceptance. -/
inductive OutcomeV3 where
  | certifiedTranslation
  | verifiedCounterexample
  | needsHumanClarification
  | unresolvedProofObligation
  | unsupportedFragment
  | searchExhausted
  | invalidProposal
  | receiptRejected
  | invalidAuthority
  deriving Repr, DecidableEq, Inhabited

def OutcomeV3.name : OutcomeV3 → String
  | .certifiedTranslation => "CERTIFIED_TRANSLATION"
  | .verifiedCounterexample => "VERIFIED_COUNTEREXAMPLE"
  | .needsHumanClarification => "NEEDS_HUMAN_CLARIFICATION"
  | .unresolvedProofObligation => "UNRESOLVED_PROOF_OBLIGATION"
  | .unsupportedFragment => "UNSUPPORTED_FRAGMENT"
  | .searchExhausted => "SEARCH_EXHAUSTED"
  | .invalidProposal => "INVALID_PROPOSAL"
  | .receiptRejected => "RECEIPT_REJECTED"
  | .invalidAuthority => "INVALID_AUTHORITY"

/-- The v3 decision. -/
structure DecisionV3 where
  outcome : OutcomeV3
  diagnostics : List Diagnostic
  semantic : SemanticStatus
  certificate : Option EquivCert
  /-- result of the receipt phase, if it was reached -/
  receipts : Option (Except ReceiptFailure (List String))
  /-- nonces consumed by this decision (empty unless certified) -/
  consumed : List String
  deriving Repr, Inhabited

def receiptOutcome : Except ReceiptFailure (List String) → OutcomeV3
  | .ok _ => .certifiedTranslation
  | .error (.quorumNotMet .confirmation _ _) => .needsHumanClarification
  | .error (.quorumNotMet _ _ _) => .unresolvedProofObligation
  | .error _ => .receiptRejected

def roleCode : ReceiptRole → FailureCode
  | .confirmation => .confirmationNotVerified
  | .elaboration => .elaborationNotVerified
  | .proof => .proofNotVerified

def rejectReasonName : RejectReason → String
  | .unknownVersion => "UNKNOWN_VERSION"
  | .roleMismatch => "ROLE_MISMATCH"
  | .unauthorizedKey => "UNAUTHORIZED_KEY"
  | .revokedKey => "REVOKED_KEY"
  | .statementMismatch => "STATEMENT_MISMATCH"
  | .outsideValidity => "OUTSIDE_VALIDITY_WINDOW"
  | .replay => "REPLAY"
  | .badSignature => "BAD_SIGNATURE"

def receiptDiagnostics : Except ReceiptFailure (List String) → List Diagnostic
  | .ok _ => []
  | .error (.rejected n r) => [⟨.proofNotVerified, "receipts", "envelope " ++ n ++ ": " ++ rejectReasonName r⟩]
  | .error (.beforeGenesis n) => [⟨.proofNotVerified, "receipts",
      "envelope " ++ n ++ ": issued before the ledger genesis"⟩]
  | .error (.quorumNotMet role k q) => [⟨roleCode role, "receipts",
      role.name ++ " quorum not met: " ++ toString k ++ " distinct issuer(s), " ++ toString q ++ " required"⟩]
  | .error (.axiomNotAllowed ax) => [⟨.proofNotVerified, "receipts", "axiom not allowed: " ++ ax⟩]

/-- Semantic diagnostics, as in v2. -/
def semanticDiagnostics (I : Interpretation) (C : Candidate) : SemanticStatus → List Diagnostic
  | .normalFormEqual | .certified _ => []
  | .counterexample _ => ⟨.semanticMismatch, "countermodel",
      "a verified finite countermodel distinguishes the candidate from the interpretation"⟩ ::
      structuralDiagnostics I C
  | .unknown _ => ⟨.semanticMismatch, "certificate",
      "no checked equivalence certificate and no countermodel within the search bounds"⟩ ::
      structuralDiagnostics I C

/-- The outcome, as a function of the four phases. -/
def classifyV3 (wf : Bool) (core : List Diagnostic) (sem : SemanticStatus)
    (rp : Except ReceiptFailure (List String)) : OutcomeV3 :=
  if !wf then .invalidAuthority
  else if core.any (fun d => d.code.isClarification) then .needsHumanClarification
  else if core.any (fun d => d.code == .unsupportedConstruct) then .unsupportedFragment
  else if !core.isEmpty then .invalidProposal
  else match sem with
    | .counterexample _ => .verifiedCounterexample
    | .unknown _ => .searchExhausted
    | _ => receiptOutcome rp

/-- The v3 decision as a function of the receipt-phase result. -/
def decideV3Core (A : AuthorityV3) (r : RequestV3) (rp : Except ReceiptFailure (List String)) :
    DecisionV3 :=
  let req := r.core.base
  let core := coreDiagnostics A.registry req ++ legacyDiagnostics req
  let sem := semanticAnalysis A.registry req.interpretation.selected req.candidate.claim
    r.core.certificate r.core.bounds
  let reached := A.wellFormedB && core.isEmpty && sem.linked
  let outcome := classifyV3 A.wellFormedB core sem rp
  { outcome := outcome,
    diagnostics := core ++ semanticDiagnostics req.interpretation req.candidate sem ++
      (if reached then receiptDiagnostics rp else []),
    semantic := sem,
    certificate := sem.cert r.core.certificate,
    receipts := if reached then some rp else none,
    consumed := if outcome = .certifiedTranslation then r.receipts.map (·.nonce) else [] }

/-- **The executable, state-aware v3 decision.** -/
def decideV3 (A : AuthorityV3) (now : Nat) (S : LedgerV3) (r : RequestV3) : DecisionV3 :=
  decideV3Core A r (receiptPhase A now S r)

/-- **The authority's state transition.** -/
def stepV3 (A : AuthorityV3) (now : Nat) (S : LedgerV3) (r : RequestV3) : DecisionV3 × LedgerV3 :=
  let d := decideV3 A now S r
  (d, { S with consumed := d.consumed ++ S.consumed })

/-! ## Specification -/

/-- **The certified v3 contract** (relative to the certificate in use). -/
structure CertifiedV3 (A : AuthorityV3) (now : Nat) (S : LedgerV3) (r : RequestV3)
    (cert : Option EquivCert) : Prop where
  authorityWellFormed : A.wellFormedB = true
  core : CoreGates A.registry r.core.base
  noLegacyReceipts : NoLegacyReceipts r.core.base
  semanticLink : SemanticallyLinked r.core.base.interpretation r.core.base.candidate cert
  receipts : ReceiptsValid A now S r

theorem classifyV3_certified {wf : Bool} {core : List Diagnostic} {sem : SemanticStatus}
    {rp : Except ReceiptFailure (List String)} (h : classifyV3 wf core sem rp = .certifiedTranslation) :
    wf = true ∧ core = [] ∧ sem.linked = true ∧ ∃ ns, rp = .ok ns := by
  unfold classifyV3 at h
  cases wf
  · simp at h
  simp only [Bool.not_true, Bool.false_eq_true, if_false] at h
  split at h
  · cases h
  split at h
  · cases h
  split at h
  · cases h
  rename_i hne
  have hcore : core = [] := by
    cases core
    · rfl
    · simp at hne
  refine ⟨rfl, hcore, ?_⟩
  split at h
  · cases h
  · cases h
  · rename_i hs1 hs2
    refine ⟨?_, ?_⟩
    · revert hs1 hs2
      cases sem <;> simp [SemanticStatus.linked]
    · unfold receiptOutcome at h
      split at h
      · exact ⟨_, rfl⟩
      all_goals cases h

theorem classifyV3_of {core : List Diagnostic} {sem : SemanticStatus} {ns : List String}
    (hcore : core = []) (hsem : sem.linked = true) :
    classifyV3 true core sem (.ok ns) = .certifiedTranslation := by
  subst hcore
  unfold classifyV3
  simp only [Bool.not_true, Bool.false_eq_true, if_false, List.any_nil, List.isEmpty_nil,
    Bool.not_true]
  revert hsem
  cases sem <;> simp [SemanticStatus.linked, receiptOutcome]

theorem decideV3_outcome (A : AuthorityV3) (now : Nat) (S : LedgerV3) (r : RequestV3) :
    (decideV3 A now S r).outcome = classifyV3 A.wellFormedB
      (coreDiagnostics A.registry r.core.base ++ legacyDiagnostics r.core.base)
      (semanticAnalysis A.registry r.core.base.interpretation.selected r.core.base.candidate.claim
        r.core.certificate r.core.bounds)
      (receiptPhase A now S r) := by
  simp only [decideV3, decideV3Core]

/-- Soundness of the v3 decision. -/
theorem decideV3_certified_sound {A : AuthorityV3} {now : Nat} {S : LedgerV3} {r : RequestV3}
    (h : (decideV3 A now S r).outcome = .certifiedTranslation) :
    CertifiedV3 A now S r (decideV3 A now S r).certificate := by
  rw [decideV3_outcome] at h
  obtain ⟨hwf, hcore, hsem, ns, hrp⟩ := classifyV3_certified h
  have hc := List.append_eq_nil_iff.mp hcore
  have hcert : (decideV3 A now S r).certificate = (semanticAnalysis A.registry
      r.core.base.interpretation.selected r.core.base.candidate.claim r.core.certificate
      r.core.bounds).cert r.core.certificate := by simp only [decideV3, decideV3Core]
  rw [hcert]
  exact ⟨hwf, (coreDiagnostics_nil _ _).mp hc.1, (legacyDiagnostics_nil _).mp hc.2,
    semanticAnalysis_linked rfl rfl hsem, receiptPhase_sound hrp⟩

theorem semanticAnalysis_linked_of {R : Registry} {iv : Interpretation} {cand : Candidate}
    {cert : Option EquivCert} {b : SearchBounds} (h : SemanticallyLinked iv cand cert) :
    (semanticAnalysis R iv.selected cand.claim cert b).linked = true := by
  unfold semanticAnalysis
  rcases h with hn | ⟨c, hc, hck⟩
  · rw [if_pos ((NClaim.equivB_iff _ _).mpr hn)]; rfl
  · split
    · rfl
    · rw [hc]; simp only; rw [if_pos hck]; rfl

/-- Completeness for the supplied certificate. -/
theorem decideV3_certified_complete {A : AuthorityV3} {now : Nat} {S : LedgerV3} {r : RequestV3}
    (h : CertifiedV3 A now S r r.core.certificate) :
    (decideV3 A now S r).outcome = .certifiedTranslation := by
  have hcore : coreDiagnostics A.registry r.core.base ++ legacyDiagnostics r.core.base = [] :=
    List.append_eq_nil_iff.mpr ⟨(coreDiagnostics_nil _ _).mpr h.core,
      (legacyDiagnostics_nil _).mpr h.noLegacyReceipts⟩
  have hsem := semanticAnalysis_linked_of (R := A.registry) (b := r.core.bounds) h.semanticLink
  have hrp := receiptPhase_complete h.receipts
  rw [decideV3_outcome, h.authorityWellFormed, hrp]
  exact classifyV3_of hcore hsem

/-- **`decideV3_certified_iff`** — exact executable/specification refinement of the stateful
    authority. -/
theorem decideV3_certified_iff (A : AuthorityV3) (now : Nat) (S : LedgerV3) (r : RequestV3) :
    (decideV3 A now S r).outcome = .certifiedTranslation ↔
      A.wellFormedB = true ∧ CoreGates A.registry r.core.base ∧ NoLegacyReceipts r.core.base ∧
      (semanticAnalysis A.registry r.core.base.interpretation.selected r.core.base.candidate.claim
        r.core.certificate r.core.bounds).linked = true ∧
      ReceiptsValid A now S r := by
  constructor
  · intro h
    rw [decideV3_outcome] at h
    obtain ⟨hwf, hcore, hsem, ns, hrp⟩ := classifyV3_certified h
    have hc := List.append_eq_nil_iff.mp hcore
    exact ⟨hwf, (coreDiagnostics_nil _ _).mp hc.1, (legacyDiagnostics_nil _).mp hc.2, hsem,
      receiptPhase_sound hrp⟩
  · rintro ⟨hwf, hc, hl, hsem, hv⟩
    have hcore : coreDiagnostics A.registry r.core.base ++ legacyDiagnostics r.core.base = [] :=
      List.append_eq_nil_iff.mpr ⟨(coreDiagnostics_nil _ _).mpr hc, (legacyDiagnostics_nil _).mpr hl⟩
    rw [decideV3_outcome, hwf, receiptPhase_complete hv]
    exact classifyV3_of hcore hsem

/-- Exact executable/specification refinement, stated with the v3 contract. -/
theorem stateful_authority_refines_specification (A : AuthorityV3) (now : Nat) (S : LedgerV3)
    (r : RequestV3) :
    ((decideV3 A now S r).outcome = .certifiedTranslation →
      CertifiedV3 A now S r (decideV3 A now S r).certificate) ∧
    (CertifiedV3 A now S r r.core.certificate →
      (decideV3 A now S r).outcome = .certifiedTranslation) :=
  ⟨decideV3_certified_sound, decideV3_certified_complete⟩

/-- **Semantic preservation of the v3 authority.** -/
theorem decideV3_certified_preserves_denotation {A : AuthorityV3} {now : Nat} {S : LedgerV3}
    {r : RequestV3} (h : (decideV3 A now S r).outcome = .certifiedTranslation) (M : Model)
    (ρ : String → M.Dom) :
    r.core.base.interpretation.selected.denote M ρ ↔ r.core.base.candidate.claim.denote M ρ := by
  rcases (decideV3_certified_sound h).semanticLink with hn | ⟨c, _, hc⟩
  · exact alphaEquiv_denote_iff hn M ρ
  · exact translation_certificate_sound hc M ρ

/-! ## State transitions -/

theorem decideV3_consumed (A : AuthorityV3) (now : Nat) (S : LedgerV3) (r : RequestV3) :
    (decideV3 A now S r).consumed =
      if (decideV3 A now S r).outcome = .certifiedTranslation then r.receipts.map (·.nonce) else [] := by
  simp only [decideV3, decideV3Core]

/-- **`stepV3_ledger`** — the ledger changes only on certification, and then exactly by the
    request's nonces; the revocation list and genesis are never changed by a decision. -/
theorem stepV3_ledger (A : AuthorityV3) (now : Nat) (S : LedgerV3) (r : RequestV3) :
    (stepV3 A now S r).1 = decideV3 A now S r ∧
    (stepV3 A now S r).2 =
      if (decideV3 A now S r).outcome = .certifiedTranslation then
        { S with consumed := r.receipts.map (·.nonce) ++ S.consumed }
      else S := by
  refine ⟨rfl, ?_⟩
  unfold stepV3
  simp only [decideV3_consumed]
  split <;> simp

/-- A non-certified request consumes nothing. -/
theorem stepV3_rejected_no_consumption {A : AuthorityV3} {now : Nat} {S : LedgerV3} {r : RequestV3}
    (h : (decideV3 A now S r).outcome ≠ .certifiedTranslation) : (stepV3 A now S r).2 = S := by
  rw [(stepV3_ledger A now S r).2, if_neg h]

/-- The consumed set only grows. -/
theorem stepV3_monotone (A : AuthorityV3) (now : Nat) (S : LedgerV3) (r : RequestV3) :
    ∀ n ∈ S.consumed, n ∈ (stepV3 A now S r).2.consumed := by
  intro n hn
  unfold stepV3
  exact List.mem_append_right _ hn

/-- **Replay rejection across transitions**: once a request is certified, no request presenting
    any of its nonces can be certified in the resulting state or in any later state whose consumed
    set contains it — whatever the clock, whatever the request. -/
theorem stepV3_replay_rejected {A : AuthorityV3} {now : Nat} {S : LedgerV3} {r : RequestV3}
    (h : (decideV3 A now S r).outcome = .certifiedTranslation) {T : LedgerV3}
    (hT : ∀ n ∈ (stepV3 A now S r).2.consumed, n ∈ T.consumed) (now' : Nat) {r' : RequestV3}
    {e' : ReceiptEnvelope} (he' : e' ∈ r'.receipts) (hn : e'.nonce ∈ r.receipts.map (·.nonce)) :
    (decideV3 A now' T r').outcome ≠ .certifiedTranslation := by
  intro h'
  have hv := (decideV3_certified_sound h').receipts.each e' he'
  apply hv.fresh
  apply hT
  rw [(stepV3_ledger A now S r).2, if_pos h]
  exact List.mem_append_left _ hn

/-- The certified decision's nonces are distinct and fresh. -/
theorem stepV3_consumed_nodup {A : AuthorityV3} {now : Nat} {S : LedgerV3} {r : RequestV3}
    (hS : S.consumed.Nodup) : (stepV3 A now S r).2.consumed.Nodup := by
  rw [(stepV3_ledger A now S r).2]
  split
  · rename_i h
    have hv := (decideV3_certified_sound h).receipts
    refine List.nodup_append.mpr ⟨hv.noncesDistinct, hS, ?_⟩
    intro a ha b hb hab
    obtain ⟨e, he, rfl⟩ := List.mem_map.mp ha
    exact (hv.each e he).fresh (hab ▸ hb)
  · exact hS

/-- Run the authority over a sequence of (clock, request) inputs. -/
def runV3 (A : AuthorityV3) : LedgerV3 → List (Nat × RequestV3) → List DecisionV3 × LedgerV3
  | S, [] => ([], S)
  | S, (now, r) :: rest =>
    let p := stepV3 A now S r
    let q := runV3 A p.2 rest
    (p.1 :: q.1, q.2)

/-- **`runV3_consumed_nodup`** — along any run of the authority, starting from a duplicate-free
    ledger, no nonce is ever consumed twice. -/
theorem runV3_consumed_nodup (A : AuthorityV3) :
    ∀ (S : LedgerV3) (xs : List (Nat × RequestV3)), S.consumed.Nodup → (runV3 A S xs).2.consumed.Nodup
  | _, [], h => h
  | _, (_, _) :: rest, h => runV3_consumed_nodup A _ rest (stepV3_consumed_nodup h)

/-- Every decision along a run consumes nonces that end up in the final ledger. -/
theorem runV3_consumed_mem (A : AuthorityV3) :
    ∀ (S : LedgerV3) (xs : List (Nat × RequestV3)),
      (∀ n ∈ S.consumed, n ∈ (runV3 A S xs).2.consumed) ∧
      ∀ d ∈ (runV3 A S xs).1, ∀ n ∈ d.consumed, n ∈ (runV3 A S xs).2.consumed
  | S, [] => ⟨fun _ h => h, fun _ h => by cases h⟩
  | S, (now, r) :: rest => by
    obtain ⟨ih1, ih2⟩ := runV3_consumed_mem A (stepV3 A now S r).2 rest
    refine ⟨fun n hn => ih1 n (stepV3_monotone A now S r n hn), ?_⟩
    intro d hd n hn
    rcases List.mem_cons.mp hd with rfl | hd
    · exact ih1 n (by unfold stepV3; exact List.mem_append_left _ hn)
    · exact ih2 d hd n hn

/-- The final ledger is the initial one extended by everything the decisions consumed. -/
theorem runV3_ledger (A : AuthorityV3) :
    ∀ (S : LedgerV3) (xs : List (Nat × RequestV3)),
      (runV3 A S xs).2.consumed = (runV3 A S xs).1.reverse.flatMap (·.consumed) ++ S.consumed
  | S, [] => by simp [runV3]
  | S, (now, r) :: rest => by
    have ih := runV3_ledger A (stepV3 A now S r).2 rest
    simp only [runV3, List.reverse_cons, List.flatMap_append, List.flatMap_cons, List.flatMap_nil,
      List.append_nil, List.append_assoc]
    rw [ih]
    simp [stepV3]

/-- **Distinct decisions along a run consume disjoint nonce sets** (no double spend). -/
theorem runV3_no_double_consumption (A : AuthorityV3) (S : LedgerV3) (xs : List (Nat × RequestV3))
    (hS : S.consumed.Nodup) :
    ((runV3 A S xs).1.reverse.flatMap (·.consumed)).Nodup := by
  have h := runV3_consumed_nodup A S xs hS
  rw [runV3_ledger] at h
  exact (List.nodup_append.mp h).1

end PCS.V2.Semantic.V3
