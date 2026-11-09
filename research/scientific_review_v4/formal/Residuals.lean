import Std

/-!
Finite exact integer residuals for pairs whose key equality is an explicit premise.
These elementary algebraic facts do not establish a join algorithm, correspondence
with Python arithmetic, source identity, empirical validity, or scientific meaning.
-/
namespace ScientificReviewV4.Residuals

universe u

structure AlignedPair (Key : Type u) where
  observedKey : Key
  predictedKey : Key
  keysEqual : observedKey = predictedKey
  observedValue : Int
  predictedValue : Int

def residual {Key : Type u} (pair : AlignedPair Key) : Int :=
  pair.observedValue - pair.predictedValue

def square (value : Int) : Int := value * value

def sse {Key : Type u} : List (AlignedPair Key) → Int
  | [] => 0
  | pair :: rest => square (residual pair) + sse rest

theorem aligned_pair_keys_equal {Key : Type u} (pair : AlignedPair Key) :
    pair.observedKey = pair.predictedKey := pair.keysEqual

theorem mismatched_keys_cannot_form_aligned_pair {Key : Type u}
    (observedKey predictedKey : Key) (mismatch : observedKey ≠ predictedKey) :
    ¬ ∃ pair : AlignedPair Key,
      pair.observedKey = observedKey ∧ pair.predictedKey = predictedKey := by
  intro ⟨pair, observed, predicted⟩
  exact mismatch (observed.symm.trans (pair.keysEqual.trans predicted))

theorem square_nonnegative (value : Int) : 0 ≤ square value := by
  cases value with
  | ofNat value => exact Int.natCast_nonneg (value * value)
  | negSucc value => exact Int.natCast_nonneg ((value + 1) * (value + 1))

theorem square_eq_zero_iff (value : Int) : square value = 0 ↔ value = 0 := by
  constructor
  · intro zero
    exact (Int.mul_eq_zero.mp zero).elim id id
  · intro zero
    subst value
    rfl

theorem residual_zero_iff_values_equal {Key : Type u} (pair : AlignedPair Key) :
    residual pair = 0 ↔ pair.observedValue = pair.predictedValue :=
  Int.sub_eq_zero

theorem sse_nonnegative {Key : Type u} (pairs : List (AlignedPair Key)) :
    0 ≤ sse pairs := by
  induction pairs with
  | nil => exact Int.le_refl 0
  | cons pair rest ih => exact Int.add_nonneg (square_nonnegative (residual pair)) ih

theorem sse_zero_iff_aligned_values_equal {Key : Type u} (pairs : List (AlignedPair Key)) :
    sse pairs = 0 ↔ ∀ pair ∈ pairs, pair.observedValue = pair.predictedValue := by
  induction pairs with
  | nil =>
    constructor
    · intro _ item member
      exact nomatch member
    · intro _
      rfl
  | cons pair rest ih =>
    constructor
    · intro zero
      have head_nonnegative := square_nonnegative (residual pair)
      have tail_nonnegative := sse_nonnegative rest
      have sum_zero : square (residual pair) + sse rest = 0 := zero
      have head_le_zero : square (residual pair) ≤ 0 := calc
        square (residual pair) = square (residual pair) + 0 := (Int.add_zero _).symm
        _ ≤ square (residual pair) + sse rest := Int.add_le_add_left tail_nonnegative _
        _ = 0 := sum_zero
      have tail_le_zero : sse rest ≤ 0 := calc
        sse rest = 0 + sse rest := (Int.zero_add _).symm
        _ ≤ square (residual pair) + sse rest := Int.add_le_add_right head_nonnegative _
        _ = 0 := sum_zero
      have head_zero := Int.le_antisymm head_le_zero head_nonnegative
      have tail_zero := Int.le_antisymm tail_le_zero tail_nonnegative
      have head_equal := (residual_zero_iff_values_equal pair).mp
        ((square_eq_zero_iff (residual pair)).mp head_zero)
      intro item member
      cases member with
      | head => exact head_equal
      | tail _ remaining => exact ih.mp tail_zero item remaining
    · intro equal
      have head_equal := equal pair (List.Mem.head rest)
      have tail_equal : ∀ item ∈ rest, item.observedValue = item.predictedValue :=
        fun item member => equal item (List.Mem.tail pair member)
      have head_zero := (square_eq_zero_iff (residual pair)).mpr
        ((residual_zero_iff_values_equal pair).mpr head_equal)
      have tail_zero := ih.mpr tail_equal
      show square (residual pair) + sse rest = 0
      rw [head_zero, tail_zero]
      rfl

theorem nonzero_residual_rules_out_zero_sse {Key : Type u}
    (pairs : List (AlignedPair Key)) (pair : AlignedPair Key)
    (member : pair ∈ pairs) (nonzero : residual pair ≠ 0) : sse pairs ≠ 0 := by
  intro zero
  exact nonzero ((residual_zero_iff_values_equal pair).mpr
    ((sse_zero_iff_aligned_values_equal pairs).mp zero pair member))

theorem sse_preserved_by_permutation {Key : Type u}
    {left right : List (AlignedPair Key)} (permutation : left.Perm right) :
    sse left = sse right := by
  induction permutation with
  | nil => rfl
  | cons pair _ ih => exact congrArg (fun total => square (residual pair) + total) ih
  | swap first second rest =>
    exact Int.add_left_comm (square (residual second)) (square (residual first)) (sse rest)
  | trans _ _ ihLeft ihRight => exact ihLeft.trans ihRight

#print axioms aligned_pair_keys_equal
#print axioms mismatched_keys_cannot_form_aligned_pair
#print axioms square_nonnegative
#print axioms square_eq_zero_iff
#print axioms residual_zero_iff_values_equal
#print axioms sse_nonnegative
#print axioms sse_zero_iff_aligned_values_equal
#print axioms nonzero_residual_rules_out_zero_sse
#print axioms sse_preserved_by_permutation

end ScientificReviewV4.Residuals
