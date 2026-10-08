import PCS.V2.Golden.PackageStage2

/-!
# Golden fixture, stage 2: certificate model, replay, normalized set, transcript

Kernel-checked evaluation of the remaining stages of `acceptPCSWithCheckers` (the
authority executed by `pcs-lean-authority`, with the certified domain-checker registry) on
the golden package input `inputV`, composed into
`acceptPCSWithCheckers_golden : acceptPCSWithCheckers certifiedRegistry goldenTranscript
goldenAnchor inputV = some resultV`.

Composition lemmas (`acceptPCS_of_stages`, `verifyNormalizedSet_of_stages`, …) are stated over
arbitrary inputs and proved by `simp` on hypotheses, so no concrete evaluation happens in the
elaborator; each concrete stage is a separate kernel-checked fact.
-/

set_option autoImplicit false

namespace PCS.V2.Golden

open PCS PCS.V2.Json PCS.V2.Hex PCS.V2.Domains PCS.V2.Package PCS.V2.Signature PCS.V2.Canonical
open PCS.V2.Witnesses.AISafetyGolden PCS.V2.SHA256 PCS.V2.Index PCS.V2.CertificateModel
open PCS.V2.EndToEnd PCS.V2.Authority PCS.V2.SplitOnFuel PCS.V2.SHA256Memo PCS.V2.Replay
open PCS.V2.NormalizedWire PCS.V2.DomainAuthority PCS.V2.Checkers

/-! ## Generic composition lemmas (arbitrary inputs) -/

theorem acceptPCS_of_stages {O : Oracles} {T : TrustAnchor} {inp : PackageInput}
    {pr : PackageResult} {m : CertModel} {env : Option (EnvBinding × List InventoryItem)}
    {table : List (String × ByteArray)} {i : IndexV2} {ps : List (EntryV2 × WireV2)}
    (h1 : verifyPackage O.unicode O.ed25519 T.pk T.expected inp = some pr)
    (h2 : decodeCertModel pr.cert = some m)
    (h3 : envStage O.capture pr.cert m inp.files = some env)
    (h4 : O.workflow (.obj pr.cert.members) inp.files = true)
    (h5 : artifactTable m inp.files = some table)
    (h6 : replayOK O.exec pr.cert m table = true)
    (h7 : verifyNormalizedSet inp.files = some (i, ps))
    (h8 : normalizedOK pr.cert m i ps = true) :
    acceptPCS O T inp = some { pkg := pr, model := m, table, env, index := i, claims := ps } := by
  simp only [accept�PЀL@�׾4r