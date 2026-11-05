import PCSCountermodel.Missions

/-! Compiled differential-test runner. Emits every mission/world verdict for sizes 1–3.
The runtime and compiler are trusted; the output is not a serialized proof certificate.
There is no submitted Lean source, JSON parsing, network access, or file mutation. -/
open PCSCountermodel PCSCountermodel.Missions

def main (args : List String) : IO UInt32 := do
  if args != ["--exhaustive"] then
    IO.eprintln "usage: pcs-countermodel-replay --exhaustive"
    return 2
  let stdout ← IO.getStdout
  for (id, a, b) in missions do
    match lower [] a, lower [] b with
    | some left, some right =>
      for n in [1, 2, 3] do
        for mask in [:2 ^ numBits n] do
          let w := worldOfBits n mask
          let l := if evalBool w emptyEnv left then 1 else 0
          let r := if evalBool w emptyEnv right then 1 else 0
          stdout.putStrLn s!"{id}\t{n}\t{mask}\t{l}\t{r}"
    | _, _ =>
      IO.eprintln s!"invalid registered mission: {id}"
      return 1
  return 0
