import PCS.V2.KernelRfl
import PCS.V2.SHA256Fast
import PCS.V2.Witnesses.AISafetyGolden
import PCS.V2.Golden.Literals

/-!
# Provenance of the golden-fixture literals (kernel-checked)

Every literal of `PCS.V2.Golden.Lit` is proved equal to the value the fixture builder
(`PCS.V2.Witnesses.AISafetyGolden`) computes, by kernel evaluation of the production
functions (`kernel_rfl`, i.e. the trusted kernel checks the definitional equality).
Before evaluation, two *proved* rewrites put the goal in a form the kernel evaluates
efficiently:

* `jcsBytes_data` — the canonical bytes of a JSON value, as a byte list, are the UTF-8
  encoding of its canonical character list (this avoids the kernel's quadratic
  `ByteArray.push` loop of `List.toByteArray`);
* `domainDigest_eq` — a domain digest is SHA-256 of that byte list.
-/

set_option autoImplicit false

namespace PCS.V2.Golden

open PCS PCS.V2.Json PCS.V2.Hex PCS.V2.Domains PCS.V2.Package PCS.V2.Signature
open PCS.V2.Witnesses.AISafetyGolden PCS.V2.SHA256 PCS.V2.Index PCS.V2.CertificateModel
open PCS.V2.NormalizedWire

theorem jcsBytes_data (v : JVal) :
    (jcsBytes v).data.toList = (ser v).flatMap String.utf8EncodeChar := by
  simp [jcsBytes, List.utf8Encode]

theorem jcsBytes_size (v : JVal) :
    (jcsBytes v).size = ((ser v).flatMap String.utf8EncodeChar).length := by
  rw [← ByteArray.size_data, ← Array.length_toList, jcsBytes_data]

theorem domainDigest_eq (d : String) (p : JVal) :
    domainDigest d p = PCS.V2.SHA256.sha256 ((ser (hashEnvelope d p)).flatMap String.utf8EncodeChar) := by
  rw [domainDigest, hashPreimage, jcsBytes_data]

theorem signedMessage_eq (d : String) (p : JVal) :
    signedMessage d p = (ser (signatureEnvelope d p)).flatMap String.utf8EncodeChar := by
  rw [signedMessage, signaturePayloadBytes, jcsBytes_data]

/-! ## Digests and member bytes -/

theorem traceDigest_eq : sha256 golden.trace.data.toList = Lit.traceDigest := by
  rw [sha256_eq_sha256Fast]; kernel_rfl

theorem semHash_eq : golden.semHash = Lit.semHash := by
  rw [FixtureSpec.semHash, domainDigest_eq, sha256_eq_sha256Fast]; kernel_rfl

theorem intHash_eq : golden.intHash = Lit.intHash := by
  rw [FixtureSpec.intHash, semHash_eq, domainDigest_eq, sha256_eq_sha256Fast]; kernel_rfl

/-- The certificate JSON value with its two hash members as literals. -/
theorem certJ_eq : golden.certJ = .obj (golden.certMembers (hexEncode Lit.semHash) (hexEncode Lit.intHash)) := by
  rw [FixtureSpec.certJ, semHash_eq, intHash_eq]

theorem certBytes_eq : golden.certBytes.data.toList = Lit.certBytes := by
  rw [FixtureSpec.certBytes, jcsBytes_data, certJ_eq]; kernel_rfl

theorem certBytes_size : golden.certBytes.size = 1683 := by
  rw [← ByteArray.size_data, ← Array.length_toList, certBytes_eq]; kernel_rfl

theorem certDigest_eq : sha256 golden.certBytes.data.toList = Lit.certDigest := by
  rw [certBytes_eq, sha256_eq_sha256Fast]; kernel_rfl

theorem commitment_eq : commitmentOf (predJ 4 7) = Lit.commitment := by
  rw [commitmentOf, domainDigest_eq, sha256_eq_sha256Fast]; kernel_rfl

theorem storageKey_eq : storageKey "C1" = Lit.storageKeyC1 := by
  rw [storageKey, sha256_eq_sha256Fast]; kernel_rfl

/-! ## The normalized wire, index and manifest -/

/-- The normalized decision wire of claim `C1`, with literal digests. -/
def wireV : WireV2 :=
  { source := { checkerVersion := checkerVersion, certificateSemanticHash := Lit.semHash,
                certificateIntegrityHash := Lit.intHash, claimId := "C1" },
    context := [{ id := "A1", statement := "Risk of action a is a mod 4 (declared toy cost model)." }],
    claim := { id := "C1", kind := .computational, predicateCommitment := Lit.commitment,
               requiredEvidence := ["E1"], assumptions := ["A1"] },
    evidence := [{ id := "E1", kind := .computationalTest, outcome := .pass,
                   predicateCommitment := Lit.commitment }],
    decision := .computational, wireSemanticHash := Lit.wireHash }

theorem certV2_eq : golden.certV2 =
    { members := golden.certMembers (hexEncode Lit.semHash) (hexEncode Lit.intHash),
      semanticHash := Lit.semHash, integrityHash := Lit.intHash } := by
  rw [FixtureSpec.certV2, semHash_eq, intHash_eq]

theorem wire_eq : golden.wire = wireV := by
  rw [FixtureSpec.wire, FixtureSpec.certModel, certV2_eq]
  simp only [deriveWire, NormalizedWire.expectedHash, commitmentOf, domainDigest_eq,
    sha256_eq_sha256Fast]
  kernel_rfl

theorem wireBytes_eq : golden.wireBytes.data.toList = Lit.wireBytes := by
  rw [FixtureSpec.wireBytes, encodedBytes, wire_eq, jcsBytes_data]; kernel_rfl

theorem wireBytes_size : golden.wireBytes.size = 1108 := by
  rw [← ByteArray.size_data, ← Array.length_toList, wireBytes_eq]; kernel_rfl

theorem wireDigest_eq : sha256 golden.wireBytes.data.toList = Lit.wireDigest := by
  rw [wireBytes_eq, sha256_eq_sha256Fast]; kernel_rfl

theorem wirePath_eq : wirePath = keyPath Lit.storageKeyC1 := by
  rw [wirePath, storageKey_eq]

/-- The normalized index, with literal digests. -/
def indexV : IndexV2 :=
  { certificateIntegrityHash := Lit.intHash, certificateSemanticHash := Lit.semHash,
    entries := [{ claimId := "C1", decision := .computational, storageKey := Lit.storageKeyC1,
                  wireSemanticHash := Lit.wireHash }],
    indexSemanticHash := Lit.indexHash }

theorem index_eq : golden.index = indexV := by
  rw [FixtureSpec.index, semHash_eq, intHash_eq, wire_eq, storageKey_eq]
  simp only [Index.expectedHash, domainDigest_eq, sha256_eq_sha256Fast]
  kernel_rfl

theorem indexBytes_eq : golden.indexBytes.data.toList = Lit.indexBytes := by
  rw [FixtureSpec.indexBytes, index_eq, jcsBytes_data]; kernel_rfl

theorem indexBytes_size : golden.indexBytes.size = 677 := by
  rw [← ByteArray.size_data, ← Array.length_toList, indexBytes_eq]; kernel_rfl

theorem indexDigest_eq : sha256 golden.indexBytes.data.toList = Lit.indexDigest := by
  rw [indexBytes_eq, sha256_eq_sha256Fast]; kernel_rfl

end PCS.V2.Golden
