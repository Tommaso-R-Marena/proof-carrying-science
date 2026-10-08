import PCS.V2.Golden.Stages
import PCS.V2.GoldenCx.Provenance2
import PCS.V2.GoldenCx.Crypto
import PCS.V2.ExecutableAuthority

/-!
# Kernel-checked stage-by-stage evaluation of the authority on the cx package

*Counterexample archive `cx` (`PCS.V2.GoldenCx.Spec`).*  This file is a mechanical
clone of the corresponding `PCS.V2.Golden` file with the fixture `golden` replaced by `cx`;
all generic lemmas are reused from `PCS.V2.Golden`.

Each lemma evaluates one stage of the production checker (`PCS.V2.EndToEnd.acceptPCS`
inside `PCS.V2.DomainAuthority.certifiedAuthority`) on the cx fixture.  Canonical-JSON
byte gates are discharged by the proved completeness theorem
`PCS.V2.Canonical.parseCanonicalBytes_complete` (the bytes are, by construction, the
canonical serialization of a canonical value), never by re-parsing; everything else is
kernel evaluation (`kernel_rfl`) of the production functions, after proved rewrites
(`sha256_eq_sha256Fast`, `PCS.V2.Golden.jcsBytes_data`, literal provenance lemmas).
-/

set_option autoImplicit false

namespace PCS.V2.GoldenCx

open PCS PCS.V2.Json PCS.V2.Hex PCS.V2.Domains PCS.V2.Package PCS.V2.Signature PCS.V2.Canonical
open PCS.V2.Witnesses.AISafetyGolden PCS.V2.SHA256 PCS.V2.Index PCS.V2.CertificateModel
open PCS.V2.EndToEnd

/-- The certificate JSON value with literal hashes. -/
def certJV : JVal := .obj (cx.certMembers (hexEncode Lit.semHash) (hexEncode Lit.intHash))

/-- The parsed certificate. -/
def certV : CertV2 :=
  { members := cx.certMembers (hexEncode Lit.semHash) (hexEncode Lit.intHash),
    semanticHash := Lit.semHash, integrityHash := Lit.intHash }

theorem certBytes_jcs : cx.certBytes = jcsBytes certJV := by
  rw [FixtureSpec.certBytes, certJ_eq]; rfl

theorem certJV_canonical : canonical certJV = true := by kernel_rfl

theorem verifyCertBytes_cx : verifyCertBytes cx.certBytes = some certV := by
  have hs : (jcsBytes certJV).size ≤ maxCertificateBytes := by
    rw [← certBytes_jcs, certBytes_size]; decide
  rw [certBytes_jcs, verifyCertBytes, parseCanonicalBytes_complete certJV_canonical hs]
  simp only [certJV, certHashesOK, PCS.V2.Golden.domainDigest_eq, sha256_eq_sha256Fast]
  kernel_rfl

/-! ## Member bytes as literal byte arrays -/

def certBA : ByteArray := ⟨⟨Lit.certBytes⟩⟩
def wireBA : ByteArray := ⟨⟨Lit.wireBytes⟩⟩
def indexBA : ByteArray := ⟨⟨Lit.indexBytes⟩⟩
def manifestBA : ByteArray := ⟨⟨Lit.manifestBytes⟩⟩
def certSigBA : ByteArray := ⟨⟨Lit.certSigBytes⟩⟩
def pkgSigBA : ByteArray := ⟨⟨Lit.pkgSigBytes⟩⟩

theorem certBA_eq : cx.certBytes = certBA := PCS.V2.Golden.ba_of_toList certBytes_eq
theorem wireBA_eq : cx.wireBytes = wireBA := PCS.V2.Golden.ba_of_toList wireBytes_eq
theorem indexBA_eq : cx.indexBytes = indexBA := PCS.V2.Golden.ba_of_toList indexBytes_eq
theorem manifestBA_eq : cx.manifestBytes = manifestBA := PCS.V2.Golden.ba_of_toList manifestBytes_eq
theorem certSigBA_eq : cx.certSigBytesWith cxCertSig = certSigBA := PCS.V2.Golden.ba_of_toList certSigBytes_eq
theorem pkgSigBA_eq : cx.pkgSigBytesWith cxPkgSig = pkgSigBA := PCS.V2.Golden.ba_of_toList pkgSigBytes_eq

/-- The signed (non-control) package members, as delivered. -/
def filesV : FileMap :=
  [(tracePath, cx.trace), ("certificate.json", certBA), (wirePath, wireBA), (indexPath, indexBA)]

theorem files_eq : cx.files = filesV := by
  rw [FixtureSpec.files, certBA_eq, wireBA_eq, indexBA_eq]; rfl

/-- The materialised cx package input (what `fromArchiveEntries` produces). -/
def inputV : PackageInput :=
  { certificateBytes := certBA, certificateSignatureBytes := certSigBA, manifestBytes := manifestBA,
    packageSignatureBytes := pkgSigBA, files := filesV }

/-! ## Stage 1: certificate, signatures, manifest, file map (`verifyPackage`) -/

theorem certBA_jcs : certBA = jcsBytes certJV := by rw [← certBA_eq, certBytes_jcs]

theorem verifyCertBytes_certBA : verifyCertBytes certBA = some certV := by
  rw [← certBA_eq]; exact verifyCertBytes_cx

/-- The certificate-signature payload (`certificate_signature_payload_v06`). -/
def certPayloadV : JVal := (certSigPayload certV).getD .null

theorem certSigPayload_certV : certSigPayload certV = some certPayloadV := by kernel_rfl

theorem certPayloadV_eq : cx.certSigPayloadJ = certPayloadV := certSigPayloadJ_eq

theorem certMsgV : signedMessage certificateSignatureDomain certPayloadV = Lit.certMsg := by
  rw [← certPayloadV_eq, ← FixtureSpec.certMsg, certMsg_eq]

theorem certMsgDigest_lit : sha256 Lit.certMsg = Lit.certMsgDigest := by
  rw [← certMsg_eq]; exact certMsgDigest_eq

def certRecV : SigRecordV2 :=
  { domain := certificateSignatureDomain, payload := certPayloadV,
    payloadSha256 := Lit.certMsgDigest, fingerprint := Lit.fingerprint, signature := cxCertSig }

theorem certSigBA_jcs : certSigBA = jcsBytes (encodeSigRecord certRecV) := by
  rw [← certSigBA_eq, FixtureSpec.certSigBytesWith, certSigRecord_eq, certPayloadV_eq]; rfl

theorem certRec_canonical : canonical (encodeSigRecord certRecV) = true := by kernel_rfl

theorem certRec_decode : decodeSigRecord (encodeSigRecord certRecV) = some certRecV := by kernel_rfl

/-- The cx trust anchor's pin is the fingerprint literal. -/
theorem goldenAnchor_eq : goldenAnchor = { pk := testPk, expected := some Lit.fingerprint } := by
  rw [goldenAnchor, fingerprint_eq]

theorem verifyCertSig_cx :
    verifySigRecordBytes PCS.V2.Ed25519.verify testPk (some Lit.fingerprint)
      certificateSignatureDomain certPayloadV certSigBA = some certRecV := by
  have hs : (jcsBytes (encodeSigRecord certRecV)).size ≤ maxSigRecordBytes := by
    rw [← certSigBA_jcs]; decide +kernel
  rw [certSigBA_jcs, verifySigRecordBytes, parseCanonicalBytes_complete certRec_canonical hs]
  dsimp only
  rw [certRec_decode]
  dsimp only
  simp only [certMsgV, certRecV, certSig_verifies, certMsgDigest_lit, pinOK, fingerprint_eq]
  kernel_rfl

end PCS.V2.GoldenCx
