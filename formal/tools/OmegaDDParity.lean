import PCSDecisionDiagram

/-! Runtime serialization for finite integration comparisons only. This codec,
Python task generation and native execution are not proved refinements. No input
decoder, authority flag promotion or kernel certification of runtime output. -/
namespace OmegaDDParity
open PCSOmega PCSDD

def arr (xs : List String) : String := "[" ++ String.intercalate "," xs ++ "]"
def obj (xs : List (String × String)) : String :=
  "{" ++ String.intercalate "," (xs.map fun (k,v) => "\"" ++ k ++ "\":" ++ v) ++ "}"
def opt (f : α → String) : Option α → String
  | none => "null"
  | some x => f x
def bs (a : List Bool) : String := arr (a.map toString)
def ns (a : List Nat) : String := arr (a.map toString)
def conditional (r : CReceipt n) : String := obj [
  ("decision", match r.decision with
    | .equivalentUnderAssumptions => "\"equivalent_under_assumptions\""
    | .counterexample => "\"counterexample\""
    | .inconsistentAssumptions => "\"inconsistent_assumptions\""
    | .resourceLimit => "\"resource_limit\""),
  ("context_example", opt bs r.contextExample),
  ("counterexample", opt (fun c => obj [("assignment", bs c.assignment),
    ("source_true", toString c.sourceTrue), ("candidate_true", toString c.candidateTrue),
    ("assumptions_true", bs c.assumptionsTrue)]) r.counterexample),
  ("unsat_core", opt ns r.unsatCore),
  ("core_necessity_witnesses", opt (fun ws => arr (ws.map fun (i,a) =>
    obj [("removed_assumption", toString i), ("assignment", bs a)])) r.coreWitnesses),
  ("diagram", opt (fun d => obj [("nodes", arr (d.nodes.toList.map fun x => ns [x.var,x.low,x.high])),
    ("source", opt toString d.source), ("candidate", opt toString d.candidate),
    ("context", toString d.context), ("difference", opt toString d.difference)]) r.diagram),
  ("limit_reached", opt (fun l => match l with
    | .nodes => "\"nodes\"" | .operations => "\"operations\"") r.limitReached),
  ("work", obj [("bdd_nodes", toString r.work.bddNodes), ("apply_calls", toString r.work.applyCalls),
    ("ast_visits", toString r.work.astVisits), ("witness_steps", toString r.work.witnessSteps)]),
  ("pcs_authority", toString r.pcsAuthority), ("lean_kernel_checked", toString r.leanKernelChecked)]
def intervention (r : IReceipt n) : String := obj [
  ("decision", match r.decision with
    | .resourceLimit => "\"resource_limit\"" | .inconsistentAssumptions => "\"inconsistent_assumptions\""
    | .noFeasiblePlan => "\"no_feasible_plan\"" | .optimalPlan => "\"optimal_plan\""),
  ("minimum_cost", opt toString r.minimumCost), ("optimal_count", opt toString r.optimalCount),
  ("assignment", opt bs r.assignment), ("flips", opt ns r.flips),
  ("mandatory_flips", opt ns r.mandatory), ("possible_flips", opt ns r.possible),
  ("bellman_cells", opt (fun cells => arr (cells.toList.map (opt fun c =>
    ns [c.cost,c.count,c.mand,c.poss]))) r.cells),
  ("dp_nodes", toString r.dpNodes), ("pcs_authority", toString r.pcsAuthority),
  ("lean_kernel_checked", toString r.leanKernelChecked)]

def emit (id : Nat) (t : ITask n) (lim : Limits) : IO Unit := do
  match plan t lim with
  | .error e => throw (IO.userError e)
  | .ok r => IO.println (obj [("id", toString id), ("conditional", conditional r.symbolic),
      ("intervention", intervention r)])
end OmegaDDParity
