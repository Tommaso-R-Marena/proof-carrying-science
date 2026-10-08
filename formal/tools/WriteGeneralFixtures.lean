import PCS.V2.ExecutableGeneralAudit
import PCS.V2.Golden.FailClosedFixtures

/-! Writes the archives of the kernel-checked rejection / counterexample theorems as files, for
    an operational cross-check with the compiled `pcs-lean-authority` binary (the theorems
    themselves are about the Lean values; these files are a convenience, not evidence).
    Each case gets `archive.zip` (for `--zip`) and `package/` (the same members, for directory
    mode), plus a transcript that reports `PASS` for every evidence item.
    Usage: `lake env lean --run tools/WriteGeneralFixtures.lean`. -/

open PCS.V2.Json PCS.V2.Witnesses.AISafetyGolden PCS.V2.Witnesses.AISafetyCampaign

def transcriptJ (s : FixtureSpec) : JVal :=
  .obj [("certificate_semantic_hash", .str (PCS.V2.Hex.hexEncode s.semHash)),
        ("checker_version", .str checkerVersion), ("environment_capture", .null),
        ("format", .str PCS.V2.Authority.authorityTranscriptFormat),
        ("replay", .arr ((("E1" :: s.extraEvidence.map (·.1))).map fun i =>
          .obj [("evidence_id", .str i), ("kind", .str "computational_test"),
                ("outcome", .str "PASS")])),
        ("workflow_ok", .bool true)]

def writeCase (name : String) (raw : ByteArray) (obs : ByteArray)
    (entries : Option (List (String × ByteArray)) := none) : IO Unit := do
  let dir : System.FilePath := "fixtures" / name
  IO.FS.createDirAll dir
  IO.FS.writeBinFile (dir / "archive.zip") raw
  IO.FS.writeBinFile (dir / "observations.json") obs
  IO.FS.writeFile (dir / "pk.b64") (PCS.V2.Base64.encodeStr testPk)
  IO.FS.writeFile (dir / "fingerprint.hex") (PCS.V2.Hex.hexEncode (PCS.V2.Signature.fingerprintOf testPk))
  if let some es := entries then
    for (n, b) in es do
      let p := dir / "package" / n
      if let some parent := p.parent then IO.FS.createDirAll parent
      IO.FS.writeBinFile p b
  IO.println s!"{name}: wrote {raw.size} archive bytes"

def specCase (name : String) (s : FixtureSpec) : IO Unit :=
  writeCase name s.build (jcsBytes (transcriptJ s))
    (some (s.entriesWith s.genCertSig s.genPkgSig))

def main : IO Unit := do
  writeCase "ai_safety_tampered" PCS.V2.Golden.tamperedRaw goldenTranscriptBytes
  writeCase "ai_safety_insider" m1.build (jcsBytes (transcriptJ m1))
  writeCase "ai_safety_counterexample" PCS.V2.GoldenCx.cxRaw
    (jcsBytes (transcriptJ PCS.V2.GoldenCx.cx)) (some PCS.V2.GoldenCx.cxEntries)
  -- fail-closed regression fixtures (correctly signed; transcript reports PASS throughout)
  specCase "failclosed_unknown_type_safe_trace" m7
  specCase "failclosed_missing_type" m7b
  specCase "failclosed_unrequired_unknown_evidence" m7c
  specCase "failclosed_claim_binding_mismatch" m15
