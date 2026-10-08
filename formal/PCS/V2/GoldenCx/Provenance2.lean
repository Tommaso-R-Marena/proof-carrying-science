import PCS.V2.GoldenCx.Provenance

/-!
# Provenance of the cx manifest, signed messages and signature records

*Counterexample archive `cx` (`PCS.V2.GoldenCx.Spec`).*  This file is a mechanical
clone of the corresponding `PCS.V2.Golden` file with the fixture `golden` replaced by `cx`;
all generic lemmas are reused from `PCS.V2.Golden`.

Continuation of `PCS.V2.Golden.Provenance` (split for build parallelism).
-/

set_option autoImplicit false

namespace PCS.V2.GoldenCx

open PCS PCS.V2.Json PCS.V2.Hex PCS.V2.Domains PCS.V2.Package PCS.V2.Signature
open PCS.V2.Witnesses.AISafetyGolden PCS.V2.SHA256 PCS.V2.Index PCS.V2.CertificateModel

/-- The package manifest, with literal digests and sizes. -/
def manifestV : ManifestV2 :=
  { certSemanticHash := Lit.semHash, certIntegrityHash := Lit.intHash,
    files := [(tracePath, ⟨Lit.traceDigest, 6⟩), ("certificate.json", ⟨Lit.certDigest, 1686⟩),
              (wirePath, ⟨Lit.wireDigest, 1108⟩), (indexPath, ⟨Lit.indexDigest, 677⟩)] }

theorem manifest_eq : cx.manifest = manifestV := by
  rw [FixtureSpec.manifest, semHash_eq, intHash_eq]
  simp only [FixtureSpec.files, List.map_cons, List.map_nil, traceDigest_eq, certDigest_eq,
    wireDigest_eq, indexDigest_eq, certBytes_size, wireBytes_size, indexBytes_size]
  kernel_rfl

theorem manifestBytes_eq : cx.manifestBytes.data.toList = Lit.manifestBytes := by
  rw [FixtureSpec.manifestBytes, manifest_eq, PCS.V2.Golden.jcsBytes_data]; kernel_rfl

theorem certSigPayloadJ_eq : cx.certSigPayloadJ =
    (certSigPayload { members := cx.certMembers (hexEncode Lit.semHash) (hexEncode Lit.intHash),
                      semanticHash := Lit.semHash, integrityHash := Lit.intHash }).getD .null := by
  rw [FixtureSpec.certSigPayloadJ, certV2_eq]

theorem certMsg_eq : cx.certMsg = Lit.certMsg := by
  rw [FixtureSpec.certMsg, PCS.V2.Golden.signedMessage_eq, certSigPayloadJ_eq]; kernel_rfl

theorem pkgMsg_eq : cx.pkgMsg = Lit.pkgMsg := by
  rw [FixtureSpec.pkgMsg, PCS.V2.Golden.signedMessage_eq, manifest_eq]; kernel_rfl

theorem certMsgDigest_eq : sha256 cx.certMsg = Lit.certMsgDigest := by
  rw [certMsg_eq, sha256_eq_sha256Fast]; kernel_rfl

theorem pkgMsgDigest_eq : sha256 cx.pkgMsg = Lit.pkgMsgDigest := by
  rw [pkgMsg_eq, sha256_eq_sha256Fast]; kernel_rfl

theorem fingerprint_eq : fingerprintOf testPk = Lit.fingerprint := by
  rw [fingerprintOf, sha256_eq_sha256Fast]; kernel_rfl

/-- The certificate signature record, with literal fields. -/
theorem certSigRecord_eq :
    FixtureSpec.sigRecord certificateSignatureDomain cx.certSigPayloadJ cxCertSig =
      { domain := certificateSignatureDomain, payload := cx.certSigPayloadJ,
        payloadSha256 := Lit.certMsgDigest, fingerprint := Lit.fingerprint,
        signature := cxCertSig } := by
  rw [FixtureSpec.sigRecord, ← FixtureSpec.certMsg, certMsgDigest_eq, fingerprint_eq]

theorem pkgSigRecord_eq :
    FixtureSpec.sigRecord packageSignatureDomain (encodeManifest cx.manifest) cxPkgSig =
      { domain := packageSignatureDomain, payload := encodeManifest cx.manifest,
        payloadSha256 := Lit.pkgMsgDigest, fingerprint := Lit.fingerprint,
        signature := cxPkgSig } := by
  rw [FixtureSpec.sigRecord, ← FixtureSpec.pkgMsg, pkgMsgDigest_eq, fingerprint_eq]

theorem certSigBytes_eq : (cx.certSigBytesWith cxCertSig).data.toList = Lit.certSigBytes := by
  rw [FixtureSpec.certSigBytesWith, certSigRecord_eq, PCS.V2.Golden.jcsBytes_data, certSigPayloadJ_eq]; kernel_rfl

theorem pkgSigBytes_eq : (cx.pkgSigBytesWith cxPkgSig).data.toList = Lit.pkgSigBytes := by
  rw [FixtureSpec.pkgSigBytesWith, pkgSigRecord_eq, PCS.V2.Golden.jcsBytes_data, manifest_eq]; kernel_rfl

end PCS.V2.GoldenCx
