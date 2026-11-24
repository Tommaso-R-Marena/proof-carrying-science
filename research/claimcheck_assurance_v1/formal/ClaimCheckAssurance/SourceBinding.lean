import ClaimCheck

/-!
# Source binding of the reviewed ClaimCheck checker

Every ClaimCheck theorem has the form `run pcs_src claim = outcome`, where
`pcs_src : Source := ⟨0xHEX, len⟩` and `HEX` is the hexadecimal dump of the data file.
`run` never sees the file: it computes on `Source.bytes pcs_src`, a list that the checker
unpacks from the numeral in 32-byte chunks.

This module proves, about the *definitions the kernel executes* (`ClaimCheck.lean`, unchanged):

* `Source.bytes_ofBytes`   the source built from the dump of a byte string `bs` is well formed
                           and its bytes are exactly `bs`;
* `Source.ofBytes_bytes`   a well-formed source is the dump of its own bytes, so the pair
                           `(numeral, length)` is a canonical name of a byte string;
* `Source.eq_of_bytes_eq`  two well-formed sources with the same bytes are equal;
* `run_ofBytes_some`,
  `run_ofBytes_none`       `run` on the dump of `bs` is `runTable` on the strict CSV parse of
                           exactly `bs`, and undefined if `bs` is not a strict CSV table.

Not proved here (trusted or tested elsewhere): that the Lean elaborator reads the text `0x…` as
that number; that the text was written from the file (checked byte for byte by the replayer and by
`pcs_srcbind.c`); that the file is the one the authors analysed.
-/

namespace PCS.ClaimCheck.Assurance

open PCS.ClaimCheck

/-- The number whose base-256 big-endian digits are `bs`: the value of the hexadecimal dump. -/
def ofBytes (bs : List Nat) : Nat := bs.foldl (fun acc b => acc * 256 + b) 0

theorem ofBytes_append_singleton (bs : List Nat) (x : Nat) :
    ofBytes (bs ++ [x]) = ofBytes bs * 256 + x := by
  simp [ofBytes, List.foldl_append]

/-! ## `pushBytesBE k n acc` is the `k` low base-256 digits of `n`, most significant first, before `acc` -/

theorem pushBytesBE_append (k n : Nat) (acc : List Nat) :
    pushBytesBE k n acc = pushBytesBE k n [] ++ acc := by
  induction k generalizing n acc with
  | zero => simp [pushBytesBE]
  | succ k ih =>
    simp only [pushBytesBE]
    rw [ih (n / 256) ((n % 256) :: acc), ih (n / 256) [n % 256]]
    simp

theorem pushBytesBE_length (k n : Nat) (acc : List Nat) :
    (pushBytesBE k n acc).length = k + acc.length := by
  induction k generalizing n acc with
  | zero => simp [pushBytesBE]
  | succ k ih => simp only [pushBytesBE]; rw [ih]; simp; omega

theorem pushBytesBE_succ_nil (k n : Nat) :
    pushBytesBE (k + 1) n [] = pushBytesBE k (n / 256) [] ++ [n % 256] := by
  simp only [pushBytesBE]
  exact pushBytesBE_append k (n / 256) [n % 256]

/-- The `c` low digits depend only on `n mod 256 ^ c`. -/
theorem pushBytesBE_mod (c n : Nat) (acc : List Nat) :
    pushBytesBE c (n % 256 ^ c) acc = pushBytesBE c n acc := by
  induction c generalizing n acc with
  | zero => simp [pushBytesBE]
  | succ c ih =>
    simp only [pushBytesBE]
    have h1 : n % 256 ^ (c + 1) % 256 = n % 256 :=
      Nat.mod_mod_of_dvd n ⟨256 ^ c, by rw [Nat.pow_succ, Nat.mul_comm]⟩
    have h2 : n % 256 ^ (c + 1) / 256 = n / 256 % 256 ^ c := by
      rw [Nat.pow_succ, Nat.mul_comm]
      exact Nat.mod_mul_right_div_self n 256 (256 ^ c)
    rw [h1, h2, ih]

/-- Splitting `a + c` digits into the `a` high ones and the `c` low ones. -/
theorem pushBytesBE_split (a c n : Nat) (acc : List Nat) :
    pushBytesBE (a + c) n acc = pushBytesBE a (n / 256 ^ c) (pushBytesBE c n acc) := by
  induction c generalizing n acc with
  | zero => simp [pushBytesBE]
  | succ c ih =>
    have e : a + (c + 1) = (a + c) + 1 := by omega
    rw [e]
    simp only [pushBytesBE]
    rw [ih, Nat.div_div_eq_div_mul, Nat.pow_succ, Nat.mul_comm (256 ^ c) 256]

