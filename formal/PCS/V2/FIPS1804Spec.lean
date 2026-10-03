/-!
# An independent mathematical specification of SHA-256 (FIPS 180-4)

This module states SHA-256 directly from the text of FIPS 180-4, in a different
mathematical domain from the executable checker `PCS.V2.SHA256`:

| FIPS 180-4                     | here                                        | executable checker            |
|--------------------------------|---------------------------------------------|-------------------------------|
| message `M` of `ℓ` bits (§5.1) | `List Bool`, MSB first                       | `List UInt8`                   |
| 32-bit words (§2.1)            | `BitVec 32` (core bit-vectors)               | `UInt32`                       |
| `x + y` (§3.2.1)               | `BitVec` addition (`mod 2^32` by definition) | `UInt32` addition              |
| `ROTR^n` (§3.2.4)              | `BitVec.rotateRight`                         | shift/or formula               |
| constants `K`, `H(0)` (§4.2.2, §5.3.3) | **derived** from the first 64 / 8 primes as integer cube / square roots | hex literal tables |
| padding (§5.1.1)               | bit-level: `1`, then `k` zero bits, then `ℓ` as 64 bits | byte-level `0x80` / zero bytes / `be64` |
| parsing (§5.2.1)               | index arithmetic on the padded bit string    | recursive `chunks`/`words`     |
| schedule `W_t` (§6.2.2 step 1) | a recurrence on `t : Nat`                    | an imperative `Array.push` loop |
| rounds (§6.2.2 step 3)         | a recurrence on the round index              | `List.foldl` over a range      |
| chaining (§6.2.2 step 4)       | a recurrence on the block index `i`          | tail-recursive block fold      |
| output `H0 ‖ … ‖ H7` (§6.2.2)  | 256-bit string, regrouped into octets        | `flatMap wordBytes`            |

Nothing in this file imports or mentions the executable implementation.  The
correspondence `PCS.V2.SHA256.sha256 = FIPS1804Spec.sha256` is proved separately
in `PCS.V2.SHA256Spec`.
-/

namespace PCS.V2.FIPS1804Spec

/-- A FIPS 180-4 32-bit word (§2.1). -/
abbrev Word := BitVec 32

/-! ## §2.2.2 / §3.2 / §4.1.2 operations on words -/

/-- `ROTR^n(x)`, the circular right shift (§3.2.4). -/
def ROTR (n : Nat) (x : Word) : Word := x.rotateRight n

/-- `SHR^n(x)`, the right shift (§3.2.3). -/
def SHR (n : Nat) (x : Word) : Word := x >>> n

/-- `Ch(x, y, z)` (§4.1.2, eq. 4.2). -/
def Ch (x y z : Word) : Word := (x &&& y) ^^^ (~~~x &&& z)

/-- `Maj(x, y, z)` (§4.1.2, eq. 4.3). -/
def Maj (x y z : Word) : Word := (x &&& y) ^^^ (x &&& z) ^^^ (y &&& z)

/-- `Σ₀^{256}` (eq. 4.4). -/
def Sigma0 (x : Word) : Word := ROTR 2 x ^^^ ROTR 13 x ^^^ ROTR 22 x
/-- `Σ₁^{256}` (eq. 4.5). -/
def Sigma1 (x : Word) : Word := ROTR 6 x ^^^ ROTR 11 x ^^^ ROTR 25 x
/-- `σ₀^{256}` (eq. 4.6). -/
def sigma0 (x : Word) : Word := ROTR 7 x ^^^ ROTR 18 x ^^^ SHR 3 x
/-- `σ₁^{256}` (eq. 4.7). -/
def sigma1 (x : Word) : Word := ROTR 17 x ^^^ ROTR 19 x ^^^ SHR 10 x

/-- Bitwise meaning of `Ch`: each result bit *chooses* `y` or `z` according to `x`. -/
theorem Ch_getLsbD (x y z : Word) {i : Nat} (hi : i < 32) :
    (Ch x y z).getLsbD i = if x.getLsbD i then y.getLsbD i else z.getLsbD i := by
  simp only [Ch, BitVec.getLsbD_xor, BitVec.getLsbD_and, BitVec.getLsbD_not]
  cases x.getLsbD i <;> cases y.getLsbD i <;> cases z.getLsbD i <;> simp [hi]

/-- Bitwise meaning of `Maj`: each result bit is the *majority* of the three input bits. -/
theorem Maj_getLsbD (x y z : Word) (i : Nat) :
    (Maj x y z).getLsbD i =
      ((x.getLsbD i && y.getLsbD i) || (x.getLsbD i && z.getLsbD i) ||
        (y.getLsbD i && z.getLsbD i)) := by
  simp only [Maj, BitVec.getLsbD_xor, BitVec.getLsbD_and]
  cases x.getLsbD i <;> cases y.getLsbD i <;> cases z.getLsbD i <;> rfl

