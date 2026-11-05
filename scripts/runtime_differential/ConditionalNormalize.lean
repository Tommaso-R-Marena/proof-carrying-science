import Lean
import PCSDecisionDiagram.Conditional

namespace PCSRuntimeDifferential
open Lean PCSDD

def optionalJson (f : α → Json) : Option α → Json
  | none => .null
  | some x => f x

/-- Test adapter: preserve all modeled receipt fields, including work and resource limits.
Names, cryptographic commitments, JSON decoding and public scope strings are outside this model. -/
def normalizeConditional {n : Nat} (r : CReceipt n) : Json := Json.mkObj [
  ("decision", toJson (match r.decision with
    | .equivalentUnderAssumptions => "equivalent_under_assumptions"
    | .counterexample => "counterexample"
    | .inconsistentAssumptions => "inconsistent_assumptions"
    | .resourceLimit => "resource_limit")),
  ("context_example", optionalJson toJson r.contextExample),
  ("counterexample", optionalJson (fun c => Json.mkObj [
    ("assignment", toJson c.assignment), ("source_true", toJson c.sourceTrue),
    ("candidate_true", toJson c.candidateTrue), ("assumptions_true", toJson c.assumptionsTrue)]) r.counterexample),
  ("unsat_core", optionalJson toJson r.unsatCore),
  ("core_necessity_witnesses", optionalJson (fun ws => toJson (ws.map (fun p =>
    Json.mkObj [("removed_assumption", toJson p.1), ("assignment", toJson p.2)]))) r.coreWitnesses),
  ("diagram", optionalJson (fun d => Json.mkObj [
    ("nodes", toJson (d.nodes.toList.map (fun nd => [nd.var, nd.low, nd.high]))),
    ("source", optionalJson toJson d.source), ("candidate", optionalJson toJson d.candidate),
    ("context", toJson d.context), ("difference", optionalJson toJson d.difference)]) r.diagram),
  ("limit_reached", optionalJson (fun l => toJson (match l with | .nodes => "nodes" | .operations => "operations")) r.limitReached),
  ("work", Json.mkObj [("bdd_nodes", toJson r.work.bddNodes), ("apply_calls", toJson r.work.applyCalls),
    ("ast_visits", toJson r.work.astVisits), ("witness_steps", toJson r.work.witnessSteps)]),
  ("pcs_authority", toJson r.pcsAuthority), ("lean_kernel_checked", toJson r.leanKernelChecked)]

end PCSRuntimeDifferential
