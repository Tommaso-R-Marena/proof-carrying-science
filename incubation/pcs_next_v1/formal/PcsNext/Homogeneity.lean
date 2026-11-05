/-
  Discrete dose-homogeneity proxy: concentration scale factor tracks dose scale.
  C_proxy(dose) := dose * k  (k encodes 1/V * exp(...) as a Nat scale).
  Scope: Nat arithmetic — not floating-point PK.
-/
namespace PcsNext.Homogeneity

def concProxy (dose k : Nat) : Nat := dose * k

theorem concProxy_scale (dose k α : Nat) :
    concProxy (α * dose) k = α * concProxy dose k := by
  unfold concProxy
  rw [Nat.mul_assoc α dose k]

theorem concProxy_zero_dose (k : Nat) : concProxy 0 k = 0 := by
  simp [concProxy]

theorem concProxy_mono_dose (dose₁ dose₂ k : Nat) (h : dose₁ ≤ dose₂) :
    concProxy dose₁ k ≤ concProxy dose₂ k := by
  unfold concProxy
  exact Nat.mul_le_mul_right k h

/-- Distinct scales disagree when dose and k are positive. -/
theorem scale_two_ne_one (dose k : Nat) (hd : 0 < dose) (hk : 0 < k) :
    concProxy (2 * dose) k ≠ concProxy dose k := by
  unfold concProxy
  intro h
  have hk' : 0 < dose * k := Nat.mul_pos hd hk
  -- h : 2 * dose * k = dose * k, and 2 * dose * k = 2 * (dose * k)
  have h' : 2 * (dose * k) = dose * k := by
    simpa [Nat.mul_assoc] using h
  omega

end PcsNext.Homogeneity
