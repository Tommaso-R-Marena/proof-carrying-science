/-
Abstract non-identifiability: if two models agree on observations but disagree
on the target, the target is not a function of the observational law.

Ordinary kernel proof; no Mathlib; no `sorry`.
-/
namespace PcsPccr

universe u v w

structure ModelClass (Obs : Type u) (Target : Type v) where
  models : Type w
  observe : models → Obs
  target : models → Target

structure NonIdentWitness {Obs : Type u} {Target : Type v} (𝓜 : ModelClass Obs Target) where
  m₁ : 𝓜.models
  m₂ : 𝓜.models
  obs_eq : 𝓜.observe m₁ = 𝓜.observe m₂
  target_ne : 𝓜.target m₁ ≠ 𝓜.target m₂

/-- A valid witness implies the target is not observationally determined. -/
theorem nonidentifiable_of_witness
    {Obs : Type u} {Target : Type v} (𝓜 : ModelClass Obs Target)
    (w : NonIdentWitness 𝓜) :
    ¬ ∃ f : Obs → Target, ∀ m : 𝓜.models, 𝓜.target m = f (𝓜.observe m) := by
  rintro ⟨f, hf⟩
  have h1 := hf w.m₁
  have h2 := hf w.m₂
  have eq : 𝓜.target w.m₁ = 𝓜.target w.m₂ := by
    calc
      𝓜.target w.m₁ = f (𝓜.observe w.m₁) := h1
      _ = f (𝓜.observe w.m₂) := by rw [w.obs_eq]
      _ = 𝓜.target w.m₂ := by rw [← h2]
  exact w.target_ne eq

inductive ToyModel where
  | mA | mB
  deriving DecidableEq, Repr

def toyObserve : ToyModel → Nat
  | .mA => 0
  | .mB => 0

def toyTarget : ToyModel → Nat
  | .mA => 1
  | .mB => 2

def toyClass : ModelClass Nat Nat where
  models := ToyModel
  observe := toyObserve
  target := toyTarget

def toyWitness : NonIdentWitness toyClass where
  m₁ := .mA
  m₂ := .mB
  obs_eq := rfl
  target_ne := by decide

theorem toy_target_not_observationally_determined :
    ¬ ∃ f : Nat → Nat, ∀ m : ToyModel, toyTarget m = f (toyObserve m) :=
  nonidentifiable_of_witness toyClass toyWitness

end PcsPccr
