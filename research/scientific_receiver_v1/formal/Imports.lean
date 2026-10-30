import Main
import Lean

open Lean Elab Command
run_cmd do
  for name in (← getEnv).header.moduleNames do
    logInfo m!"PCS_MODULE {name}"
