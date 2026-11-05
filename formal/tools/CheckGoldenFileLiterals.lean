import PCS.V2.Golden.FileLiterals

/-!
Re-checks the one non-kernel link of `PCS.V2.Golden.ArchiveBytes`: that the byte literals in
`PCS.V2.Golden.FileLit` are exactly the committed files of `fixtures/ai_safety_golden/`.

Usage (from the project root, after `lake build PCS.V2.Golden.FileLiterals`):
  lake env lean --run tools/CheckGoldenFileLiterals.lean

Prints `OK` and exits 0 iff every file matches byte for byte.
-/

open PCS.V2.Golden

def checkFile (path : String) (lit : List UInt8) : IO Bool := do
  let bs ← IO.FS.readBinFile path
  let ok := bs.data.toList == lit
  IO.println s!"{path}: {bs.size} bytes, {if ok then "match" else "MISMATCH"}"
  return ok

def checkText (path : String) (lit : String) : IO Bool := do
  let s := (← IO.FS.readFile path).trimAscii.toString
  let ok := s == lit
  IO.println s!"{path}: {if ok then "match" else "MISMATCH"}"
  return ok

def main : IO UInt32 := do
  let dir := "fixtures/ai_safety_golden/"
  let a ← checkFile (dir ++ "archive.zip") FileLit.archiveBytes
  let b ← checkFile (dir ++ "observations.json") FileLit.observationsBytes
  let c ← checkText (dir ++ "pk.b64") FileLit.pkB64
  let d ← checkText (dir ++ "fingerprint.hex") FileLit.fingerprintHex
  if a && b && c && d then IO.println "OK"; return 0 else IO.println "FAIL"; return 1
