import PCS.V2.ReceiptThreatModelV3
import PCS.V2.TranslationV2Json

/-!
# PCS v3 — canonical wire format and the stateful executable front end

* Canonical JSON codecs (with proved decode∘encode round trips) for receipt envelopes,
  v3 requests (`pcs-semantic-translation-v3`), v3 authority configurations
  (`pcs-semantic-authority-v3`) and ledger snapshots (`pcs-receipt-ledger-state-v3`).
* `semanticCheckV3` — the pure function run by `pcs-semantic-check --v3`: strict canonical
  decoding of the three inputs, Ed25519 verification, the state-aware decision `stepV3`, and the
  ledger delta to be committed by the persistent store.

`semanticCheckV3` is **stateless as a function**: the ledger snapshot is an input and the new
snapshot an output.  Atomicity, durability and the uniqueness of nonces across processes are the
responsibility of the persistent store (`python/pcs_semantic/receipt_store.py`), which must run
check-and-consume inside one exclusive transaction.  `decideV3_restrict` proves that passing the
store's consumed nonces *restricted to the request's nonces* gives exactly the same decision as
passing the whole ledger.

Kernel-checked results: `decEnvelope_enc`, `decRequestV3_enc`, `decAuthorityConfigV3_enc`,
`decLedgerSnapshot_enc`, `semanticCheckV3_step`, `semanticCheckV3_encRequestV3`,
`semanticCheckV3_malformed_rejected`, `semanticCheckV3_certified_sound`,
`semanticCheckV3_ledger_delta`.
-/

set_option autoImplicit false

namespace PCS.V2.Semantic.V3

open PCS.V2.Json PCS.V2.Canonical PCS.V2.Semantic PCS.V2.Semantic.Ledger

/-! ## Envelopes -/

def decRole : String → Option ReceiptRole
  | "confirmation" => some .confirmation
  | "elaboration" => some .elaboration
  | "proof" => some .proof
  | _ => none

theorem decRole_name (r : ReceiptRole) : decRole r.name = some r := by cases r <;> rfl

def encEnvelope (e : ReceiptEnvelope) : JVal :=
  .obj [("expires_at", encNat e.expiresAt), ("issued_at", encNat e.issuedAt),
    ("issuer", .str e.issuer), ("nonce", .str e.nonce), ("role", .str e.role.name),
    ("signature", .str e.signature), ("statement", e.statement), ("version", .str e.version)]

def decEnvelope : JVal → Option ReceiptEnvelope
  | .obj [("expires_at", x), ("issued_at", i), ("issuer", .str k), ("nonce", .str n),
      ("role", .str ro), ("signature", .str sg), ("statement", st), ("version", .str v)] =>
    match decNat x, decNat i, decRole ro with
    | some x', some i', some ro' => some ⟨ro', v, st, n, i', x', k, sg⟩
    | _, _, _ => none
  | _ => none

theorem decEnvelope_enc (e : ReceiptEnvelope) : decEnvelope (encEnvelope e) = some e := by
  obtain ⟨ro, v, st, n, i, x, k, sg⟩ := e
  simp [encEnvelope, decEnvelope, decNat_encNat, decRole_name]

/-! ## Requests -/

def requestV3Schema : String := "pcs-semantic-translation-v3"

def encRequestV3 (r : RequestV3) : JVal :=
  .obj [("proof_axioms", encStrs r.proofAxioms), ("receipts", .arr (r.receipts.map encEnvelope)),
    ("request", encRequestV2 r.core), ("schema", .str requestV3Schema)]

def decRequestV3 : JVal → Option RequestV3
  | .obj [("proof_axioms", ax), ("receipts", .arr es), ("request", q),
      ("schema", .str "pcs-semantic-translation-v3")] =>
    match decStrs ax, decList decEnvelope es, decRequestV2 q with
    | some ax', some es', some q' => some ⟨q', ax', es'⟩
    | _, _, _ => none
  | _ => none

/-- **The v3 request decoder inverts the canonical encoder.** -/
theorem decRequestV3_enc (r : RequestV3) : decRequestV3 (encRequestV3 r) = some r := by
  obtain ⟨q, ax, es⟩ := r
  have h : decList decEnvelope (es.map encEnvelope) = some es :=
    decList_map decEnvelope encEnvelope es (fun e _ => decEnvelope_enc e)
  simp only [encRequestV3, requestV3Schema, decRequestV3, decStrs_encStrs, h,
    semantic_wire_roundtrip]

