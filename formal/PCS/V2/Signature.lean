import PCS.V2.Base64

/-!
# v0.6 Ed25519 signature records (`pcs/signing_v06.py`)

A v0.6 signature record is the canonical JCS object

```
{"algorithm":"Ed25519",
 "payload":{"domain":d,"format":"pcs-jcs-ed25519-payload-v1","payload":p},
 "payload_sha256":<64 hex>, "public_key_fingerprint":<64 hex>,
 "signature":<canonical base64 of 64 bytes>, "signature_format":"pcs-ed25519-jcs-v2"}
```

`verifySigRecordBytes` is the Lean checker corresponding to
`parse_signature_record_bytes_v06` + `verify_jcs_signature`.  The Ed25519
verification primitive is a *parameter* `V`, so that three different things stay
separate:

* (A) implementation correctness of the primitive: `Ed25519ImplCorrect V Spec`;
* (B) the cryptographic unforgeability assumption, stated for the specification
  and for one public key only: `NoForgery Spec pk Signed`;
* (C) PCS's *use* of Ed25519, which is proved unconditionally here:
  the message handed to `V` is exactly `signaturePayloadBytes d p`, the domain and
  payload are the expected ones, the fingerprint is the SHA-256 of the key, the
  record bytes are unique (non-malleable), and domains cannot be confused.

The previous broad `SchemeSound` style assumption is replaced by (A) + (B), and
(B) only ever yields the fact "the key holder signed exactly these bytes".
-/

namespace PCS.V2.Signature

open PCS.V2.Json PCS.V2.Hex PCS.V2.SHA256 PCS.V2.Domains PCS.V2.Canonical PCS.V2.Common

def sigRecordFormat : String := "pcs-ed25519-jcs-v2"
def algorithmName : String := "Ed25519"
def maxSigRecordBytes : Nat := 16 * 1024 * 1024

/-- Typed signature record. -/
structure SigRecordV2 where
  domain : String
  payload : JVal
  payloadSha256 : List UInt8
  fingerprint : List UInt8
  signature : List UInt8

def encodeSigRecord (r : SigRecordV2) : JVal :=
  .obj [("algorithm", .str algorithmName),
        ("payload", signatureEnvelope r.domain r.payload),
        ("payload_sha256", .str (hexEncode r.payloadSha256)),
        ("public_key_fingerprint", .str (hexEncode r.fingerprint)),
        ("signature", .str (Base64.encodeStr r.signature)),
        ("signature_format", .str sigRecordFormat)]

/-- Signature string decoder: canonical base64 of exactly 64 bytes. -/
def decSignature (s : String) : Option (List UInt8) :=
  match Base64.decodeCanonical s with
  | some bs => if bs.length = 64 then some bs else none
  | none => none

