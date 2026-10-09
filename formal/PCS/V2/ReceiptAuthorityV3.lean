import PCS.V2.TranslationV2
import PCS.V2.ReceiptLedger
import PCS.V2.LeanSyntaxV3

/-!
# PCS Proof-Carrying Semantic Intelligence v3 — stateful receipt authority

v2 proved properties of the replay-protecting receipt protocol (`PCS.V2.Semantic.Ledger`) but the
semantic decision procedure `decideV2` still validated **stateless** v1 receipts.  This file puts
the receipt-envelope protocol on the acceptance path itself.

* `AuthorityV3` — approved registry, an explicit **authority context** (scope, exact Lean
  environment fingerprint, toolchain), role-tagged keys with validity windows (rotation), a static
  revocation list, axiom policy, and per-role **quorums** of distinct issuers.
* `LedgerV3` — the authority's mutable state: consumed nonces of the scope, dynamically revoked
  keys, and the ledger **genesis** time (receipts issued before it are rejected, so a ledger reset
  cannot re-open old receipts under a monotone clock).
* `RequestV3` — a v2 request whose legacy stateless receipt fields must be empty, the axiom list
  claimed by the proof receipts, and a list of `ReceiptEnvelope`s.
* `expectedStatement` — the exact canonical statement each receipt role must attest: confirmation
  of the exact interpretation; elaboration of the exact Lean source / declaration; a
  **kernel-check record** (checker, axioms, source, declaration).  Each statement embeds the full
  authority context including the registry, so a receipt cannot be reused across scopes,
  environments, toolchains or registries.
* `decideV3` / `stepV3` — the executable, **state-aware** decision: v2's core gates and semantic
  analysis, then fail-closed validation of every envelope (`acceptEnvelope`, reused verbatim from
  the v2 ledger specification), quorum counting, and — only on `CERTIFIED_TRANSLATION` — atomic
  consumption of all nonces.  A rejected request consumes nothing.

Main theorems (all kernel-checked):

* `receiptPhase_ok_iff` — the executable receipt phase succeeds exactly when the declarative
  `ReceiptsValid` specification holds (and returns precisely the request's nonces).
* `decideV3_certified_iff` — `CERTIFIED_TRANSLATION` **iff** `CertifiedV3` (authority
  well-formed, core gates, no legacy receipt, semantic link, `ReceiptsValid`).
* `stepV3_ledger` — the state transition: certified ⇒ nonces appended; otherwise unchanged.
* `stepV3_replay_rejected`, `runV3_consumed_nodup` — no nonce is ever consumed twice along any
  run of the authority, and a certified receipt can never certify again in any later state.
* `decideV3_consumed_congr` — the decision depends on the consumed set only through membership of
  the request's own nonces (justifies the persistent store's atomic check-and-consume).
* `role_substitution_rejected`, `cross_context_receipt_rejected`, `legacy_receipt_rejected`, …
* `certified_receipt_quorum_assurance` — under an explicit **honest-key** model (a key is honest
  iff every envelope verifying under it asserts a true fact; a malicious signer or compromised key
  is simply a dishonest key), a certified decision implies each required attested fact holds unless
  at least `quorum` distinct authorized keys of that role are all dishonest.

**A signature is not a kernel check.**  The proof receipt's statement is a *record* asserting that
a named checker ran the Lean kernel in the fingerprinted environment; its truth is the world fact
`W.Holds .proof stmt`, which PCS obtains only from the honest-key / quorum hypothesis, never from a
signature alone.
-/

set_option autoImplicit false

namespace PCS.V2.Semantic.V3

open PCS.V2.Json PCS.V2.Semantic PCS.V2.Semantic.Ledger

/-! ## Core (receipt-free) gates -/

/-- v3's additional anti-capture gate on the generated Lean syntax
    (`PCS.V2.Semantic.LeanSyntax.leanSyntaxSafeB`). -/
