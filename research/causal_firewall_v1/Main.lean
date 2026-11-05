import Refinement

def main : IO Unit := do
  let input ← IO.getStdin
  let output ← IO.getStdout
  let raw ← input.read 4097
  output.write ⟨(PCSCausalFirewall.process raw.data.toList).toArray⟩
  output.flush