def decodeSigRecord : JVal → Option SigRecordV2
  | .obj [(k₁, .str alg), (k₂, .obj [(e₁, .str d), (e₂, .str fmt), (e₃, p)]), (k₃, .str ph),
          (k₄, .str fp), (k₅, .str sg), (k₆, .str sf)] =>
    if k₁ = "algorithm" ∧ k₂ = "payload" ∧ k₃ = "payload_sha256" ∧
       k₄ = "public_key_fingerprint" ∧ k₅ = "signature" ∧ k₆ = "signature_format" ∧
       e₁ = "domain" ∧ e₂ = "format" ∧ e₃ = "payload" ∧
       alg = algorithmName ∧ fmt = signaturePayloadFormat ∧ sf = sigRecordFormat ∧
       d ∈ signatureDomains then
      match decDigest ph, decDigest fp, decSignature sg with
      | some ph', some fp', some sg' =>
        some { domain := d, payload := p, payloadSha256 := ph', fingerprint := fp',
               signature := sg' }
      | _, _, _ => none
    else none
  | _ => none

/-- Ed25519 verification primitive: public key bytes, message bytes, signature bytes. -/
abbrev Ed25519Verify := List UInt8 → List UInt8 → List UInt8 → Bool

/-- The exact message signed for domain `d` and payload `p`. -/
def signedMessage (d : String) (p : JVal) : List UInt8 := (signaturePayloadBytes d p).data.toList

/-- `public_key_fingerprint`: SHA-256 of the raw 32-byte public key. -/
def fingerprintOf (pk : List UInt8) : List UInt8 := sha256 pk

/-- Optional pinned fingerprint (`expected_fingerprint`). -/
def pinOK (expected : Option (List UInt8)) (pk : List UInt8) : Bool :=
  match expected with
  | none => true
  | some e => decide (e = fingerprintOf pk)

/-- The Lean signature-record checker. -/
def verifySigRecordBytes (V : Ed25519Verify) (pk : List UInt8) (expected : Option (List UInt8))
    (d : String) (p : JVal) (raw : ByteArray) : Option SigRecordV2 :=
  match parseCanonicalBytes maxSigRecordBytes raw with
  | none => none
  | some v =>
    match decodeSigRecord v with
    | none => none
    | some r =>
      if r.domain = d ∧ ser r.payload = ser p ∧ r.payloadSha256 = sha256 (signedMessage d p) ∧
         r.fingerprint = fingerprintOf pk ∧ pinOK expected pk = true ∧
         V pk (signedMessage d p) r.signature = true then some r else none

/-! ## Soundness of PCS's use of Ed25519 (C) -/

theorem decSignature_sound {s : String} {bs : List UInt8} (h : decSignature s = some bs) :
    Base64.encodeStr bs = s ∧ bs.length = 64 := by
  unfold decSignature at h
  split at h
  · split at h
    · cases h; exact ⟨Base64.decodeCanonical_sound (by assumption), by assumption⟩
    · cases h
  · cases h

theorem decodeSigRecord_sound {v : JVal} {r : SigRecordV2} (h : decodeSigRecord v = some r) :
    encodeSigRecord r = v ∧ r.domain ∈ signatureDomains ∧ r.payloadSha256.length = 32 ∧
      r.fingerprint.length = 32 ∧ r.signature.length = 64 := by
  unfold decodeSigRecord at h
  split at h
  · split at h
    · rename_i hk
      obtain ⟨rfl, rfl, rfl, rfl, rfl, rfl, rfl, rfl, rfl, rfl, rfl, rfl, hd⟩ := hk
      split at h
      · rename_i ph' fp' sg' hph hfp hsg
        cases h
        obtain ⟨h1, h1l⟩ := decDigest_sound hph
        obtain ⟨h2, h2l⟩ := decDigest_sound hfp
        obtain ⟨h3, h3l⟩ := decSignature_sound hsg
        refine ⟨?_, hd, h1l, h2l, h3l⟩
        simp [encodeSigRecord, signatureEnvelope, envelope, h1, h2, h3]
      · cases h
    · cases h
  · cases h

/-- Everything an accepted signature record establishes. -/
structure SigAccepted (V : Ed25519Verify) (pk : List UInt8) (expected : Option (List UInt8))
    (d : String) (p : JVal) (raw : ByteArray) (r : SigRecordV2) : Prop where
  bytes : raw = jcsBytes (encodeSigRecord r)
  canonical : canonical (encodeSigRecord r) = true
  domain : r.domain = d
  domainKnown : d ∈ signatureDomains
  payload : r.payload = p
  payloadDigest : r.payloadSha256 = sha256 (signedMessage d p)
  fingerprint : r.fingerprint = fingerprintOf pk
  pinned : ∀ e, expected = some e → e = fingerprintOf pk
  signatureLength : r.signature.length = 64
  verified : V pk (signedMessage d p) r.signature = true

theorem verifySigRecordBytes_sound {V : Ed25519Verify} {pk : List UInt8}
    {expected : Option (List UInt8)} {d : String} {p : JVal} {raw : ByteArray} {r : SigRecordV2}
    (h : verifySigRecordBytes V pk expected d p raw = some r) :
    SigAccepted V pk expected d p raw r := by
  unfold verifySigRecordBytes at h
  split at h
  · cases h
  · rename_i v hv
    split at h
    · cases h
    · rename_i r' hr
      split at h
      · rename_i hc
        cases h
        obtain ⟨hraw, hcan, _⟩ := parseCanonicalBytes_sound hv
        obtain ⟨henc, hdom, _, _, hsig⟩ := decodeSigRecord_sound hr
        obtain ⟨hd, hp, hph, hfp, hpin, hV⟩ := hc
        subst henc
        refine ⟨hraw, hcan, hd, hd ▸ hdom, ser_injective hp, hph, hfp, ?_, hsig, hV⟩
        intro e he
        subst he
        simpa [pinOK] using hpin
      · cases h

/-- The bytes handed to the Ed25519 primitive are exactly the JCS signature envelope
    of the expected domain and payload (`sign_jcs_payload`/`verify_jcs_signature`). -/
theorem verifySigRecordBytes_signs_exact {V : Ed25519Verify} {pk : List UInt8}
    {expected : Option (List UInt8)} {d : String} {p : JVal} {raw : ByteArray} {r : SigRecordV2}
    (h : verifySigRecordBytes V pk expected d p raw = some r) :
    V pk (signaturePayloadBytes d p).data.toList r.signature = true :=
  (verifySigRecordBytes_sound h).verified

/-- The record bytes are a function of (domain, payload, key, signature bytes):
    no second accepted spelling exists (canonical JCS + canonical base64). -/
theorem verifySigRecordBytes_determined {V : Ed25519Verify} {pk : List UInt8}
    {expected : Option (List UInt8)} {d : String} {p : JVal} {raw : ByteArray} {r : SigRecordV2}
    (h : verifySigRecordBytes V pk expected d p raw = some r) :
    raw = jcsBytes (encodeSigRecord
      { domain := d, payload := p, payloadSha256 := sha256 (signedMessage d p),
        fingerprint := fingerprintOf pk, signature := r.signature }) := by
  obtain ⟨hb, _, hd, _, hp, hph, hfp, _, _, _⟩ := verifySigRecordBytes_sound h
  rw [hb]
  cases r
  simp only at hd hp hph hfp
  subst hd hp hph hfp
  rfl

/-- Non-malleability: two accepted records carrying the same signature bytes are the
    same byte string. -/
theorem verifySigRecordBytes_nonmalleable {V : Ed25519Verify} {pk : List UInt8}
    {e₁ e₂ : Option (List UInt8)} {d : String} {p : JVal} {raw₁ raw₂ : ByteArray}
    {r₁ r₂ : SigRecordV2}
    (h₁ : verifySigRecordBytes V pk e₁ d p raw₁ = some r₁)
    (h₂ : verifySigRecordBytes V pk e₂ d p raw₂ = some r₂)
    (hs : r₁.signature = r₂.signature) : raw₁ = raw₂ := by
  rw [verifySigRecordBytes_determined h₁, verifySigRecordBytes_determined h₂, hs]

/-- A record accepted for one domain is never accepted for another domain. -/
theorem verifySigRecordBytes_domain_unique {V : Ed25519Verify} {pk : List UInt8}
    {e₁ e₂ : Option (List UInt8)} {d₁ d₂ : String} {p₁ p₂ : JVal} {raw : ByteArray}
    {r₁ r₂ : SigRecordV2}
    (h₁ : verifySigRecordBytes V pk e₁ d₁ p₁ raw = some r₁)
    (h₂ : verifySigRecordBytes V pk e₂ d₂ p₂ raw = some r₂) : d₁ = d₂ ∧ p₁ = p₂ := by
  have a := verifySigRecordBytes_sound h₁
  have b := verifySigRecordBytes_sound h₂
  have hr : encodeSigRecord r₁ = encodeSigRecord r₂ := jcsBytes_injective (a.bytes.symm.trans b.bytes)
  have h2 : signatureEnvelope r₁.domain r₁.payload = signatureEnvelope r₂.domain r₂.payload := by
    simp only [encodeSigRecord, JVal.obj.injEq, List.cons.injEq, Prod.mk.injEq] at hr
    exact hr.2.1.2
  obtain ⟨_, hd, hp⟩ := envelope_injective h2
  exact ⟨a.domain ▸ b.domain ▸ hd, a.payload ▸ b.payload ▸ hp⟩

/-- Certificate signatures and package signatures sign disjoint byte sets. -/
theorem certificate_package_messages_disjoint (p q : JVal) :
    signedMessage certificateSignatureDomain p ≠ signedMessage packageSignatureDomain q := by
  intro h
  exact sig_domain_separation (by decide) p q (bytes_injective h)

/-- No signed message is ever a hash preimage (hash and signature envelopes are disjoint). -/
theorem signed_message_not_hash_preimage (d d' : String) (p p' : JVal) :
    signedMessage d p ≠ (hashPreimage d' p').data.toList := by
  intro h
  exact hash_sig_separation d' d p' p (bytes_injective h).symm

/-! ## Cryptographic layer (A) + (B) as explicit, narrow hypotheses -/

/-- (A) The primitive used by the checker computes RFC 8032 verification `Spec`. -/
def Ed25519ImplCorrect (V Spec : Ed25519Verify) : Prop := ∀ pk m s, V pk m s = Spec pk m s

/-- (B) Unforgeability for one key: every (message, signature) pair the
    specification accepts under `pk` comes from the key holder having signed that
    message.  `Signed` is the (external) set of messages the key holder signed. -/
def NoForgery (Spec : Ed25519Verify) (pk : List UInt8) (Signed : List UInt8 → Prop) : Prop :=
  ∀ m s, Spec pk m s = true → Signed m

/-- Key-holder discipline: the private key is used only through `sign_jcs_payload`,
    i.e. it only signs JCS signature envelopes of payloads it intends. -/
def SignsOnlyEnvelopes (Signed : List UInt8 → Prop) (Intended : String → JVal → Prop) : Prop :=
  ∀ m, Signed m → ∃ d p, m = signedMessage d p ∧ Intended d p

/-- Authenticity: an accepted record means the key holder signed exactly the
    expected envelope bytes (under (A) and (B) only). -/
theorem verifySigRecordBytes_authentic {V Spec : Ed25519Verify} {pk : List UInt8}
    {expected : Option (List UInt8)} {d : String} {p : JVal} {raw : ByteArray} {r : SigRecordV2}
    {Signed : List UInt8 → Prop}
    (h : verifySigRecordBytes V pk expected d p raw = some r)
    (hA : Ed25519ImplCorrect V Spec) (hB : NoForgery Spec pk Signed) :
    Signed (signedMessage d p) :=
  hB _ r.signature ((hA _ _ _).symm.trans (verifySigRecordBytes_sound h).verified)

/-- Intent: under the key-holder discipline, the key holder intended exactly this
    (domain, payload) pair; a certificate signature can never be read as a package
    signature or vice versa. -/
theorem verifySigRecordBytes_intended {V Spec : Ed25519Verify} {pk : List UInt8}
    {expected : Option (List UInt8)} {d : String} {p : JVal} {raw : ByteArray} {r : SigRecordV2}
    {Signed : List UInt8 → Prop} {Intended : String → JVal → Prop}
    (h : verifySigRecordBytes V pk expected d p raw = some r)
    (hA : Ed25519ImplCorrect V Spec) (hB : NoForgery Spec pk Signed)
    (hK : SignsOnlyEnvelopes Signed Intended) : Intended d p := by
  obtain ⟨d', p', hm, hi⟩ := hK _ (verifySigRecordBytes_authentic h hA hB)
  obtain ⟨rfl, rfl⟩ := signaturePayloadBytes_injective (bytes_injective hm)
  exact hi

end PCS.V2.Signature
