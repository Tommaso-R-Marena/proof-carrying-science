/-
Exact finite probability scaffolding with proven normalization consequences
that avoid heavy Mathlib order-instance search.

Full conditioning lemmas are staged; nonnegativity of masses is recorded in the
structure fields and used by clients.
-/
import Mathlib.Data.Rat.Defs
import Mathlib.Data.Fintype.Basic
import Mathlib.Algebra.BigOperators.Group.Finset.Basic

namespace PcsCausal

/-- A finite probability mass function on an arbitrary fintype α. -/
structure FinitePMF (α : Type*) [Fintype α] where
  mass : α → ℚ
  nonneg : ∀ a, 0 ≤ mass a
  normalized : (Finset.univ.sum mass) = 1

/-- Event probability via summation over a subset. -/
def FinitePMF.eventProb {α : Type*} [Fintype α] (p : FinitePMF α) (E : Finset α) : ℚ :=
  E.sum p.mass

/-- The whole space has probability 1. -/
theorem FinitePMF.eventProb_univ {α : Type*} [Fintype α] (p : FinitePMF α) :
    p.eventProb Finset.univ = 1 :=
  p.normalized

/-- Conditioning kernel (defined only when callers supply positivity). -/
def FinitePMF.condition {α : Type*} [Fintype α] [DecidableEq α]
    (p : FinitePMF α) (E : Finset α) : α → ℚ :=
  fun a =>
    let z := p.eventProb E
    if z = 0 then 0 else if a ∈ E then p.mass a / z else 0

/-- Zero-probability events yield the zero kernel (fail-closed conditioning). -/
theorem FinitePMF.condition_zero_event {α : Type*} [Fintype α] [DecidableEq α]
    (p : FinitePMF α) (E : Finset α) (hz : p.eventProb E = 0) :
    p.condition E = fun _ => 0 := by
  funext a
  simp [FinitePMF.condition, hz]

end PcsCausal
