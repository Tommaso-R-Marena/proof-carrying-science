import PCS.V2.Canonical

/-!
# Domain-separated hashing and signing envelopes (`pcs/crypto_domains_v06.py`)

Every v0.6 digest is `sha256(JCS({"domain": d, "format": "pcs-jcs-sha256-v1",
"payload": p}))` and every Ed25519 signature covers
`JCS({"domain": d, "format": "pcs-jcs-ed25519-payload-v1", "payload": p})`.

Proved here:

* `hashEnvelopeBytes_injective` : the hashed bytes determine both domain and payload;
* `hash_domain_separation`      : different domains never produce the same hashed bytes;
* `hash_sig_separation`         : no hash preimage is ever a signature payload
  (and vice versa), for any domains and payloads;
* `digest_binding`              : equal domain digests imply equal (domain, payload),
  *or* an explicit SHA-256 collision.  This is the only form in which a
  cryptographic assumption enters: as a concrete collision witness.
-/

namespace PCS.V2.Domains

open PCS.V2.Json
open PCS.V2.SHA256

def hashEnvelopeFormat : String := "pcs-jcs-sha256-v1"
def signaturePayloadFormat : String := "pcs-jcs-ed25519-payload-v1"

def certificateSemanticDomain : String := "pcs-certificate-semantic-sha256-v2"
def certificateIntegrityDomain : String := "pcs-certificate-integrity-sha256-v2"
def runtimeSemanticDomain : String := "pcs-runtime-semantic-sha256-v2"
def intakeSemanticDomain : String := "pcs-intake-semantic-sha256-v2"
def predicateCommitmentDomain : String := "pcs-predicate-sha256-v2"
def normalizedDecisionDomain : String := "pcs-normalized-decision-sha256-v2"
def normalizedIndexDomain : String := "pcs-normalized-index-sha256-v2"

def certificateSignatureDomain : String := "pcs-certificate-signature-v2"
def packageSignatureDomain : String := "pcs-package-signature-v2"

def hashDomains : List String :=
  [certificateSemanticDomain, certificateIntegrityDomain, runtimeSemanticDomain,
   intakeSemanticDomain, predicateCommitmentDomain, normalizedDecisionDomain,
   normalizedIndexDomain]

def signatureDomains : List String := [certificateSignatureDomain, packageSignatureDomain]

theorem hashDomains_nodup : hashDomains.Nodup := by decide
theorem signatureDomains_nodup : signatureDomains.Nodup := by decide
theorem hash_signature_domains_disjoint :
    ∀ d ∈ hashDomains, d ∉ signatureDomains := by decide

/-- The JSON envelope that is hashed / signed (keys already in JCS order). -/
def envelope (fmt domain : String) (payload : JVal) : JVal :=
  .obj [("domain", .str domain), ("format", .str fmt), ("payload", payload)]

def hashEnvelope (domain : String) (payload : JVal) : JVal :=
  envelope hashEnvelopeFormat domain payload

def signatureEnvelope (domain : String) (payload : JVal) : JVal :=
  envelope signaturePayloadFormat domain payload

/-- Exact bytes fed to SHA-256 by `domain_sha256`. -/
def hashPreimage (domain : String) (payload : JVal) : ByteArray :=
  jcsBytes (hashEnvelope domain payload)

/-- Exact bytes signed by `sign_jcs_payload`. -/
def signaturePayloadBytes (domain : String) (payload : JVal) : ByteArray :=
  jcsBytes (signatureEnvelope domain payload)

/-- `domain_sha256(domain, payload)` as raw digest bytes. -/
def domainDigest (domain : String) (payload : JVal) : List UInt8 :=
  sha256 (hashPreimage domain payload).data.toList

/-- `domain_sha256(domain, payload)` as the lower-case hex string Python returns. -/
def domainSha256 (domain : String) (payload : JVal) : String :=
  PCS.V2.Hex.hexEncode (domainDigest domain payload)

