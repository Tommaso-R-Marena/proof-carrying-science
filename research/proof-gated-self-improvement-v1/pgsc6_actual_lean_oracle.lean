import PCS.V2.ProofGatedCertCodec

/-!
A RESEARCH-ONLY execution adapter for the actual kernel-checked V6 PGSC6
certificate checker. The verification policy is fixed by the compiled
Lean expression `ProofGatedStrongGate.specWide`, not read from candidate
certificate or a user-supplied configuration file.

Generation and active state are command arguments in this test adapter,
NOT a trusted monotonic state in deployment. No external security claims.
-/

open PCS.V2.ProofGatedCertCodec (checkCertBytes)
open PCS.V2.ProofGatedStrongGate (specWide)

namespace PGSC6ActualOracle

def reject (reason : String) : IO UInt32 := do
  IO.println s!"REJECT:{reason}"
  return (1 : UInt32)

def verify (generation activePath certPath : String) : IO UInt32 := do
  match generation.toNat? with
  | none => reject "bad_generation"
  | some g =>
      let active ← IO.FS.readBinFile ⟨activePath⟩
      let cert ← IO.FS.readBinFile ⟨certPath⟩
      let activeBytes := active.data.toList
      let certBytes := cert.data.toList
      if checkCertBytes specWide g activeBytes certBytes then
        IO.println "ACCEPT_PGSC6"
        return (0 : UInt32)
      else
        reject "certificate_not_authorized"

end PGSC6ActualOracle

def main (args : List String) : IO UInt32 :=
  match args with
  | ["check", generation, activePath, certPath] =>
      PGSC6ActualOracle.verify generation activePath certPath
  | _ => PGSC6ActualOracle.reject "bad_arity"
