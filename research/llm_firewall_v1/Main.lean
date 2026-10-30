import Policy

def main : IO Unit := do
  let input ← IO.getStdin
  let output ← IO.getStdout
  -- A bounded one-shot request; any short read/trailing sixth byte refuses.
  let raw ← input.read 6
  output.write ⟨(PCSLLMFirewall.process raw.data.toList).toArray⟩
  output.flush
