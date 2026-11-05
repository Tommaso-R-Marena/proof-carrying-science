import PCSCountermodel.Core

/-!
# Exhaustive world enumeration and bounded countermodel search

Flat bit layout for a world of size `n` (total `2*n + n*n` bits):
* `P i`   at bit `2*i`,
* `Q i`   at bit `2*i + 1`,
* `R i j` at bit `2*n + n*i + j`.

`allWorlds n` decodes every code `m < 2^(2*n+n*n)`. `allWorlds_complete` proves that every
world of size `n` occurs (as an actual element, hence in particular extensionally).

`search` tries `n = 1, 2, 3` in order and returns the first disagreeing world found.
* `search_sound`: anything returned is a genuine disagreement on a domain of size 1–3.
* `search_minimal`: if size `n` is returned, the formulas agree on every world of every
  nonempty size `m < n`.
* `search_none`: if nothing is returned, the formulas agree on every world of size 1–3.
* `search_none_not_unbounded`: **a `none` result does NOT establish unbounded
  equivalence** — there are closed formulas on which `search` returns `none` but which
  disagree on a world of size 4.
-/

namespace PCSCountermodel

/-- Number of bits in the flat layout. -/
def numBits (n : Nat) : Nat := 2 * n + n * n

/-- Decode a code into a world using the flat bit layout. -/
def worldOfBits (n : Nat) (m : Nat) : World n where
  P i := m.testBit (2 * i.val)
  Q i := m.testBit (2 * i.val + 1)
  R i j := m.testBit (2 * n + n * i.val + j.val)

/-- All worlds of size `n` (one per code). -/
def allWorlds (n : Nat) : List (World n) :=
  (List.range (2 ^ numBits n)).map (worldOfBits n)

/-! ### Encoding a bit function as a number -/

/-- `ofBits f s L` packs bits `f s, f (s+1), …, f (s+L-1)` LSB-first. -/
def ofBits (f : Nat → Bool) : Nat → Nat → Nat
  | _, 0 => 0
  | s, L + 1 => (if f s then 1 else 0) + 2 * ofBits f (s + 1) L

theorem testBit_bit_add_zero (b : Bool) (m : Nat) :
    ((if b then 1 else 0) + 2 * m).testBit 0 = b := by
  cases b <;> simp [Nat.testBit_zero] <;> omega

theorem testBit_bit_add_succ (b : Bool) (m i : Nat) :
    ((if b then 1 else 0) + 2 * m).testBit (i + 1) = m.testBit i := by
  rw [Nat.testBit_succ]
  congr 1
  cases b <;> simp <;> omega

theorem ofBits_lt (f : Nat → Bool) : ∀ s L, ofBits f s L < 2 ^ L := by
  intro s L
  induction L generalizing s with
  | zero => simp [ofBits]
  | succ L ih =>
      have := ih (s + 1)
      simp only [ofBits, Nat.pow_succ]
      split <;> omega

theorem testBit_ofBits (f : Nat → Bool) :
    ∀ s L i, i < L → (ofBits f s L).testBit i = f (s + i) := by
  intro s L
  induction L generalizing s with
  | zero => intro i h; omega
  | succ L ih =>
      intro i h
      cases i with
      | zero => simp only [ofBits]; rw [testBit_bit_add_zero]; simp
      | succ i =>
          simp only [ofBits]
          rw [testBit_bit_add_succ, ih (s + 1) i (by omega)]
          congr 1; omega

/-! ### The bits of a world -/

/-- The bit at position `b` of a world in the flat layout. -/
def bitsOf {n : Nat} (w : World n) (b : Nat) : Bool :=
  if h : b < 2 * n then
    (if b % 2 = 0 then w.P ⟨b / 2, by omega⟩ else w.Q ⟨b / 2, by omega⟩)
  else if h2 : b < 2 * n + n * n then
    have hn : 0 < n := by
      cases n with
      | zero => simp at h2
      | succ n => omega
    w.R ⟨(b - 2 * n) / n, by
          rw [Nat.div_lt_iff_lt_mul hn]; omega⟩
        ⟨(b - 2 * n) % n, Nat.mod_lt _ hn⟩
  else false

