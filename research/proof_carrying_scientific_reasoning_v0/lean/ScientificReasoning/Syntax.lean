import Init

/-!
# Syntax for the scientific argument calculus (object-level)
-/

namespace ScientificReasoning

abbrev PropId := Nat

inductive Formula where
  | atom : PropId → Formula
  | not : Formula → Formula
  | and : Formula → Formula → Formula
  deriving Repr, DecidableEq, Inhabited

/-- Nesting depth (atom = 0); matches Python `_formula_depth` / JsonFormula.depth. -/
def Formula.depth : Formula → Nat
  | .atom _ => 0
  | .not φ => φ.depth + 1
  | .and φ ψ => Nat.max φ.depth ψ.depth + 1

/-- Certificate schema bound (Python `MAX_DEPTH`). -/
def maxFormulaDepth : Nat := 64

theorem Formula.depth_atom (i : PropId) : (Formula.atom i).depth = 0 := rfl

theorem Formula.depth_and_le_left (φ ψ : Formula) : φ.depth < (Formula.and φ ψ).depth := by
  simp only [Formula.depth]
  exact Nat.lt_succ_of_le (Nat.le_max_left _ _)

theorem Formula.depth_and_le_right (φ ψ : Formula) : ψ.depth < (Formula.and φ ψ).depth := by
  simp only [Formula.depth]
  exact Nat.lt_succ_of_le (Nat.le_max_right _ _)

/-- Epistemic / authority classification of a premise or derived claim. -/
inductive Authority where
  | disputed
  | hypothesis
  | empiricalAsserted
  | assumption
  | derived
  | mathVerified
  deriving Repr, DecidableEq, Inhabited

structure Premise where
  id : PropId
  formula : Formula
  authority : Authority
  deriving Repr, DecidableEq, Inhabited

structure Context where
  premises : List Premise
  deriving Repr, DecidableEq, Inhabited

def Context.ids (Γ : Context) : List PropId :=
  Γ.premises.map (·.id)

def Context.uniqueIds (Γ : Context) : Prop :=
  ∀ p ∈ Γ.premises, ∀ q ∈ Γ.premises, p.id = q.id → p = q

def Context.find? (Γ : Context) (i : PropId) : Option Premise :=
  Γ.premises.find? (fun p => decide (p.id = i))

def Context.hasId (Γ : Context) (i : PropId) : Prop :=
  ∃ p ∈ Γ.premises, p.id = i

end ScientificReasoning
