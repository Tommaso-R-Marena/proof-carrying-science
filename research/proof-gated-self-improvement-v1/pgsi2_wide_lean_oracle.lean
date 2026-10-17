import PCS.V2.ProofGatedStrongArtifacts

/-!
Executable Lean oracle for PGSI2-WIDE integration tests.

This file is not a new proof and does not alter formal authority.
It calls the existing Lean reference decoder, interpreter and strong gate.
An external host still must authenticate this executable and its inputs.
-/

open PCS.V2.ProofGatedWide (Arch WideNet predict)
open PCS.V2.ProofGatedNetArtifacts (decode)
open PCS.V2.ProofGatedStrongGate (StrongSpec)
open PCS.V2.ProofGatedStrongArtifacts (acceptStrongWire)

namespace PGSI2WideOracle

def parseInts (s : String) : Option (List Int) :=
  (s.splitOn ",").mapM String.toInt?

def reject (reason : String) : IO UInt32 := do
  IO.println s!"REJECT:{reason}"
  return 1

def inference (artifactPath maxWidth bound xs : String) : IO UInt32 := do
  match maxWidth.toNat?, bound.toNat?, parseInts xs with
  | some w, some b, some inputs =>
    try
      let raw ← IO.FS.readFile ⟨artifactPath⟩
      match decode ⟨w, b⟩ raw with
      | none => reject "invalid_artifact"
      | some net =>
        let result := inputs.map fun x => toString (predict net x)
        IO.println ("PREDICT:" ++ String.intercalate "," result)
        return 0
    catch _ => reject "read_failure"
  | _, _, _ => reject "invalid_arguments"

def strongGate (oldPath candidatePath targetPath maxWidth bound lo hi corpus : String) :
    IO UInt32 := do
  match maxWidth.toNat?, bound.toNat?, lo.toInt?, hi.toInt?, parseInts corpus with
  | some w, some b, some l, some h, some xs =>
    try
      let oldRaw ← IO.FS.readFile ⟨oldPath⟩
      let newRaw ← IO.FS.readFile ⟨candidatePath⟩
      let targetRaw ← IO.FS.readFile ⟨targetPath⟩
      let arch : Arch := ⟨w, b⟩
      match decode arch targetRaw with
      | none => reject "invalid_target"
      | some target =>
        let spec : StrongSpec := ⟨arch, target, xs, l, h⟩
        if acceptStrongWire spec oldRaw newRaw then
          IO.println "ACCEPT_STRONG"
          return 0
        else
          reject "strong_gate_negative"
    catch _ => reject "read_failure"
  | _, _, _, _, _ => reject "invalid_arguments"

end PGSI2WideOracle

def main (args : List String) : IO UInt32 := do
  match args with
  | ["infer", path, maxWidth, bound, xs] =>
    PGSI2WideOracle.inference path maxWidth bound xs
  | ["strong", oldPath, candidatePath, targetPath, maxWidth, bound, lo, hi, corpus] =>
    PGSI2WideOracle.strongGate oldPath candidatePath targetPath maxWidth bound lo hi corpus
  | _ => PGSI2WideOracle.reject "bad_arity"
