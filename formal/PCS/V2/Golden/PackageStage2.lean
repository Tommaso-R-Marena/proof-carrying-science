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
def memberShaTable : List (List UInt8 Ã— List UInt8) :=
  [(golden.trace.data.toList, Lit.traceDigest), (Lit.certBytes, Lit.certDigest),
   (Lit.wireBytes, Lit.wireDigest), (Lit.indexBytes, Lit.indexDigest)]

theorem memberShaTable_correct : MemoCorrect memberShaTable :=
  memoCorrect_cons traceDigest_eq <|
  memoCorrect_cons (certBytes_eq â–¸ certDigest_eq) <|
  memoCorrect_cons (wireBytes_eq â–¸ wireDigest_eq) <|
  memoCorrect_cons (indexBytes_eq â–¸ indexDigest_eq) memoCorrect_nil

theorem fileMapOK_golden : fileMapOK authorityUnicode manifestV certV certBA filesV = true := by
  delta fileMapOK memberOK namespaceOK nameOK portableKey parentPrefixes
  rw [segments_eq_segmentsFuel segmentsFuelBound, sha256_eq_sha256Memo memberShaTable_correct,
    PCS.V2.KernelEq.byteArray_instDecidableEq_eq]
  kernel_rfl

/-! ## Package signature -/

theorem pkgMsgV : signedMessage packageSignatureDomain (encodeManifest manifestV) = Lit.pkgMsg := by
  rw [â† manifest_eq, â† FixtureSpec.pkgMsg, pkgMsg_eq]

theorem pkgMsgDigest_lit : sha256 Lit.pkgMsg = Lit.pkgMsgDigest := by
  rw [â† pkgMsg_eq]; exact pkgMsgDigest_eq

def pkgRecV : SigRecordV2 :=
  { domain := packageSignatureDomain, payload := encodeManifest manifestV,
    payloadSha256 := Lit.pkgMsgDigest, fingerprint := Lit.fingerprint, signature := goldenPkgSig }

theorem pkgSigBA_jcs : pkgSigBA = jcsBytes (encodeSigRecord pkgRecV) := by
  rw [â† pkgSigBA_eq, FixtureSpec.pkgSigBytesWith, pkgSigRecord_eq, manifest_eq]; rfl

theorem pkgRec_canonical : canonical (encodeSigRecord pkgRecV) = true := by kernel_rfl

theorem pkgRec_decode : decodeSigRecord (encodeSigRecord pkgRecV) = some pkgRecV := by kernel_rfl

theorem verifyPkgSig_golden :
    verifySigRecordBytes PCS.V2.Ed25519.verify tesMÄ­5ÙÈZ®