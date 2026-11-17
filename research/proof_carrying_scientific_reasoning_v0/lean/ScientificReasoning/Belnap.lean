import ScientificReasoning.Derivations

/-!
# Belnap-style four-valued semantics (research fragment)

Addresses Finding E: classical Boolean Entails explodes on inconsistent contexts.
Here each atom is assigned a subset of {True, False} (BOTH / NEITHER / T / F).

This is an object-level model inside Lean — not a claim that Lean itself is paraconsistent.
-/

namespace ScientificReasoning.Belnap

inductive TruthValue where
  | none      -- neither
  | onlyTrue
  | onlyFalse
  | both
  deriving Repr, DecidableEq, Inhabited

def TruthValue.neg : TruthValue → TruthValue
  | .none => .none
  | .onlyTrue => .onlyFalse
  | .onlyFalse => .onlyTrue
  | .both => .both

/-- Lattice meet for conjunction (information order / bilattice ∧). -/
def TruthValue.and : TruthValue → TruthValue → TruthValue
  | .both, _ => .both
  | _, .both => .both
  | .onlyFalse, _ => .onlyFalse
  | _, .onlyFalse => .onlyFalse
  | .none, .none => .none
  | .none, .onlyTrue => .none
  | .onlyTrue, .none => .none
  | .onlyTrue, .onlyTrue => .onlyTrue

abbrev Assignment := ScientificReasoning.PropId → TruthValue

open ScientificReasoning

def Formula.eval4 (σ : Assignment) : Formula → TruthValue
  | .atom i => σ i
  | .not φ => (Formula.eval4 σ φ).neg
  | .and φ ψ => (Formula.eval4 σ φ).and (Formula.eval4 σ ψ)

/-- Designated truth for "support": value contains True (onlyTrue or both). -/
def designated (v : TruthValue) : Bool :=
  match v with
  | .onlyTrue | .both => true
  | _ => false

/-- Four-valued entailment: every assignment that designates all context premises
designates φ. Unlike classical Entails, an inconsistent context (both on an atom)
need not designate an unrelated atom. -/
def Entails4 (Γ : Context) (φ : Formula) : Prop :=
  ∀ σ, (∀ p ∈ Γ.premises, designated (Formula.eval4 σ p.formula) = true) →
    designated (Formula.eval4 σ φ) = true

/-- Countermodel witness: demoΓ-style context does not 4-entail atom 99. -/
def σ_demo : Assignment
  | 0 => .both
  | 2 => .onlyTrue
  | _ => .none

theorem atom99_not_designated_demo : designated (Formula.eval4 σ_demo (Formula.atom 99)) = false := by
  decide

/-- Under σ_demo, premises atom0 (both) and not atom0 (both) and atom2 (onlyTrue) are designated,
while atom 99 is not — so classical explosion fails in this 4-valued sense for this assignment.
Full Entails4 non-explosion for arbitrary Γ requires relating Derives to eval4 (future work). -/
theorem demo_premises_designated_atom99_not :
    designated (Formula.eval4 σ_demo (Formula.atom 0)) = true ∧
    designated (Formula.eval4 σ_demo (Formula.not (Formula.atom 0))) = true ∧
    designated (Formula.eval4 σ_demo (Formula.atom 2)) = true ∧
    designated (Formula.eval4 σ_demo (Formula.atom 99)) = false := by
  decide

end ScientificReasoning.Belnap

#print axioms ScientificReasoning.Belnap.demo_premises_designated_atom99_not
