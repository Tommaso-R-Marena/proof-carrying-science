import CertNum.Interval.Arithmetic
import Mathlib.Tactic

/-!
# Soundness theorems for rational interval arithmetic

Fully proved (no sorry): negation, addition, subtraction, hull, intersection (→),
singleton, width nonnegativity.

Multiplication soundness is in `MulSoundness.lean`.
-/

namespace CertNum.Interval

theorem mem_neg {x : ℚ} {I : Interval} (hx : x ∈ᵢ I) : (-x) ∈ᵢ neg I := by
  cases I with
  | empty => exact False.elim hx
  | nonempty lo hi wf =>
    obtain ⟨hlo, hhi⟩ := hx
    dsimp [neg]
    exact mem_mk'_of_le (neg_le_neg hhi) (neg_le_neg hlo)

theorem mem_add {x y : ℚ} {I J : Interval}
    (hx : x ∈ᵢ I) (hy : y ∈ᵢ J) : (x + y) ∈ᵢ add I J := by
  cases I with
  | empty => exact False.elim hx
  | nonempty a b hab =>
    cases J with
    | empty => exact False.elim hy
    | nonempty c d hcd =>
      obtain ⟨ha, hb⟩ := hx
      obtain ⟨hc, hd⟩ := hy
      dsimp [add]
      exact mem_mk'_of_le (add_le_add ha hc) (add_le_add hb hd)

theorem mem_sub {x y : ℚ} {I J : Interval}
    (hx : x ∈ᵢ I) (hy : y ∈ᵢ J) : (x - y) ∈ᵢ sub I J := by
  simpa [sub, sub_eq_add_neg] using mem_add hx (mem_neg hy)

theorem mem_singleton (q : ℚ) : q ∈ᵢ singleton q := ⟨le_rfl, le_rfl⟩

theorem mem_hull_left {x : ℚ} {I J : Interval} (hx : x ∈ᵢ I) :
    x ∈ᵢ hull I J := by
  cases I with
  | empty => exact False.elim hx
  | nonempty a b hab =>
    cases J with
    | empty => simpa [hull] using hx
    | nonempty c d hcd =>
      obtain ⟨ha, hb⟩ := hx
      dsimp [hull]
      exact mem_mk'_of_le (le_trans (ratMin_le_left a c) ha)
        (le_trans hb (le_ratMax_left b d))

theorem mem_hull_right {x : ℚ} {I J : Interval} (hx : x ∈ᵢ J) :
    x ∈ᵢ hull I J := by
  cases J with
  | empty => exact False.elim hx
  | nonempty c d hcd =>
    cases I with
    | empty => simpa [hull] using hx
    | nonempty a b hab =>
      obtain ⟨hc, hd⟩ := hx
      dsimp [hull]
      exact mem_mk'_of_le (le_trans (ratMin_le_right a c) hc)
        (le_trans hd (le_ratMax_right b d))

theorem mem_inter_of_mem {x : ℚ} {I J : Interval}
    (hx : x ∈ᵢ inter I J) : x ∈ᵢ I ∧ x ∈ᵢ J := by
  cases I with
  | empty => simp [inter] at hx
  | nonempty a b hab =>
    cases J with
    | empty => simp [inter] at hx
    | nonempty c d hcd =>
      dsimp [inter, mk'] at hx
      split_ifs at hx with h
      · obtain ⟨h1, h2⟩ := hx
        refine ⟨⟨le_trans (le_ratMax_left a c) h1, le_trans h2 (ratMin_le_left b d)⟩,
                ⟨le_trans (le_ratMax_right a c) h1, le_trans h2 (ratMin_le_right b d)⟩⟩
      · exact False.elim hx

theorem width_nonneg (I : Interval) : 0 ≤ width I := by
  cases I with
  | empty => simp [width]
  | nonempty lo hi wf =>
    simpa [width] using sub_nonneg.mpr wf

end CertNum.Interval
