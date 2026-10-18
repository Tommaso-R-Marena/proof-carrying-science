/-
Non-identifiability: agreement on observations + disagreement on target
implies the target is not a function of the observational law.
-/
import Mathlib.Tactic

namespace PcsCausal

/-- Abstract model class: each model induces an observational and a target quantity. -/
structure ModelClass (Obs Target : Type*) where
  models : Type*
  observe : models → Obs
  target : models → Target

/-- A witness pair for non-identifiability of `target` from `observe`. -/
structure NonIdentWitness {Obs Target : Type*} (𝓜 : ModelClass Obs Target) where
  m₁ : 𝓜.models
  m₂ : 𝓜.models
  obs_eq : 𝓜.observe m₁ = 𝓜.observe m₂
  target_ne : 𝓜.target m₁ ≠ 𝓜.target m₂

/-- If a valid witness exists, `target` is not a function of `observe` on the model class. -/
theorem nonidentifiable_of_witness
    {Obs Target : Type*} (𝓜 : ModelClass Obs Target)
    (w : NonIdentWitness 𝓜) :
    ¬ ∃ f : Obs → Target, ∀ m : 𝓜.models, 𝓜.target m = f (𝓜.observe m) := by
  rintro ⟨f, hf⟩
  have h1 := hf w.m₁
  have h2 := hf w.m₂
  have : 𝓜.target w.m₁ = 𝓜.target w.m₂ := by
    calc
      𝓜.target w.m₁ = f (𝓜.observe w.m₁) := h1
      _ = f (𝓜.observe w.m₂) := by rw [w.obs_eq]
      _ = 𝓜.target w.m₂ := h2.symm
  exact w.target_ne this

/-!
### Scope note (documentation theorem comments)

This theorem establishes the abstract set-theoretic content of a
non-identifiability witness. Connecting it to concrete finite SCMs and
the Python witness checker is an interoperability obligation recorded in
`docs/FORMAL_STATUS.md`. No `sorry` appears in this file.
-/

end PcsCausal
