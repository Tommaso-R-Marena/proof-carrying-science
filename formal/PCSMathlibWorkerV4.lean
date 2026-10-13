import PCSProofProbe

/-! Research-local transport only. Fixed import environment; no request state
persists. Its unsafe IO entry point is never mathematical acceptance evidence.
Final proofs use independent ordinary kernel compilations. -/
open Lean

unsafe def main : IO Unit := do
  let input ← IO.getStdin
  let output ← IO.getStdout
  let opts := ({} : Options).set `maxHeartbeats (200000 : Nat) |>.set `maxRecDepth (512 : Nat)
  enableInitializersExecution
  let imports := #[`PCSProofProbe, `Mathlib.Data.Set.Function, `Mathlib.Algebra.Group.Basic,
    `Mathlib.Data.Nat.Factorial.Basic, `Mathlib.Data.List.Basic,
    `Mathlib.Data.Finset.Card, `Mathlib.Data.Real.Basic, `Mathlib.Tactic]
  let env ← importModules (imports.map fun name => {module := name}) opts 0 (loadExts := true)
  repeat
    let line ← input.getLine
    if line.isEmpty then break
    let mut errors := #[]
    try
      match Json.parse line >>= Json.getStr? with
      | .error e => errors := #[e]
      | .ok source =>
        let (_, messages) ← Lean.Elab.process source env opts
        for message in messages.toList do
          if message.severity == .error then errors := errors.push (← message.toString)
          else
            let value ← message.data.toString
            if value.startsWith "PCS_STATE:" then output.putStrLn value
    catch ex => errors := #[toString ex]
    output.putStrLn s!"PCS_END:{(Json.mkObj [("errors", toJson errors)]).compress}"
    output.flush
