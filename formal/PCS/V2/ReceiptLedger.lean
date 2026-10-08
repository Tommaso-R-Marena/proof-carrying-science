import PCS.V2.TranslationJson
import PCS.V2.JsonRoundtrip

/-!
# Receipt envelopes v2 and a stateful replay-protecting ledger

v1 receipts are bound to the exact interpretation / Lean source and verified with
role-separated Ed25519 keys, but they carry no nonce, validity window or version, and a
stateless check cannot prevent reuse.  This file specifies the **v2 receipt envelope** and an
explicitly **stateful** acceptance protocol.

* `ReceiptEnvelope` — role (`confirmation` / `elaboration` / `proof`), protocol version,
  the exact bound statement (canonical JSON), nonce, issue and expiry times, issuer key and
  signature.  The signed bytes `envelopeBytes` contain *all* of these fields inside one
  canonical JSON object under the domain-separation tag `pcs-semantic-receipt-v2`.
* `acceptEnvelope` — fail-closed acceptance against a `LedgerPolicy` (role-separated keys,
  revocation list, clock, signature verifier) and a `Ledger` (nonces already consumed).

Kernel-checked results:

* `acceptEnvelope_sound` — acceptance implies: known version, expected role, authorized and
  unrevoked key of *that* role, exact expected statement, inside the validity window, fresh
  nonce, valid signature; and the nonce is consumed.
* `replay_rejected`, `expired_rejected`, `revoked_rejected`, `role_mismatch_rejected`,
  `unknown_version_rejected`, `statement_substitution_rejected`.
* `envelopeBytes_injective` — distinct envelopes have distinct signed bytes.
* `role_confusion_and_substitution_impossible` — under an explicit unforgeability
  hypothesis (`NoForgery`: every verifying signature was produced by the honest holder of the
  key over exactly those bytes) and an honest-issuer model, an accepted envelope *is* one the
  issuer issued: same role, statement, nonce and validity window.  A confirmation signature
  can therefore not be replayed as a proof receipt or attached to another statement.

`NoForgery` (Ed25519 security and key secrecy) and issuer honesty are explicit trust
assumptions, not theorems.  A signed proof receipt is evidence that an *authorized verifier
said* the kernel accepted a proof; it is not itself a proof.
-/

set_option autoImplicit false

namespace PCS.V2.Semantic.Ledger

open PCS.V2.Json PCS.V2.Semantic

inductive ReceiptRole where
  | confirmation | elaboration | proof
  deriving Repr, DecidableEq, Inhabited

def ReceiptRole.name : ReceiptRole → String
  | .confirmation => "confirmation"
  | .elaboration => "elaboration"
  | .proof => "proof"

theorem ReceiptRole.name_injective {a b : ReceiptRole} (h : a.name = b.name) : a = b := by
  cases a <;> cases b <;> first | rfl | (simp [ReceiptRole.name] at h)

def protocolVersion : String := "pcs-receipt-v2"

structure ReceiptEnvelope where
  role : ReceiptRole
  version : String
  statement : JVal
  nonce : String
  issuedAt : Nat
  expiresAt : Nat
  issuer : String
  signature : String
  deriving Repr, Inhabited

/-- Everything the signature covers, as one canonical JSON object. -/
def envelopePayload (e : ReceiptEnvelope) : JVal :=
  .obj [("expires_at", .num (Int.ofNat e.expiresAt)), ("issued_at", .num (Int.ofNat e.issuedAt)),
    ("issuer", .str e.issuer), ("nonce", .str e.nonce), ("role", .str e.role.name),
    ("statement", e.statement), ("version", .str e.version)]

def envelopeTag : String := "pcs-semantic-receipt-v2\n"

/-- The signed bytes: UTF-8 of the domain tag followed by the canonical payload. -/
def envelopeBytes (e : ReceiptEnvelope) : List UInt8 :=
  (envelopeTag.toList ++ ser (envelopePayload e)).flatMap String.utf8EncodeChar

theorem utf8_flatMap_injective {l₁ l₂ : List Char}
    (h : l₁.flatMap String.utf8EncodeChar = l₂.flatMap String.utf8EncodeChar) : l₁ = l₂ := by
  have h' : l₁.utf8Encode = l₂.utf8Encode := by
    unfold List.utf8Encode; rw [h]
  have := congrArg String.fromUTF8? h'
  rw [PCS.V2.Canonical.fromUTF8?_utf8Encode, PCS.V2.Canonical.fromUTF8?_utf8Encode] at this
  exact String.ofList_injective (Option.some.inj this)

/-- What is signed determines every envelope field except the signature itself. -/
structure SameSignedContent (e f : ReceiptEnvelope) : Prop where
  role : e.role = f.role
  version : e.version = f.version
  statement : e.statement = f.statement
  nonce : e.nonce = f.nonce
  issuedAt : e.issuedAt = f.issuedAt
  expiresAt : e.expiresAt = f.expiresAt
  issuer : e.issuer = f.issuer

