import PCS.V2.Golden.AuthorityStage
import PCS.V2.GoldenCx.PackageStage2

/-!
# Counterexample fixture `cx`, stage 2: certificate model, replay, normalized set, transcript

*Counterexample archive `cx` (`PCS.V2.GoldenCx.Spec`).*  This file is a mechanical
clone of the corresponding `PCS.V2.Golden` file with the fixture `golden` replaced by `cx`;
all generic lemmas are reused from `PCS.V2.Golden`.

Kernel-checked evaluation of the remaining stages of `acceptPCSWithCheckers` (the
authority executed by `pcs-lean-authority`, with the certified domain-checker registry) on
the cx package input `inputV`, composed into
`acceptPCSWithCheckers_cx : acceptPCSWithCheckers certifiedRegistry cxTranscript
goldenAnchor inputV = some resultV`.

Composition lemmas (`PCS.V2.Golden.acceptPCS_of_stages`, `PCS.V2.Golden.verifyNormalizedSet_of_stages`, …) are stated over
arbitrary inputs and proved by `simp` on hypotheses, so no concrete evaluation happens in the
elaborator; each concrete stage is a separate kernel-checked fact.
-/

set_option autoImplicit false

namespace PCS.V2.GoldenCx

open PCS PCS.V2.Json PCS.V2.Hex PCS.V2.Domains PCS.V2.Package PCS.V2.Signature PCS.V2.Canonical
open PCS.V2.Witnesses.AISafetyGolden PCS.V2.SHA256 PCS.V2.Index PCS.V2.CertificateModel
open PCS.V2.EndToEnd PCS.V2.Authority PCS.V2.SplitOnFuel PCS.V2.SHA256Memo PCS.V2.Replay
open PCS.V2.NormalizedWire PCS.V2.DomainAuthority PCS.V2.Checkers

/-! ## Generic composition lemmas (arbitrary inputs) -/

/-! ## Certificate model, environment, workflow, artifact table, replay -/

/-- The oracles of the executable authority for the cx transcript. -/
abbrev authO : Oracles := authorityOraclesWith certifiedRegistry cxTranscript

/-- The decoded certificate model. -/
def modelV : CertModel := (decodeCertModel certV).getD ⟨"", [], [], [], []⟩

theorem decodeCertModel_cx : decodeCertModel certV = some modelV := by kernel_rfl

theorem envStage_cx : envStage authO.capture certV modelV filesV = some none := by kernel_rfl

theorem workflow_cx : authO.workflow (.obj certV.members) filesV = true := by kernel_rfl

/-- The artifact table: the single SHA-256-checked trace artifact. -/
def tableV : List (String × ByteArray) := [(traceId, cx.trace)]

theorem artifactTable_cx : artifactTable modelV filesV = some tableV := by
  delta artifactTable artifactEntry
  rw [sha256_eq_sha256Memo memberShaTable_correct]
  kernel_rfl

/-- **Replay**: the single evidence item `E1` is re-executed by the certified
    `trace_invariant` checker on the delivered trace, and its fresh observation equals the
    recorded `computational_test`/`PASS`. -/
theorem replayOK_cx : replayOK authO.exec certV modelV tableV = true := by kernel_rfl

/-! ## Normalized index and decision wire -/

theorem indexBA_jcs : indexBA = jcsBytes (encodeIndex indexV) := by
  rw [← indexBA_eq, FixtureSpec.indexBytes, index_eq]

theorem index_canonical : canonical (encodeIndex indexV) = true := by kernel_rfl

theorem index_decode : decodeIndex (encodeIndex indexV) = some indexV := by kernel_rfl

theorem index_semanticOK : Index.semanticOK indexV = true := by
  delta Index.semanticOK Index.expectedHash
  rw [PCS.V2.Golden.domainDigest_eq, sha256_eq_sha256Fast]
  kernel_rfl

theorem verifyIndexBytes_cx : verifyIndexBytes indexBA = some indexV := by
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
  rw [PCS.V2.Golden.domainDigest_eq, sha256_eq_sha256Fast]
  kernel_rfl

theorem verifyWireBytes_cx : verifyWireBytes wireBA = some wireV := by
  have hs : (jcsBytes (encodeWire wireV)).size ≤ maxWireBytes := by
    rw [← wireBA_jcs]; decide +kernel
  rw [wireBA_jcs, verifyWireBytes, parseCanonicalBytes_complete wire_canonical hs]
  simp only [wire_decode, wire_semanticOK, if_true]

/-- The single index entry (claim `C1`). -/
def entryV : EntryV2 :=
  { claimId := "C1", decision := .computational, storageKey := Lit.storageKeyC1,
    wireSemanticHash := Lit.wireHash }

theorem indexV_entries : indexV.entries = [entryV] := rfl

theorem lookup_index_cx : lookup filesV indexPath = some indexBA := by kernel_rfl

theorem lookup_wire_cx : lookup filesV (keyPath entryV.storageKey) = some wireBA := by
  kernel_rfl

theorem membersOK_cx : membersOK filesV indexV = true := by kernel_rfl

theorem entryBinds_cx : entryBinds indexV entryV wireV = true := by kernel_rfl

theorem verifyNormalizedSet_cx :
    verifyNormalizedSet filesV = some (indexV, [(entryV, wireV)]) :=
  PCS.V2.Golden.verifyNormalizedSet_of_stages lookup_index_cx verifyIndexBytes_cx membersOK_cx
    (indexV_entries ▸ PCS.V2.Golden.checkEntries_single lookup_wire_cx verifyWireBytes_cx
      entryBinds_cx)

theorem normalizedOK_cx : normalizedOK certV modelV indexV [(entryV, wireV)] = true := by
  delta normalizedOK
  simp only [deriveWire, NormalizedWire.expectedHash, commitmentOf, PCS.V2.Golden.domainDigest_eq,
    sha256_eq_sha256Fast]
  kernel_rfl

/-! ## Stage 2 composed: the executable authority's acceptance on the cx input -/

/-- The accepted result on the cx input. -/
def resultV : AcceptedResult :=
  { pkg := pkgResultV, model := modelV, table := tableV, env := none, index := indexV,
    claims := [(entryV, wireV)] }

/-- The cx transcript with its certificate hash as a literal. -/
theorem cxTranscript_eq : cxTranscript =
    { certificateSemanticHash := Lit.semHash, checkerVersion := checkerVersion,
      workflowOk := true, environmentCapture := .null,
      replay := [⟨"E1", .computationalTest, .pass⟩], workflowAnalysis := [] } := by
  rw [cxTranscript, FixtureSpec.transcript, semHash_eq]; rfl

theorem transcriptCovers_cx : transcriptCovers cxTranscript resultV = true := by
  rw [cxTranscript_eq]; kernel_rfl

theorem acceptPCS_cx : acceptPCS authO goldenAnchor inputV = some resultV := by
  rw [goldenAnchor_eq]
  exact PCS.V2.Golden.acceptPCS_of_stages verifyPackage_cx decodeCertModel_cx envStage_cx
    workflow_cx artifactTable_cx replayOK_cx verifyNormalizedSet_cx
    normalizedOK_cx

/-- **Decoded-package acceptance (kernel-checked).**  The certified extended authority
    (built-ins + certified domain-checker registry, transcript fallback) accepts the cx
    package input. -/
theorem acceptPCSWithCheckers_cx :
    acceptPCSWithCheckers certifiedRegistry cxTranscript goldenAnchor inputV = some resultV :=
  PCS.V2.Golden.acceptPCSWithCheckers_of acceptPCS_cx transcriptCovers_cx

end PCS.V2.GoldenCx
