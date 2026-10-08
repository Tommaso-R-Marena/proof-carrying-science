import PCS.V2.Golden.Provenance

/-!
# Provenance of the golden manifest, signed messages and signature records

Continuation of `PCS.V2.Golden.Provenance` (split for build parallelism).
-/

set_option autoImplicit false

namespace PCS.V2.Golden

open PCS PCS.V2.Json PCS.V2.Hex PCS.V2.Domains PCS.V2.Package PCS.V2.Signature
open PCS.V2.Witnesses.AISafetyGolden PCS.V2.SHA256 PCS.V2.Index PCS.V2.CertificateModel

/-- The package manifest, with literal digests and sizes. -/
def manifestV : ManifestV2 :=
  { certSemanticHash := Lit.semHash, certIntegrityHash := Lit.intHash,
    files := [(tracePath, ‚ü®Lit.traceDigest, 6‚ü©), ("certificate.json", ‚ü®Lit.certDigest, 1683‚ü©),
              (wirePath, ‚ü®Lit.wireDigest, 1108‚ü©), (indexPath, ‚ü®Lit.indexDigest, 677‚ü©)] }

theorem manifest_eq : golden.manifest = manifestV := by
  rw [FixtureSpec.manifest, semHash_eq, intHash_eq]
  simp only [FixtureSpec.files, List.map_cons, List.map_nil, traceDigest_eq, certDigest_eq,
    wireDigest_eq, indexDigest_eq, certBytes_size, wireBytes_size, indexBytes_size]
  kernel_rfl

theorem manifestBytes_eq : golden.manifestBytes.data.toList = Lit.manifestBytes := by
  rw [FixtureSpec.manifestBytes, manifest_eq, jcsBytes_data]; kernel_rfl

theorem certSigPayloadJ_eq : golden.certSigPayloadJ =
    (certSigPayload { members := golden.certMembers (hexEncode Lit.semHash) (hexEncode Lit.intHash),
                      semanticHash := Lit.semHash, integrityHash := Lit.intHash }).getD .null := by
  rw [FixtureSpec.certSigPayloadJ, certV2_eq]

theorem certMsg_eq : golden.certMsg = Lit.certMsg := by
  rw [FixtureSpec.certMsg, signedMessage_eq, certSigPayloadJ_eq]; kernel_rfl

theorem pkgMsg_eq : golden.pkgMsg = Lit.pkgMsg := by
  rw [FixtureSpec.pkgMsg, signedMessage_eq, manifest_eq]; kernel_rfl

theorem certMsgDigest_eq : sha256 golden.certMsg = Lit.certMsgDigest := by
  rw [certMsg_eq, sha256_eq_sha256Fast]; kernel_rfl

theorem pkgMsgDigest_eq : sha256 golden.pkgMsg = Lit.pkgMsgDigest := by
  rw [pkgMsg_d—P–ÄL@¯ÎoÖ™Ï