/-- The code of a world. -/
def encode {n : Nat} (w : World n) : Nat := ofBits (bitsOf w) 0 (numBits n)

theorem encode_lt {n : Nat} (w : World n) : encode w < 2 ^ numBits n :=
  ofBits_lt _ _ _

theorem testBit_encode {n : Nat} (w : World n) (b : Nat) (hb : b < numBits n) :
    (encode w).testBit b = bitsOf w b := by
  unfold encode
  rw [testBit_ofBits _ 0 _ b hb, Nat.zero_add]

theorem R_index_lt {n : Nat} (i j : Fin n) : n * i.val + j.val < n * n := by
  have hi := i.isLt
  have hj := j.isLt
  have : n * (i.val + 1) ≤ n * n := Nat.mul_le_mul_left n hi
  rw [Nat.mul_succ] at this
  omega

/-- Decoding the code of a world gives back that world. -/
theorem worldOfBits_encode {n : Nat} (w : World n) : worldOfBits n (encode w) = w := by
  cases w with
  | mk P Q R =>
  simp only [worldOfBits, World.mk.injEq]
  refine ⟨?_, ?_, ?_⟩
  · funext i
    have hi := i.isLt
    rw [testBit_encode _ _ (by unfold numBits; omega)]
    unfold bitsOf
    rw [dif_pos (by omega), if_pos (by omega)]
    show P _ = P i
    congr 1; apply Fin.ext; simp only; omega
  · funext i
    have hi := i.isLt
    rw [testBit_encode _ _ (by unfold numBits; omega)]
    unfold bitsOf
    rw [dif_pos (by omega), if_neg (by omega)]
    show Q _ = Q i
    congr 1; apply Fin.ext; simp only; omega
  · funext i j
    have hij := R_index_lt i j
    rw [testBit_encode _ _ (by unfold numBits; omega)]
    unfold bitsOf
    have hn : 0 < n := Nat.lt_of_le_of_lt (Nat.zero_le _) i.isLt
    rw [dif_neg (by omega), dif_pos (by omega)]
    have e1 : 2 * n + n * i.val + j.val - 2 * n = j.val + n * i.val := by omega
    show R _ _ = R i j
    congr 1
    · apply Fin.ext; simp only [e1]; rw [Nat.add_mul_div_left _ _ hn, Nat.div_eq_of_lt j.isLt]
      omega
    · apply Fin.ext; simp only [e1]; rw [Nat.add_mul_mod_self_left, Nat.mod_eq_of_lt j.isLt]

/-- **Enumeration coverage.** Every world of size `n` occurs in `allWorlds n`. -/
theorem allWorlds_complete {n : Nat} (w : World n) : w ∈ allWorlds n := by
  unfold allWorlds
  rw [List.mem_map]
  exact ⟨encode w, List.mem_range.mpr (encode_lt w), worldOfBits_encode w⟩

/-- **Enumeration coverage, extensional form with explicit code.** For every interpretation
of `P`, `Q`, `R` there is a code `m < 2^(2n+n²)` whose decoded world agrees pointwise. -/
theorem enumeration_covers {n : Nat} (w : World n) :
    ∃ m, m < 2 ^ numBits n ∧
      (∀ i, (worldOfBits n m).P i = w.P i) ∧
      (∀ i, (worldOfBits n m).Q i = w.Q i) ∧
      (∀ i j, (worldOfBits n m).R i j = w.R i j) :=
  ⟨encode w, encode_lt w, by rw [worldOfBits_encode]; intros; rfl,
    by rw [worldOfBits_encode]; intros; rfl, by rw [worldOfBits_encode]; intros; rfl⟩

/-! ### Bounded search -/

/-- Search all worlds of size `n` for a disagreement. -/
def searchAt (n : Nat) (a b : Formula 0) : Option (World n) :=
  (allWorlds n).find? (fun w => checker w a b)

