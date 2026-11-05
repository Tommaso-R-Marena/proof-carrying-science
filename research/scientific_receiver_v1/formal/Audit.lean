import PCSScientificReceiver
import Lean

set_option pp.universes true
set_option pp.fullNames true
open Lean Elab Command
run_cmd do
  for (name, info) in (← getEnv).constants.toList do
    match info with
    | .thmInfo _ =>
      if "PCSScientificReceiver.".isPrefixOf name.toString then
        elabCommand (← `(#check $(mkIdent name)))
        elabCommand (← `(#print axioms $(mkIdent name)))
    | _ => pure ()