/-- Word addition is addition modulo `2^32` (§3.2.1). -/
theorem add_toNat (x y : Word) : (x + y).toNat = (x.toNat + y.toNat) % 2 ^ 32 :=
  BitVec.toNat_add x y

/-! ## §4.2.2 / §5.3.3 constants, derived from the primes

FIPS 180-4 defines `K_t` as "the first thirty-two bits of the fractional parts of the
cube roots of the first sixty-four prime numbers" and `H(0)` as the first thirty-two
bits of the fractional parts of the square roots of the first eight primes.  For a
prime `p`, the first 32 fractional bits of `p^{1/k}` are
`⌊p^{1/k} · 2^32⌋ mod 2^32 = ⌊(p · 2^{32k})^{1/k}⌋ mod 2^32`. -/

/-- Trial-division primality. -/
def isPrime (n : Nat) : Bool := 2 ≤ n && (List.range n).all (fun d => d < 2 || n % d != 0)

/-- The primes below `n`, in increasing order. -/
def primesBelow (n : Nat) : List Nat := (List.range n).filter isPrime

/-- Binary search for the integer `k`-th root, invariant `lo^k ≤ n < hi^k`. -/
def irootAux (k n : Nat) : Nat → Nat → Nat → Nat
  | 0, lo, _ => lo
  | fuel + 1, lo, hi =>
    if hi ≤ lo + 1 then lo
    else
      let mid := (lo + hi) / 2
      if mid ^ k ≤ n then irootAux k n fuel mid hi else irootAux k n fuel lo mid

/-- `⌊n^{1/k}⌋` (for the arguments used here; see `K_roots`/`H0_roots`). -/
def iroot (k n : Nat) : Nat := irootAux k n 256 0 (n + 1)

/-- First 32 fractional bits of `p^{1/k}`. -/
def fracRootBits (k p : Nat) : Nat := iroot k (p * 2 ^ (32 * k)) % 2 ^ 32

/-- The first sixty-four primes (311 is the 64th prime). -/
def first64Primes : List Nat := primesBelow 312

/-- `K^{256}_t`, `0 ≤ t ≤ 63` (§4.2.2). -/
def K (t : Nat) : Word := BitVec.ofNat 32 (fracRootBits 3 (first64Primes.getD t 0))

/-- `H^{(0)}_j`, `0 ≤ j ≤ 7` (§5.3.3). -/
def H0 (j : Fin 8) : Word := BitVec.ofNat 32 (fracRootBits 2 (first64Primes.getD j.val 0))

theorem first64Primes_length : first64Primes.length = 64 := by decide +kernel

/-- The roots used for `K` really are the integer cube roots: `r^3 ≤ p·2^96 < (r+1)^3`. -/
theorem K_roots : ∀ t < 64,
    (iroot 3 (first64Primes.getD t 0 * 2 ^ 96)) ^ 3 ≤ first64Primes.getD t 0 * 2 ^ 96 ∧
    first64Primes.getD t 0 * 2 ^ 96 < (iroot 3 (first64Primes.getD t 0 * 2 ^ 96) + 1) ^ 3 := by
  decide +kernel

/-- The roots used for `H(0)` really are the integer square roots. -/
theorem H0_roots : ∀ j < 8,
    (iroot 2 (first64Primes.getD j 0 * 2 ^ 64)) ^ 2 ≤ first64Primes.getD j 0 * 2 ^ 64 ∧
    first64Primes.getD j 0 * 2 ^ 64 < (iroot 2 (first64Primes.getD j 0 * 2 ^ 64) + 1) ^ 2 := by
  decide +kernel

/-! ## Bit strings -/

/-- The `n`-bit big-endian (most significant bit first) representation of `x mod 2^n`. -/
def bitsBE (n x : Nat) : List Bool := (List.range n).reverse.map x.testBit

/-- The value of a big-endian bit string. -/
def bitsVal : List Bool → Nat
  | [] => 0
  | b :: bs => (if b then 2 ^ bs.length else 0) + bitsVal bs

/-- A byte-oriented message as the FIPS bit string: each octet MSB first. -/
def messageBits (m : List UInt8) : List Bool := m.flatMap (fun b => bitsBE 8 b.toNat)

/-! ## §5.1.1 padding -/

/-- The number `k` of zero bits: the smallest `k ≥ 0` with `ℓ + 1 + k ≡ 448 (mod 512)`. -/
def padK (l : Nat) : Nat := (448 + 512 - (l + 1) % 512) % 512

theorem padK_spec (l : Nat) : (l + 1 + padK l) % 512 = 448 ∧ padK l < 512 := by
  unfold padK; omega

theorem padK_minimal (l k : Nat) (h : (l + 1 + k) % 512 = 448) : padK l ≤ k := by
  unfold padK; omega

/-- `M ‖ 1 ‖ 0^k ‖ ⟨ℓ⟩₆₄` (§5.1.1). -/
def pad (M : List Bool) : List Bool :=
  M ++ [true] ++ List.replicate (padK M.length) false ++ bitsBE 64 M.length

/-! ## §5.2.1 parsing -/

/-- Number of 512-bit blocks `N` of a padded message. -/
def numBlocks (P : List Bool) : Nat := P.length / 512

/-- `M^{(i)}_j`: the `j`-th 32-bit word of the `i`-th 512-bit block. -/
def blockWord (P : List Bool) (i j : Nat) : Word :=
  BitVec.ofNat 32 (bitsVal ((P.drop (512 * i + 32 * j)).take 32))

/-! ## §6.2.2 step 1: message schedule -/

/-- `W_t` for the block whose words are `Mi` (eq. 6.2.2.1). -/
def W (Mi : Nat → Word) (t : Nat) : Word :=
  if t < 16 then Mi t
  else sigma1 (W Mi (t - 2)) + W Mi (t - 7) + sigma0 (W Mi (t - 15)) + W Mi (t - 16)
termination_by t
decreasing_by all_goals omega

/-! ## §6.2.2 steps 2–4: working variables, rounds, intermediate hash -/

structure Vars where
  a : Word
  b : Word
  c : Word
  d : Word
  e : Word
  f : Word
  g : Word
  h : Word

/-- An intermediate hash value `H(i)` is eight words `H(i)_0 … H(i)_7`. -/
abbrev HashValue := Fin 8 → Word

/-- Step 2: initialise the working variables from `H(i-1)`. -/
def initVars (H : HashValue) : Vars :=
  { a := H 0, b := H 1, c := H 2, d := H 3, e := H 4, f := H 5, g := H 6, h := H 7 }

/-- Step 3, one round `t`. -/
def roundStep (v : Vars) (Kt Wt : Word) : Vars :=
  let T1 := v.h + Sigma1 v.e + Ch v.e v.f v.g + Kt + Wt
  let T2 := Sigma0 v.a + Maj v.a v.b v.c
  { a := T1 + T2, b := v.a, c := v.b, d := v.c, e := v.d + T1, f := v.e, g := v.f, h := v.g }

/-- Working variables after rounds `0, …, t-1`. -/
def varsAfter (H : HashValue) (Wf : Nat → Word) : Nat → Vars
  | 0 => initVars H
  | t + 1 => roundStep (varsAfter H Wf t) (K t) (Wf t)

/-- The `j`-th working variable `a, …, h`. -/
def Vars.get (v : Vars) (j : Fin 8) : Word :=
  match j with
  | ⟨0, _⟩ => v.a | ⟨1, _⟩ => v.b | ⟨2, _⟩ => v.c | ⟨3, _⟩ => v.d
  | ⟨4, _⟩ => v.e | ⟨5, _⟩ => v.f | ⟨6, _⟩ => v.g | ⟨7, _⟩ => v.h

/-- Step 4: `H(i)_j = var_j + H(i-1)_j`, after the 64 rounds. -/
def compress (H : HashValue) (Mi : Nat → Word) : HashValue :=
  fun j => (varsAfter H (W Mi) 64).get j + H j

/-- `H(i)` for the padded message `P` (§6.2.2, iterated over `i = 1 … N`). -/
def hashAfter (P : List Bool) : Nat → HashValue
  | 0 => H0
  | i + 1 => compress (hashAfter P i) (blockWord P i)

/-! ## Output -/

/-- The 256-bit message digest `H(N)_0 ‖ H(N)_1 ‖ … ‖ H(N)_7`. -/
def digestBits (H : HashValue) : List Bool :=
  (List.finRange 8).flatMap (fun j => bitsBE 32 (H j).toNat)

/-- Regroup a bit string into octets (MSB first). -/
def octets (bs : List Bool) : List UInt8 :=
  (List.range (bs.length / 8)).map (fun k => UInt8.ofNat (bitsVal ((bs.drop (8 * k)).take 8)))

/-- **SHA-256** of a byte message, as specified by FIPS 180-4. -/
def sha256 (m : List UInt8) : List UInt8 :=
  let P := pad (messageBits m)
  octets (digestBits (hashAfter P (numBlocks P)))

end PCS.V2.FIPS1804Spec
