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
time and compares them byte for byte with these literals.  (`PCSAuthority.main` itself â€” file
reading and `println` â€” is also outside the kernel statement; the theorems are about the pure
function `zipModeOutput` / `dirModeOutput` whose result `main` prints.)
-/

set_option autoImplicit false

namespace PCS.V2.Golden

open PCS PCS.V2.Json PCS.V2.Hex PCS.V2.Domains PCS.V2.Package PCS.V2.Signature PCS.V2.Canonical
open PCS.V2.Witnesses.AISafetyGolden PCS.V2.SHA256 PCS.V2.Index PCS.V2.CertificateModel
open PCS.V2.EndToEnd PCS.V2.Authority PCS.V2.DomainAuthority PCS.V2.Zip PCS.V2.Crc32Memo
open PCS.V2.AuthorityCLI

/-! ## CRC-32 of the seven members (kernel-checked checkpoints) -/

theorem crcOK0 : crcChunksOK 0xFFFFFFFF FileLit.crcChunks0 = true :=$ÑPÐ€L@üçO…ªì