theorem envelope_injective {f₁ f₂ d₁ d₂ : String} {p₁ p₂ : JVal}
    (h : envelope f₁ d₁ p₁ = envelope f₂ d₂ p₂) : f₁ = f₂ ∧ d₁ = d₂ ∧ p₁ = p₂ := by
  simp only [envelope, JVal.obj.injEq, List.cons.injEq, Prod.mk.injEq, JVal.str.injEq,
    true_and, and_true] at h
  exact ⟨h.2.1, h.1, h.2.2⟩

theorem hashEnvelopeBytes_injective {d₁ d₂ : String} {p₁ p₂ : JVal}
    (h : hashPreimage d₁ p₁ = hashPreimage d₂ p₂) : d₁ = d₂ ∧ p₁ = p₂ := by
  have := envelope_injective (jcsBytes_injective h)
  exact ⟨this.2.1, this.2.2⟩

theorem hash_domain_separation {d₁ d₂ : String} (hd : d₁ ≠ d₂) (p₁ p₂ : JVal) :
    hashPreimage d₁ p₁ ≠ hashPreimage d₂ p₂ :=
  fun h => hd (hashEnvelopeBytes_injective h).1

theorem hash_sig_separation (d₁ d₂ : String) (p₁ p₂ : JVal) :
    hashPreimage d₁ p₁ ≠ signaturePayloadBytes d₂ p₂ := by
  intro h
  have := (envelope_injective (jcsBytes_injective h)).1
  revert this; decide

theorem signaturePayloadBytes_injective {d₁ d₂ : String} {p₁ p₂ : JVal}
    (h : signaturePayloadBytes d₁ p₁ = signaturePayloadBytes d₂ p₂) : d₁ = d₂ ∧ p₁ = p₂ := by
  have := envelope_injective (jcsBytes_injective h)
  exact ⟨this.2.1, this.2.2⟩

theorem sig_domain_separation {d₁ d₂ : String} (hd : d₁ ≠ d₂) (p₁ p₂ : JVal) :
    signaturePayloadBytes d₁ p₁ ≠ signaturePayloadBytes d₂ p₂ :=
  fun h => hd (signaturePayloadBytes_injective h).1

/-- An explicit SHA-256 collision: two different byte strings with the same digest.
    No PCS theorem assumes these do not exist; theorems instead *produce* one
    whenever binding would fail. -/
def Sha256Collision : Prop := ∃ m₁ m₂ : List UInt8, m₁ ≠ m₂ ∧ sha256 m₁ = sha256 m₂

theorem bytes_injective {a b : ByteArray} (h : a.data.toList = b.data.toList) : a = b :=
  ByteArray.ext (Array.toList_inj.mp h)

/-- Digest binding: equal domain digests mean equal domain and payload, or a
    concrete SHA-256 collision exists. -/
theorem digest_binding {d₁ d₂ : String} {p₁ p₂ : JVal}
    (h : domainDigest d₁ p₁ = domainDigest d₂ p₂) :
    (d₁ = d₂ ∧ p₁ = p₂) ∨ Sha256Collision := by
  by_cases hm : (hashPreimage d₁ p₁).data.toList = (hashPreimage d₂ p₂).data.toList
  · exact Or.inl (hashEnvelopeBytes_injective (bytes_injective hm))
  · exact Or.inr ⟨_, _, hm, h⟩

/-- Hex form of `digest_binding` (the strings stored in PCS JSON). -/
theorem domainSha256_binding {d₁ d₂ : String} {p₁ p₂ : JVal}
    (h : domainSha256 d₁ p₁ = domainSha256 d₂ p₂) :
    (d₁ = d₂ ∧ p₁ = p₂) ∨ Sha256Collision :=
  digest_binding (PCS.V2.Hex.hexEncode_injective h)

/-- Cross-domain non-confusion: a digest in one domain can coincide with a digest
    in a different domain only through a SHA-256 collision. -/
theorem cross_domain_digest_collision {d₁ d₂ : String} (hd : d₁ ≠ d₂) {p₁ p₂ : JVal}
    (h : domainDigest d₁ p₁ = domainDigest d₂ p₂) : Sha256Collision := by
  rcases digest_binding h with h' | h'
  · exact absurd h'.1 hd
  · exact h'

end PCS.V2.Domains
