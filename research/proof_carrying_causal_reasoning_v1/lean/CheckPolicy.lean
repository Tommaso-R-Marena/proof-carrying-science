import PcsPccr.PolicyReceiver

/-! One study supplied on the command line (in a file), proposals on stdin.
--paired takes an ordered study file, checks proposal i against study i, and
fails the replay if the two input streams have different lengths. -/
open PcsPccr.PolicyReceiver

private def readLines (path : String) : IO (List String) := do
  let body ← IO.FS.readFile path
  return (body.dropSuffix "\n").toString.splitOn "\n"

def main (args : List String) : IO Unit := do
  let (paired, path) ← match args with
    | [path] => pure (false, path)
    | ["--paired", path] => pure (true, path)
    | _ => throw (IO.userError "expected [--paired] study-file")
  let studies := (← readLines path).toArray
  if !paired && studies.size != 1 then
    throw (IO.userError "expected exactly one study")
  let input ← IO.getStdin
  let output ← IO.getStdout
  let mut count := 0
  repeat
    let raw ← input.getLine
    if raw.isEmpty then break
    let proposal := (raw.dropSuffix "\n").toString
    let some source := studies[if paired then count else 0]? |
      throw (IO.userError "more proposals than studies")
    output.putStrLn ((check source proposal).getD "REJECT")
    count := count + 1
  if paired && count != studies.size then
    throw (IO.userError "fewer proposals than studies")