/-! ## Authority configuration -/

def encKeyEntry (k : KeyEntry) : JVal :=
  .obj [("key", .str k.key), ("not_after", encNat k.notAfter), ("not_before", encNat k.notBefore),
    ("role", .str k.role.name)]

def decKeyEntry : JVal → Option KeyEntry
  | .obj [("key", .str k), ("not_after", a), ("not_before", b), ("role", .str ro)] =>
    match decNat a, decNat b, decRole ro with
    | some a', some b', some ro' => some ⟨k, ro', b', a'⟩
    | _, _, _ => none
  | _ => none

theorem decKeyEntry_enc (k : KeyEntry) : decKeyEntry (encKeyEntry k) = some k := by
  obtain ⟨k, ro, b, a⟩ := k
  simp [encKeyEntry, decKeyEntry, decNat_encNat, decRole_name]

def encContextCfg (c : AuthorityContext) : JVal :=
  .obj [("env_fingerprint", .str c.envFingerprint), ("scope", .str c.scope),
    ("toolchain", .str c.toolchain)]

def decContextCfg : JVal → Option AuthorityContext
  | .obj [("env_fingerprint", .str f), ("scope", .str s), ("toolchain", .str t)] => some ⟨s, f, t⟩
  | _ => none

/-- The wire form of the v3 authority. -/
structure AuthorityConfigV3 where
  registry : Registry
  context : AuthorityContext
  keys : List KeyEntry
  revoked : List String
  allowedAxioms : List String
  requireElaboration : Bool
  requireProof : Bool
  confirmationQuorum : Nat
  elaborationQuorum : Nat
  proofQuorum : Nat
  deriving Repr, Inhabited

def authorityV3Schema : String := "pcs-semantic-authority-v3"

def encAuthorityConfigV3 (a : AuthorityConfigV3) : JVal :=
  .obj [("allowed_axioms", encStrs a.allowedAxioms), ("confirmation_quorum", encNat a.confirmationQuorum),
    ("context", encContextCfg a.context), ("elaboration_quorum", encNat a.elaborationQuorum),
    ("keys", .arr (a.keys.map encKeyEntry)), ("proof_quorum", encNat a.proofQuorum),
    ("registry", encRegistry a.registry), ("require_elaboration", .bool a.requireElaboration),
    ("require_proof", .bool a.requireProof), ("revoked", encStrs a.revoked),
    ("schema", .str authorityV3Schema)]

def decAuthorityConfigV3 : JVal → Option AuthorityConfigV3
  | .obj [("allowed_axioms", ax), ("confirmation_quorum", cq), ("context", ctx),
      ("elaboration_quorum", eq), ("keys", .arr ks), ("proof_quorum", pq), ("registry", reg),
      ("require_elaboration", .bool re), ("require_proof", .bool rp), ("revoked", rv),
      ("schema", .str "pcs-semantic-authority-v3")] =>
    match decStrs ax, decNat cq, decContextCfg ctx, decNat eq, decList decKeyEntry ks, decNat pq,
      decRegistry reg, decStrs rv with
    | some ax', some cq', some ctx', some eq', some ks', some pq', some reg', some rv' =>
      some ⟨reg', ctx', ks', rv', ax', re, rp, cq', eq', pq'⟩
    | _, _, _, _, _, _, _, _ => none
  | _ => none

theorem decRegistry_encRegistry (R : Registry) : decRegistry (encRegistry R) = some R := by
  obtain ⟨ss, ys⟩ := R
  have h1 : decList decSortEntry (ss.map encSortEntry) = some ss :=
    decList_map decSortEntry encSortEntry ss (fun e _ => by cases e; rfl)
  have h2 : decList decSymbolEntry (ys.map encSymbolEntry) = some ys :=
    decList_map decSymbolEntry encSymbolEntry ys (fun e _ => decSymbolEntry_enc e)
  simp [encRegistry, decRegistry, h1, h2]