def checkLeanSyntax (R : Registry) (c : Candidate) : List Diagnostic :=
  failIf (LeanSyntax.leanSyntaxSafeB R c.claim) ⟨.binderShadowing, "candidate.lean_syntax",
    "a binder is not a plain identifier, is a keyword, or could capture a registry name, type, " ++
    "name component or True/False in the generated Lean text; or a registry name is not a " ++
    "dotted identifier; or a symbol/sort does not resolve"⟩

/-- All non-receipt, non-semantic gates of v2 (the receipt gates are replaced by envelopes),
    plus v3's Lean-syntax safety gate. -/
def coreDiagnostics (R : Registry) (req : Request) : List Diagnostic :=
  let I := req.interpretation
  let c := req.candidate
  checkAmbiguity I ++ checkRegistry R ++
  checkInterpretationSymbols R I ++ checkCandidateSymbols R c ++ checkGroundingRefs R c ++
  checkTyping R I c ++ checkSupported I c ++ checkFreeVars I c ++ checkHygiene R c ++
  checkExplanationV2 R c ++ checkLeanRendering R c ++ checkLeanSyntax R c

/-- The core gates as a specification. -/
structure CoreGates (R : Registry) (req : Request) : Prop where
  noUnresolvedAmbiguity : NoUnresolvedAmbiguity req.interpretation
  interpretationGrounded : InterpretationGrounded R req.interpretation
  groundedSymbols : GroundedSymbols R req.candidate
  wellTyped : WellTypedPair R req.interpretation req.candidate
  supportedFragment : SupportedFragment req.interpretation req.candidate
  noUnexpectedFreeVariables : NoUnexpectedFreeVariables req.interpretation req.candidate
  hygienic : req.candidate.claim.hygienicB R = true
  explanationFaithful : ExplanationFaithful R req.candidate
  leanRendering : LeanRenderingFaithful R req.candidate
  leanSyntaxSafe : LeanSyntax.leanSyntaxSafeB R req.candidate.claim = true

theorem coreDiagnostics_nil (R : Registry) (req : Request) :
    coreDiagnostics R req = [] ↔ CoreGates R req := by
  unfold coreDiagnostics
  simp only [List.append_eq_nil_iff, checkAmbiguity_nil, checkRegistry_nil,
    checkInterpretationSymbols_nil, checkCandidateSymbols_nil, checkGroundingRefs_nil,
    checkTyping_nil, checkSupported_nil, checkFreeVars_nil, checkExplanationV2_nil,
    checkHygiene, checkLeanRendering, checkLeanSyntax, failIf_nil, decide_eq_true_eq, and_assoc]
  constructor
  · rintro ⟨h1, h3, h4, h5, h6, h7, h8, h9, h10, h11, h12, h13⟩
    exact ⟨h1, h4, ⟨h3, h5, h6⟩, h7, h8, h9, h10, h11, h12, h13⟩
  · rintro ⟨h1, h4, ⟨h3, h5, h6⟩, h7, h8, h9, h10, h11, h12, h13⟩
    exact ⟨h1, h3, h4, h5, h6, h7, h8, h9, h10, h11, h12, h13⟩

/-! ## Authority, keys, context, ledger -/

/-- A role-tagged verification key with a validity window `[notBefore, notAfter)` (rotation). -/
structure KeyEntry where
  key : String
  role : ReceiptRole
  notBefore : Nat
  notAfter : Nat
  deriving Repr, DecidableEq, Inhabited

/-- Authority context bound into every receipt statement. -/
structure AuthorityContext where
  /-- the authority scope: the domain within which nonces are unique -/
  scope : String
  /-- fingerprint of the exact Lean environment (modules and registry constants) -/
  envFingerprint : String
  /-- the pinned Lean toolchain -/
  toolchain : String
  deriving Repr, DecidableEq, Inhabited

/-- The trusted v3 authority configuration. -/
structure AuthorityV3 where
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
  /-- signature verifier (Ed25519 in the executable) -/
  verify : String → List UInt8 → String → Bool

