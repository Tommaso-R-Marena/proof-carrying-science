/-
  Discrete direct-Emax proxy:
    E = e0 + emax * c / (ec50 + c)
  Scope: Nat arithmetic — not continuous pharmacology.
-/
namespace PcsNext.Emax

def effect (e0 emax c ec50 : Nat) : Nat :=
  e0 + emax * c / (ec50 + c)

theorem effect_at_zero (e0 emax ec50 : Nat) : effect e0 emax 0 ec50 = e0 := by
  simp [effect]

theorem effect_ge_e0 (e0 emax c ec50 : Nat) : e0 ≤ effect e0 emax c ec50 := by
  unfold effect
  exact Nat.le_add_right e0 _

theorem effect_le_e0_add_emax (e0 emax c ec50 : Nat) :
    effect e0 emax c ec50 ≤ e0 + emax := by
  unfold effect
  have h : emax * c / (ec50 + c) ≤ emax := by
    by_cases hz : ec50 + c = 0
    · have : c = 0 := by omega
      simp [this]
    · have hle : c ≤ ec50 + c := Nat.le_add_left c ec50
      have hmul : emax * c ≤ (ec50 + c) * emax := by
        rw [Nat.mul_comm (ec50 + c) emax]
        exact Nat.mul_le_mul_left emax hle
      exact Nat.div_le_of_le_mul hmul
  exact Nat.add_le_add_left h e0

theorem effect_ec50_zero_pos_c (e0 emax c : Nat) (hc : 0 < c) :
    effect e0 emax c 0 = e0 + emax := by
  unfold effect
  simp
  rw [Nat.mul_comm emax c]
  have : c * emax / c = emax := Nat.mul_div_cancel_left emax hc
  rw [this]

end PcsNext.Emax
