import PCSProofProbe

/-! Receiver-controlled local worker. Every request starts from the same imported
environment; no declaration or goal mutation persists between requests. This
worker is never exposed as an arbitrary-source network service. -/
open Lean

unsafe def main : IO Unit := do
  let input ← IO.getStdin
  let output ← IO.getStdout
  let opts := ({} : Options).set `maxHeartbeats (100000 : Nat) |>.set `maxRecDepth (512 : Nat)
  enableInitializersExecution
  let env ← importModules #[{module := `PCSProofProbe}] opts 0 (loadExts := true)
  repeat
    let line ← input.getLine
    if line.isEmpty then break
    let mut errors := #[]
    try
      match Json.parse line with
      | .error e => errors := #[e]
      | .ok j =>
        match j.getStr? with
        | .error e => errors := #[e]
        | .ok source =>
          let (_, messages) ← Lean.Elab.process source env opts
          for message in messages.toList do
            if message.severity == .error then
              errors := errors.push (← message.toString)
            else
              let value ← message.data.toString
              if value.startsWith "PCS_STATE:" then
                output.putStrLn value
    catch ex => errors := #[toString ex]
    output.putStrLn s!"PCS_END:{(Json.mkObj [("errors", toJson errors)]).compress}"
    output.flush
