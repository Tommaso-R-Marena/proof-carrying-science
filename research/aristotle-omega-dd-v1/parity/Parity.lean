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

open PCSOmega PCSDD OmegaDDParity
def t0 : ITask 0 := ⟨⟨.tt, .ff, []⟩, [], [], []⟩
def t1 : ITask 0 := ⟨⟨.ff, .ff, []⟩, [], [], []⟩
def t2 : ITask 0 := ⟨⟨.tt, .ff, [.ff]⟩, [], [], []⟩
def t3 : ITask 2 := ⟨⟨(.or (.atom ⟨0, by decide⟩) (.atom ⟨1, by decide⟩)), .ff, []⟩, [false,false], [1,1], []⟩
def t4 : ITask 2 := ⟨⟨(.atom ⟨1, by decide⟩), .ff, [(.atom ⟨0, by decide⟩),(.imp (.atom ⟨0, by decide⟩) (.atom ⟨1, by decide⟩))]⟩, [false,false], [1,1], []⟩
def t5 : ITask 2 := ⟨⟨(.and (.atom ⟨0, by decide⟩) (.atom ⟨1, by decide⟩)), .ff, [(.atom ⟨0, by decide⟩),(.not (.atom ⟨0, by decide⟩)),(.atom ⟨1, by decide⟩)]⟩, [false,false], [1,1], []⟩
def t6 : ITask 2 := ⟨⟨(.or (.atom ⟨0, by decide⟩) (.and (.atom ⟨1, by decide⟩) (.not (.atom ⟨1, by decide⟩)))), .ff, []⟩, [false,false], [1,1], []⟩
def t7 : ITask 2 := ⟨⟨(.or (.atom ⟨0, by decide⟩) (.atom ⟨1, by decide⟩)), .ff, []⟩, [false,false], [3,1], []⟩
def t8 : ITask 2 := ⟨⟨(.or (.atom ⟨0, by decide⟩) (.atom ⟨1, by decide⟩)), .ff, []⟩, [false,false], [1,1], []⟩
def t9 : ITask 2 := ⟨⟨(.or (.atom ⟨0, by decide⟩) (.atom ⟨1, by decide⟩)), .ff, []⟩, [false,true], [1,1], []⟩
def t10 : ITask 2 := ⟨⟨(.or (.atom ⟨0, by decide⟩) (.atom ⟨1, by decide⟩)), .ff, []⟩, [true,false], [1,1], []⟩
def t11 : ITask 2 := ⟨⟨(.or (.atom ⟨0, by decide⟩) (.atom ⟨1, by decide⟩)), .ff, []⟩, [true,true], [1,1], []⟩
def t12 : ITask 2 := ⟨⟨(.or (.atom ⟨0, by decide⟩) (.atom ⟨1, by decide⟩)), .ff, []⟩, [false,false], [1,1], [0]⟩
def t13 : ITask 2 := ⟨⟨(.or (.atom ⟨0, by decide⟩) (.atom ⟨1, by decide⟩)), .ff, []⟩, [false,true], [1,1], [0]⟩
def t14 : ITask 2 := ⟨⟨(.or (.atom ⟨0, by decide⟩) (.atom ⟨1, by decide⟩)), .ff, []⟩, [true,false], [1,1], [0]⟩
def t15 : ITask 2 := ⟨⟨(.or (.atom ⟨0, by decide⟩) (.atom ⟨1, by decide⟩)), .ff, []⟩, [true,true], [1,1], [0]⟩
def t16 : ITask 2 := ⟨⟨(.or (.atom ⟨0, by decide⟩) (.atom ⟨1, by decide⟩)), .ff, []⟩, [false,false], [1,1], [1]⟩
def t17 : ITask 2 := ⟨⟨(.or (.atom ⟨0, by decide⟩) (.atom ⟨1, by decide⟩)), .ff, []⟩, [false,true], [1,1], [1]⟩
def t18 : ITask 2 := ⟨⟨(.or (.atom ⟨0, by decide⟩) (.atom ⟨1, by decide⟩)), .ff, []⟩, [true,false], [1,1], [1]⟩
def t19 : ITask 2 := ⟨⟨(.or (.atom ⟨0, by decide⟩) (.atom ⟨1, by decide⟩)), .ff, []⟩, [true,true], [1,1], [1]⟩
def t20 : ITask 2 := ⟨⟨(.or (.atom ⟨0, by decide⟩) (.atom ⟨1, by decide⟩)), .ff, []⟩, [false,false], [1,1], [0,1]⟩
def t21 : ITask 2 := ⟨⟨(.or (.atom ⟨0, by decide⟩) (.atom ⟨1, by decide⟩)), .ff, []⟩, [false,true], [1,1], [0,1]⟩
def t22 : ITask 2 := ⟨⟨(.or (.atom ⟨0, by decide⟩) (.atom ⟨1, by decide⟩)), .ff, []⟩, [true,false], [1,1], [0,1]⟩
def t23 : ITask 2 := ⟨⟨(.or (.atom ⟨0, by decide⟩) (.atom ⟨1, by decide⟩)), .ff, []⟩, [true,true], [1,1], [0,1]⟩
def t24 : ITask 3 := ⟨⟨(.or (.atom ⟨2, by decide⟩) (.or (.not .tt) (.atom ⟨2, by decide⟩))), .ff, [(.or (.atom ⟨2, by decide⟩) (.atom ⟨1, by decide⟩)),(.not (.or .tt (.atom ⟨0, by decide⟩)))]⟩, [true,true,false], [7,9,9], [2]⟩
def t25 : ITask 4 := ⟨⟨(.or (.imp (.imp .tt (.atom ⟨2, by decide⟩)) (.or (.atom ⟨1, by decide⟩) (.atom ⟨0, by decide⟩))) (.or (.not (.atom ⟨1, by decide⟩)) .tt)), .ff, [(.and (.or (.atom ⟨3, by decide⟩) (.atom ⟨2, by decide⟩)) (.and (.atom ⟨3, by decide⟩) (.atom ⟨0, by decide⟩))),(.not (.and (.atom ⟨0, by decide⟩) (.atom ⟨2, by decide⟩))),(.atom ⟨1, by decide⟩)]⟩, [false,false,false,true], [3,9,3,4], [0,2]⟩
def t26 : ITask 2 := ⟨⟨(.imp (.and (.atom ⟨0, by decide⟩) (.not .tt)) .ff), .ff, [(.imp (.imp (.atom ⟨0, by decide⟩) (.atom ⟨1, by decide⟩)) (.imp .tt (.atom ⟨1, by decide⟩)))]⟩, [false,true], [6,7], [1]⟩
def t27 : ITask 4 := ⟨⟨(.or (.atom ⟨3, by decide⟩) (.not (.not (.atom ⟨1, by decide⟩)))), .ff, [(.imp (.atom ⟨3, by decide⟩) (.or (.atom ⟨2, by decide⟩) (.atom ⟨0, by decide⟩))),(.imp (.not (.atom ⟨0, by decide⟩)) (.not (.atom ⟨3, by decide⟩))),(.not (.atom ⟨0, by decide⟩))]⟩, [true,true,false,false], [8,2,1,9], [1,3]⟩
def t28 : ITask 5 := ⟨⟨(.and (.and (.not .ff) (.or (.atom ⟨4, by decide⟩) (.atom ⟨3, by decide⟩))) (.atom ⟨0, by decide⟩)), .ff, [(.imp (.and (.atom ⟨2, by decide⟩) (.atom ⟨2, by decide⟩)) (.or (.atom ⟨1, by decide⟩) .tt))]⟩, [false,false,true,true,false], [4,5,9,3,4], []⟩
def t29 : ITask 5 := ⟨⟨(.not (.or (.imp (.atom ⟨3, by decide⟩) (.atom ⟨4, by decide⟩)) (.or (.atom ⟨2, by decide⟩) (.atom ⟨3, by decide⟩)))), .ff, [(.not (.not (.atom ⟨1, by decide⟩))),(.and (.or .tt (.atom ⟨0, by decide⟩)) (.imp .ff (.atom ⟨2, by decide⟩))),(.not (.imp (.atom ⟨0, by decide⟩) (.atom ⟨2, by decide⟩)))]⟩, [false,true,true,true,true], [6,4,4,5,1], [4]⟩
def t30 : ITask 0 := ⟨⟨.ff, .ff, []⟩, [], [], []⟩
def t31 : ITask 6 := ⟨⟨(.or (.and (.not (.atom ⟨5, by decide⟩)) (.not .ff)) (.and (.and (.atom ⟨3, by decide⟩) (.atom ⟨2, by decide⟩)) (.imp .tt (.atom ⟨0, by decide⟩)))), .ff, [(.not (.imp (.atom ⟨1, by decide⟩) (.atom ⟨5, by decide⟩))),(.not (.imp (.atom ⟨4, by decide⟩) .ff))]⟩, [true,false,true,false,true,false], [8,6,7,5,3,3], [3]⟩
def t32 : ITask 1 := ⟨⟨(.atom ⟨0, by decide⟩), .ff, []⟩, [false], [9], []⟩
def t33 : ITask 3 := ⟨⟨(.not (.imp (.or .tt (.atom ⟨2, by decide⟩)) (.atom ⟨1, by decide⟩))), .ff, [(.atom ⟨1, by decide⟩),(.and (.atom ⟨0, by decide⟩) (.not (.atom ⟨1, by decide⟩)))]⟩, [true,true,true], [7,7,3], []⟩
def t34 : ITask 5 := ⟨⟨(.imp (.and (.not .ff) (.not (.atom ⟨0, by decide⟩))) (.atom ⟨3, by decide⟩)), .ff, [(.atom ⟨0, by decide⟩),(.or (.atom ⟨3, by decide⟩) (.and (.atom ⟨2, by decide⟩) (.atom ⟨4, by decide⟩))),(.atom ⟨1, by decide⟩)]⟩, [true,true,true,true,false], [1,7,8,5,2], []⟩
def t35 : ITask 3 := ⟨⟨(.imp .tt (.and (.and (.atom ⟨0, by decide⟩) (.atom ⟨0, by decide⟩)) (.atom ⟨1, by decide⟩))), .ff, [(.not (.imp (.atom ⟨1, by decide⟩) (.atom ⟨2, by decide⟩)))]⟩, [false,false,true], [3,8,3], []⟩
def t36 : ITask 1 := ⟨⟨(.imp (.not (.and (.atom ⟨0, by decide⟩) .ff)) (.imp (.imp .tt .tt) (.or .tt (.atom ⟨0, by decide⟩)))), .ff, []⟩, [true], [9], []⟩
def t37 : ITask 1 := ⟨⟨(.not (.imp .tt (.or (.atom ⟨0, by decide⟩) (.atom ⟨0, by decide⟩)))), .ff, []⟩, [true], [7], []⟩
def t38 : ITask 5 := ⟨⟨(.imp (.imp (.imp (.atom ⟨3, by decide⟩) (.atom ⟨0, by decide⟩)) (.atom ⟨1, by decide⟩)) (.and (.or (.atom ⟨4, by decide⟩) (.atom ⟨2, by decide⟩)) (.or (.atom ⟨2, by decide⟩) (.atom ⟨3, by decide⟩)))), .ff, []⟩, [false,true,true,true,true], [3,9,3,3,6], [0,4]⟩
def t39 : ITask 4 := ⟨⟨(.or (.imp (.imp (.atom ⟨0, by decide⟩) (.atom ⟨3, by decide⟩)) .tt) (.imp (.imp .ff (.atom ⟨1, by decide⟩)) (.or (.atom ⟨2, by decide⟩) .tt))), .ff, []⟩, [false,true,false,true], [8,2,6,1], [1]⟩
def t40 : ITask 2 := ⟨⟨(.imp (.imp (.not .tt) (.and .ff (.atom ⟨0, by decide⟩))) (.and (.or .ff .ff) (.imp .ff (.atom ⟨1, by decide⟩)))), .ff, []⟩, [false,false], [6,3], [1]⟩
def t41 : ITask 5 := ⟨⟨(.or (.imp (.imp (.atom ⟨1, by decide⟩) (.atom ⟨4, by decide⟩)) (.and (.atom ⟨1, by decide⟩) (.atom ⟨3, by decide⟩))) (.and (.and (.atom ⟨0, by decide⟩) (.atom ⟨1, by decide⟩)) (.or .ff (.atom ⟨2, by decide⟩)))), .ff, [(.or (.or (.atom ⟨2, by decide⟩) (.atom ⟨0, by decide⟩)) (.atom ⟨4, by decide⟩))]⟩, [true,false,false,true,true], [1,4,6,5,1], [4]⟩
def t42 : ITask 4 := ⟨⟨(.or (.and (.atom ⟨3, by decide⟩) (.and (.atom ⟨0, by decide⟩) .tt)) (.atom ⟨2, by decide⟩)), .ff, [(.not (.and (.atom ⟨1, by decide⟩) .ff)),(.and (.atom ⟨0, by decide⟩) (.not (.atom ⟨2, by decide⟩))),(.atom ⟨2, by decide⟩)]⟩, [false,true,false,true], [4,2,7,5], [0,1]⟩
def t43 : ITask 5 := ⟨⟨(.atom ⟨3, by decide⟩), .ff, [(.imp (.and (.atom ⟨1, by decide⟩) (.atom ⟨2, by decide⟩)) (.not (.atom ⟨0, by decide⟩))),(.atom ⟨4, by decide⟩)]⟩, [true,true,true,false,false], [2,4,9,6,4], [0]⟩
def t44 : ITask 2 := ⟨⟨(.not (.or (.not (.atom ⟨1, by decide⟩)) (.atom ⟨0, by decide⟩))), .ff, []⟩, [false,false], [9,8], []⟩
def t45 : ITask 2 := ⟨⟨(.not (.not (.atom ⟨1, by decide⟩))), .ff, [(.atom ⟨0, by decide⟩)]⟩, [true,false], [1,1], [0,1]⟩
def t46 : ITask 2 := ⟨⟨(.atom ⟨1, by decide⟩), .ff, [(.atom ⟨0, by decide⟩)]⟩, [false,true], [4,5], []⟩
def t47 : ITask 4 := ⟨⟨(.atom ⟨2, by decide⟩), .ff, [(.or (.atom ⟨1, by decide⟩) (.not (.atom ⟨0, by decide⟩))),(.or (.atom ⟨0, by decide⟩) (.imp (.atom ⟨2, by decide⟩) (.atom ⟨2, by decide⟩))),(.imp (.atom ⟨1, by decide⟩) (.imp (.atom ⟨3, by decide⟩) .ff))]⟩, [false,true,true,true], [9,2,9,6], []⟩
def t48 : ITask 3 := ⟨⟨(.atom ⟨1, by decide⟩), .ff, [(.or (.atom ⟨0, by decide⟩) (.atom ⟨2, by decide⟩)),(.atom ⟨0, by decide⟩),(.imp .tt (.or .ff (.atom ⟨2, by decide⟩)))]⟩, [false,true,true], [8,7,6], [1,2]⟩
def t49 : ITask 4 := ⟨⟨(.and (.and (.or (.atom ⟨0, by decide⟩) .tt) (.or .ff (.atom ⟨3, by decide⟩))) .tt), .ff, [(.atom ⟨1, by decide⟩),(.or (.atom ⟨1, by decide⟩) (.or (.atom ⟨2, by decide⟩) (.atom ⟨2, by decide⟩)))]⟩, [true,false,false,true], [8,8,3,6], [3]⟩
def t50 : ITask 1 := ⟨⟨(.atom ⟨0, by decide⟩), .ff, []⟩, [false], [4], []⟩
def t51 : ITask 4 := ⟨⟨(.atom ⟨3, by decide⟩), .ff, [(.or (.and (.atom ⟨0, by decide⟩) .ff) (.or (.atom ⟨2, by decide⟩) (.atom ⟨3, by decide⟩))),(.imp (.or (.atom ⟨1, by decide⟩) (.atom ⟨2, by decide⟩)) (.and .tt (.atom ⟨0, by decide⟩)))]⟩, [false,false,false,false], [4,6,7,7], [1]⟩
def t52 : ITask 5 := ⟨⟨(.and (.imp (.atom ⟨4, by decide⟩) (.not (.atom ⟨3, by decide⟩))) (.imp (.imp (.atom ⟨2, by decide⟩) (.atom ⟨0, by decide⟩)) (.imp (.atom ⟨4, by decide⟩) (.atom ⟨4, by decide⟩)))), .ff, [(.or (.or .tt .tt) (.and (.atom ⟨1, by decide⟩) (.atom ⟨0, by decide⟩))),(.or (.imp (.atom ⟨3, by decide⟩) .tt) (.imp (.atom ⟨2, by decide⟩) (.atom ⟨2, by decide⟩)))]⟩, [false,true,false,false,true], [3,4,3,3,6], [0]⟩
def t53 : ITask 3 := ⟨⟨(.atom ⟨1, by decide⟩), .ff, [(.not .tt),(.or (.or (.atom ⟨2, by decide⟩) .tt) (.atom ⟨0, by decide⟩))]⟩, [true,false,false], [1,8,5], [1,2]⟩
def t54 : ITask 0 := ⟨⟨.tt, .ff, []⟩, [], [], []⟩
def t55 : ITask 6 := ⟨⟨(.imp (.and (.atom ⟨4, by decide⟩) (.and .ff (.atom ⟨0, by decide⟩))) (.imp (.atom ⟨1, by decide⟩) (.imp .ff (.atom ⟨5, by decide⟩)))), .ff, [(.imp (.and (.atom ⟨2, by decide⟩) (.atom ⟨2, by decide⟩)) (.and (.atom ⟨2, by decide⟩) (.atom ⟨3, by decide⟩)))]⟩, [false,false,false,true,false,false], [2,1,6,3,4,6], [0]⟩
def t56 : ITask 4 := ⟨⟨(.and (.and (.or .ff (.atom ⟨2, by decide⟩)) (.atom ⟨0, by decide⟩)) (.not (.atom ⟨3, by decide⟩))), .ff, [.tt,(.imp (.and (.atom ⟨2, by decide⟩) (.atom ⟨0, by decide⟩)) .ff),(.or (.imp (.atom ⟨0, by decide⟩) .ff) (.atom ⟨1, by decide⟩))]⟩, [true,true,false,true], [5,7,2,9], [0]⟩
def t57 : ITask 1 := ⟨⟨(.atom ⟨0, by decide⟩), .ff, []⟩, [true], [7], [0]⟩
def t58 : ITask 6 := ⟨⟨(.or (.and (.and (.atom ⟨1, by decide⟩) (.atom ⟨1, by decide⟩)) (.or (.atom ⟨0, by decide⟩) (.atom ⟨5, by decide⟩))) (.or (.not (.atom ⟨3, by decide⟩)) (.atom ⟨1, by decide⟩))), .ff, [(.or (.and (.atom ⟨4, by decide⟩) (.atom ⟨0, by decide⟩)) (.atom ⟨0, by decide⟩)),(.imp (.and (.atom ⟨2, by decide⟩) (.atom ⟨3, by decide⟩)) .tt),(.or (.atom ⟨0, by decide⟩) (.imp .ff (.atom ⟨2, by decide⟩)))]⟩, [true,false,false,false,false,false], [8,3,5,7,7,1], [4]⟩
def t59 : ITask 5 := ⟨⟨(.and (.or (.or (.atom ⟨4, by decide⟩) (.atom ⟨2, by decide⟩)) (.atom ⟨2, by decide⟩)) (.or (.not (.atom ⟨0, by decide⟩)) (.imp (.atom ⟨4, by decide⟩) (.atom ⟨1, by decide⟩)))), .ff, [(.and (.or (.atom ⟨4, by decide⟩) (.atom ⟨3, by decide⟩)) (.or .tt (.atom ⟨4, by decide⟩))),(.not .tt)]⟩, [true,false,false,true,false], [2,1,8,8,8], [0,1,4]⟩
def t60 : ITask 1 := ⟨⟨(.not (.atom ⟨0, by decide⟩)), .ff, []⟩, [true], [9], []⟩
def t61 : ITask 1 := ⟨⟨(.imp (.or (.not (.atom ⟨0, by decide⟩)) (.and .ff (.atom ⟨0, by decide⟩))) (.not .tt)), .ff, [(.and (.not .tt) .ff)]⟩, [true], [9], []⟩
def t62 : ITask 3 := ⟨⟨(.or (.atom ⟨2, by decide⟩) (.not (.or .tt .tt))), .ff, [(.and (.atom ⟨0, by decide⟩) (.or (.atom ⟨1, by decide⟩) .ff))]⟩, [true,true,false], [8,1,1], []⟩
def t63 : ITask 5 := ⟨⟨(.or (.atom ⟨4, by decide⟩) (.imp (.atom ⟨3, by decide⟩) (.imp .ff (.atom ⟨4, by decide⟩)))), .ff, [(.atom ⟨2, by decide⟩),(.imp (.not (.atom ⟨0, by decide⟩)) (.and (.atom ⟨1, by decide⟩) (.atom ⟨4, by decide⟩)))]⟩, [true,true,false,true,true], [8,9,7,8,8], []⟩
def t64 : ITask 3 := ⟨⟨(.and (.atom ⟨1, by decide⟩) .ff), .ff, [(.atom ⟨2, by decide⟩),(.or (.not (.atom ⟨0, by decide⟩)) (.or (.atom ⟨0, by decide⟩) .tt))]⟩, [false,false,false], [1,5,8], []⟩
def t65 : ITask 4 := ⟨⟨(.and (.not (.and .tt (.atom ⟨1, by decide⟩))) (.atom ⟨2, by decide⟩)), .ff, [(.or (.imp (.atom ⟨2, by decide⟩) .ff) (.imp (.atom ⟨3, by decide⟩) (.atom ⟨0, by decide⟩)))]⟩, [false,false,true,true], [6,8,2,7], [1]⟩
def t66 : ITask 5 := ⟨⟨(.imp (.not (.imp (.atom ⟨0, by decide⟩) (.atom ⟨2, by decide⟩))) (.and (.and (.atom ⟨3, by decide⟩) .tt) (.imp .ff (.atom ⟨1, by decide⟩)))), .ff, [(.not (.not (.atom ⟨2, by decide⟩))),(.or (.imp (.atom ⟨4, by decide⟩) (.atom ⟨4, by decide⟩)) (.or (.atom ⟨0, by decide⟩) (.atom ⟨2, by decide⟩)))]⟩, [true,true,true,false,true], [8,9,2,4,9], [1]⟩
def t67 : ITask 3 := ⟨⟨(.not (.or (.imp (.atom ⟨1, by decide⟩) .ff) (.not (.atom ⟨1, by decide⟩)))), .ff, [(.not (.imp (.atom ⟨0, by decide⟩) (.atom ⟨2, by decide⟩)))]⟩, [true,false,true], [9,5,9], [1,2]⟩
def t68 : ITask 5 := ⟨⟨(.or (.and (.imp (.atom ⟨2, by decide⟩) (.atom ⟨0, by decide⟩)) (.imp .tt .tt)) (.imp (.or .tt (.atom ⟨1, by decide⟩)) (.and (.atom ⟨3, by decide⟩) (.atom ⟨3, by decide⟩)))), .ff, [(.imp (.imp (.atom ⟨4, by decide⟩) (.atom ⟨3, by decide⟩)) (.imp (.atom ⟨2, by decide⟩) (.atom ⟨4, by decide⟩)))]⟩, [true,true,true,false,true], [5,5,8,2,5], []⟩
def t69 : ITask 4 := ⟨⟨(.and (.and (.or .tt (.atom ⟨2, by decide⟩)) (.and (.atom ⟨0, by decide⟩) (.atom ⟨3, by decide⟩))) (.and (.imp (.atom ⟨1, by decide⟩) (.atom ⟨0, by decide⟩)) .tt)), .ff, [(.or (.or .ff .ff) (.imp (.atom ⟨0, by decide⟩) (.atom ⟨1, by decide⟩)))]⟩, [false,true,true,true], [1,9,6,7], [0,2,3]⟩
def t70 : ITask 1 := ⟨⟨(.not (.atom ⟨0, by decide⟩)), .ff, []⟩, [true], [9], [0]⟩
def t71 : ITask 2 := ⟨⟨(.not (.and (.atom ⟨1, by decide⟩) (.not (.atom ⟨0, by decide⟩)))), .ff, []⟩, [false,true], [1,2], []⟩
def t72 : ITask 1 := ⟨⟨(.atom ⟨0, by decide⟩), .ff, []⟩, [true], [6], []⟩
def t73 : ITask 4 := ⟨⟨.ff, .ff, [(.atom ⟨3, by decide⟩),(.or (.atom ⟨0, by decide⟩) (.and (.atom ⟨2, by decide⟩) (.atom ⟨2, by decide⟩))),(.and (.not .tt) (.not (.atom ⟨1, by decide⟩)))]⟩, [true,false,true,true], [2,6,5,3], []⟩
def t74 : ITask 1 := ⟨⟨(.not .tt), .ff, [(.imp (.or .tt .tt) (.not (.atom ⟨0, by decide⟩)))]⟩, [false], [3], []⟩
def t75 : ITask 6 := ⟨⟨(.not (.imp (.imp (.atom ⟨4, by decide⟩) (.atom ⟨3, by decide⟩)) (.and (.atom ⟨0, by decide⟩) (.atom ⟨2, by decide⟩)))), .ff, [(.atom ⟨1, by decide⟩),(.atom ⟨5, by decide⟩)]⟩, [true,false,false,false,false,false], [3,3,1,5,7,5], [3]⟩
def t76 : ITask 4 := ⟨⟨(.imp .tt (.not (.imp (.atom ⟨1, by decide⟩) (.atom ⟨0, by decide⟩)))), .ff, [(.or (.or (.atom ⟨2, by decide⟩) .ff) (.imp (.atom ⟨1, by decide⟩) (.atom ⟨0, by decide⟩))),(.and (.and .ff (.atom ⟨0, by decide⟩)) (.not .tt)),(.or (.and (.atom ⟨3, by decide⟩) .tt) (.imp (.atom ⟨2, by decide⟩) (.atom ⟨2, by decide⟩)))]⟩, [true,true,true,true], [9,1,1,7], [2]⟩
def t77 : ITask 3 := ⟨⟨(.and (.or (.not (.atom ⟨2, by decide⟩)) (.imp (.atom ⟨0, by decide⟩) .ff)) (.atom ⟨2, by decide⟩)), .ff, [.ff,(.and (.atom ⟨2, by decide⟩) (.or (.atom ⟨1, by decide⟩) (.atom ⟨0, by decide⟩)))]⟩, [true,false,true], [1,7,8], [1]⟩
def t78 : ITask 2 := ⟨⟨(.atom ⟨1, by decide⟩), .ff, [(.and (.and (.atom ⟨0, by decide⟩) (.atom ⟨0, by decide⟩)) .tt)]⟩, [false,false], [1,8], [0]⟩
def t79 : ITask 5 := ⟨⟨.tt, .ff, [(.or (.or (.atom ⟨1, by decide⟩) (.atom ⟨1, by decide⟩)) (.imp (.atom ⟨0, by decide⟩) (.atom ⟨2, by decide⟩))),(.atom ⟨3, by decide⟩),(.not (.atom ⟨4, by decide⟩))]⟩, [false,true,false,false,false], [4,6,8,7,2], [1,3]⟩
def t80 : ITask 6 := ⟨⟨(.or (.or (.not (.atom ⟨2, by decide⟩)) (.or (.atom ⟨5, by decide⟩) (.atom ⟨5, by decide⟩))) (.not (.atom ⟨0, by decide⟩))), .ff, [(.and (.or (.atom ⟨3, by decide⟩) (.atom ⟨1, by decide⟩)) (.and .ff (.atom ⟨4, by decide⟩))),(.or (.imp .tt (.atom ⟨1, by decide⟩)) (.or .tt (.atom ⟨5, by decide⟩)))]⟩, [false,true,false,false,true,false], [3,2,6,8,5,8], [4]⟩
def t81 : ITask 4 := ⟨⟨(.or (.imp (.imp (.atom ⟨2, by decide⟩) (.atom ⟨3, by decide⟩)) .tt) (.and (.or (.atom ⟨3, by decide⟩) (.atom ⟨0, by decide⟩)) (.or (.atom ⟨0, by decide⟩) (.atom ⟨0, by decide⟩)))), .ff, [(.atom ⟨1, by decide⟩)]⟩, [false,true,true,false], [3,8,8,4], [3]⟩
def t82 : ITask 2 := ⟨⟨.tt, .ff, [(.and (.and .ff (.atom ⟨0, by decide⟩)) (.and .tt .tt)),(.imp (.and (.atom ⟨1, by decide⟩) .ff) (.atom ⟨0, by decide⟩))]⟩, [true,true], [2,1], [0]⟩
def t83 : ITask 3 := ⟨⟨(.imp (.imp (.and .tt (.atom ⟨2, by decide⟩)) (.not (.atom ⟨1, by decide⟩))) (.atom ⟨0, by decide⟩)), .ff, [(.atom ⟨1, by decide⟩)]⟩, [false,false,false], [5,7,4], []⟩
def t84 : ITask 2 := ⟨⟨(.or (.or (.atom ⟨1, by decide⟩) (.not (.atom ⟨0, by decide⟩))) (.imp .ff .ff)), .ff, []⟩, [false,false], [5,7], [0]⟩
def t85 : ITask 3 := ⟨⟨(.not (.and (.atom ⟨1, by decide⟩) (.or (.atom ⟨0, by decide⟩) (.atom ⟨2, by decide⟩)))), .ff, [.ff]⟩, [true,true,true], [7,1,9], [0,1]⟩
def t86 : ITask 3 := ⟨⟨(.and (.atom ⟨1, by decide⟩) .tt), .ff, [(.and (.atom ⟨1, by decide⟩) (.imp (.atom ⟨2, by decide⟩) (.atom ⟨0, by decide⟩)))]⟩, [true,false,true], [9,7,2], []⟩
def t87 : ITask 3 := ⟨⟨(.not (.or (.imp (.atom ⟨1, by decide⟩) (.atom ⟨0, by decide⟩)) (.imp (.atom ⟨2, by decide⟩) .tt))), .ff, []⟩, [true,true,true], [3,3,3], []⟩
def t88 : ITask 24 := ⟨⟨(.and (.and (.and (.or (.atom ⟨0, by decide⟩) (.atom ⟨1, by decide⟩)) (.and (.or (.atom ⟨2, by decide⟩) (.atom ⟨3, by decide⟩)) (.or (.atom ⟨4, by decide⟩) (.atom ⟨5, by decide⟩)))) (.and (.or (.atom ⟨6, by decide⟩) (.atom ⟨7, by decide⟩)) (.and (.or (.atom ⟨8, by decide⟩) (.atom ⟨9, by decide⟩)) (.or (.atom ⟨10, by decide⟩) (.atom ⟨11, by decide⟩))))) (.and (.and (.or (.atom ⟨12, by decide⟩) (.atom ⟨13, by decide⟩)) (.and (.or (.atom ⟨14, by decide⟩) (.atom ⟨15, by decide⟩)) (.or (.atom ⟨16, by decide⟩) (.atom ⟨17, by decide⟩)))) (.and (.or (.atom ⟨18, by decide⟩) (.atom ⟨19, by decide⟩)) (.and (.or (.atom ⟨20, by decide⟩) (.atom ⟨21, by decide⟩)) (.or (.atom ⟨22, by decide⟩) (.atom ⟨23, by decide⟩)))))), .ff, []⟩, [false,false,false,false,false,false,false,false,false,false,false,false,false,false,false,false,false,false,false,false,false,false,false,false], [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1], []⟩
def t89 : ITask 24 := ⟨⟨(.not (.and (.and (.and (.and (.atom ⟨0, by decide⟩) (.and (.atom ⟨1, by decide⟩) (.atom ⟨2, by decide⟩))) (.and (.atom ⟨3, by decide⟩) (.and (.atom ⟨4, by decide⟩) (.atom ⟨5, by decide⟩)))) (.and (.and (.atom ⟨6, by decide⟩) (.and (.atom ⟨7, by decide⟩) (.atom ⟨8, by decide⟩))) (.and (.atom ⟨9, by decide⟩) (.and (.atom ⟨10, by decide⟩) (.atom ⟨11, by decide⟩))))) (.and (.and (.and (.atom ⟨12, by decide⟩) (.and (.atom ⟨13, by decide⟩) (.atom ⟨14, by decide⟩))) (.and (.atom ⟨15, by decide⟩) (.and (.atom ⟨16, by decide⟩) (.atom ⟨17, by decide⟩)))) (.and (.and (.atom ⟨18, by decide⟩) (.and (.atom ⟨19, by decide⟩) (.atom ⟨20, by decide⟩))) (.and (.atom ⟨21, by decide⟩) (.and (.atom ⟨22, by decide⟩) (.atom ⟨23, by decide⟩))))))), .ff, []⟩, [false,false,false,false,false,false,false,false,false,false,false,false,false,false,false,false,false,false,false,false,false,false,false,false], [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1], []⟩
def t90 : ITask 24 := ⟨⟨(.or (.or (.or (.and (.atom ⟨0, by decide⟩) (.atom ⟨12, by decide⟩)) (.or (.and (.atom ⟨1, by decide⟩) (.atom ⟨13, by decide⟩)) (.and (.atom ⟨2, by decide⟩) (.atom ⟨14, by decide⟩)))) (.or (.and (.atom ⟨3, by decide⟩) (.atom ⟨15, by decide⟩)) (.or (.and (.atom ⟨4, by decide⟩) (.atom ⟨16, by decide⟩)) (.and (.atom ⟨5, by decide⟩) (.atom ⟨17, by decide⟩))))) (.or (.or (.and (.atom ⟨6, by decide⟩) (.atom ⟨18, by decide⟩)) (.or (.and (.atom ⟨7, by decide⟩) (.atom ⟨19, by decide⟩)) (.and (.atom ⟨8, by decide⟩) (.atom ⟨20, by decide⟩)))) (.or (.and (.atom ⟨9, by decide⟩) (.atom ⟨21, by decide⟩)) (.or (.and (.atom ⟨10, by decide⟩) (.atom ⟨22, by decide⟩)) (.and (.atom ⟨11, by decide⟩) (.atom ⟨23, by decide⟩)))))), .ff, []⟩, [false,false,false,false,false,false,false,false,false,false,false,false,false,false,false,false,false,false,false,false,false,false,false,false], [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1], []⟩
def main : IO Unit := do
  emit 0 t0 ⟨4096, 100000⟩
  emit 1 t1 ⟨4096, 100000⟩
  emit 2 t2 ⟨4096, 100000⟩
  emit 3 t3 ⟨4096, 100000⟩
  emit 4 t4 ⟨4096, 100000⟩
  emit 5 t5 ⟨4096, 100000⟩
  emit 6 t6 ⟨4096, 100000⟩
  emit 7 t7 ⟨4096, 100000⟩
  emit 8 t8 ⟨4096, 100000⟩
  emit 9 t9 ⟨4096, 100000⟩
  emit 10 t10 ⟨4096, 100000⟩
  emit 11 t11 ⟨4096, 100000⟩
  emit 12 t12 ⟨4096, 100000⟩
  emit 13 t13 ⟨4096, 100000⟩
  emit 14 t14 ⟨4096, 100000⟩
  emit 15 t15 ⟨4096, 100000⟩
  emit 16 t16 ⟨4096, 100000⟩
  emit 17 t17 ⟨4096, 100000⟩
  emit 18 t18 ⟨4096, 100000⟩
  emit 19 t19 ⟨4096, 100000⟩
  emit 20 t20 ⟨4096, 100000⟩
  emit 21 t21 ⟨4096, 100000⟩
  emit 22 t22 ⟨4096, 100000⟩
  emit 23 t23 ⟨4096, 100000⟩
  emit 24 t24 ⟨1, 100000⟩
  emit 25 t25 ⟨4096, 1⟩
  emit 26 t26 ⟨4096, 100000⟩
  emit 27 t27 ⟨4096, 100000⟩
  emit 28 t28 ⟨4096, 100000⟩
  emit 29 t29 ⟨4096, 100000⟩
  emit 30 t30 ⟨4096, 100000⟩
  emit 31 t31 ⟨4096, 100000⟩
  emit 32 t32 ⟨1, 100000⟩
  emit 33 t33 ⟨4096, 1⟩
  emit 34 t34 ⟨4096, 100000⟩
  emit 35 t35 ⟨4096, 100000⟩
  emit 36 t36 ⟨4096, 100000⟩
  emit 37 t37 ⟨4096, 100000⟩
  emit 38 t38 ⟨4096, 100000⟩
  emit 39 t39 ⟨4096, 100000⟩
  emit 40 t40 ⟨1, 100000⟩
  emit 41 t41 ⟨4096, 1⟩
  emit 42 t42 ⟨4096, 100000⟩
  emit 43 t43 ⟨4096, 100000⟩
  emit 44 t44 ⟨4096, 100000⟩
  emit 45 t45 ⟨4096, 100000⟩
  emit 46 t46 ⟨4096, 100000⟩
  emit 47 t47 ⟨4096, 100000⟩
  emit 48 t48 ⟨1, 100000⟩
  emit 49 t49 ⟨4096, 1⟩
  emit 50 t50 ⟨4096, 100000⟩
  emit 51 t51 ⟨4096, 100000⟩
  emit 52 t52 ⟨4096, 100000⟩
  emit 53 t53 ⟨4096, 100000⟩
  emit 54 t54 ⟨4096, 100000⟩
  emit 55 t55 ⟨4096, 100000⟩
  emit 56 t56 ⟨1, 100000⟩
  emit 57 t57 ⟨4096, 1⟩
  emit 58 t58 ⟨4096, 100000⟩
  emit 59 t59 ⟨4096, 100000⟩
  emit 60 t60 ⟨4096, 100000⟩
  emit 61 t61 ⟨4096, 100000⟩
  emit 62 t62 ⟨4096, 100000⟩
  emit 63 t63 ⟨4096, 100000⟩
  emit 64 t64 ⟨1, 100000⟩
  emit 65 t65 ⟨4096, 1⟩
  emit 66 t66 ⟨4096, 100000⟩
  emit 67 t67 ⟨4096, 100000⟩
  emit 68 t68 ⟨4096, 100000⟩
  emit 69 t69 ⟨4096, 100000⟩
  emit 70 t70 ⟨4096, 100000⟩
  emit 71 t71 ⟨4096, 100000⟩
  emit 72 t72 ⟨1, 100000⟩
  emit 73 t73 ⟨4096, 1⟩
  emit 74 t74 ⟨4096, 100000⟩
  emit 75 t75 ⟨4096, 100000⟩
  emit 76 t76 ⟨4096, 100000⟩
  emit 77 t77 ⟨4096, 100000⟩
  emit 78 t78 ⟨4096, 100000⟩
  emit 79 t79 ⟨4096, 100000⟩
  emit 80 t80 ⟨1, 100000⟩
  emit 81 t81 ⟨4096, 1⟩
  emit 82 t82 ⟨4096, 100000⟩
  emit 83 t83 ⟨4096, 100000⟩
  emit 84 t84 ⟨4096, 100000⟩
  emit 85 t85 ⟨4096, 100000⟩
  emit 86 t86 ⟨4096, 100000⟩
  emit 87 t87 ⟨4096, 100000⟩
  emit 88 t88 ⟨4096, 100000⟩
  emit 89 t89 ⟨4096, 100000⟩
  emit 90 t90 ⟨40, 100000⟩
