import PCS.V2.ProofGatedStrongArtifacts

/-!
Research-only executable Lean oracle for actual PGSI2-WIDE predictions
and V5 strong-gate decisions. Not a new proof or trusted OS runtime.
-/

open PCS.V2.ProofGatedWide (Arch predict)
open PCS.V2.ProofGatedNetArtifacts (decode)
open PCS.V2.ProofGatedStrongGate (StrongSpec)
open PCS.V2.ProofGatedStrongArtifacts (acceptStrongWire)

namespace PGSI2WideOracle

def parseInts (s : String) : Option (List Int) :=
  (s.splitOn ",").mapM String.toInt?

def reject (reason : String) : IO UInt32 := do
  IO.println s!"REJECT:{reason}"
  return 1

def inferenceImpl (artifactPath : String) (width maxMagnitude : Nat)
    (inputs : List Int) : IO UInt32 := do
  try
    let raw ← IO.FS.readFile ⟨artifactPath⟩
    match decode ⟨width, maxMagnitude⟩ raw with
    | none => reject "invalid_artifact"
    | some net =>
      let outputs := inputs.map fun x => toString (predict net x)
      IO.println ("PREDICT:" ++ String.intercalate "," outputs)
      return 0
  catch _ => reject "read_failure"

def inference (artifactPath maxWidth bound xs : String) : IO UInt32 :=
  match maxWidth.toNat?, bound.toNat?, parseInts xs with
  | some w, some b, some inputs => inferenceImpl artifactPath w b inputs
  | _, _, _ => reject "invalid_arguments"

def strongImpl (oldPath candidatePath targetPath : String)
    (width maxMagnitude : Nat) (lo hi : Int) (corpus : List Int) : IO UInt32 := do
  try
    let oldRaw ← IO.FS.readFile ⟨oldPath⟩
    let newRaw ← IO.FS.readFile ⟨candidatePath⟩
    let targetRaw ← IO.FS.readFile ⟨targetPath⟩
    let arch : Arch := ⟨width, maxMagnitude⟩
    match decode arch targetRaw with
    | none => reject "invalid_target"
    | some target =>
      let spec : StrongSpec := ⟨arch, target, corpus, lo, hi⟩
      if acceptStrongWire spec oldRaw newRaw then
        IO.println "ACCEPT_STRONG"
        return 0
      else
        reject "strong_gate_negative"
  catch _ => reject "read_failure"

def strongGate (oldPath candidatePath targetPath maxWidth bound lo hi corpus : String) :
    IO UInt32 :=
  match maxWidth.toNat?, bound.toNat?, lo.toInt?, hi.toInt?, parseInts corpus with
  | some w, some b, some l, some h, some xs =>
      strongImpl oldPath candidatePath targetPath w b l h xs
  | _, _, _, _, _ => reject "invalid_arguments"

end PGSI2WideOracle

def main (args : List String) : IO UInt32 :=
  match args with
  | ["infer", path, maxWidth, bound, xs] =>
      PGSI2WideOracle.inference path maxWidth bound xs
  | ["strong", oldPath, candidatePath, targetPath, maxWidth, bound, lo, hi, corpus] =>
      PGSI2WideOracle.strongGate oldPath candidatePath targetPath maxWidth bound lo hi corpus
  | _ => PGSI2WideOracle.reject "bad_arity"