theorem decAuthorityConfigV3_enc (a : AuthorityConfigV3) :
    decAuthorityConfigV3 (encAuthorityConfigV3 a) = some a := by
  obtain ⟨reg, ⟨s, f, t⟩, ks, rv, ax, re, rp, cq, eq, pq⟩ := a
  have h : decList decKeyEntry (ks.map encKeyEntry) = some ks :=
    decList_map decKeyEntry encKeyEntry ks (fun k _ => decKeyEntry_enc k)
  simp only [encAuthorityConfigV3, authorityV3Schema, decAuthorityConfigV3, decStrs_encStrs,
    decNat_encNat, encContextCfg, decContextCfg, h, decRegistry_encRegistry]

/-- Ed25519 signature check of a base64 key over a message (key *authorization* is decided
    separately, by role and validity window, in `activeKeys`). -/
def ed25519Verify (key : String) (msg : List UInt8) (sig : String) : Bool :=
  match PCS.V2.Base64.decode key.toList, PCS.V2.Base64.decode sig.toList with
  | some pk, some s => PCS.V2.Ed25519.verify pk msg s
  | _, _ => false

/-- The executable v3 authority induced by a configuration. -/
def AuthorityConfigV3.toAuthority (a : AuthorityConfigV3) : AuthorityV3 :=
  { registry := a.registry, context := a.context, keys := a.keys, revoked := a.revoked,
    allowedAxioms := a.allowedAxioms, requireElaboration := a.requireElaboration,
    requireProof := a.requireProof, confirmationQuorum := a.confirmationQuorum,
    elaborationQuorum := a.elaborationQuorum, proofQuorum := a.proofQuorum,
    verify := ed25519Verify }

/-! ## Ledger snapshots -/

/-- A ledger snapshot together with the trusted clock reading. -/
structure LedgerSnapshot where
  state : LedgerV3
  now : Nat
  deriving Repr, Inhabited

def encLedgerSnapshot (s : LedgerSnapshot) : JVal :=
  .obj [("consumed", encStrs s.state.consumed), ("genesis", encNat s.state.genesis),
    ("now", encNat s.now), ("revoked", encStrs s.state.revoked),
    ("schema", .str "pcs-receipt-ledger-state-v3")]

def decLedgerSnapshot : JVal → Option LedgerSnapshot
  | .obj [("consumed", c), ("genesis", g), ("now", n), ("revoked", rv),
      ("schema", .str "pcs-receipt-ledger-state-v3")] =>
    match decStrs c, decNat g, decNat n, decStrs rv with
    | some c', some g', some n', some rv' => some ⟨⟨c', rv', g'⟩, n'⟩
    | _, _, _, _ => none
  | _ => none

theorem decLedgerSnapshot_enc (s : LedgerSnapshot) : decLedgerSnapshot (encLedgerSnapshot s) = some s := by
  obtain ⟨⟨c, rv, g⟩, n⟩ := s
  simp [encLedgerSnapshot, decLedgerSnapshot, decStrs_encStrs, decNat_encNat]

/-! ## The front end -/

/-- What the v3 front end computes. -/
structure CliResultV3 where
  decision : DecisionV3
  /-- the snapshot after the transition (equal to the input snapshot unless certified) -/
  newState : Option LedgerV3
  explanation : Option ExplanationIR
  expectedLeanSource : String
  deriving Repr, Inhabited

def malformedDecisionV3 (component : String) : DecisionV3 :=
  ⟨.invalidProposal, [⟨.malformedInput, component, "input is not canonical JSON of the expected schema"⟩],
    .unknown .exhausted, none, none, []⟩

def malformedV3 (component : String) : CliResultV3 :=
  ⟨malformedDecisionV3 component, none, none, ""⟩

/-- Clamp the untrusted search bounds (denial-of-service protection only). -/
def RequestV3.clamp (r : RequestV3) : RequestV3 :=
  { r with core := { r.core with bounds := r.core.bounds.clamp } }