theorem drop_pushBytesBE (a c n : Nat) :
    (pushBytesBE (a + c) n []).drop a = pushBytesBE c n [] := by
  rw [pushBytesBE_split, pushBytesBE_append]
  have h := @List.drop_left _ (pushBytesBE a (n / 256 ^ c) []) (pushBytesBE c n [])
  rw [pushBytesBE_length] at h
  simpa using h

theorem pushBytesBE_lt (k n : Nat) (acc : List Nat) :
    ∀ x ∈ pushBytesBE k n acc, x < 256 ∨ x ∈ acc := by
  induction k generalizing n acc with
  | zero => intro x hx; exact Or.inr (by simpa [pushBytesBE] using hx)
  | succ k ih =>
    intro x hx
    simp only [pushBytesBE] at hx
    rcases ih (n / 256) ((n % 256) :: acc) x hx with h | h
    · exact Or.inl h
    · rcases List.mem_cons.mp h with h | h
      · exact Or.inl (by rw [h]; exact Nat.mod_lt _ (by decide))
      · exact Or.inr h

/-! ## The chunked unpacking used by the checker equals plain digit extraction -/

theorem unpackChunks_digitsLE (k n : Nat) (acc : List Nat) :
    unpackChunks (digitsLE (256 ^ chunk) k n) acc = pushBytesBE (k * chunk) n acc := by
  induction k generalizing n acc with
  | zero => simp [digitsLE, unpackChunks, pushBytesBE]
  | succ k ih =>
    simp only [digitsLE, unpackChunks]
    rw [ih, pushBytesBE_mod, Nat.succ_mul, pushBytesBE_split]

/-- What the checker computes on: the `len` low base-256 digits of the numeral, first byte first.
Holds for every source, well formed or not. -/
theorem Source.bytes_eq (s : Source) : s.bytes = pushBytesBE s.len s.num [] := by
  unfold Source.bytes
  simp only []
  rw [unpackChunks_digitsLE]
  have hle : s.len ≤ (s.len + chunk - 1) / chunk * chunk := by unfold chunk; omega
  obtain ⟨a, ha⟩ : ∃ a, (s.len + chunk - 1) / chunk * chunk = a + s.len :=
    ⟨_, (Nat.sub_add_cancel hle).symm⟩
  rw [ha, Nat.add_sub_cancel, drop_pushBytesBE]

theorem Source.bytes_length (s : Source) : s.bytes.length = s.len := by
  rw [Source.bytes_eq, pushBytesBE_length]; simp

theorem Source.bytes_lt (s : Source) : ∀ x ∈ s.bytes, x < 256 := by
  intro x hx
  rw [Source.bytes_eq] at hx
  rcases pushBytesBE_lt s.len s.num [] x hx with h | h
  · exact h
  · simp at h

/-! ## Round trip and canonicity -/

theorem pushBytesBE_ofBytes_reverse (rs : List Nat) (h : ∀ x ∈ rs, x < 256) (acc : List Nat) :
    pushBytesBE rs.length (ofBytes rs.reverse) acc = rs.reverse ++ acc := by
  induction rs generalizing acc with
  | nil => simp [pushBytesBE, ofBytes]
  | cons x rs ih =>
    have hx : x < 256 := h x (by simp)
    have hrs : ∀ y ∈ rs, y < 256 := fun y hy => h y (by simp [hy])
    simp only [List.reverse_cons, List.length_cons, ofBytes_append_singleton, pushBytesBE]
    have h1 : (ofBytes rs.reverse * 256 + x) / 256 = ofBytes rs.reverse := by omega
    have h2 : (ofBytes rs.reverse * 256 + x) % 256 = x := by omega
    rw [h1, h2, ih hrs]
    simp

theorem ofBytes_reverse_lt (rs : List Nat) (h : ∀ x ∈ rs, x < 256) :
    ofBytes rs.reverse < 256 ^ rs.length := by
  induction rs with
  | nil => simp [ofBytes]
  | cons x rs ih =>
    have hx : x < 256 := h x (by simp)
    have := ih (fun y hy => h y (by simp [hy]))
    simp only [List.reverse_cons, ofBytes_append_singleton, List.length_cons, Nat.pow_succ]
    omega

theorem ofBytes_lt (bs : List Nat) (h : ∀ x ∈ bs, x < 256) : ofBytes bs < 256 ^ bs.length := by
  have := ofBytes_reverse_lt bs.reverse (by simpa using h)
  simpa using this

theorem ofBytes_pushBytesBE (k n : Nat) : ofBytes (pushBytesBE k n []) = n % 256 ^ k := by
  induction k generalizing n with
  | zero => simp [pushBytesBE, ofBytes, Nat.mod_one]
  | succ k ih =>
    rw [pushBytesBE_succ_nil, ofBytes_append_singleton, ih, Nat.pow_succ,
      Nat.mul_comm (256 ^ k) 256, Nat.mod_mul]
    omega