theorem searchAt_sound {n : Nat} {a b : Formula 0} {w : World n}
    (h : searchAt n a b = some w) :
    ¬ (Holds w emptyEnv a ↔ Holds w emptyEnv b) := by
  unfold searchAt at h
  have hc := List.find?_some h
  exact (checker_iff w a b).mp hc

theorem searchAt_none_iff (n : Nat) (a b : Formula 0) :
    searchAt n a b = none ↔ ∀ w : World n, (Holds w emptyEnv a ↔ Holds w emptyEnv b) := by
  unfold searchAt
  rw [List.find?_eq_none]
  constructor
  · intro h w
    have h1 := h w (allWorlds_complete w)
    have h2 := checker_iff w a b
    simp only [h1] at h2
    exact Decidable.byContradiction (fun hc => absurd (h2.mpr hc) (by simp))
  · intro h w _ hc
    exact (checker_iff w a b).mp (by simpa using hc) (h w)

/-- Bounded search over domain sizes 1, 2, 3 (in this order). -/
def search (a b : Formula 0) : Option (Σ n : Nat, World n) :=
  match searchAt 1 a b with
  | some w => some ⟨1, w⟩
  | none =>
    match searchAt 2 a b with
    | some w => some ⟨2, w⟩
    | none =>
      match searchAt 3 a b with
      | some w => some ⟨3, w⟩
      | none => none

/-- **Search soundness.** A returned witness is a genuine disagreement on a domain of
size 1, 2 or 3. -/
theorem search_sound {a b : Formula 0} {n : Nat} {w : World n}
    (h : search a b = some ⟨n, w⟩) :
    1 ≤ n ∧ n ≤ 3 ∧ ¬ (Holds w emptyEnv a ↔ Holds w emptyEnv b) := by
  unfold search at h
  split at h
  · rename_i w1 h1; cases h; exact ⟨by decide, by decide, searchAt_sound h1⟩
  · split at h
    · rename_i w2 h2; cases h; exact ⟨by decide, by decide, searchAt_sound h2⟩
    · split at h
      · rename_i w3 h3; cases h; exact ⟨by decide, by decide, searchAt_sound h3⟩
      · cases h

/-- **Search minimality.** If size `n` is returned, then on every nonempty smaller domain
the two formulas agree in every world. -/
theorem search_minimal {a b : Formula 0} {n : Nat} {w : World n}
    (h : search a b = some ⟨n, w⟩) :
    ∀ m, 1 ≤ m → m < n → ∀ w' : World m, (Holds w' emptyEnv a ↔ Holds w' emptyEnv b) := by
  intro m hm1 hmn
  unfold search at h
  split at h
  · cases h; omega
  · rename_i h1
    split at h
    · cases h
      have : m = 1 := by omega
      subst this; exact (searchAt_none_iff 1 a b).mp h1
    · rename_i h2
      split at h
      · cases h
        have : m = 1 ∨ m = 2 := by omega
        rcases this with rfl | rfl
        · exact (searchAt_none_iff 1 a b).mp h1
        · exact (searchAt_none_iff 2 a b).mp h2
      · cases h

/-- **Search exhaustiveness.** If nothing is returned, the formulas agree on every world of
every domain size 1, 2, 3 — and nothing more is claimed. -/
theorem search_none {a b : Formula 0} (h : search a b = none) :
    ∀ n, 1 ≤ n → n ≤ 3 → ∀ w : World n, (Holds w emptyEnv a ↔ Holds w emptyEnv b) := by
  unfold search at h
  split at h
  · cases h
  · rename_i h1
    split at h
    · cases h
    · rename_i h2
      split at h
      · cases h
      · rename_i h3
        intro n hn1 hn3
        have : n = 1 ∨ n = 2 ∨ n = 3 := by omega
        rcases this with rfl | rfl | rfl
        · exact (searchAt_none_iff 1 a b).mp h1
        · exact (searchAt_none_iff 2 a b).mp h2
        · exact (searchAt_none_iff 3 a b).mp h3

