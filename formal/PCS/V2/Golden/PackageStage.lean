import PCS.V2.Golden.Stages
import PCS.V2.SplitOnFuel
import PCS.V2.SHA256Memo

/-!
# Golden fixture, stage 1 continued: manifest, file map, package signature, `verifyPackage`
-/

set_option autoImplicit false

namespace PCS.V2.Golden

open PCS PCS.V2.Json PCS.V2.Hex PCS.V2.Domains PCS.V2.Package PCS.V2.Signature PCS.V2.Canonical
open PCS.V2.Witnesses.AISafetyGolden PCS.V2.SHA256 PCS.V2.Index PCS.V2.CertificateModel
open PCS.V2.EndToEnd PCS.V2.Authority PCS.V2.SplitOnFuel PCS.V2.SHA256Memo

theorem manifestBA_jcs : manifestBA = jcsBytes (encodeManifest manifestV) := by
  rw [← manifestBA_eq, FixtureSpec.manifestBytes, manifest_eq]

theorem manifest_canonical : canonical (encodeManifest manifestV) = true := by kernel_rfl

theorem manifest_decode : decodeManifest (encodeManifest manifestV) = some manifestV := by kernel_rfl

theorem manifestOK_golden : manifestOK authorityUnicode manifestV = true := by
  delta manifestOK namespaceOK nameOK portableKey parentPrefixes
  rw [segments_eq_segmentsFuel segmentsFuelBound]
  kernel_rfl

theorem verifyManifestBytes_golden :
    verifyManifestBytes authorityUnicode manifestBA = some manifestV := by
  have hs : (jcsBytes (encodeManifest manifestV)).size ≤ maxManifestBytes := by
    rw [← manifestBA_jcs]; decide +kernel
  rw [manifestBA_jcs, verifyManifestBytes, parseCanonicalBytes_complete manifest_canonical hs]
  dsimp only
  rw [manifest_decode]
  dsimp only
  rw [manifestOK_golden]
  rfl

end PCS.V2.Golden
