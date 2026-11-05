import PCS.V2.ExecutableAuthority
import PCS.V2.Base64

/-!
# The pure verdict computed by `pcs-lean-authority`

`PCSAuthority.main` reads its input files and then computes exactly the functions below
(`zipModeOutput` for `--zip`, `dirModeOutput` for a materialised directory) and prints the
returned line.  Factoring them out lets theorems speak about the command-line behaviour on
concrete input bytes; the only remaining steps in `main` are the file reads and the
`println`.
-/

set_option autoImplicit false

namespace PCS.V2.AuthorityCLI

open PCS.V2.EndToEnd PCS.V2.Authority PCS.V2.DomainAuthority

/-- The trust anchor built from the command-line public key (canonical base64) and
    optional fingerprint pin (hex). -/
def cliAnchor (keyB64 : String) (fp : Option String) : TrustAnchor :=
  { pk := (PCS.V2.Base64.decodeCanonical keyB64).getD [], expected := fp.bind PCS.V2.Hex.hexDecode }

/-- The line printed by `pcs-lean-authority --zip` (`none`: invalid transcript, exit 2). -/
def zipModeOutput (archive transcript : ByteArray) (keyB64 : String) (fp : Option String) :
    Option String :=
  match decodeAuthorityTranscriptBytes transcript with
  | none => none
  | some t =>
    let stage := executableAuthority t (cliAnchor keyB64 fp) archive
    some (if stage = "ACCEPT" then "ACCEPT" else "REJECT:" ++ stage)

/-- The line printed by `pcs-lean-authority <dir>` on the collected entries. -/
def dirModeOutput (entries : List (String × ByteArray)) (transcript : ByteArray) (keyB64 : String)
    (fp : Option String) : Option String :=
  match decodeAuthorityTranscriptBytes transcript with
  | none => none
  | some t =>
    match executableAuthorityEntries t (cliAnchor keyB64 fp) entries with
    | "archive_partition" => some "REJECT"
    | stage => some (if stage = "ACCEPT" then "ACCEPT" else "REJECT:" ++ stage)

/-- `--zip` prints `ACCEPT` iff the transcript decodes and the executable authority accepts. -/
theorem zipModeOutput_accept_iff (archive transcript : ByteArray) (keyB64 : String)
    (fp : Option String) :
    zipModeOutput archive transcript keyB64 fp = some "ACCEPT" ↔
      ∃ t, decodeAuthorityTranscriptBytes transcript = some t ∧
        executableAuthority t (cliAnchor keyB64 fp) archive = "ACCEPT" := by
  unfold zipModeOutput
  cases decodeAuthorityTranscriptBytes transcript with
  | none => simp
  | some t =>
    simp only [Option.some.injEq, exists_eq_left']
    by_cases h : executableAuthority t (cliAnchor keyB64 fp) archive = "ACCEPT"
    · simp [h]
    · simp only [h, if_false, iff_false]
      intro h'
      have := congrArg String.toList h'
      rw [String.toList_append, show "REJECT:".toList = ['R', 'E', 'J', 'E', 'C', 'T', ':'] by decide,
        show "ACCEPT".toList = ['A', 'C', 'C', 'E', 'P', 'T'] by decide] at this
      simp at this

end PCS.V2.AuthorityCLI
