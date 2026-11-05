import PCS.V2.Golden.PackageStage
import PCS.V2.KernelEq
import PCS.V2.SplitOnFuel
import PCS.V2.SHA256Memo

/-!
# Golden fixture, stage 1 concluded: file map, package signature, `verifyPackage`
-/

set_option autoImplicit false

namespace PCS.V2.Golden

open PCS PCS.V2.Json PCS.V2.Hex PCS.V2.Domains PCS.V2.Package PCS.V2.Signature PCS.V2.Canonical
open PCS.V2.Witnesses.AISafetyGolden PCS.V2.SHA256 PCS.V2.Index PCS.V2.CertificateModel
open PCS.V2.EndToEnd PCS.V2.Authority PCS.V2.SplitOnFuel PCS.V2.SHA256Memo

/-! ## File map -/

/-- Proved SHA-256 facts for the four signed members (each kernel-checked once). -/
def memberShaTable : List (List UInt8 × List UInt8) :=
  [(golden.trace.data.toList, Lit.traceDigest), (Lit.certBytes, Lit.certDigest),
   (Lit.wireBytes, Lit.wireDigest), (Lit.indexBytes, Lit.indexDigest)]

theorem memberShaTable_correct : MemoCorrect memberShaTable :=
  memoCorrect_cons traceDigest_eq <|
  memoCorrect_cons (certBytes_eq ▸ certDigest_eq) <|
  memoCorrect_cons (wireBytes_eq ▸ wireDigest_eq) <|
  memoCorrect_cons (indexBytes_eq ▸ indexDigest_eq) memoCorrect_nil

theorem fileMapOK_golden : fileMapOK authorityUnicode manifestV certV certBA filesV = true := by
  delta fileMapOK memberOK namespaceOK nameOK portableKey parentPrefixes
  rw [segments_eq_segmentsFuel segmentsFuelBound, sha256_eq_sha256Memo memberShaTable_correct,
    PCS.V2.KernelEq.byteArray_instDecidableEq_eq]
  kernel_rfl

/-! ## Package signature -/

theorem pkgMsgV : signedMessage packageSignatureDomain (encodeManifest manifestV) = Lit.pkgMsg := by
  rw [← manifest_eq, ← FixtureSpec.pkgMsg, pkgMsg_eq]

theorem pkgMsgDigest_lit : sha256 Lit.pkgMsg = Lit.pkgMsgDigest := by
  rw [← pkgMsg_eq]; exact pkgMsgDigest_eq

def pkgRecV : SigRecordV2 :=
  { domain := packageSignatureDomain, payload := encodeManifest manifestV,
    payloadSha256 := Lit.pkgMsgDigest, fingerprint := Lit.fingerprint, signature := goldenPkgSig }

theorem pkgSigBA_jcs : pkgSigBA = jcsBytes (encodeSigRecord pkgRecV) := by
  rw [← pkgSigBA_eq, FixtureSpec.pkgSigBytesWith, pkgSigRecord_eq, manifest_eq]; rfl

theorem pkgRec_canonical : canonical (encodeSigRecord pkgRecV) = true := by kernel_rfl

theorem pkgRec_decode : decodeSigRecord (encodeSigRecord pkgRecV) = some pkgRecV := by kernel_rfl

theorem verifyPkgSig_golden :
    verifySigRecordBytes PCS.V2.Ed25519.verify testPk (some Lit.fingerprint)
      packageSignatureDomain (encodeManifest manifestV) pkgSigBA = some pkgRecV := by
  have hs : (jcsBytes (encodeSigRecord pkgRecV)).size ≤ maxSigRecordBytes := by
    rw [← pkgSigBA_jcs]; decide +kernel
  rw [pkgSigBA_jcs, verifySigRecordBytes, parseCanonicalBytes_complete pkgRec_canonical hs]
  dsimp only
  rw [pkgRec_decode]
  dsimp only
  simp only [pkgMsgV, pkgRecV, pkgSig_verifies, pkgMsgDigest_lit, pinOK, fingerprint_eq]
  kernel_rfl

/-! ## Stage 1 composed: `verifyPackage` on the golden input -/

/-- The package-stage result on the golden input. -/
def pkgResultV : PackageResult :=
  { cert := certV, certSignature := certRecV, manifest := manifestV, packageSignature := pkgRecV }

/-- `verifyPackage` succeeds once each of its stages is known to succeed (stated over
arbitrary inputs, so no concrete evaluation happens in the elaborator). -/
theorem verifyPackage_of_stages {U : UnicodeOps} {V : Ed25519Verify} {pk : List UInt8}
    {expected : Option (List UInt8)} {inp : PackageInput} {c : CertV2} {csp : JVal}
    {cs ps : SigRecordV2} {m : ManifestV2}
    (h1 : verifyCertBytes inp.certificateBytes = some c)
    (h2 : certSigPayload c = some csp)
    (h3 : verifySigRecordBytes V pk expected certificateSignatureDomain csp
            inp.certificateSignatureBytes = some cs)
    (h4 : verifyManifestBytes U inp.manifestBytes = some m)
    (h5 : fileMapOK U m c inp.certificateBytes inp.files = true)
    (h6 : verifySigRecordBytes V pk expected packageSignatureDomain (encodeManifest m)
            inp.packageSignatureBytes = some ps) :
    verifyPackage U V pk expected inp =
      some { cert := c, certSignature := cs, manifest := m, packageSignature := ps } := by
  simp only [verifyPackage, h1, h2, h3, h4, h5, h6, if_true]

theorem verifyPackage_golden :
    verifyPackage authorityUnicode PCS.V2.Ed25519.verify testPk (some Lit.fingerprint) inputV =
      some pkgResultV :=
  verifyPackage_of_stages (inp := inputV) verifyCertBytes_certBA certSigPayload_certV
    verifyCertSig_golden verifyManifestBytes_golden fileMapOK_golden verifyPkgSig_golden

end PCS.V2.Golden
