import CertNum.Interval.MulSoundness
import Mathlib.Tactic
import Mathlib.Algebra.Order.Field.Basic

/-!
# Reciprocal / division soundness on intervals excluding zero
-/

namespace CertNum.Interval

theorem mem_recip_pos {x lo hi : ℚ} (hlo : lo ≤ x) (hhi : x ≤ hi)
    (hpos : 0 < lo) :
    (1 / x) ∈ᵢ mk' (1 / hi) (1 / lo) := by
  have hx0 : 0 < x := lt_of_lt_of_le hpos hlo
  have h1 : 1 / hi ≤ 1 / x := one_div_le_one_div_of_le hx0 hhi
  have h2 : 1 / x ≤ 1 / lo := one_div_le_one_div_of_le hpos hlo
  exact mem_mk'_of_le h1 h2

theorem mem_recip_neg {x lo hi : ℚ} (hlo : lo ≤ x) (hhi : x ≤ hi)
    (hneg : hi < 0) :
    (1 / x) ∈ᵢ mk' (1 / hi) (1 / lo) := by
  have hx0 : x < 0 := lt_of_le_of_lt hhi hneg
  -- `one_div_le_one_div_of_neg_of_le (hb : b < 0) (h : a ≤ b) : 1/b ≤ 1/a`
  have h1 : 1 / hi ≤ 1 / x := one_div_le_one_div_of_neg_of_le hneg hhi
  have h2 : 1 / x ≤ 1 / lo := one_div_le_one_div_of_neg_of_le hx0 hlo
  exact mem_mk'_of_le h1 h2

theorem recip_ok_of_excludes_zero {I : Interval}
    (hex : I.excludesZero = true) :
    (recip I).status = .ok := by
  cases I with
  | empty => simp [excludesZero] at hex
  | nonempty lo hi wf =>
    simp only [excludesZero, decide_eq_true_eq] at hex
    unfold recip
    simp only [hex, ite_true]
    rfl

theorem mem_recip {x : ℚ} {I : Interval}
    (hx : x ∈ᵢ I) (hex : I.excludesZero = true) :
    ∃ R, recip I = Enclosure.ok R ∧ (1 / x) ∈ᵢ R := by
  cases I with
  | empty => simp [excludesZero] at hex
  | nonempty lo hi wf =>
    obtain ⟨hlo, hhi⟩ := hx
    simp only [excludesZero, decide_eq_true_eq] at hex
    refine ⟨mk' (1 / hi) (1 / lo), ?_, ?_⟩
    · unfold recip; simp only [hex, ite_true]
    · cases hex with
      | inl hneg => exact mem_recip_neg hlo hhi hneg
      | inr hpos => exact mem_recip_pos hlo hhi hpos

theorem mem_div {x y : ℚ} {I J : Interval}
    (hx : x ∈ᵢ I) (hy : y ∈ᵢ J) (hex : J.excludesZero = true) :
    ∃ R, div I J = Enclosure.ok R ∧ (x / y) ∈ᵢ R := by
  obtain ⟨R, hR, hmem⟩ := mem_recip (x := y) hy hex
  have hdiv : div I J = Enclosure.ok (I.mul R) := by
    unfold div
    rw [hR]
    rfl
  refine ⟨I.mul R, hdiv, ?_⟩
  have : x / y = x * (1 / y) := by field_simp
  rw [this]
  exact mem_mul hx hmem

end CertNum.Interval
