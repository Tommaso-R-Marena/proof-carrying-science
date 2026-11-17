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