theorem Source.lt_of_wellFormed {s : Source} (h : s.wellFormed = true) : s.num < 256 ^ s.len := by
  have h0 : s.num / 256 ^ s.len = 0 := Nat.eq_of_beq_eq_true h
  rcases Nat.div_eq_zero_iff.mp h0 with h1 | h1
  · exact absurd h1 (Nat.ne_of_gt (Nat.pow_pos (by decide)))
  · exact h1

/-- **Round trip.** The source built from the dump of `bs` is well formed and its bytes are `bs`. -/
theorem Source.bytes_ofBytes (bs : List Nat) (h : ∀ x ∈ bs, x < 256) :
    (Source.mk (ofBytes bs) bs.length).wellFormed = true ∧
      (Source.mk (ofBytes bs) bs.length).bytes = bs := by
  have hr : ∀ x ∈ bs.reverse, x < 256 := by simpa using h
  constructor
  · have hlt := ofBytes_lt bs h
    simp [Source.wellFormed, Nat.div_eq_of_lt hlt]
  · rw [Source.bytes_eq]
    have := pushBytesBE_ofBytes_reverse bs.reverse hr []
    simpa using this

/-- **Canonicity.** A well-formed source is the dump of its own bytes. -/
theorem Source.ofBytes_bytes (s : Source) (h : s.wellFormed = true) :
    Source.mk (ofBytes s.bytes) s.bytes.length = s := by
  have hlen := Source.bytes_length s
  have hnum : ofBytes s.bytes = s.num := by
    rw [Source.bytes_eq, ofBytes_pushBytesBE, Nat.mod_eq_of_lt (Source.lt_of_wellFormed h)]
  cases s
  simp_all

/-- Two well-formed sources with the same bytes are the same source: the numeral and the length in
a proof file determine, and are determined by, the bytes the kernel computes on. -/
theorem Source.eq_of_bytes_eq {s t : Source} (hs : s.wellFormed = true) (ht : t.wellFormed = true)
    (h : s.bytes = t.bytes) : s = t := by
  rw [← Source.ofBytes_bytes s hs, ← Source.ofBytes_bytes t ht, h]

/-- A numeral too large for its stated length is never silently truncated: `run` reports it. -/
theorem run_not_wellFormed (s : Source) (c : Claim) (h : s.wellFormed = false) :
    run s c = .undefined .sourceNotWellFormed := by
  simp [run, h]

/-- **What every ClaimCheck theorem is about.** On the dump of a byte string `bs`, `run` is
`runTable` on the strict CSV parse of exactly `bs`. -/
theorem run_ofBytes_some (bs : List Nat) (h : ∀ x ∈ bs, x < 256) (c : Claim) (t : Table)
    (ht : parseTable bs = some t) :
    run (Source.mk (ofBytes bs) bs.length) c = runTable t c := by
  obtain ⟨hw, hb⟩ := Source.bytes_ofBytes bs h
  simp [run, hw, hb, ht]

/-- If the bytes are not a strict CSV table, every claim about them is undefined. -/
theorem run_ofBytes_none (bs : List Nat) (h : ∀ x ∈ bs, x < 256) (c : Claim)
    (ht : parseTable bs = none) :
    run (Source.mk (ofBytes bs) bs.length) c = .undefined .csvMalformed := by
  obtain ⟨hw, hb⟩ := Source.bytes_ofBytes bs h
  simp [run, hw, hb, ht]

/-- `run` depends on a well-formed source only through its bytes. -/
theorem run_congr_bytes {s t : Source} (hs : s.wellFormed = true) (ht : t.wellFormed = true)
    (h : s.bytes = t.bytes) (c : Claim) : run s c = run t c := by
  rw [Source.eq_of_bytes_eq hs ht h]

/-! ## Negative controls: the hypotheses are needed -/

/-- A numeral that does not fit its length is rejected by `wellFormed`. -/
example : (Source.mk 0x010203 2).wellFormed = false := by decide

/-- Without well-formedness two different sources have the same bytes, so canonicity fails. -/
example : (Source.mk 0x010203 2).bytes = (Source.mk 0x0203 2).bytes ∧
    (Source.mk 0x010203 2) ≠ (Source.mk 0x0203 2) :=
  ⟨by decide, fun h => absurd (congrArg Source.num h) (by decide)⟩

/-- Without the byte bound the round trip fails: `[256]` is not a byte string. -/
example : (Source.mk (ofBytes [256]) 1).bytes ≠ [256] := by decide

/-- Leading zero bytes are data: the same numeral with another length is another file. -/
example : (Source.mk 0x41 1).bytes = [0x41] ∧ (Source.mk 0x41 2).bytes = [0, 0x41] := by decide

end PCS.ClaimCheck.Assurance
