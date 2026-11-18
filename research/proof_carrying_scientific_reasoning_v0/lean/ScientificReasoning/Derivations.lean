import ScientificReasoning.Authority

/-!
# Derivations with support sets

No ex falso rule — contradiction containment for this fragment.
-/

namespace ScientificReasoning

/-- Support set: premise ids on which a derivation depends. -/
abbrev Support := List PropId

def Support.subsetOf (S : Support) (ids : List PropId) : Prop :=
  ∀ i ∈ S, i ∈ ids

/-- Inductive derivations: Hyp / AndI / AndE₁ / AndE₂ only. -/
inductive Derives : Context → Support → Authority → Formula → Prop
  | hyp (Γ : Context) (p : Premise) (hp : p ∈ Γ.premises) :
      Derives Γ [p.id] p.authority p.formula
  | andI (Γ : Context) (S T : Support) (a b : Authority) (φ ψ : Formula) :
      Derives Γ S a φ →
      Derives Γ T b ψ →
      Derives Γ (S ++ T) (Authority.meet a b) (Formula.and φ ψ)
  | andE1 (Γ : Context) (S : Support) (a : Authority) (φ ψ : Formula) :
      Derives Γ S a (Formula.and φ ψ) →
      Derives Γ S a φ
  | andE2 (Γ : Context) (S : Support) (a : Authority) (φ ψ : Formula) :
      Derives Γ S a (Formula.and φ ψ) →
      Derives Γ S a ψ

/-- Semantic entailment for this fragment: truth assignment respecting context atoms.
We interpret only positive context formulas that are atoms or negated atoms for v0
evaluation of explosion-freedom; full boolean algebra is not claimed. -/
abbrev Assignment := PropId → Bool

/-- Evaluate formulas under a boolean assignment of atoms. -/
def Formula.eval (σ : Assignment) : Formula → Bool
  | .atom i => σ i
  | .not φ => !(Formula.eval σ φ)
  | .and φ ψ => Formula.eval σ φ && Formula.eval σ ψ

/-- Context is satisfied if every *declared* premise formula evaluates true under σ.
(Empirical truth of the world is external; this is the object-level model.) -/
def Context.satisfied (Γ : Context) (σ : Assignment) : Prop :=
  ∀ p ∈ Γ.premises, Formula.eval σ p.formula = true

/-- Semantic consequence: every satisfying assignment makes φ true. -/
def Entails (Γ : Context) (φ : Formula) : Prop :=
  ∀ σ, Context.satisfied Γ σ → Formula.eval σ φ = true

end ScientificReasoning
