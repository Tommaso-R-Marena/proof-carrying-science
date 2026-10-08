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
    files := [(tracePath, ‚ü®Lit.traceDigest, 6‚ü©), ("certificate.json", ‚ü®Lit.certDigest, 1686‚ü©),
              (wirePath, ‚ü®Lit.wireDigest, 1108‚ü©), (indexPath, ‚ü®Lit.indexDigest, 677‚ü©)] }

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
  rw [FixtureSpec.certMsg, PCS.V2.Golden.signedMessage_eq, certSigPayloadJ_eq]; kernd—P–ÄL@¯˜mÖ™Ï