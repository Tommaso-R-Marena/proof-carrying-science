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

* `jcsBytes_data` ‚Äî the canonical bytes of a JSON value, as a byte list, are the UTF-8
  encoding of its canonical character list (this avoids the kernel's quadratic
  `ByteArray.push` loop of `List.toByteArray`);
* `domainDigest_eq` ‚Äî a domain digest is SHA-256 of that byte list.
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
  rw [‚Üê ByteArray.size_data, ‚Üê Array.length_toList, jcsBytes_data]

theorem domainDigest_eq (d : String) (p : JVal) :
    domainDigest d p = PCS.V2.SHA256.sha256 ((ser (hashEnvelope d p)).flatMap String.utf8EncodeChar) := by
  rw [domainDigest, hashPreimage, jcsBytes_data]

theorem signedMessage_eq (d : String) (p : JVal) :
    signedMessage d p = (ser (signatureEnvelope d p)).flatMap String.utf8EncodeChar := by
  rw [signedMessage, signaturePayloadBytes, jcsBytes_data]

/-! ## Digests and member bytes -/

theorem traceDigest_eq : sha256 golden.trace.data.toList = Lit.traceDigest := by
  rw [sha256_eq_sha256Fast]; kernel_rfl

theorem semHash_eq : golden.semHd—P–ÄL@˚˜≠Ö™Ï