import PCS.V2.Golden.PackageStage2
import PCS.V2.GoldenCx.PackageStage
import PCS.V2.KernelEq
import PCS.V2.SplitOnFuel
import PCS.V2.SHA256Memo

/-!
# Counterexample fixture `cx`, stage 1 concluded: file map, package signature, `verifyPackage`

*Counterexample archive `cx` (`PCS.V2.GoldenCx.Spec`).*  This file is a mechanical
clone of the corresponding `PCS.V2.Golden` file with the fixture `golden` replaced by `cx`;
all generic lemmas are reused from `PCS.V2.Golden`.
-/

set_option autoImplicit false

namespace PCS.V2.GoldenCx

open PCS PCS.V2.Json PCS.V2.Hex PCS.V2.Domains PCS.V2.Package PCS.V2.Signature PCS.V2.Canonical
open PCS.V2.Witnesses.AISafetyGolden PCS.V2.SHA256 PCS.V2.Index PCS.V2.CertificateModel
open PCS.V2.EndToEnd PCS.V2.Authority PCS.V2.SplitOnFuel PCS.V2.SHA256Memo

/-! ## File map -/

/-- Proved SHA-256 facts for the four signed members (each kernel-checked once). -/
def memberShaTable : List (List UInt8 × List UInt8) :=
  [(cx.trace.data.toList, Lit.traceDigest), (Lit.certBytes, Lit.certDigest),
   (Lit.wireBytes, Lit.wireDigest), (Lit.indexBytes, Lit.indexDigest)]

theorem memberShaTable_correct : MemoCorrect memberShaTable :=
  memoCorrect_cons traceDigest_eq <|
  memoCorrect_cons (certBytes_eq ▸ certDigest_eq) <|
  memoCorrect_cons (wireBytes_eq ▸ wireDigest_eq) <|
  memoCorrect_cons (indexBytes_eq ▸ indexDigest_eq) memoCorrect_nil

theorem fileMapOK_cx : fileMapOK authorityUnicode manifestV certV certBA filesV = true := by
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
    payloadSha256 := Lit.pkgMsgDigest, fingerprint := Lit.fingerprint, signature := cxPkgSig }

theorem pkgSigBA_jcs : pkgSigBA = jcsBytes (encodeSigRecord pkgRecV) := by
  rw [← pkgSigBA_eq, FixtureSpec.pkgSigBytesWith, pkgSigRecord_eq, manifest_eq]; rfl

theorem pkgRec_canonical : canonical (encodeSigRecord pkgRecV) = true := by kernel_rfl

theorem pkgRec_decode : decodeSigRecord (encodeSigRecord pkgRecV) = some pkgRecV := by kernel_rfl

theorem verifyPkgSig_cx :
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

/-! ## Stage 1 composed: `verifyPackage` on the cx input -/

/-- The package-stage result on the cx input. -/
def pkgResultV : PackageResult :=
  { cert := certV, certSignature := certRecV, manifest := manifestV, packageSignature := pkgRecV }

theorem verifyPackage_cx :
    verifyPackage authorityUnicode PCS.V2.Ed25519.verify testPk (some Lit.fingerprint) inputV =
      some pkgResultV :=
  PCS.V2.Golden.verifyPackage_of_stages (inp := inputV) verifyCertBytes_certBA certSigPayload_certV
    verifyCertSig_cx verifyManifestBytes_cx fileMapOK_cx verifyPkgSig_cx

end PCS.V2.GoldenCx
