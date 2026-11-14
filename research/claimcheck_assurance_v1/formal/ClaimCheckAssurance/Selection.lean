/-!
# What the decoy rule guarantees against a chooser who has seen the data

ClaimCheck v1.1 confirms a printed number `x` only if few *comparable* numbers (same number of
decimals and of digits, the nearest `2r` of them, `r = 50`) are reproduced by some eligible reading
of the sentence.  The rule is meant to bound coincidences when whoever chose the reading had looked
at the data.

Model.  Number the comparable numbers of one printed format `0, 1, 2, …` in increasing order.
`R n = true` means: some eligible reading that the sentence's wording attaches to the number
reproduces the `n`-th comparable number.  `R` is arbitrary: it already contains every reading the
chooser could pick, so nothing below depends on how the reading is chosen.  The implemented rule
confirms position `c` only if `R c` holds and at most `k` positions within distance `r` of `c`
satisfy `R` (`c` included; `k = 2` for the limit of 2 % with 100 decoys).

Results.

* `confirmable_block_le`   any `r + 1` consecutive comparable numbers contain at most `k`
                            confirmable ones;
* `confirmable_count_le`   among the first `q (r + 1)` comparable numbers at most `q k` are
                            confirmable; `confirmable_count_le_general` for any `N`.

So if the printed number is unrelated to the table, and is modelled as equally likely to be any of
`N` comparable numbers, the probability that *any* choice of reading gets it confirmed is at most
about `k / (r + 1)`: **2/51 ≈ 3.9 % for the implemented rule, not the nominal 2 %**.
`sliding_window_exceeds_nominal_rate` gives a table-independent pattern that reaches 2/52 ≈ 3.8 %,
so the bound cannot be improved to 2 % for this rule.

Two rules that do meet 2 % are proved as well:

* `k = 1` (no decoy reproduced): at most 1/51 ≈ 1.96 % (`strict_rule_within_two_percent`);
* fixed blocks of `b = 100` comparable numbers instead of a sliding window, `k = 2`: at most
  2/100 exactly (`blockConfirmable_count_le`).

Scope.  Counting statements about this model.  The uniform model of an unrelated number is an
assumption, stated here and nowhere proved; under a model whose probabilities are at most `λ` times
uniform the bounds scale by `λ`.  Nothing here is about numbers that *are* related to the table.
Pure Lean core, no imports.
-/

namespace PCS.ClaimCheck.Assurance

/-- Reproducible comparable numbers at distance at most `r` from position `c` (`c` included). -/
def windowCount (R : Nat → Bool) (r c : Nat) : Nat :=
  (List.range' (c - r) (c + r + 1 - (c - r))).countP R

/-- The decoy rule: position `c` may be confirmed only if it is reproducible and at most `k`
reproducible positions lie within distance `r` of it. -/
def confirmable (R : Nat → Bool) (r k c : Nat) : Bool :=
  R c && decide (windowCount R r c ≤ k)

/-- A stretch `a, …, a + m − 1` inside `s, …, s + n − 1` is a sublist of it. -/
theorem range'_sublist_range' {s n a m : Nat} (h1 : s ≤ a) (h2 : a + m ≤ s + n) :
    (List.range' a m).Sublist (List.range' s n) := by
  obtain ⟨t, ht⟩ : ∃ t, n = (a - s) + (m + t) := ⟨s + n - (a + m), by omega⟩
  have e1 : List.range' s (a - s) ++ List.range' a (m + t) = List.range' s n := by
    have := @List.range'_append s (a - s) (m + t) 1
    rw [Nat.one_mul, Nat.add_sub_cancel' h1] at this
    rw [this, ht]
  have e2 : List.range' a m ++ List.range' (a + m) t = List.range' a (m + t) := by
    have := @List.range'_append a m t 1
    rw [Nat.one_mul] at this
    exact this
  rw [← e1, ← e2]
  exact (List.sublist_append_left _ _).trans (List.sublist_append_right _ _)

/-- **Any `r + 1` consecutive comparable numbers contain at most `k` confirmable ones.** -/
theorem confirmable_block_le (R : Nat → Bool) (r k a : Nat) :
    (List.range' a (r + 1)).countP (confirmable R r k) ≤ k := by
  by_cases h : ∃ c ∈ List.range' a (r + 1), confirmable R r k c = true
  · obtain ⟨c, hc, hconf⟩ := h
    have hc' := List.mem_range'_1.mp hc
    have hwin : windowCount R r c ≤ k := by
      simp [confirmable] at hconf
      exact hconf.2
    have hsub : (List.range' a (r + 1)).Sublist (List.range' (c - r) (c + r + 1 - (c - r))) :=
      range'_sublist_range' (by omega) (by omega)
    calc (List.range' a (r + 1)).countP (confirmable R r k)
        ≤ (List.range' a (r + 1)).countP R :=
          List.countP_mono_left (fun x _ hx => by simp [confirmable] at hx; exact hx.1)
      _ ≤ (List.range' (c - r) (c + r + 1 - (c - r))).countP R := hsub.countP_le
      _ ≤ k := hwin
  · have : (List.range' a (r + 1)).countP (confirmable R r k) = 0 := by
      apply List.countP_eq_zero.mpr
      intro x hx hconf
      exact h ⟨x, hx, hconf⟩
    omega

/-- **Among the first `q (r + 1)` comparable numbers at most `q k` are confirmable**, whatever
readings exist and whichever is chosen. -/
theorem confirmable_count_le (R : Nat → Bool) (r k q : Nat) :
    (List.range (q * (r + 1))).countP (confirmable R r k) ≤ q * k := by
  induction q with
  | zero => simp
  | succ q ih =>
    have e : List.range ((q + 1) * (r + 1)) =
        List.range (q * (r + 1)) ++ List.range' (q * (r + 1)) (r + 1) := by
      have := @List.range'_append 0 (q * (r + 1)) (r + 1) 1
      rw [Nat.one_mul, Nat.zero_add] at this
      rw [List.range_eq_range', List.range_eq_range', this, Nat.succ_mul]
    rw [e, List.countP_append, Nat.succ_mul]
    have := confirmable_block_le R r k (q * (r + 1))
    omega

/-- The same for any number `N` of comparable numbers. -/
theorem confirmable_count_le_general (R : Nat → Bool) (r k N : Nat) :
    (List.range N).countP (confirmable R r k) ≤ (N / (r + 1) + 1) * k := by
  have hN : N ≤ (N / (r + 1) + 1) * (r + 1) := by
    have h1 := Nat.div_add_mod N (r + 1)
    have h2 : N % (r + 1) < r + 1 := Nat.mod_lt N (by omega)
    rw [Nat.mul_comm] at h1
    rw [Nat.succ_mul]
    omega
  have hsub : (List.range N).Sublist (List.range ((N / (r + 1) + 1) * (r + 1))) := by
    rw [List.range_eq_range', List.range_eq_range']
    exact range'_sublist_range' (Nat.le_refl 0) (by omega)
  exact Nat.le_trans hsub.countP_le (confirmable_count_le R r k _)

/-- The implemented rule (100 decoys, limit 2 %: at most one decoy reproduced, so `k = 2`,
`r = 50`) on the 900 three-digit numbers of one format: at most 36 are confirmable, 4 %. -/
theorem implemented_rule_three_digits (R : Nat → Bool) :
    (List.range 900).countP (confirmable R 50 2) ≤ 36 :=
  confirmable_count_le_general R 50 2 900

/-- **The nominal 2 % is not a bound for the sliding-window rule.**  When the reproducible numbers
come in adjacent pairs every 52 positions, 4 of 104 comparable numbers are confirmable: 3.8 %. -/
theorem sliding_window_exceeds_nominal_rate :
    (List.range 104).countP (confirmable (fun n => decide (n % 52 < 2)) 50 2) = 4 ∧ 2 * 104 < 4 * 100 := by
  decide +kernel

/-- Requiring that no decoy is reproduced (`k = 1`) keeps the sliding window and gives at most
one confirmable number in every 51: 1/51 < 2 %. -/
theorem strict_rule_within_two_percent (R : Nat → Bool) (q : Nat) :
    (List.range (q * 51)).countP (confirmable R 50 1) * 50 ≤ q * 51 := by
  have h : (List.range (q * 51)).countP (confirmable R 50 1) ≤ q * 1 := confirmable_count_le R 50 1 q
  omega

/-! ## A fixed-block rule meets the nominal rate exactly -/

/-- Reproducible positions in the block of `b` consecutive positions that contains `c`. -/
def blockCount (R : Nat → Bool) (b c : Nat) : Nat :=
  (List.range' (c / b * b) b).countP R

/-- Block rule: `c` may be confirmed only if it is reproducible and at most `k` positions of its
own block are. -/
def blockConfirmable (R : Nat → Bool) (b k c : Nat) : Bool :=
  R c && decide (blockCount R b c ≤ k)

theorem blockConfirmable_block_le (R : Nat → Bool) (b k j : Nat) :
    (List.range' (j * b) b).countP (blockConfirmable R b k) ≤ k := by
  by_cases h : ∃ c ∈ List.range' (j * b) b, blockConfirmable R b k c = true
  · obtain ⟨c, hc, hconf⟩ := h
    have hc' := List.mem_range'_1.mp hc
    have hdiv : c / b = j := by
      apply Nat.div_eq_of_lt_le
      · exact hc'.1
      · rw [Nat.succ_mul]; exact hc'.2
    have hwin : blockCount R b c ≤ k := by
      simp [blockConfirmable] at hconf
      exact hconf.2
    rw [blockCount, hdiv] at hwin
    exact Nat.le_trans
      (List.countP_mono_left (fun x _ hx => by simp [blockConfirmable] at hx; exact hx.1)) hwin
  · have : (List.range' (j * b) b).countP (blockConfirmable R b k) = 0 := by
      apply List.countP_eq_zero.mpr
      intro x hx hconf
      exact h ⟨x, hx, hconf⟩
    omega

/-- **Block rule: among `q b` comparable numbers at most `q k` are confirmable**, that is `k / b`:
exactly 2 % for `b = 100`, `k = 2`. -/
theorem blockConfirmable_count_le (R : Nat → Bool) (b k q : Nat) :
    (List.range (q * b)).countP (blockConfirmable R b k) ≤ q * k := by
  induction q with
  | zero => simp
  | succ q ih =>
    have e : List.range ((q + 1) * b) = List.range (q * b) ++ List.range' (q * b) b := by
      have := @List.range'_append 0 (q * b) b 1
      rw [Nat.one_mul, Nat.zero_add] at this
      rw [List.range_eq_range', List.range_eq_range', this, Nat.succ_mul]
    rw [e, List.countP_append, Nat.succ_mul]
    have := blockConfirmable_block_le R b k q
    omega

/-- The block rule's bound is attained, so it is exact. -/
example : (List.range 200).countP (blockConfirmable (fun n => decide (n % 100 < 2)) 100 2) = 4 := by
  decide +kernel

/-- Without the window condition the rule bounds nothing: every reproducible number is confirmable. -/
example : (List.range 100).countP (confirmable (fun _ => true) 50 1000) = 100 := by
  decide +kernel

end PCS.ClaimCheck.Assurance
