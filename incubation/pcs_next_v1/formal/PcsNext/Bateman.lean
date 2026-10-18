/-
  Discrete positivity facts for the Bateman oral PK shape on Nat-encoded parameters.
  This is a finite arithmetic fragment — not a proof about floating-point runtime.
-/
namespace PcsNext.Bateman

/-- Nonnegativity of a simplified nonnegative Bateman-style term on Nats:
    (dose * ka) * (ke^t)  (proxy placeholder using Nat powers; not IEEE floats). -/
def proxyTerm (dose ka ke t : Nat) : Nat :=
  dose * ka * (ke ^ t)

theorem proxyTerm_nonneg (dose ka ke t : Nat) : 0 ≤ proxyTerm dose ka ke t :=
  Nat.zero_le _

theorem proxyTerm_zero_dose (ka ke t : Nat) : proxyTerm 0 ka ke t = 0 := by
  simp [proxyTerm]

theorem proxyTerm_mono_dose (dose₁ dose₂ ka ke t : Nat) (h : dose₁ ≤ dose₂) :
    proxyTerm dose₁ ka ke t ≤ proxyTerm dose₂ ka ke t := by
  unfold proxyTerm
  exact Nat.mul_le_mul_right _ (Nat.mul_le_mul_right _ h)

end PcsNext.Bateman
