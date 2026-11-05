import PCSReferenceCertificates.Compile
import PCSDecisionDiagram.Intervention
namespace PCSDD
open PCSOmega
set_option maxHeartbeats 0
def resolvedReceipt (t : CTask n) (lim : Limits) (ctx s c d : Nat) (m : Mgr) : CReceipt n :=
      let cex := (world n m.nodes d).map (fun w =>
        ({ assignment := w, sourceTrue := t.source.eval (envOf w),
           candidateTrue := t.candidate.eval (envOf w),
           assumptionsTrue := t.assumptions.map (fun f => f.eval (envOf w)) } : CexRec))
      { task := t, limits := lim,
        decision := if d = 0 then .equivalentUnderAssumptions else .counterexample,
        contextExample := world n m.nodes ctx, counterexample := cex, unsatCore := none,
        coreWitnesses := none, diagram := some ⟨m.nodes, some s, some c, ctx, some d⟩,
        limitReached := none, work := m.work, pcsAuthority := false, leanKernelChecked := false }

theorem check_of_pipeline {t : CTask n} {lim : Limits} {ctx s c d : Nat} {m : Mgr}
  (h : pipeline t lim = .ok (.decided ctx s c d,m)) :
  check t lim = resolvedReceipt t lim ctx s c d m := by
  unfold check
  rw [h]
  rfl

def planAgainst (t : ITask n) (lim : Limits) (sym : CReceipt n) : Except String (IReceipt n) :=
  if t.validB = false then .error "invalid intervention task" else
  if lim.valid = false then .error "invalid limits" else
  match sym.decision with
  | .resourceLimit => .ok (IReceipt.bare t lim sym .resourceLimit)
  | .inconsistentAssumptions => .ok (IReceipt.bare t lim sym .inconsistentAssumptions)
  | _ =>
    match sym.diagram with
    | none => .error "internal: missing diagram"
    | some dr =>
      match dr.difference with
      | none => .error "internal: missing difference root"
      | some root =>
        let P := t.prices
        let st := bellmanPass dr.nodes P
        match st.cells.getD root none with
        | none => .ok { IReceipt.bare t lim sym .noFeasiblePlan with
                        cells := some st.cells, dpNodes := dr.nodes.size }
        | some c =>
          match walkPy dr.nodes st.choices (dr.nodes.size + 1) root (baseList P n) with
          | none => .error "internal: reconstruction did not reach TRUE"
          | some a =>
            if guard t a c.cost then
              .ok { task := t, limits := lim, symbolic := sym, decision := .optimalPlan,
                    minimumCost := some c.cost, optimalCount := some c.count, assignment := some a,
                    flips := some ((List.range n).filter (fun i => flips P a i)),
                    mandatory := some (bitsOf n c.mand), possible := some (bitsOf n c.poss),
                    cells := some st.cells, dpNodes := dr.nodes.size, pcsAuthority := false,
                    leanKernelChecked := false }
            else .error "internal: plan witness does not match the declared task or cost"

theorem plan_of_check {t : ITask n} {lim : Limits} {sym : CReceipt n}
  (h : check t.problem lim = sym) : plan t lim = planAgainst t lim sym := by
  unfold plan planAgainst
  rw [h]
  rfl

theorem plan_from_pipeline {t : ITask n} {lim : Limits} {ctx s c d : Nat} {m : Mgr} {r : IReceipt n}
  (h : pipeline t.problem lim = .ok (.decided ctx s c d,m))
  (hp : planAgainst t lim (resolvedReceipt t.problem lim ctx s c d m) = .ok r) :
  plan t lim = .ok r := (plan_of_check (check_of_pipeline h)).trans hp
#print axioms check_of_pipeline
#print axioms plan_of_check
#print axioms plan_from_pipeline
end PCSDD