/-- Conversely, if the formulas agree on all worlds of sizes 1–3 then `search` returns `none`. -/
theorem search_eq_none_of_agree {a b : Formula 0}
    (h : ∀ n, 1 ≤ n → n ≤ 3 → ∀ w : World n, (Holds w emptyEnv a ↔ Holds w emptyEnv b)) :
    search a b = none := by
  have h1 := (searchAt_none_iff 1 a b).mpr (h 1 (by decide) (by decide))
  have h2 := (searchAt_none_iff 2 a b).mpr (h 2 (by decide) (by decide))
  have h3 := (searchAt_none_iff 3 a b).mpr (h 3 (by decide) (by decide))
  simp [search, h1, h2, h3]

/-! ### Bounded search does not establish unbounded equivalence -/

/-- A closed formula only satisfiable on domains of size ≥ 4:
`∃ x₀ x₁ x₂ x₃, (∀ i < j, R xᵢ xⱼ) ∧ (∀ i, ¬ R xᵢ xᵢ)`.
(De Bruijn index `3` is the outermost binder `x₀`, index `0` the innermost `x₃`.) -/
def fourChain : Formula 0 :=
  .ex <| .ex <| .ex <| .ex <|
    .and (.and (.and (.rel 3 2) (.rel 3 1))
               (.and (.rel 3 0) (.rel 2 1)))
    (.and (.and (.rel 2 0) (.rel 1 0))
      (.and (.and (.not (.rel 3 3)) (.not (.rel 2 2)))
            (.and (.not (.rel 1 1)) (.not (.rel 0 0)))))

/-- A contradiction: `∃ x, P x ∧ ¬ P x`. -/
def falsum : Formula 0 := .ex (.and (.pred .P 0) (.not (.pred .P 0)))

theorem falsum_false {n : Nat} (w : World n) : ¬ Holds w emptyEnv falsum := by
  simp [falsum, Holds]

theorem distinct_of_rel {n : Nat} (w : World n) {a b : Fin n}
    (hab : w.R a b = true) (haa : w.R a a = true → False) : a.val ≠ b.val := by
  intro e
  have : a = b := Fin.ext e
  subst this
  exact haa hab

theorem fourChain_needs_four {n : Nat} (w : World n) (h : Holds w emptyEnv fourChain) :
    4 ≤ n := by
  simp only [fourChain, Holds] at h
  obtain ⟨a, b, c, d, h⟩ := h
  have e0 : extend (extend (extend (extend emptyEnv a) b) c) d 0 = d := rfl
  have e1 : extend (extend (extend (extend emptyEnv a) b) c) d 1 = c := rfl
  have e2 : extend (extend (extend (extend emptyEnv a) b) c) d 2 = b := rfl
  have e3 : extend (extend (extend (extend emptyEnv a) b) c) d 3 = a := rfl
  rw [e0, e1, e2, e3] at h
  obtain ⟨⟨⟨hab, hac⟩, had, hbc⟩, ⟨hbd, hcd⟩, ⟨haa, hbb⟩, hcc, hdd⟩ := h
  have := distinct_of_rel w hab haa
  have := distinct_of_rel w hac haa
  have := distinct_of_rel w had haa
  have := distinct_of_rel w hbc hbb
  have := distinct_of_rel w hbd hbb
  have := distinct_of_rel w hcd hcc
  have := a.isLt; have := b.isLt; have := c.isLt; have := d.isLt
  omega

/-- The strict "less-than" relation on `Fin 4`. -/
def chainWorld : World 4 where
  P _ := false
  Q _ := false
  R i j := decide (i < j)

/-- **No returned witness through `n = 3` does not establish unbounded equivalence.**
`search fourChain falsum = none`, yet the two closed formulas disagree on a 4-element world. -/
theorem search_none_not_unbounded :
    search fourChain falsum = none ∧
      ¬ (Holds chainWorld emptyEnv fourChain ↔ Holds chainWorld emptyEnv falsum) := by
  refine ⟨search_eq_none_of_agree ?_, ?_⟩
  · intro n _ hn w
    constructor
    · intro h; have := fourChain_needs_four w h; omega
    · intro h; exact absurd h (falsum_false w)
  · decide

end PCSCountermodel
