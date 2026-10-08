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
def memberShaTable : List (List UInt8 Ã— List UInt8) :=
  [(cx.trace.data.toList, Lit.traceDigest), (Lit.certBytes, Lit.certDigest),
   (Lit.wireBytes, Lit.wireDigest), (Lit.indexBytes, Lit.indexDigest)]

theorem memberShaTable_correct : MemoCorrect memberShaTable :=
  memoCorrect_cons traceDigest_eq <|
  memoCorrect_cons (certBytes_eq â–¸ certDigest_eq) <|
  memoCorrect_cons (wireBytes_eq â–¸ wireDigest_eq) <|
  memoCorrect_cons (indexBytes_eq â–¸ indexDigest_eq) memoCorrect_nil

theorem fileMapOK_cx : fileMapOK authorityUnicode manifestV certV certBA filesV = true := by
  delta fileMapOK memberOK namespaceOK nameOK portableKey parentPrefixes
  rw [segments_eq_segmentsFuel segmentsFuelBound, sha256_eq_sha256Memo memberShaTable_correct,
    PCS.V2.KernelEq.byteArray_instDecidableEq_eq]
  kernel_rfl

/-! ## Package signature -/

theorem pkgMsgV : signedMessage packageSignatureDomain (encodeManifest manifestV) = Lit.pkgMsg := by
  rw [â† manifest_eq, â† FixtureSpec.pkgMsg, pkgMsg_eq]

tdÑPÐ€L@ø÷…ªì