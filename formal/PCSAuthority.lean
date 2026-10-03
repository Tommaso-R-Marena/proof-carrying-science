import PCS

open PCS.V2.Json PCS.V2.Package PCS.V2.EndToEnd PCS.V2.Authority

partial def collectAuthorityFiles (root : System.FilePath) (rel : String) :
    IO (List (String × ByteArray)) := do
  let dir := if rel.isEmpty then root else root / rel
  let mut out := []
  for entry in (← dir.readDir) do
    let r := if rel.isEmpty then entry.fileName else rel ++ "/" ++ entry.fileName
    if (← entry.path.isDir) then
      out := out ++ (← collectAuthorityFiles root r)
    else
      out := out ++ [(r, ← IO.FS.readBinFile entry.path)]
  return out

def main (args : List String) : IO UInt32 := do
  match args with
  | "--zip" :: archivePath :: keyB64 :: transcriptPath :: rest =>
    -- High-assurance mode: the Lean authority decodes the raw canonical archive bytes
    -- itself (`PCS.V2.Zip.decodeZip`, proved sound against `CanonicalZip`); no external
    -- ZIP library or filesystem materialisation is on the authoritative path.
    let transcriptBytes ← IO.FS.readBinFile transcriptPath
    let some transcript := decodeAuthorityTranscriptBytes transcriptBytes
      | IO.eprintln "invalid authority observation transcript"; return 2
    let raw ← IO.FS.readBinFile archivePath
    let pk := (PCS.V2.Base64.decodeCanonical keyB64).getD []
    let expected := match rest with
      | fp :: _ => PCS.V2.Hex.hexDecode fp
      | [] => none
    let stage := PCS.V2.CanonicalArchive.diagnoseArchiveWithTranscript transcript { pk, expected } raw
    if stage = "ACCEPT" then
      IO.println "ACCEPT"
    else
      IO.println ("REJECT:" ++ stage)
    return 0
  | dir :: keyB64 :: transcriptPath :: rest =>
    let transcriptBytes ← IO.FS.readBinFile transcriptPath
    let some transcript := decodeAuthorityTranscriptBytes transcriptBytes
      | IO.eprintln "invalid authority observation transcript"; return 2
    let entries ← collectAuthorityFiles dir ""
    let pk := (PCS.V2.Base64.decodeCanonical keyB64).getD []
    let expected := match rest with
      | fp :: _ => PCS.V2.Hex.hexDecode fp
      | [] => none
    match fromArchiveEntries entries with
    | none => IO.println "REJECT"; return 0
    | some inp =>
      let stage := diagnosePCSWithTranscript transcript { pk, expected } inp
      if stage = "ACCEPT" then
        IO.println "ACCEPT"
      else
        IO.println ("REJECT:" ++ stage)
      return 0
  | _ =>
    IO.eprintln ("usage: pcs-lean-authority <package-dir> <pk-b64> <observations.json> [fingerprint]\n" ++
      "       pcs-lean-authority --zip <canonical-archive.zip> <pk-b64> <observations.json> [fingerprint]")
    return 2
