import Release

def main : IO Unit := do
  let input ← IO.getStdin
  let output ← IO.getStdout
  let raw ← input.read 4097
  output.write ⟨(PCSRelationalRelease.process raw.data.toList).toArray⟩
  output.flush
