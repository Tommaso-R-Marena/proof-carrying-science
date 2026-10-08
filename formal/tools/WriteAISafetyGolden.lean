import PCS.V2.Witnesses.AISafetyGolden

/-! Writes the golden AI-safety fixture files (archive, transcript, key) for the
    `pcs-lean-authority` binary.  Usage: `lake env lean --run tools/WriteAISafetyGolden.lean`. -/

open PCS.V2.Witnesses.AISafetyGolden

def main : IO Unit := do
  let dir : System.FilePath := "fixtures/ai_safety_golden"
  IO.FS.createDirAll dir
  IO.FS.writeBinFile (dir / "archive.zip") goldenRaw
  IO.FS.writeBinFile (dir / "observations.json") goldenTranscriptBytes
  IO.FS.writeFile (dir / "pk.b64") (PCS.V2.Base64.encodeStr testPk)
  IO.FS.writeFile (dir / "fingerprint.hex") (PCS.V2.Hex.hexEncode (PCS.V2.Signature.fingerprintOf testPk))
  for (n, b) in goldenEntries do
    let p := dir / "package" / n
    if let some parent := p.parent then IO.FS.createDirAll parent
    IO.FS.writeBinFile p b
  IO.println s!"wrote {goldenRaw.size} archive bytes"