/-- **The pure v3 front end** run by `pcs-semantic-check --v3`. -/
def semanticCheckV3 (authorityRaw requestRaw stateRaw : ByteArray) : CliResultV3 :=
  match (parseCanonicalBytes maxInputBytes authorityRaw).bind decAuthorityConfigV3 with
  | none => malformedV3 "authority"
  | some cfg =>
    match (parseCanonicalBytes maxInputBytes stateRaw).bind decLedgerSnapshot with
    | none => malformedV3 "ledger_state"
    | some snap =>
      match (parseCanonicalBytes maxInputBytes requestRaw).bind decRequestV3 with
      | none => malformedV3 "request"
      | some r =>
        let A := cfg.toAuthority
        let p := stepV3 A snap.now snap.state r.clamp
        { decision := p.1,
          newState := some p.2,
          explanation := if p.1.outcome = .certifiedTranslation then
            some (toExplanation A.registry r.core.base.candidate.claim) else none,
          expectedLeanSource := renderClaimLean A.registry r.core.base.candidate.claim }

theorem semanticCheckV3_step {aRaw rRaw sRaw : ByteArray} {cfg : AuthorityConfigV3}
    {snap : LedgerSnapshot} {r : RequestV3}
    (ha : (parseCanonicalBytes maxInputBytes aRaw).bind decAuthorityConfigV3 = some cfg)
    (hs : (parseCanonicalBytes maxInputBytes sRaw).bind decLedgerSnapshot = some snap)
    (hr : (parseCanonicalBytes maxInputBytes rRaw).bind decRequestV3 = some r) :
    (semanticCheckV3 aRaw rRaw sRaw).decision = (stepV3 cfg.toAuthority snap.now snap.state r.clamp).1 ∧
    (semanticCheckV3 aRaw rRaw sRaw).newState = some (stepV3 cfg.toAuthority snap.now snap.state r.clamp).2 := by
  unfold semanticCheckV3; rw [ha, hs, hr]; exact ⟨rfl, rfl⟩

/-- On the canonical bytes of any v3 request the front end runs exactly `stepV3`. -/
theorem semanticCheckV3_encRequestV3 {aRaw sRaw : ByteArray} {cfg : AuthorityConfigV3}
    {snap : LedgerSnapshot} (r : RequestV3)
    (ha : (parseCanonicalBytes maxInputBytes aRaw).bind decAuthorityConfigV3 = some cfg)
    (hs : (parseCanonicalBytes maxInputBytes sRaw).bind decLedgerSnapshot = some snap)
    (hc : canonical (encRequestV3 r) = true) (hz : (jcsBytes (encRequestV3 r)).size ≤ maxInputBytes) :
    (semanticCheckV3 aRaw (jcsBytes (encRequestV3 r)) sRaw).decision =
      (stepV3 cfg.toAuthority snap.now snap.state r.clamp).1 := by
  refine (semanticCheckV3_step ha hs ?_).1
  rw [parseCanonicalBytes_complete hc hz]
  exact decRequestV3_enc r

/-- Undecodable input is never certified and yields no new ledger state. -/
theorem semanticCheckV3_malformed_rejected {aRaw rRaw sRaw : ByteArray}
    (h : (parseCanonicalBytes maxInputBytes rRaw).bind decRequestV3 = none ∨
      (parseCanonicalBytes maxInputBytes aRaw).bind decAuthorityConfigV3 = none ∨
      (parseCanonicalBytes maxInputBytes sRaw).bind decLedgerSnapshot = none) :
    (semanticCheckV3 aRaw rRaw sRaw).decision.outcome = .invalidProposal ∧
    (semanticCheckV3 aRaw rRaw sRaw).newState = none := by
  unfold semanticCheckV3
  rcases h with h | h | h
  · split
    · exact ⟨rfl, rfl⟩
    · split
      · exact ⟨rfl, rfl⟩
      · rw [h]; exact ⟨rfl, rfl⟩
  · rw [h]; exact ⟨rfl, rfl⟩
  · split
    · exact ⟨rfl, rfl⟩
    · rw [h]; exact ⟨rfl, rfl⟩

/-- **Wire-level soundness of the stateful authority**: a certified outcome on raw bytes means
    the three inputs decode, the request satisfies the full v3 contract against the decoded
    ledger snapshot and clock, and the returned ledger is the snapshot extended by exactly the
    request's nonces. -/
