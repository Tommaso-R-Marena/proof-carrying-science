/-
PCS ClaimCheck v1 — real-number meaning of the checker's rational tests (Mathlib).

RESEARCH SIDECAR; proof-only.  Nothing here is needed to check or replay a claim.  These
theorems are about the *same definitions* that `ClaimCheck.lean` executes, and say what a
kernel-checked verdict means in ordinary real-number terms:

* `sqrtInInterval_iff`  the rational test used for standard deviations, standard errors and
  correlations is equivalent to `lo ≤ s·√q ≤ hi` over the reals;
* `within_rat_iff` / `within_sqrt_iff`  a `consistent` verdict is exactly "the scaled statistic
  lies within half a unit of the last printed digit of the reported value";
* `sumQ_eq_sum`, `meanQ_eq`, `ssQ_eq`  the executable sum, mean and sum of squares are the textbook ones;
* `pearson_signed_sqrt`  the signed-square-root representation of a correlation equals the
  textbook `Sxy / (√Sxx · √Syy)`.
-/
import Mathlib.Analysis.SpecialFunctions.Sqrt
import Mathlib.Tactic
import ClaimCheck

namespace PCS.ClaimCheck

/-- `a ≤ √q` over the reals, in rational terms. -/
theorem le_sqrt_rat (a q : ℚ) : (a : ℝ) ≤ Real.sqrt (q : ℝ) ↔ (a ≤ 0 ∨ a * a ≤ q) := by
  constructor
  · intro h
    by_cases ha : a ≤ 0
    · exact Or.inl ha
    · right
      have ha' : (0 : ℝ) < (a : ℝ) := by exact_mod_cast (not_le.mp ha)
      have h2 : (a : ℝ) ^ 2 ≤ (q : ℝ) := (Real.le_sqrt' ha').mp h
      have h3 : ((a * a : ℚ) : ℝ) ≤ (q : ℝ) := by push_cast; nlinarith [h2]
      exact_mod_cast h3
  · rintro (ha | h)
    · exact le_trans (by exact_mod_cast ha) (Real.sqrt_nonneg _)
    · by_cases ha : a ≤ 0
      · exact le_trans (by exact_mod_cast ha) (Real.sqrt_nonneg _)
      · have ha' : (0 : ℝ) < (a : ℝ) := by exact_mod_cast (not_le.mp ha)
        have h3 : ((a * a : ℚ) : ℝ) ≤ (q : ℝ) := by exact_mod_cast h
        push_cast at h3
        exact (Real.le_sqrt' ha').mpr (by nlinarith [h3])

