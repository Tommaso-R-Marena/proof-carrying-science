import PCCA.Stoich
import Mathlib.Tactic.Ring

/-!
# Elemental / moiety conservation from stoichiometric balance

If every reaction is balanced for an atom (or moiety) counting vector `A`, then
`A` is a stoichiometric conservation law. Combined with `conserved_all_times`,
every stoichiometric trajectory preserves the total atom/moiety count.
-/
set_option autoImplicit false
set_option linter.unusedSectionVars false

namespace PCCA.Elemental

open Finset PCCA.Stoich

variable {σ ρ K : Type*} [Fintype σ] [Fintype ρ] [Field K]

/-- Reaction `r` is atom-balanced for counting vector `A` when net atom change is 0. -/
def AtomBalanced (A : σ → K) (S : Matrix σ ρ K) (r : ρ) : Prop :=
  ∑ s, A s * S s r = 0

/-- Every reaction is atom-balanced. -/
def ElementBalanced (A : σ → K) (S : Matrix σ ρ K) : Prop :=
  ∀ r, AtomBalanced A S r

/-- Element balance is exactly the conservation-law predicate. -/
theorem elementBalanced_iff_conservation (A : σ → K) (S : Matrix σ ρ K) :
    ElementBalanced A S ↔ ConservationLaw A S :=
  Iff.rfl

theorem elemental_is_conservation (A : σ → K) (S : Matrix σ ρ K)
    (h : ElementBalanced A S) : ConservationLaw A S :=
  (elementBalanced_iff_conservation A S).mp h

theorem elemental_pool_invariant (A : σ → K) (S : Matrix σ ρ K)
    (h : ElementBalanced A S) (ξs : Nat → ρ → K) (x : σ → K) (n : Nat) :
    pool A (evolve S ξs x n) = pool A x :=
  conserved_all_times A S (elemental_is_conservation A S h) ξs x n

/-- Exact rational elemental-balance check. -/
def checkElemental {nSpec nRxn : Nat}
    (A : Fin nSpec → ℚ) (S : Fin nSpec → Fin nRxn → ℚ) : Bool :=
  PCCA.Stoich.check A S

theorem checkElemental_sound {nSpec nRxn : Nat}
    {A : Fin nSpec → ℚ} {S : Fin nSpec → Fin nRxn → ℚ}
    (h : checkElemental A S = true) : ElementBalanced A S :=
  PCCA.Stoich.check_sound h

/-- Sum of two independent elemental conservation laws (e.g. C and H). -/
theorem joint_elemental (A B : σ → K) (S : Matrix σ ρ K)
    (hA : ElementBalanced A S) (hB : ElementBalanced B S) :
    ConservationLaw (fun s => A s + B s) S :=
  conservation_add A B S (elemental_is_conservation A S hA)
    (elemental_is_conservation B S hB)

end PCCA.Elemental