theorem semanticCheckV3_certified_sound {aRaw rRaw sRaw : ByteArray}
    (h : (semanticCheckV3 aRaw rRaw sRaw).decision.outcome = .certifiedTranslation) :
    ∃ cfg snap r, (parseCanonicalBytes maxInputBytes aRaw).bind decAuthorityConfigV3 = some cfg ∧
      (parseCanonicalBytes maxInputBytes sRaw).bind decLedgerSnapshot = some snap ∧
      (parseCanonicalBytes maxInputBytes rRaw).bind decRequestV3 = some r ∧
      (semanticCheckV3 aRaw rRaw sRaw).decision = decideV3 cfg.toAuthority snap.now snap.state r.clamp ∧
      CertifiedV3 cfg.toAuthority snap.now snap.state r.clamp
        (semanticCheckV3 aRaw rRaw sRaw).decision.certificate ∧
      (semanticCheckV3 aRaw rRaw sRaw).newState =
        some { snap.state with consumed := r.receipts.map (·.nonce) ++ snap.state.consumed } := by
  unfold semanticCheckV3 at h ⊢
  split at h
  · cases h
  · rename_i cfg hcfg
    split at h
    · cases h
    · rename_i snap hsnap
      split at h
      · cases h
      · rename_i r hr
        refine ⟨cfg, snap, r, hcfg, hsnap, hr, rfl, ?_, ?_⟩
        · exact decideV3_certified_sound h
        · have h' : (decideV3 cfg.toAuthority snap.now snap.state r.clamp).outcome =
              .certifiedTranslation := h
          show some (stepV3 cfg.toAuthority snap.now snap.state r.clamp).2 = _
          rw [(stepV3_ledger _ _ _ _).2, if_pos h']
          rfl

/-- The ledger delta reported by the front end: empty unless certified. -/
theorem semanticCheckV3_ledger_delta {aRaw rRaw sRaw : ByteArray}
    (h : (semanticCheckV3 aRaw rRaw sRaw).decision.outcome ≠ .certifiedTranslation) :
    (semanticCheckV3 aRaw rRaw sRaw).decision.consumed = [] := by
  unfold semanticCheckV3 at h ⊢
  split at h
  · rfl
  · rename_i cfg hcfg
    split at h
    · rfl
    · rename_i snap hsnap
      split at h
      · rfl
      · rename_i r hr
        have h' : (decideV3 cfg.toAuthority snap.now snap.state r.clamp).outcome ≠
            .certifiedTranslation := h
        show (decideV3 cfg.toAuthority snap.now snap.state r.clamp).consumed = []
        rw [decideV3_consumed, if_neg h']

/-! ## Output encoding -/

def encReceiptFailure : ReceiptFailure → JVal
  | .rejected n r => .obj [("kind", .str "REJECTED"), ("nonce", .str n), ("reason", .str (rejectReasonName r))]
  | .beforeGenesis n => .obj [("kind", .str "BEFORE_GENESIS"), ("nonce", .str n)]
  | .quorumNotMet ro k q => .obj [("distinct", encNat k), ("kind", .str "QUORUM_NOT_MET"),
      ("required", encNat q), ("role", .str ro.name)]
  | .axiomNotAllowed ax => .obj [("axiom", .str ax), ("kind", .str "AXIOM_NOT_ALLOWED")]

def encReceiptPhase : Option (Except ReceiptFailure (List String)) → JVal
  | none => .obj [("status", .str "NOT_REACHED")]
  | some (.ok ns) => .obj [("nonces", encStrs ns), ("status", .str "VALID")]
  | some (.error f) => .obj [("failure", encReceiptFailure f), ("status", .str "INVALID")]

def encCliResultV3 (res : CliResultV3) : JVal :=
  .obj [
    ("certificate", encOpt encCert res.decision.certificate),
    ("consumed_nonces", encStrs res.decision.consumed),
    ("diagnostics", .arr (res.decision.diagnostics.map encDiagnostic)),
    ("expected_lean_source", .str res.expectedLeanSource),
    ("explanation", encOpt encExplanation res.explanation),
    ("new_ledger_consumed", match res.newState with
      | some s => encStrs s.consumed
      | none => .null),
    ("outcome", .str res.decision.outcome.name),
    ("receipt_phase", encReceiptPhase res.decision.receipts),
    ("schema", .str "pcs-semantic-decision-v3"),
    ("semantic_status", encSemanticStatus res.decision.semantic)]

end PCS.V2.Semantic.V3
