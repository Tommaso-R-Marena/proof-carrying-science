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
    -- itself (`PCS.V2.Zip.decodeZip`, proved sound and complete against `CanonicalZip`); no
    -- external ZIP library or filesystem materialisation is on the authoritative path.
    -- The printed line is `PCS.V2.AuthorityCLI.zipModeOutput` of the bytes read, i.e. the
    -- verdict of the certified extended authority
    -- (`PCS.V2.DomainAuthority.executableAuthority_refines_certifiedAuthority`).
    let transcriptBytes ← IO.FS.readBinFile transcriptPath
    let raw ← IO.FS.readBinFile archivePath
    match PCS.V2.AuthorityCLI.zipModeOutput raw transcriptBytes keyB64 rest.head? with
    | none => IO.eprintln "invalid authority observation transcript"; return 2
    | some line => IO.println line; return 0
  | dir :: keyB64 :: transcriptPath :: rest =>
    let transcriptBytes ← IO.FS.readBinFile transcriptPath
    let entries ← collectAuthorityFiles dir ""
    match PCS.V2.AuthorityCLI.dirModeOutput entries transcriptBytes keyB64 rest.head? with
    | none => IO.eprintln "invalid authority observation transcript"; return 2
    | some line => IO.println line; return 0
  | _ =>
    IO.eprintln ("usage: pcs-lean-authority <package-dir> <pk-b64> <observations.json> [fingerprint]\n" ++
      "       pcs-lean-authority --zip <canonical-archive.zip> <pk-b64> <observations.json> [fingerprint]")
    return 2
