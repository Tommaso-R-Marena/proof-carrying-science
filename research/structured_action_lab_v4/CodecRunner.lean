import ActionCodec
import Lean
-- Fixed differential-test harness. Malformed transport gets ERROR, never approval.
def main : IO Unit := do
  let input ← IO.getStdin
  let output ← IO.getStdout
  repeat
    let line ← input.getLine
    if line.isEmpty then break
    let result := do
      let j ← Lean.Json.parse line
      let arr ← j.getArr?
      let nums ← arr.toList.mapM Lean.Json.getNat?
      if nums.length > 64 then throw "byte budget"
      if nums.any (· > 255) then throw "not octets"
      pure (match PCSActionFormat.decode nums with | some a => toString a.val | none => "none")
    match result with
    | .ok value => output.putStrLn value
    | .error _ => output.putStrLn "ERROR"