/-- Role separation of keys (no key is registered for two roles) and a non-empty scope. -/
def AuthorityV3.wellFormedB (A : AuthorityV3) : Bool :=
  A.keys.all (fun k => A.keys.all (fun k' => k.key != k'.key || k.role == k'.role)) &&
    A.context.scope != ""

/-- Effective number of distinct issuers required per role.  Confirmation is always required. -/
def AuthorityV3.quorum (A : AuthorityV3) : ReceiptRole → Nat
  | .confirmation => max 1 A.confirmationQuorum
  | .elaboration => if A.requireElaboration then max 1 A.elaborationQuorum else 0
  | .proof => if A.requireProof then max 1 A.proofQuorum else 0

/-- The authority's mutable state. -/
structure LedgerV3 where
  /-- nonces consumed within the authority scope -/
  consumed : List String
  /-- keys revoked at run time (in addition to the configuration's list) -/
  revoked : List String
  /-- ledger epoch start: receipts issued before it are rejected -/
  genesis : Nat
  deriving Repr, DecidableEq, Inhabited

/-- Keys of a role that are active at time `now`. -/
def activeKeys (A : AuthorityV3) (now : Nat) (role : ReceiptRole) : List String :=
  (A.keys.filter (fun k => k.role == role && decide (k.notBefore ≤ now) && decide (now < k.notAfter))).map
    (·.key)

/-- The v2 ledger policy induced by the authority, its state and the trusted clock. -/
def policy (A : AuthorityV3) (S : LedgerV3) (now : Nat) : LedgerPolicy :=
  { keys := activeKeys A now, revoked := A.revoked ++ S.revoked, now := now, verify := A.verify }

/-! ## Requests and expected statements -/

/-- A v3 request. -/
structure RequestV3 where
  /-- the v2 request (legacy stateless receipt fields must be `none`) -/
  core : RequestV2
  /-- axioms the proof receipts claim the kernel-checked proof depends on -/
  proofAxioms : List String
  /-- receipt envelopes (any order) -/
  receipts : List ReceiptEnvelope
  deriving Repr, Inhabited

def encContext (A : AuthorityV3) : JVal :=
  .obj [("env_fingerprint", .str A.context.envFingerprint), ("registry", encRegistry A.registry),
    ("scope", .str A.context.scope), ("toolchain", .str A.context.toolchain)]

/-- Name of the external kernel-checking operation a proof receipt attests. -/
def kernelCheckerId : String := "lean4-kernel-check"

/-- What a confirmation receipt must attest: the exact interpretation, in this context. -/
def confirmationStatement (A : AuthorityV3) (I : Interpretation) : JVal :=
  .obj [("ambiguities", encAmbiguities I.ambiguities), ("context", encContext A),
    ("purpose", .str "confirmation"), ("selected", encClaim I.selected),
    ("source_text", .str I.sourceText)]

/-- What an elaboration receipt must attest. -/
def elaborationStatement (A : AuthorityV3) (c : Candidate) : JVal :=
  .obj [("context", encContext A), ("decl_name", .str c.declName),
    ("lean_source", .str c.leanSource), ("purpose", .str "elaboration")]

/-- What a proof receipt must attest: a **kernel-check record**. -/
def proofStatement (A : AuthorityV3) (c : Candidate) (axs : List String) : JVal :=
  .obj [("axioms", encStrs axs), ("checker", .str kernelCheckerId), ("context", encContext A),
    ("decl_name", .str c.declName), ("lean_source", .str c.leanSource),
    ("purpose", .str "kernel-proof-check")]

/-- The exact statement expected for each role. -/
def expectedStatement (A : AuthorityV3) (r : RequestV3) : ReceiptRole → JVal
  | .confirmation => confirmationStatement A r.core.base.interpretation
  | .elaboration => elaborationStatement A r.core.base.candidate
  | .proof => proofStatement A r.core.base.candidate r.proofAxioms

/-! ## Distinct issuers -/

/-- Order-preserving duplicate removal (first occurrence kept). -/
def dedup : List String → List String
  | [] => []
  | x :: xs => if (dedup xs).contains x then dedup xs else x :: dedup xs

theorem mem_dedup {x : String} : ∀ {l : List String}, x ∈ dedup l ↔ x ∈ l
  | [] => by simp [dedup]
  | y :: ys => by
    unfold dedup
    split
    · rename_i h
      rw [mem_dedup]
      constructor
      · intro hx; exact List.mem_cons_of_mem _ hx
      · intro hx
        rcases List.mem_cons.mp hx with rfl | hx
        · exact mem_dedup.mp (List.contains_iff_mem.mp h)
        · exact hx
    · simp [mem_dedup]

theorem dedup_nodup : ∀ (l : List String), (dedup l).Nodup
  | [] => by simp [dedup]
  | y :: ys => by
    unfold dedup
    split
    · exact dedup_nodup ys
    · rename_i h
      refine List.nodup_cons.mpr ⟨fun hm => h (List.contains_iff_mem.mpr hm), dedup_nodup ys⟩

/-- Distinct issuers of the envelopes of a role. -/
def issuersOf (role : ReceiptRole) (es : List ReceiptEnvelope) : List String :=
  dedup ((es.filter (fun e => e.role == role)).map (·.issuer))

theorem mem_issuersOf {role : ReceiptRole} {es : List ReceiptEnvelope} {k : String} :
    k ∈ issuersOf role es ↔ ∃ e ∈ es, e.role = role ∧ e.issuer = k := by
  unfold issuersOf
  rw [mem_dedup]
  simp [and_assoc]

/-! ## The executable receipt phase -/

/-- Why receipt validation failed. -/
inductive ReceiptFailure where
  | rejected (nonce : String) (reason : RejectReason)
  | beforeGenesis (nonce : String)
  | quorumNotMet (role : ReceiptRole) (distinct : Nat) (required : Nat)
  | axiomNotAllowed (ax : String)
  deriving Repr, DecidableEq, Inhabited

/-- Validate and (tentatively) consume all envelopes, in order, against the v2 acceptance
    function.  Each envelope is checked against the statement expected for **its own role**,
    with keys of that role only.  Returns the consumed nonces. -/
def acceptAllV3 (P : LedgerPolicy) (stmt : ReceiptRole → JVal) (genesis : Nat) :
    LedgerState → List ReceiptEnvelope → Except ReceiptFailure (List String)
  | _, [] => .ok []
  | L, e :: es =>
    if e.issuedAt < genesis then .error (.beforeGenesis e.nonce)
    else match acceptEnvelope P L e.role (stmt e.role) e with
      | .error r => .error (.rejected e.nonce r)
      | .ok L' => (acceptAllV3 P stmt genesis L' es).map (e.nonce :: ·)

/-- First role (in a fixed order) whose quorum is not met. -/
def quorumFailure (A : AuthorityV3) (es : List ReceiptEnvelope) : Option ReceiptFailure :=
  [ReceiptRole.confirmation, .elaboration, .proof].findSome? (fun role =>
    if A.quorum role ≤ (issuersOf role es).length then none
    else some (.quorumNotMet role (issuersOf role es).length (A.quorum role)))

/-- **The executable receipt phase.** -/
def receiptPhase (A : AuthorityV3) (now : Nat) (S : LedgerV3) (r : RequestV3) :
    Except ReceiptFailure (List String) :=
  match r.proofAxioms.find? (fun ax => !A.allowedAxioms.contains ax) with
  | some ax => .error (.axiomNotAllowed ax)
  | none =>
    match acceptAllV3 (policy A S now) (expectedStatement A r) S.genesis ⟨S.consumed⟩ r.receipts with
    | .error f => .error f
    | .ok ns =>
      match quorumFailure A r.receipts with
      | some f => .error f
      | none => .ok ns

/-! ## Declarative receipt specification -/

/-- Everything an individual envelope must satisfy. -/
structure EnvelopeValid (A : AuthorityV3) (now : Nat) (S : LedgerV3) (r : RequestV3)
    (e : ReceiptEnvelope) : Prop where
  version : e.version = protocolVersion
  activeKey : e.issuer ∈ activeKeys A now e.role
  notRevoked : e.issuer ∉ A.revoked ++ S.revoked
  statement : e.statement = expectedStatement A r e.role
  issuedBeforeNow : e.issuedAt ≤ now
  notExpired : now < e.expiresAt
  afterGenesis : S.genesis ≤ e.issuedAt
  fresh : e.nonce ∉ S.consumed
  signature : A.verify e.issuer (envelopeBytes e) e.signature = true

/-- **Receipt specification.** -/
structure ReceiptsValid (A : AuthorityV3) (now : Nat) (S : LedgerV3) (r : RequestV3) : Prop where
  axiomsAllowed : ∀ ax ∈ r.proofAxioms, ax ∈ A.allowedAxioms
  each : ∀ e ∈ r.receipts, EnvelopeValid A now S r e
  noncesDistinct : (r.receipts.map (·.nonce)).Nodup
  quorum : ∀ role, A.quorum role ≤ (issuersOf role r.receipts).length

/-! ### Exact characterisation of `acceptEnvelope` -/

/-- The state-independent conditions of `acceptEnvelope`. -/
structure EnvOK (P : LedgerPolicy) (role : ReceiptRole) (stmt : JVal) (e : ReceiptEnvelope) : Prop where
  version : e.version = protocolVersion
  roleEq : e.role = role
  key : e.issuer ∈ P.keys role
  notRevoked : e.issuer ∉ P.revoked
  statement : e.statement = stmt
  window : e.issuedAt ≤ P.now ∧ P.now < e.expiresAt
  signature : P.verify e.issuer (envelopeBytes e) e.signature = true

theorem acceptEnvelope_ok_iff {P : LedgerPolicy} {L L' : LedgerState} {role : ReceiptRole}
    {stmt : JVal} {e : ReceiptEnvelope} :
    acceptEnvelope P L role stmt e = .ok L' ↔
      EnvOK P role stmt e ∧ e.nonce ∉ L.seenNonces ∧ L' = ⟨e.nonce :: L.seenNonces⟩ := by
  constructor
  · intro h
    obtain ⟨h1, h2, h3, h4, h5, h6, h7, h8, h9, h10⟩ := acceptEnvelope_sound h
    exact ⟨⟨h1, h2, h3, h4, h5, ⟨h6, h7⟩, h9⟩, h8, h10⟩
  · rintro ⟨⟨h1, h2, h3, h4, h5, ⟨h6, h7⟩, h9⟩, h8, rfl⟩
    unfold acceptEnvelope
    have c3 : (P.keys role).contains e.issuer = true := List.contains_iff_mem.mpr h3
    have c4 : P.revoked.contains e.issuer = false := by
      cases hc : P.revoked.contains e.issuer
      · rfl
      · exact absurd (List.contains_iff_mem.mp hc) h4
    have c7 : L.seenNonces.contains e.nonce = false := by
      cases hc : L.seenNonces.contains e.nonce
      · rfl
      · exact absurd (List.contains_iff_mem.mp hc) h8
    simp [h1, h2, h3, h4, h5, h6, h7, h8, h9]

/-- The error (if any) of `acceptEnvelope` depends on the ledger only through the freshness of
    the envelope's own nonce. -/
theorem acceptEnvelope_error_congr {P : LedgerPolicy} {L₁ L₂ : LedgerState} {role : ReceiptRole}
    {stmt : JVal} {e : ReceiptEnvelope}
    (h : e.nonce ∈ L₁.seenNonces ↔ e.nonce ∈ L₂.seenNonces) (r : RejectReason) :
    acceptEnvelope P L₁ role stmt e = .error r ↔ acceptEnvelope P L₂ role stmt e = .error r := by
  have hc : L₁.seenNonces.contains e.nonce = L₂.seenNonces.contains e.nonce := by
    cases h1 : L₁.seenNonces.contains e.nonce <;> cases h2 : L₂.seenNonces.contains e.nonce
    · rfl
    · exact absurd (h.mpr (List.contains_iff_mem.mp h2))
        (fun hm => by rw [List.contains_iff_mem.mpr hm] at h1; cases h1)
    · exact absurd (h.mp (List.contains_iff_mem.mp h1))
        (fun hm => by rw [List.contains_iff_mem.mpr hm] at h2; cases h2)
    · rfl
  unfold acceptEnvelope
  rw [hc]
  constructor <;> intro hh <;> revert hh <;> (repeat' split) <;> simp_all

/-! ### `acceptAllV3` -/

theorem acceptAllV3_ok_iff {P : LedgerPolicy} {stmt : ReceiptRole → JVal} {g : Nat} :
    ∀ {L : LedgerState} {es : List ReceiptEnvelope} {ns : List String},
    acceptAllV3 P stmt g L es = .ok ns ↔
      (∀ e ∈ es, g ≤ e.issuedAt ∧ EnvOK P e.role (stmt e.role) e ∧ e.nonce ∉ L.seenNonces) ∧
      (es.map (·.nonce)).Nodup ∧ ns = es.map (·.nonce)
  | L, [], ns => by
    simp only [acceptAllV3, List.not_mem_nil, false_implies, implies_true, List.map_nil,
      List.nodup_nil, true_and]
    constructor
    · intro h; cases h; rfl
    · intro h; subst h; rfl
  | L, e :: es, ns => by
    unfold acceptAllV3
    by_cases hg : e.issuedAt < g
    · rw [if_pos hg]
      constructor
      · intro h; cases h
      · rintro ⟨h, -, -⟩
        have := (h e List.mem_cons_self).1
        omega
    · rw [if_neg hg]
      cases hacc : acceptEnvelope P L e.role (stmt e.role) e with
      | error r =>
        simp only
        constructor
        · intro h; cases h
        · rintro ⟨h, -, -⟩
          obtain ⟨-, hok, hfr⟩ := h e List.mem_cons_self
          have := acceptEnvelope_ok_iff.mpr ⟨hok, hfr, rfl⟩
          rw [hacc] at this; cases this
      | ok L' =>
        obtain ⟨hok, hfr, rfl⟩ := acceptEnvelope_ok_iff.mp hacc
        simp only
        cases hrest : acceptAllV3 P stmt g ⟨e.nonce :: L.seenNonces⟩ es with
        | error f =>
          simp only [Except.map]
          constructor
          · intro h; cases h
          · rintro ⟨h, hnd, -⟩
            have hr : acceptAllV3 P stmt g ⟨e.nonce :: L.seenNonces⟩ es = .ok (es.map (·.nonce)) := by
              apply acceptAllV3_ok_iff.mpr
              refine ⟨fun e' he' => ?_, (List.nodup_cons.mp hnd).2, rfl⟩
              obtain ⟨h1, h2, h3⟩ := h e' (List.mem_cons_of_mem _ he')
              refine ⟨h1, h2, fun hm => ?_⟩
              rcases List.mem_cons.mp hm with heq | hm
              · exact (List.nodup_cons.mp hnd).1 (by show e.nonce ∈ _; rw [← heq]; exact List.mem_map_of_mem (f := (·.nonce)) he')
              · exact h3 hm
            rw [hrest] at hr; cases hr
        | ok ns' =>
          have ih := (acceptAllV3_ok_iff (L := ⟨e.nonce :: L.seenNonces⟩) (es := es) (ns := ns')).mp hrest
          obtain ⟨hall, hnd, hns⟩ := ih
          simp only [Except.map, Except.ok.injEq]
          constructor
          · intro h
            subst h hns
            refine ⟨fun e' he' => ?_, ?_, rfl⟩
            · rcases List.mem_cons.mp he' with rfl | he'
              · exact ⟨by omega, hok, hfr⟩
              · obtain ⟨h1, h2, h3⟩ := hall e' he'
                exact ⟨h1, h2, fun hm => h3 (List.mem_cons_of_mem _ hm)⟩
            · refine List.nodup_cons.mpr ⟨fun hm => ?_, hnd⟩
              obtain ⟨e', he', heq⟩ := List.mem_map.mp hm
              exact (hall e' he').2.2 (heq ▸ List.mem_cons_self)
          · rintro ⟨-, -, h⟩
            rw [h, hns]; rfl

/-- `acceptAllV3` depends on the ledger only through membership of the envelopes' nonces. -/
theorem acceptAllV3_congr {P : LedgerPolicy} {stmt : ReceiptRole → JVal} {g : Nat} :
    ∀ {L₁ L₂ : LedgerState} {es : List ReceiptEnvelope},
    (∀ n ∈ es.map (·.nonce), n ∈ L₁.seenNonces ↔ n ∈ L₂.seenNonces) →
    acceptAllV3 P stmt g L₁ es = acceptAllV3 P stmt g L₂ es
  | _, _, [], _ => rfl
  | L₁, L₂, e :: es, h => by
    unfold acceptAllV3
    split
    · rfl
    · have he : e.nonce ∈ L₁.seenNonces ↔ e.nonce ∈ L₂.seenNonces := h _ List.mem_cons_self
      cases h1 : acceptEnvelope P L₁ e.role (stmt e.role) e with
      | error r =>
        have h2 := (acceptEnvelope_error_congr he r).mp h1
        rw [h2]
      | ok L₁' =>
        cases h2 : acceptEnvelope P L₂ e.role (stmt e.role) e with
        | error r =>
          have := (acceptEnvelope_error_congr he r).mpr h2
          rw [h1] at this; cases this
        | ok L₂' =>
          obtain ⟨-, -, rfl⟩ := acceptEnvelope_ok_iff.mp h1
          obtain ⟨-, -, rfl⟩ := acceptEnvelope_ok_iff.mp h2
          simp only
          rw [acceptAllV3_congr (L₁ := ⟨e.nonce :: L₁.seenNonces⟩) (L₂ := ⟨e.nonce :: L₂.seenNonces⟩)]
          intro n hn
          simp only [List.mem_cons]
          exact or_congr Iff.rfl (h n (List.mem_cons_of_mem _ hn))

/-! ### Quorum -/

theorem quorumFailure_none_iff (A : AuthorityV3) (es : List ReceiptEnvelope) :
    quorumFailure A es = none ↔ ∀ role, A.quorum role ≤ (issuersOf role es).length := by
  unfold quorumFailure
  simp only [List.findSome?_eq_none_iff, List.mem_cons, List.mem_nil_iff, or_false]
  constructor
  · intro h role
    have := h role (by cases role <;> simp)
    by_cases hc : A.quorum role ≤ (issuersOf role es).length
    · exact hc
    · rw [if_neg hc] at this; cases this
  · intro h role _
    rw [if_pos (h role)]

/-! ### Exact refinement of the receipt phase -/

theorem receiptPhase_ok_iff (A : AuthorityV3) (now : Nat) (S : LedgerV3) (r : RequestV3)
    (ns : List String) :
    receiptPhase A now S r = .ok ns ↔ ReceiptsValid A now S r ∧ ns = r.receipts.map (·.nonce) := by
  unfold receiptPhase
  cases hax : r.proofAxioms.find? (fun ax => !A.allowedAxioms.contains ax) with
  | some ax =>
    simp only
    constructor
    · intro h; cases h
    · rintro ⟨hv, -⟩
      have hm := List.mem_of_find?_eq_some hax
      have hp := List.find?_some hax
      have := hv.axiomsAllowed ax hm
      rw [List.contains_iff_mem.mpr this] at hp; cases hp
  | none =>
    have hax' : ∀ ax ∈ r.proofAxioms, ax ∈ A.allowedAxioms := by
      intro ax hm
      have := List.find?_eq_none.mp hax ax hm
      simp only [Bool.not_eq_eq_eq_not, Bool.not_true, Bool.not_eq_false] at this
      exact List.contains_iff_mem.mp (by simpa using this)
    simp only
    cases hacc : acceptAllV3 (policy A S now) (expectedStatement A r) S.genesis ⟨S.consumed⟩ r.receipts with
    | error f =>
      simp only
      constructor
      · intro h; cases h
      · rintro ⟨hv, -⟩
        have : acceptAllV3 (policy A S now) (expectedStatement A r) S.genesis ⟨S.consumed⟩ r.receipts =
            .ok (r.receipts.map (·.nonce)) := by
          apply acceptAllV3_ok_iff.mpr
          refine ⟨fun e he => ?_, hv.noncesDistinct, rfl⟩
          have v := hv.each e he
          exact ⟨v.afterGenesis, ⟨v.version, rfl, v.activeKey, v.notRevoked, v.statement,
            ⟨v.issuedBeforeNow, v.notExpired⟩, v.signature⟩, v.fresh⟩
        rw [hacc] at this; cases this
    | ok ns' =>
      obtain ⟨hall, hnd, hns⟩ := acceptAllV3_ok_iff.mp hacc
      simp only
      cases hq : quorumFailure A r.receipts with
      | some f =>
        simp only
        constructor
        · intro h; cases h
        · rintro ⟨hv, -⟩
          have := (quorumFailure_none_iff A r.receipts).mpr hv.quorum
          rw [hq] at this; cases this
      | none =>
        simp only [Except.ok.injEq]
        have hquo := (quorumFailure_none_iff A r.receipts).mp hq
        constructor
        · intro h
          subst h
          refine ⟨⟨hax', fun e he => ?_, hnd, hquo⟩, hns⟩
          obtain ⟨hg, hok, hfr⟩ := hall e he
          exact ⟨hok.version, hok.key, hok.notRevoked, hok.statement, hok.window.1, hok.window.2,
            hg, hfr, hok.signature⟩
        · rintro ⟨-, h⟩
          rw [h, hns]

theorem receiptPhase_ok_nonces {A : AuthorityV3} {now : Nat} {S : LedgerV3} {r : RequestV3}
    {ns : List String} (h : receiptPhase A now S r = .ok ns) : ns = r.receipts.map (·.nonce) :=
  ((receiptPhase_ok_iff A now S r ns).mp h).2

theorem receiptPhase_sound {A : AuthorityV3} {now : Nat} {S : LedgerV3} {r : RequestV3}
    {ns : List String} (h : receiptPhase A now S r = .ok ns) : ReceiptsValid A now S r :=
  ((receiptPhase_ok_iff A now S r ns).mp h).1

theorem receiptPhase_complete {A : AuthorityV3} {now : Nat} {S : LedgerV3} {r : RequestV3}
    (h : ReceiptsValid A now S r) : receiptPhase A now S r = .ok (r.receipts.map (·.nonce)) :=
  (receiptPhase_ok_iff A now S r _).mpr ⟨h, rfl⟩

/-- The receipt phase depends on the consumed set only through the request's own nonces. -/
theorem receiptPhase_consumed_congr {A : AuthorityV3} {now : Nat} {S T : LedgerV3}
    {r : RequestV3} (hrev : S.revoked = T.revoked) (hgen : S.genesis = T.genesis)
    (h : ∀ n ∈ r.receipts.map (·.nonce), n ∈ S.consumed ↔ n ∈ T.consumed) :
    receiptPhase A now S r = receiptPhase A now T r := by
  unfold receiptPhase
  have hp : policy A S now = policy A T now := by unfold policy; rw [hrev]
  rw [hp, hgen, acceptAllV3_congr (L₂ := ⟨T.consumed⟩) h]

end PCS.V2.Semantic.V3