/-- **Signed-bytes injectivity.** -/
theorem envelopeBytes_injective {e f : ReceiptEnvelope} (h : envelopeBytes e = envelopeBytes f) :
    SameSignedContent e f := by
  have h1 := utf8_flatMap_injective h
  have h2 := ser_injective (List.append_cancel_left h1)
  simp only [envelopePayload, JVal.obj.injEq, List.cons.injEq, Prod.mk.injEq, JVal.str.injEq,
    JVal.num.injEq, Int.ofNat.injEq, true_and, and_true] at h2
  obtain ⟨hx, hi, hiss, hn, hr, hs, hv⟩ := h2
  exact ⟨ReceiptRole.name_injective hr, hv, hs, hn, hi, hx, hiss⟩

/-! ## Policy, ledger, acceptance -/

structure LedgerPolicy where
  keys : ReceiptRole → List String
  revoked : List String
  now : Nat
  verify : String → List UInt8 → String → Bool

structure LedgerState where
  seenNonces : List String
  deriving Repr, Inhabited

/-- Rejection reasons. -/
inductive RejectReason where
  | unknownVersion | roleMismatch | unauthorizedKey | revokedKey | statementMismatch
  | outsideValidity | replay | badSignature
  deriving Repr, DecidableEq, Inhabited

/-- **Fail-closed, stateful envelope acceptance.** -/
def acceptEnvelope (P : LedgerPolicy) (L : LedgerState) (role : ReceiptRole) (stmt : JVal)
    (e : ReceiptEnvelope) : Except RejectReason LedgerState :=
  if e.version ≠ protocolVersion then .error .unknownVersion
  else if e.role ≠ role then .error .roleMismatch
  else if !(P.keys role).contains e.issuer then .error .unauthorizedKey
  else if P.revoked.contains e.issuer then .error .revokedKey
  else if ser e.statement ≠ ser stmt then .error .statementMismatch
  else if ¬ (e.issuedAt ≤ P.now ∧ P.now < e.expiresAt) then .error .outsideValidity
  else if L.seenNonces.contains e.nonce then .error .replay
  else if !P.verify e.issuer (envelopeBytes e) e.signature then .error .badSignature
  else .ok ⟨e.nonce :: L.seenNonces⟩

/-- **Acceptance soundness.** -/
theorem acceptEnvelope_sound {P : LedgerPolicy} {L L' : LedgerState} {role : ReceiptRole}
    {stmt : JVal} {e : ReceiptEnvelope} (h : acceptEnvelope P L role stmt e = .ok L') :
    e.version = protocolVersion ∧ e.role = role ∧ e.issuer ∈ P.keys role ∧
    e.issuer ∉ P.revoked ∧ e.statement = stmt ∧ e.issuedAt ≤ P.now ∧ P.now < e.expiresAt ∧
    e.nonce ∉ L.seenNonces ∧ P.verify e.issuer (envelopeBytes e) e.signature = true ∧
    L' = ⟨e.nonce :: L.seenNonces⟩ := by
  unfold acceptEnvelope at h
  by_cases h1 : e.version ≠ protocolVersion
  · rw [if_pos h1] at h; cases h
  rw [if_neg h1] at h
  by_cases h2 : e.role ≠ role
  · rw [if_pos h2] at h; cases h
  rw [if_neg h2] at h
  by_cases h3 : (!(P.keys role).contains e.issuer) = true
  · rw [if_pos h3] at h; cases h
  rw [if_neg h3] at h
  by_cases h4 : P.revoked.contains e.issuer = true
  · rw [if_pos h4] at h; cases h
  rw [if_neg h4] at h
  by_cases h5 : ser e.statement ≠ ser stmt
  · rw [if_pos h5] at h; cases h
  rw [if_neg h5] at h
  by_cases h6 : ¬ (e.issuedAt ≤ P.now ∧ P.now < e.expiresAt)
  · rw [if_pos h6] at h; cases h
  rw [if_neg h6] at h
  by_cases h7 : L.seenNonces.contains e.nonce = true
  · rw [if_pos h7] at h; cases h
  rw [if_neg h7] at h
  by_cases h8 : (!P.verify e.issuer (envelopeBytes e) e.signature) = true
  · rw [if_pos h8] at h; cases h
  rw [if_neg h8] at h
  cases h
  simp only [ne_eq, Decidable.not_not, Bool.not_eq_true', Bool.not_eq_false] at h1 h2 h3 h4 h5 h6 h7 h8
  refine ⟨h1, h2, List.contains_iff_mem.mp h3, fun hm => ?_, ser_injective h5, h6.1, h6.2,
    fun hm => ?_, h8, rfl⟩
  · rw [List.contains_iff_mem.mpr hm] at h4; exact h4 rfl
  · rw [List.contains_iff_mem.mpr hm] at h7; exact h7 rfl

/-- **Replay is rejected**: once an envelope was accepted, any envelope with the same nonce
    (in particular the same envelope) is rejected by the updated ledger. -/
theorem replay_rejected {P : LedgerPolicy} {L L' : LedgerState} {role role' : ReceiptRole}
    {stmt stmt' : JVal} {e e' : ReceiptEnvelope} (h : acceptEnvelope P L role stmt e = .ok L')
    (hn : e'.nonce = e.nonce) : ∀ L'', acceptEnvelope P L' role' stmt' e' ≠ .ok L'' := by
  intro L'' h'
  obtain ⟨-, -, -, -, -, -, -, hfresh, -, -⟩ := acceptEnvelope_sound h'
  obtain ⟨-, -, -, -, -, -, -, -, -, hL⟩ := acceptEnvelope_sound h
  subst hL
  exact hfresh (by rw [hn]; exact List.mem_cons_self)

theorem expired_rejected {P : LedgerPolicy} {L : LedgerState} {role : ReceiptRole} {stmt : JVal}
    {e : ReceiptEnvelope} (hx : e.expiresAt ≤ P.now) :
    ∀ L', acceptEnvelope P L role stmt e ≠ .ok L' := by
  intro L' h
  obtain ⟨-, -, -, -, -, -, h7, -⟩ := acceptEnvelope_sound h
  omega

theorem revoked_rejected {P : LedgerPolicy} {L : LedgerState} {role : ReceiptRole} {stmt : JVal}
    {e : ReceiptEnvelope} (hr : e.issuer ∈ P.revoked) :
    ∀ L', acceptEnvelope P L role stmt e ≠ .ok L' := by
  intro L' h
  exact (acceptEnvelope_sound h).2.2.2.1 hr

theorem role_mismatch_rejected {P : LedgerPolicy} {L : LedgerState} {role : ReceiptRole}
    {stmt : JVal} {e : ReceiptEnvelope} (hr : e.role ≠ role) :
    ∀ L', acceptEnvelope P L role stmt e ≠ .ok L' := by
  intro L' h
  exact hr (acceptEnvelope_sound h).2.1

theorem unknown_version_rejected {P : LedgerPolicy} {L : LedgerState} {role : ReceiptRole}
    {stmt : JVal} {e : ReceiptEnvelope} (hv : e.version ≠ protocolVersion) :
    ∀ L', acceptEnvelope P L role stmt e ≠ .ok L' := by
  intro L' h
  exact hv (acceptEnvelope_sound h).1

theorem statement_substitution_rejected {P : LedgerPolicy} {L : LedgerState} {role : ReceiptRole}
    {stmt : JVal} {e : ReceiptEnvelope} (hs : e.statement ≠ stmt) :
    ∀ L', acceptEnvelope P L role stmt e ≠ .ok L' := by
  intro L' h
  exact hs (acceptEnvelope_sound h).2.2.2.2.1

/-! ## Unforgeability model -/

/-- **Explicit trust assumption** (Ed25519 security, key secrecy): every verifying signature
    under key `k` was produced by the holder of `k` over exactly those bytes. -/
def NoForgery (P : LedgerPolicy) (Signed : List (String × List UInt8)) : Prop :=
  ∀ k m s, P.verify k m s = true → (k, m) ∈ Signed

/-- **Explicit trust assumption** (issuer honesty): the key holders only sign the canonical
    bytes of envelopes they actually issued. -/
def HonestIssuers (Signed : List (String × List UInt8)) (Issued : List ReceiptEnvelope) : Prop :=
  ∀ k m, (k, m) ∈ Signed → ∃ e₀ ∈ Issued, m = envelopeBytes e₀

/-- **Role confusion and evidence substitution are impossible** (under the two explicit
    assumptions): an accepted envelope has exactly the role, statement, nonce and validity
    window of an envelope the issuer actually issued. -/
theorem role_confusion_and_substitution_impossible {P : LedgerPolicy}
    {Signed : List (String × List UInt8)} {Issued : List ReceiptEnvelope}
    (hNF : NoForgery P Signed) (hH : HonestIssuers Signed Issued) {L L' : LedgerState}
    {role : ReceiptRole} {stmt : JVal} {e : ReceiptEnvelope}
    (h : acceptEnvelope P L role stmt e = .ok L') :
    ∃ e₀ ∈ Issued, SameSignedContent e e₀ ∧ e₀.role = role ∧ e₀.statement = stmt := by
  obtain ⟨-, hrole, -, -, hstmt, -, -, -, hsig, -⟩ := acceptEnvelope_sound h
  obtain ⟨e₀, hmem, hbytes⟩ := hH _ _ (hNF _ _ _ hsig)
  have hs := envelopeBytes_injective hbytes
  exact ⟨e₀, hmem, hs, hs.role ▸ hrole, hs.statement ▸ hstmt⟩

/-- The concrete Ed25519 instantiation (same verifier as v1 receipts). -/
def ed25519Policy (keys : ReceiptRole → List String) (revoked : List String) (now : Nat) :
    LedgerPolicy :=
  { keys := keys, revoked := revoked, now := now,
    verify := fun k m s => sigOK [k] k m s }

end PCS.V2.Semantic.Ledger
