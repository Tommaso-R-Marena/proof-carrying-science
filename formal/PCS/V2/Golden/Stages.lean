import PCS.V2.Golden.Provenance2
import PCS.V2.Golden.Crypto
import PCS.V2.ExecutableAuthority

/-!
# Kernel-checked stage-by-stage evaluation of the authority on the golden package

Each lemma evaluates one stage of the production checker (`PCS.V2.EndToEnd.acceptPCS`
inside `PCS.V2.DomainAuthority.certifiedAuthority`) on the golden fixture.  Canonical-JSON
byte gates are discharged by the proved completeness theorem
`PCS.V2.Canonical.parseCanonicalBytes_complete` (the bytes are, by construction, the
canonical serialization of a canonical value), never by re-parsing; everything else is
kernel evaluation (`kernel_rfl`) of the production functions, after proved rewrites
(`sha256_eq_sha256Fast`, `jcsBytes_data`, literal provenance lemmas).
-/

set_option autoImplicit false

namespace PCS.V2.Golden

open PCS PCS.V2.Json PCS.V2.Hex PCS.V2.Domains PCS.V2.Package PCS.V2.Signature PCS.V2.Canonical
open PCS.V2.Witnesses.AISafetyGolden PCS.V2.SHA256 PCS.V2.Index PCS.V2.CertificateModel
open PCS.V2.EndToEnd

/-- The certificate JSON value with literal hashes. -/
def certJV : JVal := .obj (golden.certMembers (hexEncode Lit.semHash) (hexEncode Lit.intHash))

/-- The parsed certificate. -/
def certV : CertV2 :=
  { members := golden.certMembers (hexEncode Lit.semHash) (hexEncode Lit.intHash),
    semanticHash := Lit.semHash, integrityHash := Lit.intHash }

theorem certBytes_jcs : golden.certBytes = jcsBytes certJV := by
  rw [FixtureSpec.certBytes, certJ_eq]; rfl

theorem certJV_canonical : canonical certJV = true := by kernel_rfl

theorem verifyCertBytes_golden : verifyCertBytes golden.certBytes = some certV := by
  have hs : (jcsBytes certJV).size ≤ maxCertificateBytes := by
    rw [← certBytes_jcs, certBytes_size]; decide
  rw [certBytes_jcs, verifyCertBytes, parseCanonicalBytes_complete certJV_canonical hs]
  simp only [certJV, certHashesOK, domainDigest_eq, sha256_eq_sha256Fast]
  kernel_rfl

/-! ## Member bytes as literal byte arrays -/

theorem ba_of_toList {a : ByteArray} {l : List UInt8} (h : a.data.toList = l) :
    a = ⟨⟨l⟩⟩ := by
  cases a with | mk d => cases d with | mk l' => subst h; rfl

def certBA : ByteArray := ⟨⟨Lit.certBytes⟩⟩
def wireBA : ByteArray := ⟨⟨Lit.wireBytes⟩⟩
def indexBA : ByteArray := ⟨⟨Lit.indexBytes⟩⟩
def manifestBA : ByteArray := ⟨⟨Lit.manifestBytes⟩⟩
def certSigBA : ByteArray := ⟨⟨Lit.certSigBytes⟩⟩
def pkgSigBA : ByteArray := ⟨⟨Lit.pkgSigBytes⟩⟩

theorem certBA_eq : golden.certBytes = certBA := ba_of_toList certBytes_eq
theorem wireBA_eq : golden.wireBytes = wireBA := ba_of_toList wireBytes_eq
theorem indexBA_eq : golden.indexBytes = indexBA := ba_of_toList indexBytes_eq
theorem manifestBA_eq : golden.manifestBytes = manifestBA := ba_of_toList manifestBytes_eq
theorem certSigBA_eq : golden.certSigBytesWith goldenCertSig = certSigBA := ba_of_toList certSigBytes_eq
theorem pkgSigBA_eq : golden.pkgSigBytesWith goldenPkgSig = pkgSigBA := ba_of_toList pkgSigBytes_eq

/-- The signed (non-control) package members, as delivered. -/
def filesV : FileMap :=
  [(tracePath, golden.trace), ("certificate.json", certBA), (wirePath, wireBA), (indexPath, indexBA)]

theorem files_eq : golden.files = filesV := by
  rw [FixtureSpec.files, certBA_eq, wireBA_eq, indexBA_eq]; rfl

/-- The materialised golden package input (what `fromArchiveEntries` produces). -/
def inputV : PackageInput :=
  { certificateBytes := certBA, certificateSignatureBytes := certSigBA, manifestBytes := manifestBA,
    packageSignatureBytes := pkgSigBA, files := filesV }

/-! ## Stage 1: certificate, signatures, manifest, file map (`verifyPackage`) -/

theorem certBA_jcs : certBA = jcsBytes certJV := by rw [← certBA_eq, certBytes_jcs]

theorem verifyCertBytes_certBA : verifyCertBytes certBA = some certV := by
  rw [← certBA_eq]; exact verifyCertBytes_golden

/-- The certificate-signature payload (`certificate_signature_payload_v06`). -/
def certPayloadV : JVal := (certSigPayload certV).getD .null

theorem certSigPayload_certV : certSigPayload certV = some certPayloadV := by kernel_rfl

theorem certPayloadV_eq : golden.certSigPayloadJ = certPayloadV := certSigPayloadJ_eq

theorem certMsgV : signedMessage certificateSignatureDomain certPayloadV = Lit.certMsg := by
  rw [← certPayloadV_eq, ← FixtureSpec.certMsg, certMsg_eq]

theorem certMsgDigest_lit : sha256 Lit.certMsg = Lit.certMsgDigest := by
  rw [← certMsg_eq]; exact certMsgDigest_eq

def certRecV : SigRecordV2 :=
  { domain := certificateSignatureDomain, payload := certPayloadV,
    payloadSha256 := Lit.certMsgDigest, fingerprint := Lit.fingerprint, signature := goldenCertSig }

theorem certSigBA_jcs : certSigBA = jcsBytes (encodeSigRecord certRecV) := by
  rw [← certSigBA_eq, FixtureSpec.certSigBytesWith, certSigRecord_eq, certPayloadV_eq]; rfl

theorem certRec_canonical : canonical (encodeSigRecord certRecV) = true := by kernel_rfl

theorem certRec_decode : decodeSigRecord (encodeSigRecord certRecV) = some certRecV := by kernel_rfl

/-- The golden trust anchor's pin is the fingerprint literal. -/
theorem goldenAnchor_eq : goldenAnchor = { pk := testPk, expected := some Lit.fingerprint } := by
  rw [goldenAnchor, fingerprint_eq]

theorem verifyCertSig_golden :
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

end PCS.V2.Golden