/-- `√q ≤ b` over the reals, in rational terms. -/
theorem sqrt_le_rat (b q : ℚ) (hq : 0 ≤ q) : Real.sqrt (q : ℝ) ≤ (b : ℝ) ↔ (0 ≤ b ∧ q ≤ b * b) := by
  have hq' : (0 : ℝ) ≤ (q : ℝ) := by exact_mod_cast hq
  constructor
  · intro h
    have hb : (0 : ℝ) ≤ (b : ℝ) := le_trans (Real.sqrt_nonneg _) h
    refine ⟨by exact_mod_cast hb, ?_⟩
    have h2 : (q : ℝ) ≤ (b : ℝ) ^ 2 := (Real.sqrt_le_left hb).mp h
    have h3 : (q : ℝ) ≤ ((b * b : ℚ) : ℝ) := by push_cast; nlinarith [h2]
    exact_mod_cast h3
  · rintro ⟨hb, h⟩
    have hb' : (0 : ℝ) ≤ (b : ℝ) := by exact_mod_cast hb
    have h3 : (q : ℝ) ≤ ((b * b : ℚ) : ℝ) := by exact_mod_cast h
    push_cast at h3
    exact (Real.sqrt_le_left hb').mpr (by nlinarith [h3])

/--
**Meaning of the square-root test.**  For a sign `s ∈ {-1, 0, 1}` and a rational `q ≥ 0`,
the checker's rational test holds exactly when `lo ≤ s·√q ≤ hi` over the reals.
-/
theorem sqrtInInterval_iff (lo hi : ℚ) (s : ℤ) (q : ℚ) (hq : 0 ≤ q)
    (hs : s = 0 ∨ s = 1 ∨ s = -1) :
    sqrtInInterval lo hi s q = true ↔
      (lo : ℝ) ≤ (s : ℝ) * Real.sqrt (q : ℝ) ∧ (s : ℝ) * Real.sqrt (q : ℝ) ≤ (hi : ℝ) := by
  by_cases hq0 : q = 0
  · subst hq0
    simp [sqrtInInterval]
  · have hqpos : 0 < q := lt_of_le_of_ne hq (Ne.symm hq0)
    rcases hs with rfl | rfl | rfl
    · simp [sqrtInInterval]
    · have h1 := le_sqrt_rat lo q
      have h2 := sqrt_le_rat hi q hq
      simp only [sqrtInInterval, hq0, Int.cast_one, one_mul]
      simp [h1, h2]
    · -- s = -1 :  lo ≤ -√q ↔ √q ≤ -lo,   -√q ≤ hi ↔ -hi ≤ √q
      have h1 := sqrt_le_rat (-lo) q hq
      have h2 := le_sqrt_rat (-hi) q
      have e1 : (lo : ℝ) ≤ ((-1 : ℤ) : ℝ) * Real.sqrt (q : ℝ) ↔ Real.sqrt (q : ℝ) ≤ ((-lo : ℚ) : ℝ) := by
        push_cast; constructor <;> intro h <;> linarith
      have e2 : ((-1 : ℤ) : ℝ) * Real.sqrt (q : ℝ) ≤ (hi : ℝ) ↔ ((-hi : ℚ) : ℝ) ≤ Real.sqrt (q : ℝ) := by
        push_cast; constructor <;> intro h <;> linarith
      rw [e1, e2, h1, h2]
      simp only [sqrtInInterval, hq0]
      simp

/-- The executable sum is the ordinary list sum. -/
theorem sumQ_eq_sum (xs : List ℚ) : sumQ xs = xs.sum := by
  induction xs with
  | nil => rfl
  | cons x xs ih => simp [sumQ, ih]

/-- The executable mean is `sum / n`. -/
theorem meanQ_eq (xs : List ℚ) : meanQ xs = xs.sum / (xs.length : ℚ) := by
  simp [meanQ, lenQ, sumQ_eq_sum]

/-- The executable sum of squares is `Σ (x - mean)²`. -/
theorem ssQ_eq (xs : List ℚ) :
    ssQ xs = (xs.map fun x => (x - xs.sum / (xs.length : ℚ)) ^ 2).sum := by
  simp [ssQ, sumQ_eq_sum, meanQ_eq, pow_two]

/-- A `consistent` verdict for a rational statistic: within half a printed unit of the report. -/
theorem within_rat_iff (q scale r half : ℚ) :
    (Value.rat q).within scale (r - half) (r + half) = true ↔ |q * scale - r| ≤ half := by
  simp only [Value.within, Bool.and_eq_true, decide_eq_true_eq]
  rw [abs_le]
  constructor
  · rintro ⟨h1, h2⟩; constructor <;> linarith
  · rintro ⟨h1, h2⟩; constructor <;> linarith

/-- A `consistent` verdict for a square-root statistic (SD, SEM, correlation), over the reals. -/
theorem within_sqrt_iff (s : ℤ) (q scale r half : ℚ) (hq : 0 ≤ q) (hscale : 0 < scale)
    (hs : s = 0 ∨ s = 1 ∨ s = -1) :
    (Value.sqrt s q).within scale (r - half) (r + half) = true ↔
      |(s : ℝ) * Real.sqrt (q : ℝ) * (scale : ℝ) - (r : ℝ)| ≤ (half : ℝ) := by
  have hsc : (0 : ℝ) < (scale : ℝ) := by exact_mod_cast hscale
  simp only [Value.within]
  rw [sqrtInInterval_iff _ _ _ _ hq hs, abs_le]
  push_cast
  constructor
  · rintro ⟨h1, h2⟩
    have a1 := (div_le_iff₀ hsc).mp h1
    have a2 := (le_div_iff₀ hsc).mp h2
    constructor <;> linarith
  · rintro ⟨h1, h2⟩
    refine ⟨(div_le_iff₀ hsc).mpr (by linarith), (le_div_iff₀ hsc).mpr (by linarith)⟩

/--
The signed square root used for correlations is the textbook Pearson coefficient:
`sign(Sxy) · √(Sxy² / (Sxx·Syy)) = Sxy / (√Sxx · √Syy)` whenever `Sxx, Syy > 0`.
-/
theorem pearson_signed_sqrt (sxy sxx syy : ℚ) (hx : 0 < sxx) (hy : 0 < syy) :
    ((signQ sxy : ℤ) : ℝ) * Real.sqrt ((sxy * sxy / (sxx * syy) : ℚ) : ℝ) =
      (sxy : ℝ) / (Real.sqrt (sxx : ℝ) * Real.sqrt (syy : ℝ)) := by
  have hx' : (0 : ℝ) < (sxx : ℝ) := by exact_mod_cast hx
  have hy' : (0 : ℝ) < (syy : ℝ) := by exact_mod_cast hy
  have hden : (0 : ℝ) < Real.sqrt (sxx : ℝ) * Real.sqrt (syy : ℝ) :=
    mul_pos (Real.sqrt_pos.mpr hx') (Real.sqrt_pos.mpr hy')
  have hroot : Real.sqrt ((sxy * sxy / (sxx * syy) : ℚ) : ℝ) =
      |(sxy : ℝ)| / (Real.sqrt (sxx : ℝ) * Real.sqrt (syy : ℝ)) := by
    push_cast
    rw [Real.sqrt_div (mul_self_nonneg _), Real.sqrt_mul_self_eq_abs, Real.sqrt_mul hx'.le]
  rw [hroot]
  rcases lt_trichotomy sxy 0 with h | h | h
  · have hr : (sxy : ℝ) < 0 := by exact_mod_cast h
    have : signQ sxy = -1 := by simp [signQ, h, not_lt.mpr h.le]
    rw [this, abs_of_neg hr]; push_cast; ring
  · subst h; simp [signQ]
  · have hr : (0 : ℝ) < (sxy : ℝ) := by exact_mod_cast h
    have : signQ sxy = 1 := by simp [signQ, h]
    rw [this, abs_of_pos hr]; push_cast; ring

end PCS.ClaimCheck
