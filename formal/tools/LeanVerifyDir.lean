import PCS

/-!
Differential-testing driver: runs the Lean v0.6 checker `acceptPCS` on a package
directory and prints `ACCEPT` or `REJECT`.

Usage (from `formal/`, after `lake build`):
  lake env lean --run tools/LeanVerifyDir.lean <package-dir> <public-key-raw-base64> [<fingerprint-hex>]

Oracles: Lean Ed25519 (real signature verification), ASCII-only Unicode folding,
the verified Lean `reaction_balance` executor (`PCS.V2.Chemistry.chemExecWith`) with a
*recorded-outcome* fallback for every other check type, and permissive workflow/capture
oracles.
The driver therefore cross-checks every structural, canonical-byte, hash, signature,
package, normalization and normalized-set layer against production, but NOT the
external replay/environment executors (those remain production-only).
-/

open PCS.V2.Json PCS.V2.Package PCS.V2.Signature PCS.V2.Index PCS.V2.EndToEnd PCS.V2.Replay
open PCS.V2.CertificateModel

/-- Replays nothing: reports the outcome recorded in the evidence object itself. -/
def recordedExecutor : Executor := fun req =>
  match decodeCertEvidence req.evidence with
  | some e => ⟨e.kind, e.outcome⟩
  | none => ⟨.provenance, .unverified⟩

def oracles : Oracles :=
  { unicode := PCS.V2.Vectors.asciiUnicode, ed25519 := PCS.V2.Ed25519.verify,
    capture := fun _ => .null, workflow := fun _ _ => true,
    exec := PCS.V2.Chemistry.chemExecWith recordedExecutor }

partial def collect (root : System.FilePath) (rel : String) : IO (List (String × ByteArray)) := do
  let dir := if rel.isEmpty then root else root / rel
  let mut out := []
  for entry in (← dir.readDir) do
    let r := if rel.isEmpty then entry.fileName else rel ++ "/" ++ entry.fileName
    if (← entry.path.isDir) then
      out := out ++ (← collect root r)
    else
      out := out ++ [(r, ← IO.FS.readBinFile entry.path)]
  return out

def main (args : List String) : IO UInt32 := do
  match args with
  | dir :: keyB64 :: rest =>
    let entries ← collect dir ""
    let pk := (PCS.V2.Base64.decodeCanonical keyB64).getD []
    let expected := match rest with
      | fp :: _ => PCS.V2.Hex.hexDecode fp
      | [] => none
    match fromArchiveEntries entries with
    | none => IO.println "REJECT"; return 0
    | some inp =>
      match acceptPCS oracles { pk, expected } inp with
      | some _ => IO.println "ACCEPT"
      | none => IO.println "REJECT"
      return 0
  | _ => IO.eprintln "usage: LeanVerifyDir <dir> <pk-b64> [fingerprint]"; return 2
