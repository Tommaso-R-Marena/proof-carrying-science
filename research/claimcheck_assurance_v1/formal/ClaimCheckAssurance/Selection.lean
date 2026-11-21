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

/-! ## Both confirmation routes together

The implemented policy confirms a number either directly (the readings `R` bound to it) or with the
support of a confirmed sibling number in the same sentence (`policy.py`, the pinned analysis). The
sibling route looks only at readings that are also bound to the number and that the sibling fixes,
so its reproducible set `R'` is a subset of `R`. A chooser may offer several siblings, giving
several such subsets. -/

/-- Confirmable directly, or through one of the sibling-supported reading sets `Rs`. -/
def confirmableByRoutes (R : Nat → Bool) (Rs : List (Nat → Bool)) (r k c : Nat) : Bool :=
  confirmable R r k c || Rs.any (fun R' => confirmable R' r k c)

theorem countP_or_le (p q : Nat → Bool) (l : List Nat) :
    l.countP (fun x => p x || q x) ≤ l.countP p + l.countP q := by
  induction l with
  | nil => simp
  | cons x l ih =>
    simp only [List.countP_cons]
    cases hp : p x <;> cases hq : q x <;> simp [hp, hq] <;> omega

theorem countP_any_le {α : Type} (ys : List α) (g : α → Nat → Bool) (l : List Nat) :
    l.countP (fun x => ys.any (fun y => g y x)) ≤ (ys.map (fun y => l.countP (g y))).sum := by
  induction ys with
  | nil => simp
  | cons y ys ih =>
    simp only [List.any_cons, List.map_cons, List.sum_cons]
    exact Nat.le_trans (countP_or_le (g y) (fun x => ys.any (fun y' => g y' x)) l) (by omega)

theorem sum_map_le {α : Type} (ys : List α) (f : α → Nat) (k : Nat) (h : ∀ y ∈ ys, f y ≤ k) :
    (ys.map f).sum ≤ ys.length * k := by
  induction ys with
  | nil => simp
  | cons y ys ih =>
    simp only [List.map_cons, List.sum_cons, List.length_cons, Nat.succ_mul]
    have h1 := h y (by simp)
    have h2 := ih (fun y' hy' => h y' (by simp [hy']))
    omega

/-- **Both routes together:** any `r + 1` consecutive comparable numbers contain at most
`max 1 s · k` numbers confirmable by some route, where `s` is the number of sibling-supported
reading sets, each a subset of the direct one. With one sibling set the bound is the same `k` as
for the direct route alone. -/
theorem routes_block_le (R : Nat → Bool) (Rs : List (Nat → Bool))
    (hsub : ∀ R' ∈ Rs, ∀ n, R' n = true → R n = true) (r k a : Nat) :
    (List.range' a (r + 1)).countP (confirmableByRoutes R Rs r k) ≤ max 1 Rs.length * k := by
  have hk : k ≤ max 1 Rs.length * k := Nat.le_trans (Nat.le_of_eq (Nat.one_mul k).symm)
    (Nat.mul_le_mul_right k (Nat.le_max_left 1 _))
  by_cases h : ∃ c ∈ List.range' a (r + 1), confirmable R r k c = true
  · obtain ⟨c, hc, hconf⟩ := h
    have hc' := List.mem_range'_1.mp hc
    have hwin : windowCount R r c ≤ k := by
      simp [confirmable] at hconf
      exact hconf.2
    have hsubl : (List.range' a (r + 1)).Sublist (List.range' (c - r) (c + r + 1 - (c - r))) :=
      range'_sublist_range' (by omega) (by omega)
    have hR : (List.range' a (r + 1)).countP R ≤ k := Nat.le_trans hsubl.countP_le hwin
    have himp : ∀ x ∈ List.range' a (r + 1), confirmableByRoutes R Rs r k x = true → R x = true := by
      intro x _ hx
      simp only [confirmableByRoutes, Bool.or_eq_true, List.any_eq_true] at hx
      rcases hx with hx | ⟨R', hR', hx⟩
      · simp [confirmable] at hx
        exact hx.1
      · simp [confirmable] at hx
        exact hsub R' hR' x hx.1
    exact Nat.le_trans (Nat.le_trans (List.countP_mono_left himp) hR) hk
  · have himp : ∀ x ∈ List.range' a (r + 1), confirmableByRoutes R Rs r k x = true →
        Rs.any (fun R' => confirmable R' r k x) = true := by
      intro x hx hconf
      have hnot : confirmable R r k x = false := by
        cases e : confirmable R r k x
        · rfl
        · exact absurd ⟨x, hx, e⟩ h
      simpa [confirmableByRoutes, hnot] using hconf
    calc (List.range' a (r + 1)).countP (confirmableByRoutes R Rs r k)
        ≤ (List.range' a (r + 1)).countP (fun x => Rs.any (fun R' => confirmable R' r k x)) :=
          List.countP_mono_left himp
      _ ≤ (Rs.map (fun R' => (List.range' a (r + 1)).countP (confirmable R' r k))).sum :=
          countP_any_le Rs (fun R' => confirmable R' r k) _
      _ ≤ Rs.length * k := sum_map_le Rs _ k (fun R' _ => confirmable_block_le R' r k a)
      _ ≤ max 1 Rs.length * k := Nat.mul_le_mul_right k (Nat.le_max_right 1 _)

/-- Among the first `q (r + 1)` comparable numbers at most `q · max 1 s · k` are confirmable by
some route. For the implemented rule with one supporting sibling: at most 2 in every 51. -/
theorem routes_count_le (R : Nat → Bool) (Rs : List (Nat → Bool))
    (hsub : ∀ R' ∈ Rs, ∀ n, R' n = true → R n = true) (r k q : Nat) :
    (List.range (q * (r + 1))).countP (confirmableByRoutes R Rs r k) ≤ q * (max 1 Rs.length * k) := by
  induction q with
  | zero => simp
  | succ q ih =>
    have e : List.range ((q + 1) * (r + 1)) = List.range (q * (r + 1)) ++ List.range' (q * (r + 1)) (r + 1) := by
      have := @List.range'_append 0 (q * (r + 1)) (r + 1) 1
      rw [Nat.one_mul, Nat.zero_add] at this
      rw [List.range_eq_range', List.range_eq_range', this, Nat.succ_mul]
    rw [e, List.countP_append, Nat.succ_mul]
    have := routes_block_le R Rs hsub r k (q * (r + 1))
    omega

/-- The subset hypothesis is needed: a sibling set that is not a subset of the direct one adds two
confirmable numbers to a block that already has one, 3 > max 1 1 · 2. -/
example : (List.range' 0 51).countP
    (confirmableByRoutes (fun n => n == 0) [fun n => n == 30 || n == 31] 50 2) = 3 := by
  decide +kernel

/-- Several sibling sets can each confirm different numbers: the bound grows with their number. -/
example : (List.range' 0 51).countP
    (confirmableByRoutes (fun n => decide (n % 10 = 0)) [fun n => n == 10, fun n => n == 20, fun n => n == 30] 50 2) = 3 := by
  decide +kernel

end PCS.ClaimCheck.Assurance
