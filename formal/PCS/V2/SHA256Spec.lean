import PCS.V2.SHA256
import PCS.V2.FIPS1804Spec

/-!
# The executable SHA-256 is FIPS 180-4 SHA-256

`sha256_eq_fips1804` : for every byte message `m`,
`PCS.V2.SHA256.sha256 m = PCS.V2.FIPS1804Spec.sha256 m`.

The specification side (`PCS.V2.FIPS1804Spec`) is stated over bit strings and
`BitVec 32`, derives the round constants and initial hash value from the primes, and
uses recurrences; the implementation side uses bytes, `UInt32`, hex tables, an
imperative schedule loop and a tail-recursive block fold.  The proof goes component by
component:

1. bit-string arithmetic (`bitsBE`, `bitsVal`, octet framing);
2. word operations (`UInt32` ↦ `BitVec 32` homomorphism for `+`, `Ch`, `Maj`, `Σ`, `σ`,
   rotations as `BitVec.rotateRight`);
3. constants (`K`, `H0` tables = prime-root derivation);
4. padding (byte-level `0x80`/`be64` padding = bit-level `1 ‖ 0^k ‖ ⟨ℓ⟩₆₄`);
5. parsing (`chunks`/`words` = index arithmetic on the padded bit string);
6. message schedule (array loop = recurrence);
7. compression (round fold = round recurrence; final addition);
8. chaining and output serialization.
-/

namespace PCS.V2.SHA256Spec

open PCS.V2.FIPS1804Spec (bitsBE bitsVal messageBits)

/-! ## 1. Bit strings -/

theorem bitsBE_length (n x : Nat) : (bitsBE n x).length = n := by simp [bitsBE]

theorem bitsBE_zero (x : Nat) : bitsBE 0 x = [] := rfl

theorem bitsBE_succ (n x : Nat) : bitsBE (n + 1) x = x.testBit n :: bitsBE n x := by
  simp [bitsBE, List.range_succ]

theorem bitsVal_append : ∀ (xs ys : List Bool),
    bitsVal (xs ++ ys) = bitsVal xs * 2 ^ ys.length + bitsVal ys
  | [], ys => by simp [bitsVal]
  | b :: xs, ys => by
    simp only [List.cons_append, bitsVal, List.length_append, bitsVal_append xs ys]
    cases b
    · simp
    · simp only [if_true, Nat.pow_add, Nat.add_mul]
      omega

theorem mod_two_pow_succ' (x n : Nat) :
    x % 2 ^ (n + 1) = (if x.testBit n then 2 ^ n else 0) + x % 2 ^ n := by
  rw [Nat.mod_pow_succ, Nat.testBit_eq_decide_div_mod_eq]
  rcases Nat.mod_two_eq_zero_or_one (x / 2 ^ n) with h | h <;> simp [h] <;> omega

theorem bitsVal_bitsBE : ∀ (n x : Nat), bitsVal (bitsBE n x) = x % 2 ^ n
  | 0, x => by simp [bitsBE, bitsVal, Nat.mod_one]
  | n + 1, x => by
    rw [bitsBE_succ, bitsVal, bitsBE_length, bitsVal_bitsBE n x, mod_two_pow_succ']

theorem bitsBE_split : ∀ (a b x : Nat), bitsBE (a + b) x = bitsBE a (x / 2 ^ b) ++ bitsBE b x
  | 0, b, x => by simp [bitsBE_zero]
  | a + 1, b, x => by
    rw [show a + 1 + b = (a + b) + 1 by omega, bitsBE_succ, bitsBE_split a b x, bitsBE_succ,
      Nat.testBit_div_two_pow, Nat.add_comm a b]
    rfl

theorem bitsBE_mod (n m x : Nat) (h : n ≤ m) : bitsBE n (x % 2 ^ m) = bitsBE n x := by
  simp only [bitsBE, List.map_inj_left, List.mem_reverse, List.mem_range]
  intro i hi
  rw [Nat.testBit_mod_two_pow]
  simp [show i < m by omega]

/-! ### Octet framing -/

theorem messageBits_nil : messageBits [] = [] := rfl

theorem messageBits_cons (b : UInt8) (l : List UInt8) :
    messageBits (b :: l) = bitsBE 8 b.toNat ++ messageBits l := by
  simp [messageBits]

theorem messageBits_append (l l' : List UInt8) :
    messageBits (l ++ l') = messageBits l ++ messageBits l' := by
  simp [messageBits]

theorem messageBits_length (l : List UInt8) : (messageBits l).length = 8 * l.length := by
  induction l with
  | nil => rfl
  | cons b l ih => rw [messageBits_cons, List.length_append, bitsBE_length, ih]; simp; omega

theorem messageBits_drop : ∀ (k : Nat) (l : List UInt8),
    (messageBits l).drop (8 * k) = messageBits (l.drop k)
  | 0, l => by simp
  | k + 1, [] => by simp [messageBits_nil]
  | k + 1, b :: l => by
    rw [messageBits_cons, show 8 * (k + 1) = 8 + 8 * k by omega, ← List.drop_drop,
      List.drop_left' (bitsBE_length 8 _), messageBits_drop k l]
    rfl

theorem messageBits_take : ∀ (k : Nat) (l : List UInt8),
    (messageBits l).take (8 * k) = messageBits (l.take k)
  | 0, l => by simp [messageBits_nil]
  | k + 1, [] => by simp [messageBits_nil]
  | k + 1, b :: l => by
    rw [messageBits_cons, show 8 * (k + 1) = 8 + 8 * k by omega, List.take_append,
      List.take_of_length_le (by rw [bitsBE_length]; omega), bitsBE_length,
      show 8 + 8 * k - 8 = 8 * k by omega, messageBits_take k l]
    rfl

theorem uint8_ofNat_toNat_mod (b : UInt8) : UInt8.ofNat (b.toNat % 2 ^ 8) = b := by
  rw [Nat.mod_eq_of_lt (by have := b.toNat_lt; simpa using this)]
  simp

theorem octets_messageBits (l : List UInt8) :
    PCS.V2.FIPS1804Spec.octets (messageBits l) = l := by
  unfold PCS.V2.FIPS1804Spec.octets
  rw [messageBits_length, show 8 * l.length / 8 = l.length by omega]
  apply List.ext_getElem
  · simp
  · intro k h1 h2
    simp only [List.getElem_map, List.getElem_range]
    rw [messageBits_drop, show (8 : Nat) = 8 * 1 by rfl, messageBits_take]
    have hk : k < l.length := h2
    rw [List.take_one, List.head?_drop, List.getElem?_eq_getElem hk]
    simp only [Option.toList_some]
    rw [messageBits_cons, messageBits_nil, List.append_nil, bitsVal_bitsBE, uint8_ofNat_toNat_mod]


/-! ## 2. Word operations -/

open PCS.V2.SHA256 in
theorem rotr_toBitVec (x : UInt32) (n : Nat) (h0 : 0 < n) (h : n < 32) :
    (rotr x (UInt32.ofNat n)).toBitVec = PCS.V2.FIPS1804Spec.ROTR n x.toBitVec := by
  unfold rotr PCS.V2.FIPS1804Spec.ROTR
  rw [BitVec.rotateRight_def, UInt32.toBitVec_or, UInt32.toBitVec_shiftRight,
    UInt32.toBitVec_shiftLeft, BitVec.ushiftRight_eq', BitVec.shiftLeft_eq']
  have h1 : ((UInt32.ofNat n).toBitVec % 32).toNat = n := by
    rw [BitVec.toNat_umod]; simp; omega
  have h2 : ((32 - UInt32.ofNat n).toBitVec % 32).toNat = 32 - n := by
    rw [BitVec.toNat_umod, UInt32.toBitVec_sub, BitVec.toNat_sub]; simp; omega
  rw [h1, h2, Nat.mod_eq_of_lt h]

open PCS.V2.SHA256 in
theorem shr_toBitVec (x : UInt32) (n : Nat) (h : n < 32) :
    (x >>> UInt32.ofNat n).toBitVec = PCS.V2.FIPS1804Spec.SHR n x.toBitVec := by
  unfold PCS.V2.FIPS1804Spec.SHR
  rw [UInt32.toBitVec_shiftRight, BitVec.ushiftRight_eq']
  congr 1
  rw [BitVec.toNat_umod]; simp; omega

open PCS.V2.SHA256 in
theorem ch_toBitVec (x y z : UInt32) :
    (ch x y z).toBitVec = PCS.V2.FIPS1804Spec.Ch x.toBitVec y.toBitVec z.toBitVec := by
  simp [ch, PCS.V2.FIPS1804Spec.Ch]

open PCS.V2.SHA256 in
theorem maj_toBitVec (x y z : UInt32) :
    (maj x y z).toBitVec = PCS.V2.FIPS1804Spec.Maj x.toBitVec y.toBitVec z.toBitVec := by
  simp [maj, PCS.V2.FIPS1804Spec.Maj]

open PCS.V2.SHA256 in
theorem bsig0_toBitVec (x : UInt32) :
    (bsig0 x).toBitVec = PCS.V2.FIPS1804Spec.Sigma0 x.toBitVec := by
  unfold bsig0 PCS.V2.FIPS1804Spec.Sigma0
  rw [UInt32.toBitVec_xor, UInt32.toBitVec_xor,
    ← rotr_toBitVec x 2 (by decide) (by decide), ← rotr_toBitVec x 13 (by decide) (by decide),
    ← rotr_toBitVec x 22 (by decide) (by decide)]
  rfl

open PCS.V2.SHA256 in
theorem bsig1_toBitVec (x : UInt32) :
    (bsig1 x).toBitVec = PCS.V2.FIPS1804Spec.Sigma1 x.toBitVec := by
  unfold bsig1 PCS.V2.FIPS1804Spec.Sigma1
  rw [UInt32.toBitVec_xor, UInt32.toBitVec_xor,
    ← rotr_toBitVec x 6 (by decide) (by decide), ← rotr_toBitVec x 11 (by decide) (by decide),
    ← rotr_toBitVec x 25 (by decide) (by decide)]
  rfl

open PCS.V2.SHA256 in
theorem ssig0_toBitVec (x : UInt32) :
    (ssig0 x).toBitVec = PCS.V2.FIPS1804Spec.sigma0 x.toBitVec := by
  unfold ssig0 PCS.V2.FIPS1804Spec.sigma0
  rw [UInt32.toBitVec_xor, UInt32.toBitVec_xor,
    ← rotr_toBitVec x 7 (by decide) (by decide), ← rotr_toBitVec x 18 (by decide) (by decide),
    ← shr_toBitVec x 3 (by decide)]
  rfl

open PCS.V2.SHA256 in
theorem ssig1_toBitVec (x : UInt32) :
    (ssig1 x).toBitVec = PCS.V2.FIPS1804Spec.sigma1 x.toBitVec := by
  unfold ssig1 PCS.V2.FIPS1804Spec.sigma1
  rw [UInt32.toBitVec_xor, UInt32.toBitVec_xor,
    ← rotr_toBitVec x 17 (by decide) (by decide), ← rotr_toBitVec x 19 (by decide) (by decide),
    ← shr_toBitVec x 10 (by decide)]
  rfl

/-! ## 3. Constants -/

/-- The hex table `K` is the prime-cube-root derivation of FIPS 180-4 §4.2.2. -/
theorem K_table : ∀ t < 64, (PCS.V2.SHA256.K.getD t 0).toBitVec = PCS.V2.FIPS1804Spec.K t := by
  decide +kernel

/-- The hex table `H0` is the prime-square-root derivation of FIPS 180-4 §5.3.3. -/
theorem H0_table : ∀ j : Fin 8, (PCS.V2.SHA256.H0.getD j.val 0).toBitVec = PCS.V2.FIPS1804Spec.H0 j := by
  decide +kernel


/-! ## 4. Padding -/

theorem messageBits_replicate_zero (z : Nat) :
    messageBits (List.replicate z (0 : UInt8)) = List.replicate (8 * z) false := by
  induction z with
  | zero => rfl
  | succ z ih =>
    rw [List.replicate_succ, messageBits_cons, ih, show 8 * (z + 1) = 8 + 8 * z by omega,
      ← List.replicate_append_replicate]
    rfl

theorem messageBits_be_bytes (n : Nat) : ∀ k : Nat,
    messageBits ((List.range k).reverse.map fun i => UInt8.ofNat (n / 256 ^ i)) = bitsBE (8 * k) n
  | 0 => rfl
  | k + 1 => by
    rw [List.range_succ, List.reverse_append]
    simp only [List.reverse_cons, List.reverse_nil, List.nil_append, List.singleton_append]
    rw [List.map_cons, messageBits_cons, messageBits_be_bytes n k,
      show 8 * (k + 1) = 8 + 8 * k by omega, bitsBE_split 8 (8 * k) n]
    congr 1
    rw [UInt8.toNat_ofNat', bitsBE_mod 8 8 _ (Nat.le_refl _), show (256 : Nat) = 2 ^ 8 from rfl,
      ← Nat.pow_mul]

theorem messageBits_be64 (n : Nat) : messageBits (PCS.V2.SHA256.be64 n) = bitsBE 64 n :=
  messageBits_be_bytes n 8

/-- Byte-level padding (`0x80`, zero bytes, `be64`) is FIPS 180-4 §5.1.1 bit-level padding. -/
theorem messageBits_pad (m : List UInt8) :
    messageBits (PCS.V2.SHA256.pad m) = PCS.V2.FIPS1804Spec.pad (messageBits m) := by
  unfold PCS.V2.SHA256.pad PCS.V2.FIPS1804Spec.pad
  rw [messageBits_append, messageBits_append, messageBits_append, messageBits_replicate_zero,
    messageBits_be64, messageBits_length]
  have h80 : messageBits [(0x80 : UInt8)] = [true] ++ List.replicate 7 false := by decide
  rw [h80]
  have hk : PCS.V2.FIPS1804Spec.padK (8 * m.length) = 7 + 8 * PCS.V2.SHA256.padZeros m.length := by
    unfold PCS.V2.FIPS1804Spec.padK PCS.V2.SHA256.padZeros; omega
  rw [hk, ← List.replicate_append_replicate]
  simp only [List.append_assoc]


/-! ## 5. Parsing: blocks and words -/

theorem or_shift_merge (x y k s : Nat) (hy : y < 2 ^ k) :
    (x <<< (k + s)) ||| (y <<< s) = (x * 2 ^ k + y) <<< s := by
  rw [Nat.shiftLeft_add, ← Nat.shiftLeft_or_distrib, ← Nat.shiftLeft_add_eq_or_of_lt hy,
    Nat.shiftLeft_eq x k]

theorem word_toNat (a b c d : UInt8) :
    (PCS.V2.SHA256.word a b c d).toNat =
      ((a.toNat * 2 ^ 8 + b.toNat) * 2 ^ 8 + c.toNat) * 2 ^ 8 + d.toNat := by
  have ha := a.toNat_lt; have hb := b.toNat_lt; have hc := c.toNat_lt; have hd := d.toNat_lt
  simp only [PCS.V2.SHA256.word, UInt32.toNat_or, UInt32.toNat_shiftLeft, UInt8.toNat_toUInt32]
  have e24 : ((24 : UInt32).toNat % 32) = 24 := rfl
  have e16 : ((16 : UInt32).toNat % 32) = 16 := rfl
  have e8 : ((8 : UInt32).toNat % 32) = 8 := rfl
  rw [e24, e16, e8]
  rw [Nat.mod_eq_of_lt (a := a.toNat <<< 24) (by rw [Nat.shiftLeft_eq]; omega),
    Nat.mod_eq_of_lt (a := b.toNat <<< 16) (by rw [Nat.shiftLeft_eq]; omega),
    Nat.mod_eq_of_lt (a := c.toNat <<< 8) (by rw [Nat.shiftLeft_eq]; omega)]
  rw [show (24 : Nat) = 8 + 16 from rfl, or_shift_merge _ _ 8 16 hb,
    show (16 : Nat) = 8 + 8 from rfl, or_shift_merge _ _ 8 8 hc,
    ← Nat.shiftLeft_add_eq_or_of_lt hd, Nat.shiftLeft_eq]

/-- The word assembled from four octets. -/
def wordOf : List UInt8 → UInt32
  | [a, b, c, d] => PCS.V2.SHA256.word a b c d
  | _ => 0

theorem bitsVal_messageBits_byte (b : UInt8) : bitsVal (bitsBE 8 b.toNat) = b.toNat := by
  rw [bitsVal_bitsBE, Nat.mod_eq_of_lt (by have := b.toNat_lt; simpa using this)]

/-- Big-endian word decoding agrees with the bit-string value of the 32 message bits. -/
theorem wordOf_toBitVec (l : List UInt8) (h : l.length = 4) :
    (wordOf l).toBitVec = BitVec.ofNat 32 (bitsVal (messageBits l)) := by
  match l, h with
  | [a, b, c, d], _ =>
    apply BitVec.eq_of_toNat_eq
    rw [UInt32.toNat_toBitVec, BitVec.toNat_ofNat]
    simp only [wordOf, word_toNat, messageBits_cons, messageBits_nil, List.append_nil,
      bitsVal_append, bitsBE_length, bitsVal_messageBits_byte]
    have ha := a.toNat_lt; have hb := b.toNat_lt; have hc := c.toNat_lt; have hd := d.toNat_lt
    rw [Nat.mod_eq_of_lt (by simp only [List.length_append, bitsBE_length]; omega)]
    simp only [List.length_append, bitsBE_length]
    omega

theorem chunks_eq_map : ∀ (N : Nat) (l : List UInt8), l.length = 64 * N →
    PCS.V2.SHA256.chunks l = (List.range N).map (fun i => (l.drop (64 * i)).take 64)
  | 0, l, h => by
    have : l = [] := List.eq_nil_of_length_eq_zero (by omega)
    subst this; rw [PCS.V2.SHA256.chunks.eq_def]; rfl
  | N + 1, l, h => by
    match l, h with
    | a :: l', h =>
      rw [PCS.V2.SHA256.chunks.eq_def]
      simp only
      rw [chunks_eq_map N ((a :: l').drop 64) (by simp at h ⊢; omega), List.range_succ_eq_map]
      simp only [List.map_cons, List.map_map, Nat.mul_zero, List.drop_zero, List.drop_drop]
      congr 1
      apply List.map_congr_left
      intro i _
      simp only [Function.comp_apply]
      congr 2
      omega

theorem words_eq_map : ∀ (n : Nat) (l : List UInt8), l.length = 4 * n →
    PCS.V2.SHA256.words l = (List.range n).map (fun j => wordOf ((l.drop (4 * j)).take 4))
  | 0, l, h => by
    have : l = [] := List.eq_nil_of_length_eq_zero (by omega)
    subst this; rfl
  | n + 1, l, h => by
    match l, h with
    | a :: b :: c :: d :: rest, h =>
      rw [PCS.V2.SHA256.words, words_eq_map n rest (by simp at h; omega), List.range_succ_eq_map]
      simp only [List.map_cons, List.map_map, Nat.mul_zero, List.drop_zero]
      congr 1

theorem words_length_of (l : List UInt8) (h : l.length = 64) : (PCS.V2.SHA256.words l).length = 16 := by
  rw [words_eq_map 16 l (by omega)]; simp

/-- The words of block `i` of the padded byte message are FIPS's `M^{(i)}_j`. -/
theorem block_word_eq (P : List UInt8) (i j : Nat) (hi : 64 * (i + 1) ≤ P.length) (hj : j < 16) :
    ((PCS.V2.SHA256.words ((P.drop (64 * i)).take 64)).getD j 0).toBitVec =
      PCS.V2.FIPS1804Spec.blockWord (messageBits P) i j := by
  have hlen : ((P.drop (64 * i)).take 64).length = 64 := by simp; omega
  rw [words_eq_map 16 _ (by omega), List.getD_eq_getElem?_getD, List.getElem?_map,
    List.getElem?_range hj]
  simp only [Option.map_some, Option.getD_some]
  rw [wordOf_toBitVec _ (by simp; omega)]
  unfold PCS.V2.FIPS1804Spec.blockWord
  rw [show 512 * i + 32 * j = 8 * (64 * i + 4 * j) by omega, show (32 : Nat) = 8 * 4 from rfl,
    messageBits_drop, messageBits_take]
  congr 3
  rw [List.drop_take, List.drop_drop, List.take_take]
  congr 1
  omega

/-! ## Output serialization -/

theorem wordBytes_bits (x : UInt32) :
    messageBits (PCS.V2.SHA256.wordBytes x) = bitsBE 32 x.toNat := by
  simp only [PCS.V2.SHA256.wordBytes, messageBits_cons, messageBits_nil, List.append_nil,
    UInt32.toNat_toUInt8, UInt32.toNat_shiftRight]
  have e24 : ((24 : UInt32).toNat % 32) = 24 := rfl
  have e16 : ((16 : UInt32).toNat % 32) = 16 := rfl
  have e8 : ((8 : UInt32).toNat % 32) = 8 := rfl
  rw [e24, e16, e8, bitsBE_mod 8 8 _ (Nat.le_refl _), bitsBE_mod 8 8 _ (Nat.le_refl _),
    bitsBE_mod 8 8 _ (Nat.le_refl _), bitsBE_mod 8 8 _ (Nat.le_refl _),
    Nat.shiftRight_eq_div_pow, Nat.shiftRight_eq_div_pow, Nat.shiftRight_eq_div_pow]
  rw [show (32 : Nat) = 8 + 24 from rfl, bitsBE_split 8 24, show (24 : Nat) = 8 + 16 from rfl,
    bitsBE_split 8 16, show (16 : Nat) = 8 + 8 from rfl, bitsBE_split 8 8]


/-! ## 6. Message schedule -/

open PCS.V2.SHA256 in
/-- One iteration of the imperative schedule loop. -/
def schedStep (w : Array UInt32) (t : Nat) : Array UInt32 :=
  w.push (ssig1 w[t-2]! + w[t-7]! + ssig0 w[t-15]! + w[t-16]!)

theorem schedule_eq_foldl (block : List UInt8) :
    PCS.V2.SHA256.schedule block = (List.range' 16 48).foldl schedStep (PCS.V2.SHA256.words block).toArray := by
  unfold PCS.V2.SHA256.schedule
  simp [Id.run]
  rfl

theorem push_getElem!_lt {A : Array UInt32} {v : UInt32} {t : Nat} (h : t < A.size) :
    (A.push v)[t]! = A[t]! := by
  rw [getElem!_pos (A.push v) t (by simp; omega), getElem!_pos A t h, Array.getElem_push_lt h]

theorem push_getElem!_size {A : Array UInt32} {v : UInt32} : (A.push v)[A.size]! = v := by
  rw [getElem!_pos (A.push v) A.size (by simp), Array.getElem_push_eq]

/-- Loop invariant: after `k` iterations the array holds exactly `W_0 … W_{15+k}`. -/
theorem schedule_invariant (Mi : Nat → PCS.V2.FIPS1804Spec.Word) (w0 : Array UInt32)
    (h0 : w0.size = 16) (hM : ∀ t < 16, w0[t]!.toBitVec = Mi t) : ∀ k : Nat,
    ((List.range' 16 k).foldl schedStep w0).size = 16 + k ∧
    ∀ t < 16 + k, ((List.range' 16 k).foldl schedStep w0)[t]!.toBitVec = PCS.V2.FIPS1804Spec.W Mi t
  | 0 => by
    refine ⟨by simpa using h0, fun t ht => ?_⟩
    simp only [List.range'_zero, List.foldl_nil]
    rw [hM t (by omega), PCS.V2.FIPS1804Spec.W, if_pos (by omega)]
  | k + 1 => by
    obtain ⟨hs, hv⟩ := schedule_invariant Mi w0 h0 hM k
    rw [List.range'_concat, List.foldl_append, List.foldl_cons, List.foldl_nil]
    generalize hA : (List.range' 16 k).foldl schedStep w0 = A at hs hv
    refine ⟨by simp [schedStep, hs]; omega, fun t ht => ?_⟩
    unfold schedStep
    by_cases htk : t < 16 + k
    · rw [push_getElem!_lt (by omega)]; exact hv t htk
    · have ht' : t = A.size := by omega
      subst ht'
      rw [push_getElem!_size, UInt32.toBitVec_add, UInt32.toBitVec_add, UInt32.toBitVec_add,
        ssig1_toBitVec, ssig0_toBitVec, hv _ (by omega), hv _ (by omega), hv _ (by omega),
        hv _ (by omega), PCS.V2.FIPS1804Spec.W.eq_def Mi A.size, if_neg (by omega),
        show 16 + 1 * k = A.size by omega]

/-- The imperative schedule computes FIPS 180-4's `W_t` for every `t < 64`. -/
theorem schedule_eq_W (block : List UInt8) (hb : block.length = 64)
    (Mi : Nat → PCS.V2.FIPS1804Spec.Word)
    (hM : ∀ t < 16, ((PCS.V2.SHA256.words block).getD t 0).toBitVec = Mi t) :
    ∀ t < 64, (PCS.V2.SHA256.schedule block)[t]!.toBitVec = PCS.V2.FIPS1804Spec.W Mi t := by
  intro t ht
  have hw := words_length_of block hb
  rw [schedule_eq_foldl]
  refine (schedule_invariant Mi _ (by simp [hw]) (fun t ht => ?_) 48).2 t (by omega)
  rw [getElem!_pos _ t (by simp [hw]; omega), ← hM t ht, List.getD_eq_getElem?_getD,
    List.getElem?_eq_getElem (by omega)]
  simp

/-! ## 7. Compression -/

open PCS.V2.SHA256 in
/-- The implementation state viewed as FIPS working variables. -/
def toVars (s : State) : PCS.V2.FIPS1804Spec.Vars :=
  { a := s.a.toBitVec, b := s.b.toBitVec, c := s.c.toBitVec, d := s.d.toBitVec,
    e := s.e.toBitVec, f := s.f.toBitVec, g := s.g.toBitVec, h := s.h.toBitVec }

/-- The implementation hash list viewed as a FIPS hash value. -/
def toHV (hs : List UInt32) : PCS.V2.FIPS1804Spec.HashValue := fun j => (hs.getD j.val 0).toBitVec

open PCS.V2.SHA256 in
theorem round_toVars (s : State) (k w : UInt32) :
    toVars (round s k w) = PCS.V2.FIPS1804Spec.roundStep (toVars s) k.toBitVec w.toBitVec := by
  simp only [round, PCS.V2.FIPS1804Spec.roundStep, toVars, UInt32.toBitVec_add, bsig1_toBitVec,
    ch_toBitVec, bsig0_toBitVec, maj_toBitVec]

open PCS.V2.SHA256 in
theorem rounds_toVars (hs : List UInt32) (w : Array UInt32) (Wf : Nat → PCS.V2.FIPS1804Spec.Word)
    (hW : ∀ t < 64, w[t]!.toBitVec = Wf t) : ∀ n ≤ 64,
    toVars ((List.range n).foldl (fun s t => round s (K.getD t 0) w[t]!) (ofList hs)) =
      PCS.V2.FIPS1804Spec.varsAfter (toHV hs) Wf n
  | 0, _ => rfl
  | n + 1, hn => by
    rw [List.range_succ, List.foldl_append, List.foldl_cons, List.foldl_nil, round_toVars,
      rounds_toVars hs w Wf hW n (by omega), K_table n (by omega), hW n (by omega)]
    rfl

open PCS.V2.SHA256 in
theorem toVars_get (s : State) (j : Fin 8) :
    (toVars s).get j = ((toList s).getD j.val 0).toBitVec := by
  match j with
  | ⟨0, _⟩ => rfl | ⟨1, _⟩ => rfl | ⟨2, _⟩ => rfl | ⟨3, _⟩ => rfl
  | ⟨4, _⟩ => rfl | ⟨5, _⟩ => rfl | ⟨6, _⟩ => rfl | ⟨7, _⟩ => rfl

theorem getD_zipWith_add : ∀ (l l' : List UInt32) (i : Nat), i < l.length → i < l'.length →
    (List.zipWith (· + ·) l l').getD i 0 = l.getD i 0 + l'.getD i 0
  | [], _, _, h, _ => by simp at h
  | _ :: _, [], _, _, h => by simp at h
  | a :: l, b :: l', 0, _, _ => rfl
  | a :: l, b :: l', i + 1, h, h' => by
    simp only [List.zipWith_cons_cons, List.getD_cons_succ]
    exact getD_zipWith_add l l' i (by simpa using h) (by simpa using h')

open PCS.V2.SHA256 in
/-- One block compression agrees with FIPS 180-4 §6.2.2 steps 1–4. -/
theorem compress_toHV (hs : List UInt32) (hlen : hs.length = 8) (block : List UInt8)
    (hb : block.length = 64) (Mi : Nat → PCS.V2.FIPS1804Spec.Word)
    (hM : ∀ t < 16, ((words block).getD t 0).toBitVec = Mi t) :
    toHV (compress hs block) = PCS.V2.FIPS1804Spec.compress (toHV hs) Mi := by
  have hv := rounds_toVars hs (schedule block) (PCS.V2.FIPS1804Spec.W Mi)
    (schedule_eq_W block hb Mi hM) 64 (Nat.le_refl _)
  unfold compress PCS.V2.FIPS1804Spec.compress
  simp only
  rw [← hv]
  generalize (List.range 64).foldl (fun s t => round s (K.getD t 0) (schedule block)[t]!) (ofList hs) = s
  funext j
  have hj := j.isLt
  simp only [toHV]
  rw [getD_zipWith_add hs (toList s) j.val (by omega) (by simp [toList]), UInt32.toBitVec_add,
    toVars_get, BitVec.add_comm]


/-! ## 8. Chaining and output -/

theorem toHV_H0 : toHV PCS.V2.SHA256.H0 = PCS.V2.FIPS1804Spec.H0 := by
  funext j; exact H0_table j

open PCS.V2.SHA256 in
/-- Folding `compress` over the first `n` blocks yields FIPS's `H(n)`. -/
theorem chain_toHV (P : List UInt8) (N : Nat) (hP : P.length = 64 * N) : ∀ n ≤ N,
    toHV (((List.range n).map (fun i => (P.drop (64 * i)).take 64)).foldl compress H0) =
      PCS.V2.FIPS1804Spec.hashAfter (messageBits P) n ∧
    (((List.range n).map (fun i => (P.drop (64 * i)).take 64)).foldl compress H0).length = 8
  | 0, _ => ⟨toHV_H0, rfl⟩
  | n + 1, hn => by
    obtain ⟨ih, hl⟩ := chain_toHV P N hP n (by omega)
    rw [List.range_succ, List.map_append, List.foldl_append, List.map_cons, List.map_nil,
      List.foldl_cons, List.foldl_nil]
    refine ⟨?_, compress_length _ _ hl⟩
    rw [compress_toHV _ hl _ (by simp; omega) (PCS.V2.FIPS1804Spec.blockWord (messageBits P) n)
      (fun t ht => block_word_eq P n t (by omega) ht), ih]
    rfl

theorem messageBits_flatMap_wordBytes (hs : List UInt32) :
    messageBits (hs.flatMap PCS.V2.SHA256.wordBytes) = hs.flatMap (fun x => bitsBE 32 x.toNat) := by
  induction hs with
  | nil => rfl
  | cons x hs ih => rw [List.flatMap_cons, messageBits_append, wordBytes_bits, ih, List.flatMap_cons]

theorem digestBits_toHV (hs : List UInt32) (h : hs.length = 8) :
    PCS.V2.FIPS1804Spec.digestBits (toHV hs) = hs.flatMap (fun x => bitsBE 32 x.toNat) := by
  match hs, h with
  | [h0, h1, h2, h3, h4, h5, h6, h7], _ =>
    rfl

/-- **SHA-256 implementation = FIPS 180-4 specification**, for every byte message.

The FIPS standard defines SHA-256 for messages of fewer than `2^64` bits; the
specification `PCS.V2.FIPS1804Spec.sha256` extends it to all lengths by encoding `ℓ mod
2^64` in the length field, and the implementation agrees with it everywhere. -/
theorem sha256_eq_spec (m : List UInt8) : PCS.V2.SHA256.sha256 m = PCS.V2.FIPS1804Spec.sha256 m := by
  have hmod := PCS.V2.SHA256.pad_length_mod m
  have hP : (PCS.V2.SHA256.pad m).length = 64 * ((PCS.V2.SHA256.pad m).length / 64) := by omega
  obtain ⟨hhash, hlen⟩ := chain_toHV (PCS.V2.SHA256.pad m) _ hP _ (Nat.le_refl _)
  unfold PCS.V2.SHA256.sha256 PCS.V2.FIPS1804Spec.sha256
  rw [PCS.V2.SHA256.compressBlocks_eq_chunks_foldl, chunks_eq_map _ _ hP]
  simp only
  rw [← messageBits_pad]
  have hN : PCS.V2.FIPS1804Spec.numBlocks (messageBits (PCS.V2.SHA256.pad m)) =
      (PCS.V2.SHA256.pad m).length / 64 := by
    unfold PCS.V2.FIPS1804Spec.numBlocks; rw [messageBits_length]; omega
  rw [hN, ← hhash, digestBits_toHV _ hlen, ← messageBits_flatMap_wordBytes, octets_messageBits]

/-- **SHA-256 implementation = FIPS 180-4 specification** on the standard's message domain
    (fewer than `2^64` bits, i.e. fewer than `2^61` bytes). -/
theorem sha256_eq_fips1804 (m : List UInt8) (_hLen : m.length < 2 ^ 61) :
    PCS.V2.SHA256.sha256 m = PCS.V2.FIPS1804Spec.sha256 m :=
  sha256_eq_spec m

/-- The hex digest used throughout the checker is the hex encoding of FIPS SHA-256. -/
theorem sha256Hex_eq_spec (b : ByteArray) :
    PCS.V2.SHA256.sha256Hex b = PCS.V2.Hex.hexEncode (PCS.V2.FIPS1804Spec.sha256 b.data.toList) := by
  rw [PCS.V2.SHA256.sha256Hex, sha256_eq_spec]

end PCS.V2.SHA256Spec
