/-
  Discrete Michaelis–Menten proxy on Nats:
    rate = vmax * conc / (km + conc)
  Scope: Nat arithmetic — not floating-point enzyme kinetics.
-/
namespace PcsNext.MM

def rate (vmax conc km : Nat) : Nat :=
  vmax * conc / (km + conc)

theorem rate_zero_conc (vmax km : Nat) : rate vmax 0 km = 0 := by
  simp [rate]

theorem rate_le_vmax (vmax conc km : Nat) : rate vmax conc km ≤ vmax := by
  unfold rate
  by_cases hz : km + conc = 0
  · have : conc = 0 := by omega
    simp [this]
  · have hle : conc ≤ km + conc := Nat.le_add_left conc km
    have hmul : vmax * conc ≤ (km + conc) * vmax := by
      rw [Nat.mul_comm (km + conc) vmax]
      exact Nat.mul_le_mul_left vmax hle
    exact Nat.div_le_of_le_mul hmul

/-- When km = 0 and conc > 0, rate collapses to vmax. -/
theorem rate_km_zero_of_pos_conc (vmax conc : Nat) (hc : 0 < conc) :
    rate vmax conc 0 = vmax := by
  unfold rate
  simp
  -- vmax * conc / conc = vmax
  rw [Nat.mul_comm vmax conc]
  exact Nat.mul_div_cancel_left vmax hc

theorem rate_zero_vmax (conc km : Nat) : rate 0 conc km = 0 := by
  simp [rate]

end PcsNext.MM
