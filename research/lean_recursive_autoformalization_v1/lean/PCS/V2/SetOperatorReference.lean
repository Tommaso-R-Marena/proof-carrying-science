import PCS.V2.SetAlgebra

namespace PCS.SetAlgebra

def pairEnv (a b : Pred α) : Fin 2 → Pred α :=
  Fin.cases a (Fin.cases b Fin.elim0)

def asOperator (e : Expr 2) (a b : Pred α) := e.denote (pairEnv a b)

/-- The restricted external reader changes equality of two binary set operators
into a universally quantified equality of their applications. -/
theorem function_reference_iff (e f : Expr 2) :
    (Contract.mk [] ⟨.equal, e, f⟩).Valid ↔
    ∀ α : Type, @asOperator α e = @asOperator α f := by
  constructor
  · intro h α
    apply funext
    intro a
    apply funext
    intro b
    exact h α (pairEnv a b) (by simp)
  · intro h α ρ _
    have env : pairEnv (ρ 0) (ρ 1) = ρ := by
      funext i
      exact Fin.cases rfl (fun j => Fin.cases rfl (fun k => Fin.elim0 k) j) i
    change e.denote ρ = f.denote ρ
    simpa [asOperator, env] using congrFun (congrFun (h α) (ρ 0)) (ρ 1)

#print axioms function_reference_iff
end PCS.SetAlgebra
