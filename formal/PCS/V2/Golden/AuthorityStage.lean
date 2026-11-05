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
  simp only [acceptPCS, h1, h2, h3, h4, h5, h6, h7, h8, if_true]

theorem acceptPCSWithCheckers_of {cs : List CertifiedChecker} {t : AuthorityTranscript}
    {T : TrustAnchor} {inp : PackageInput} {r : AcceptedResult}
    (h : acceptPCS (authorityOraclesWith cs t) T inp = some r) (hc : transcriptCovers t r = true) :
    acceptPCSWithCheckers cs t T inp = some r := by
  simp only [acceptPCSWithCheckers, h, hc, if_true]

theorem checkEntries_single {files : FileMap} {i : IndexV2} {e : EntryV2} {raw : ByteArray}
    {w : WireV2} (h1 : lookup files (keyPath e.storageKey) = some raw)
    (h2 : verifyWireBytes raw = some w) (h3 : entryBinds i e w = true) :
    checkEntries files i [e] = some [(e, w)] := by
  simp only [checkEntries, h1, h2, h3, if_true, Option.map_some]

theorem verifyNormalizedSet_of_stages {files : FileMap} {raw : ByteArray} {i : IndexV2}
    {ps : List (EntryV2 × WireV2)} (h1 : lookup files indexPath = some raw)
    (h2 : verifyIndexBytes raw = some i) (h3 : membersOK files i = true)
    (h4 : checkEntries files i i.entries = some ps) :
    verifyNormalizedSet files = some (i, ps) := by
  simp only [verifyNormalizedSet, h1, h2, h3, h4, if_true, Option.map_some]

/-! ## Certificate model, environment, workflow, artifact table, replay -/

/-- The oracles of the executable authority for the golden transcript. -/
abbrev authO : Oracles := authorityOraclesWith certifiedRegistry goldenTranscript

/-- The decoded certificate model. -/
def modelV : CertModel := (decodeCertModel certV).getD ⟨"", [], [], [], []⟩

theorem decodeCertModel_golden : decodeCertModel certV = some modelV := by kernel_rfl

theorem envStage_golden : envStage authO.capture certV modelV filesV = some none := by kernel_rfl

theorem workflow_golden : authO.workflow (.obj certV.members) filesV = true := by kernel_rfl

/-- The artifact table: the single SHA-256-checked trace artifact. -/
def tableV : List (String × ByteArray) := [(traceId, golden.trace)]

theorem artifactTable_golden : artifactTable modelV filesV = some tableV := by
  delta artifactTable artifactEntry
  rw [sha256_eq_sha256Memo memberShaTable_correct]
  kernel_rfl

/-- **Replay**: the single evidence item `E1` is re-executed by the certified
    `trace_invariant` checker on the delivered trace, and its fresh observation equals the
    recorded `computational_test`/`PASS`. -/
theorem replayOK_golden : replayOK authO.exec certV modelV tableV = true := by kernel_rfl

/-! ## Normalized index and decision wire -/

theorem indexBA_jcs : indexBA = jcsBytes (encodeIndex indexV) := by
  rw [← indexBA_eq, FixtureSpec.indexBytes, index_eq]

theorem index_canonical : canonical (encodeIndex indexV) = true := by kernel_rfl

theorem index_decode : decodeIndex (encodeIndex indexV) = some indexV := by kernel_rfl

theorem index_semanticOK : Index.semanticOK indexV = true := by
  delta Index.semanticOK Index.expectedHash
  rw [domainDigest_eq, sha256_eq_sha256Fast]
  kernel_rfl

theorem verifyIndexBytes_golden : verifyIndexBytes indexBA = some indexV := by
  have hs : (jcsBytes (encodeIndex indexV)).size ≤ maxIndexBytes := by
    rw [← indexBA_jcs]; decide +kernel
  rw [indexBA_jcs, verifyIndexBytes, parseCanonicalBytes_complete index_canonical hs]
  simp only [index_decode, index_semanticOK, if_true]

theorem wireBA_jcs : wireBA = jcsBytes (encodeWire wireV) := by
  rw [← wireBA_eq, FixtureSpec.wireBytes, encodedBytes, wire_eq]

theorem wire_canonical : canonical (encodeWire wireV) = true := by kernel_rfl

theorem wire_decode : decodeWire (encodeWire wireV) = some wireV := by kernel_rfl

theorem wire_semanticOK : NormalizedWire.semanticOK wireV = true := by
  delta NormalizedWire.semanticOK hashOK NormalizedWire.expectedHash
  rw [domainDigest_eq, sha256_eq_sha256Fast]
  kernel_rfl

theorem verifyWireBytes_golden : verifyWireBytes wireBA = some wireV := by
  have hs : (jcsBytes (encodeWire wireV)).size ≤ maxWireBytes := by
    rw [← wireBA_jcs]; decide +kernel
  rw [wireBA_jcs, verifyWireBytes, parseCanonicalBytes_complete wire_canonical hs]
  simp only [wire_decode, wire_semanticOK, if_true]

/-- The single index entry (claim `C1`). -/
def entryV : EntryV2 :=
  { claimId := "C1", decision := .computational, storageKey := Lit.storageKeyC1,
    wireSemanticHash := Lit.wireHash }

theorem indexV_entries : indexV.entries = [entryV] := rfl

theorem lookup_index_golden : lookup filesV indexPath = some indexBA := by kernel_rfl

theorem lookup_wire_golden : lookup filesV (keyPath entryV.storageKey) = some wireBA := by
  kernel_rfl

theorem membersOK_golden : membersOK filesV indexV = true := by kernel_rfl

theorem entryBinds_golden : entryBinds indexV entryV wireV = true := by kernel_rfl

theorem verifyNormalizedSet_golden :
    verifyNormalizedSet filesV = some (indexV, [(entryV, wireV)]) :=
  verifyNormalizedSet_of_stages lookup_index_golden verifyIndexBytes_golden membersOK_golden
    (indexV_entries ▸ checkEntries_single lookup_wire_golden verifyWireBytes_golden
      entryBinds_golden)

theorem normalizedOK_golden : normalizedOK certV modelV indexV [(entryV, wireV)] = true := by
  delta normalizedOK
  simp only [deriveWire, NormalizedWire.expectedHash, commitmentOf, domainDigest_eq,
    sha256_eq_sha256Fast]
  kernel_rfl

/-! ## Stage 2 composed: the executable authority's acceptance on the golden input -/

/-- The accepted result on the golden input. -/
def resultV : AcceptedResult :=
  { pkg := pkgResultV, model := modelV, table := tableV, env := none, index := indexV,
    claims := [(entryV, wireV)] }

/-- The golden transcript with its certificate hash as a literal. -/
theorem goldenTranscript_eq : goldenTranscript =
    { certificateSemanticHash := Lit.semHash, checkerVersion := checkerVersion,
      workflowOk := true, environmentCapture := .null,
      replay := [⟨"E1", .computationalTest, .pass⟩], workflowAnalysis := [] } := by
  rw [goldenTranscript, FixtureSpec.transcript, semHash_eq]; rfl

theorem transcriptCovers_golden : transcriptCovers goldenTranscript resultV = true := by
  rw [goldenTranscript_eq]; kernel_rfl

theorem acceptPCS_golden : acceptPCS authO goldenAnchor inputV = some resultV := by
  rw [goldenAnchor_eq]
  exact acceptPCS_of_stages verifyPackage_golden decodeCertModel_golden envStage_golden
    workflow_golden artifactTable_golden replayOK_golden verifyNormalizedSet_golden
    normalizedOK_golden

/-- **Decoded-package acceptance (kernel-checked).**  The certified extended authority
    (built-ins + certified domain-checker registry, transcript fallback) accepts the golden
    package input. -/
theorem acceptPCSWithCheckers_golden :
    acceptPCSWithCheckers certifiedRegistry goldenTranscript goldenAnchor inputV = some resultV :=
  acceptPCSWithCheckers_of acceptPCS_golden transcriptCovers_golden

end PCS.V2.Golden
