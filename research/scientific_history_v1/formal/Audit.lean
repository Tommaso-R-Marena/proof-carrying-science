import PCSScientificHistoryV1
import Lean
open Lean Elab Command
set_option pp.fullNames true
run_cmd do
  for (name, info) in (← getEnv).constants.toList do
    match info with
    | .thmInfo _ =>
      if "PCSScientificHistoryV1.".isPrefixOf name.toString then
        elabCommand (← `(#check $(mkIdent name)))
        elabCommand (← `(#print axioms $(mkIdent name)))
    | _ => pure ()
