import PCS.V2.FailClosedGate

/-!
# Properties of the fail-closed gates (arbitrary inputs)
-/

set_option autoImplicit false

namespace PCS.V2.FailClosed

open PCS PCS.V2.Json PCS.V2.EndToEnd PCS.V2.Authority PCS.V2.Replay PCS.V2.Package
open PCS.V2.CertificateModel PCS.V2.Checkers PCS.V2.DomainAuthority PCS.V2.DomainAdapter
open PCS.V2.ClaimGraph PCS.V2.NormalizedWire PCS.V2.Index PCS.V2.Witnesses PCS.V2.PKPDCheck
open PCS.V2.Zip PCS.V2.CanonicalArchive

/-! ## Stages of `acceptPCS` -/

theorem acceptPCS_stages {O : Oracles} {T : TrustAnchor} {inp : PackageInput}
    {r : AcceptedResult} (h : acceptPCS O T inp = some r) :
    verifyPackage O.unicode O.ed25519 T.pk T.expected inp = some r.pkg ∧
    decodeCertModel r.pkg.cert = some r.model ∧
    envStage O.capture r.pkg.cert r.model inp.files = some r.env ∧
    O.workflow (.obj r.pkg.cert.members) inp.files = true ∧
    artifactTable r.model inp.files = some r.table ∧
    replayOK O.exec r.pkg.cert r.model r.table = true ∧
    verifyNormalizedSet inp.files = some (r.index, r.claims) ∧
    normalizedOK r.pkg.cert r.model r.index r.claims = true := by
  unfold acceptPCS at h
  split at h
  · cases h
  · rename_i pr hpr
    split at h
    · cases h
    · rename_i m hm
      split at h
      · cases h
      · rename_i env henv
        split at h
        · rename_i hw
          split at h
          · cases h
          · rename_i table htab
            split at h
            · rename_i hrep
              split at h
              · cases h
              · rename_i i ps hset
                split at h
                · rename_i hn
                  cases h
                  exact ⟨hpr, hm, henv, hw, htab, hrep, hset, hn⟩
                · cases h
            · cases h
        · cases h

theorem acceptPCS_of_stages {O : Oracles} {T : TrustAnchor} {inp : PackageInput}
    {pr : PackageResult} {m : Cet�PЀL@��vr