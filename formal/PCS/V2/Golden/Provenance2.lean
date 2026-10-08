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
    files := [(tracePath, ⟨Lit.traceDigest, 6⟩), ("certificate.json", ⟨Lit.certDigest, 1683⟩),
              (wirePath, ⟨Lit.wireDigest, 1108⟩), (indexPath, ⟨Lit.indexDigest, 677⟩)] }

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
  rw [pkgMsg_eq, sha256_eq_sha256Fast]; kernel_rfl

theorem fingerprint_eq : fingerprintOf testPk = Lit.fingerprint := by
  rw [fingerprintOf, sha256_eq_sha256Fast]; kernel_rfl

/-- The certificate signature record, with literal fields. -/
theorem certSigRecord_eq :
    FixtureSpec.sigRecord certificateSignatureDomain golden.certSigPayloadJ goldenCertSig =
      { domain := certificateSignatureDomain, payload := golden.certSigPayloadJ,
        payloadSha256 := Lit.certMsgDigest, fingerprint := Lit.fingerprint,
        signature := goldenCertSig } := by
  rw [FixtureSpec.sigRecord, ← FixtureSpec.certMsg, certMsgDigest_eq, fingerprint_eq]

theorem pkgSigRecord_eq :
    FixtureSpec.sigRecord packageSignatureDomain (encodeManifest golden.manifest) goldenPkgSig =
      { domain := packageSignatureDomain, payload := encodeManifest golden.manifest,
        payloadSha256 := Lit.pkgMsgDigest, fingerprint := Lit.fingerprint,
        signature := goldenPkgSig } := by
  rw [FixtureSpec.sigRecord, ← FixtureSpec.pkgMsg, pkgMsgDigest_eq, fingerprint_eq]

theorem certSigBytes_eq : (golden.certSigBytesWith goldenCertSig).data.toList = Lit.certSigBytes := by
  rw [FixtureSpec.certSigBytesWith, certSigRecord_eq, jcsBytes_data, certSigPayloadJ_eq]; kernel_rfl

theorem pkgSigBytes_eq : (golden.pkgSigBytesWith goldenPkgSig).data.toList = Lit.pkgSigBytes := by
  rw [FixtureSpec.pkgSigBytesWith, pkgSigRecord_eq, jcsBytes_data, manifest_eq]; kernel_rfl

end PCS.V2.Golden
