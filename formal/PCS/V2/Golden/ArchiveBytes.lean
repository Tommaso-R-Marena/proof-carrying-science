import PCS.V2.Golden.Acceptance
import PCS.V2.Golden.FileLiterals
import PCS.V2.Crc32Memo
import PCS.V2.AuthorityCLI

/-!
# The committed golden fixture files, byte for byte

`PCS.V2.Golden.FileLit` holds the bytes of the committed files `archive.zip` and
`observations.json` (and the contents of `pk.b64` / `fingerprint.hex`) as literals.  This file
proves in the kernel that

* the archive literal **is** the canonical encoding of the golden entries
  (`archiveBytes_eq_goldenRaw`), every CRC-32 field included (via kernel-checked CRC
  checkpoints, `PCS.V2.Crc32Memo`);
* the transcript literal is the canonical JSON of the golden transcript and decodes to it
  (`observationsBA_eq`, `decodeAuthorityTranscriptBytes_golden`);
* the public-key and fingerprint strings yield the golden trust anchor (`cliAnchor_golden`);
* hence **`pcs-lean-authority --zip` computes the line `ACCEPT` on these exact bytes**
  (`pcsLeanAuthority_golden_zip_output`), and likewise in directory mode on the seven member
  files in canonical order (`pcsLeanAuthority_golden_dir_output`).

The one link that is not a Lean theorem is "the literal equals the file on disk"; it is
re-checked by `tools/CheckGoldenFileLiterals.lean`, which reads the committed files at run
time and compares them byte for byte with these literals.  (`PCSAuthority.main` itself — file
reading and `println` — is also outside the kernel statement; the theorems are about the pure
function `zipModeOutput` / `dirModeOutput` whose result `main` prints.)
-/

set_option autoImplicit false

namespace PCS.V2.Golden

open PCS PCS.V2.Json PCS.V2.Hex PCS.V2.Domains PCS.V2.Package PCS.V2.Signature PCS.V2.Canonical
open PCS.V2.Witnesses.AISafetyGolden PCS.V2.SHA256 PCS.V2.Index PCS.V2.CertificateModel
open PCS.V2.EndToEnd PCS.V2.Authority PCS.V2.DomainAuthority PCS.V2.Zip PCS.V2.Crc32Memo
open PCS.V2.AuthorityCLI

/-! ## CRC-32 of the seven members (kernel-checked checkpoints) -/

theorem crcOK0 : crcChunksOK 0xFFFFFFFF FileLit.crcChunks0 = true := by kernel_rfl
theorem crcOK1 : crcChunksOK 0xFFFFFFFF FileLit.crcChunks1 = true := by kernel_rfl
theorem crcOK2 : crcChunksOK 0xFFFFFFFF FileLit.crcChunks2 = true := by kernel_rfl
theorem crcOK3 : crcChunksOK 0xFFFFFFFF FileLit.crcChunks3 = true := by kernel_rfl
theorem crcOK4 : crcChunksOK 0xFFFFFFFF FileLit.crcChunks4 = true := by kernel_rfl
theorem crcOK5 : crcChunksOK 0xFFFFFFFF FileLit.crcChunks5 = true := by kernel_rfl
theorem crcOK6 : crcChunksOK 0xFFFFFFFF FileLit.crcChunks6 = true := by kernel_rfl

/-- Proved CRC-32 facts for the member bytes. -/
def memberCrcTable : List (List UInt8 × UInt32) :=
  [FileLit.crcChunks0, FileLit.crcChunks1, FileLit.crcChunks2, FileLit.crcChunks3,
   FileLit.crcChunks4, FileLit.crcChunks5, FileLit.crcChunks6].map
    fun cs => (chunksBytes cs, chunksFinal 0xFFFFFFFF cs ^^^ 0xFFFFFFFF)

theorem memberCrcTable_correct : CrcMemoCorrect memberCrcTable :=
  crcMemoCorrect_cons (crc32_of_crcChunksOK crcOK0) <|
  crcMemoCorrect_cons (crc32_of_crcChunksOK crcOK1) <|
  crcMemoCorrect_cons (crc32_of_crcChunksOK crcOK2) <|
  crcMemoCorrect_cons (crc32_of_crcChunksOK crcOK3) <|
  crcMemoCorrect_cons (crc32_of_crcChunksOK crcOK4) <|
  crcMemoCorrect_cons (crc32_of_crcChunksOK crcOK5) <|
  crcMemoCorrect_cons (crc32_of_crcChunksOK crcOK6) crcMemoCorrect_nil

/-! ## The archive literal is the canonical encoding -/

/-- The committed `archive.zip` literal. -/
def archiveBA : ByteArray := ⟨⟨FileLit.archiveBytes⟩⟩

/-- **The committed archive bytes are exactly `goldenRaw`** (the canonical ZIP encoding of
    the golden entries), every header field and CRC-32 included. -/
theorem archiveBytes_eq_goldenRaw : archiveBA = goldenRaw := by
  rw [goldenRaw, goldenEntries_eq]
  simp only [encodeZip, entryBytes, entriesV, List.map, locals, centrals, localRecord,
    localHeader, centralRecord]
  rw [crc32_eq_crc32Memo memberCrcTable_correct]
  kernel_rfl

/-! ## The transcript and trust-anchor inputs -/

/-- The transcript JSON value with the certificate hash as a literal. -/
def transcriptJV : JVal :=
  .obj [("certificate_semantic_hash", .str (hexEncode Lit.semHash)),
        ("checker_version", .str checkerVersion), ("environment_capture", .null),
        ("format", .str authorityTranscriptFormat),
        ("replay", .arr [.obj [("evidence_id", .str "E1"), ("kind", .str "computational_test"),
                               ("outcome", .str "PASS")]]),
        ("workflow_ok", .bool true)]

theorem goldenTranscriptJ_eq : goldenTranscriptJ = transcriptJV := by
  rw [goldenTranscriptJ, semHash, semHash_eq]; rfl

/-- The committed `observations.json` literal. -/
def observationsBA : ByteArray := ⟨⟨FileLit.observationsBytes⟩⟩

theorem observationsBA_jcs : observationsBA = jcsBytes transcriptJV := by kernel_rfl

theorem observationsBA_eq : observationsBA = goldenTranscriptBytes := by
  rw [observationsBA_jcs, goldenTranscriptBytes, goldenTranscriptJ_eq]

theorem transcriptJV_canonical : canonical transcriptJV = true := by kernel_rfl

theorem decodeTranscript_golden :
    decodeAuthorityTranscript transcriptJV = some goldenTranscript := by
  rw [goldenTranscript_eq]; kernel_rfl

theorem decodeAuthorityTranscriptBytes_golden :
    decodeAuthorityTranscriptBytes observationsBA = some goldenTranscript := by
  have hs : (jcsBytes transcriptJV).size ≤ maxAuthorityTranscriptBytes := by
    rw [← observationsBA_jcs]; decide +kernel
  rw [observationsBA_jcs, decodeAuthorityTranscriptBytes,
    parseCanonicalBytes_complete transcriptJV_canonical hs]
  exact decodeTranscript_golden

theorem cliAnchor_golden :
    cliAnchor FileLit.pkB64 (some FileLit.fingerprintHex) = goldenAnchor := by
  rw [goldenAnchor_eq]; kernel_rfl

theorem pcsLeanAuthority_golden_zip_output :
    zipModeOutput archiveBA observationsBA FileLit.pkB64 (some FileLit.fingerprintHex) =
      some "ACCEPT" :=
  (zipModeOutput_accept_iff _ _ _ _).2 ⟨_, decodeAuthorityTranscriptBytes_golden, by
    rw [cliAnchor_golden, archiveBytes_eq_goldenRaw]; exact aiSafetyGoldenArchive_accepts⟩

theorem pcsLeanAuthority_golden_dir_output :
    dirModeOutput goldenEntries observationsBA FileLit.pkB64 (some FileLit.fingerprintHex) =
      some "ACCEPT" := by
  rw [dirModeOutput, decodeAuthorityTranscriptBytes_golden]
  dsimp only
  rw [cliAnchor_golden, aiSafetyGoldenArchive_entries_accepts]
  rfl

end PCS.V2.Golden
