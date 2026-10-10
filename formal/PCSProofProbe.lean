import Lean

/-! Experimental structured proof-state observer. It never admits a theorem.
Only the receiver's independently compiled final theorem authorizes success. -/
open Lean Elab Command Term Meta Tactic

namespace PCSProofProbe

partial def expression (e : Expr) : Json :=
  let node (kind : String) (children : Array Json := #[]) (value : String := "") :=
    Json.mkObj [("kind", toJson kind), ("value", toJson value), ("children", toJson children)]
  match e with
  | .bvar n => node "bound" #[] (toString n)
  | .fvar n => node "local" #[] (toString n.name)
  | .mvar n => node "goal" #[] (toString n.name)
  | .sort u => node "sort" #[] (toString u)
  | .const n us => node "constant" #[] s!"{n}:{us}"
  | .app f a => node "application" #[expression f, expression a]
  | .lam n t b _ => node "lambda" #[expression t, expression b] (toString n)
  | .forallE n t b _ => node "forall" #[expression t, expression b] (toString n)
  | .letE n t v b _ => node "let" #[expression t, expression v, expression b] (toString n)
  | .lit (.natVal n) => node "natural" #[] (toString n)
  | .lit (.strVal s) => node "string" #[] s
  | .mdata _ b => expression b
  | .proj n i b => node "projection" #[expression b] s!"{n}:{i}"

def stateJson (goals : List MVarId) : TermElabM Json := do
  let mut result := #[]
  for goal in goals do
    let item ← goal.withContext do
      let target ← instantiateMVars (← goal.getType)
      let mut locals := #[]
      for decl in (← getLCtx) do
        unless decl.isImplementationDetail do
          let type ← instantiateMVars decl.type
          locals := locals.push <| Json.mkObj [
            ("name", toJson (toString decl.userName)),
            ("id", toJson (toString decl.fvarId.name)),
            ("type", toJson (toString (← ppExpr type))),
            ("expression", expression type)]
      pure <| Json.mkObj [("target", toJson (toString (← ppExpr target))),
        ("expression", expression target), ("locals", toJson locals)]
    result := result.push item
  pure <| Json.mkObj [("goals", toJson result)]

syntax "#pcs_probe " term " => " "[" tactic,* "]" : command

elab_rules : command
  | `(#pcs_probe $type => [$actions:tactic,*]) => do
    liftTermElabM do
      let type ← elabType type
      synthesizeSyntheticMVarsNoPostponing
      let goal ← mkFreshExprMVar type
      let mut goals := [goal.mvarId!]
      let mut states := #[← stateJson goals]
      let mut status := "open"
      let mut error := ""
      for action in actions.getElems do
        if status != "invalid" then
          try
            let root ← mkFreshExprMVar (mkConst ``True)
            goals ← Tactic.run root.mvarId! do
              setGoals goals
              evalTactic action
            states := states.push (← stateJson goals)
          catch ex =>
            status := "invalid"
            error := toString (← ex.toMessageData.toString)
      if status != "invalid" && goals.isEmpty then
        let proof ← instantiateMVars goal
        if proof.hasMVar || proof.hasSorry then
          status := "invalid"
          error := "unresolved metavariable or sorry"
        else
          status := "closed"
      let result := Json.mkObj [("format", toJson "pcs-lean-state-v1"),
        ("status", toJson status), ("states", toJson states), ("error", toJson error)]
      IO.println s!"PCS_STATE:{result.compress}"

end PCSProofProbe

syntax "#pcs_catalog" : command
elab_rules : command
  | `(#pcs_catalog) => do
    liftTermElabM do
      let mut entries := #[]
      for name in [``Nat.add_zero, ``Nat.zero_add, ``Nat.add_comm, ``Nat.add_assoc,
                   ``Nat.mul_zero, ``Nat.zero_mul, ``Nat.mul_comm, ``Nat.mul_one, ``Nat.one_mul] do
        let info ← getConstInfo name
        entries := entries.push <| Json.mkObj [("name", toJson (toString name)),
          ("type", toJson (toString (← ppExpr info.type))), ("expression", PCSProofProbe.expression info.type)]
      IO.println s!"PCS_CATALOG:{(toJson entries).compress}"

syntax "#pcs_audit " ident : command
elab_rules : command
  | `(#pcs_audit $name:ident) => do
    let axioms ← collectAxioms name.getId
    let info ← getConstInfo name.getId
    let result := Json.mkObj [("format", toJson "pcs-lean-kernel-v1"),
      ("axioms", toJson (axioms.map toString)),
      ("expression", PCSProofProbe.expression info.type)]
    IO.println s!"PCS_KERNEL:{result.compress}"
