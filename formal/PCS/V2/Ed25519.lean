import PCS.V2.SHA512
import PCS.V2.Signature

/-!
# Ed25519 verification (RFC 8032 §5.1) in Lean

A direct transcription of RFC 8032 §5.1.2–§5.1.3 (encoding/decoding),
the extended-coordinate group law of §5.1.4 and the verification procedure of
§5.1.7, in the cofactorless, encoding-comparing form used by OpenSSL (the backend of
Python `cryptography`): accept iff `S < L`, `A` and `R` decode, and
`encode([S]B − [k]A) = R`, where `k = SHA-512(R ‖ A ‖ M) mod L`.

With this definition the Lean checker can run with `ed25519 := Ed25519.verify`, in
which case the implementation-correctness hypothesis (A) is discharged by `rfl`
(`ed25519ImplCorrect_self`), leaving only unforgeability (B) for the specification.

Faithfulness of this transcription to RFC 8032 is validated by known-answer and
negative vectors (including the real PCS golden-package signatures) in
`PCS.V2.Vectors`; those are tests, not proofs.  Cofactored and cofactorless variants
differ only on adversarially crafted small-order / non-canonical inputs; the
variant is fixed here and named by `Ed25519ImplCorrect`.
-/

namespace PCS.V2.Ed25519

def p : Nat := 2 ^ 255 - 19
def L : Nat := 2 ^ 252 + 27742317777372353535851937790883648493
def d : Nat := 37095705934669439343138083508754565189542113879843219016388785533085940283555
def sqrtM1 : Nat := 19681161376707505956807079304988542015446066515923890162744021073123829784752

def fadd (a b : Nat) : Nat := (a + b) % p
def fsub (a b : Nat) : Nat := (a + p - b % p) % p
def fmul (a b : Nat) : Nat := (a * b) % p

def fpow (b e : Nat) : Nat := Id.run do
  let mut r := 1
  let mut x := b % p
  let mut k := e
  for _ in [0:256] do
    if k % 2 = 1 then r := fmul r x
    x := fmul x x
    k := k / 2
  return r

def finv (a : Nat) : Nat := fpow a (p - 2)

/-- Extended homogeneous coordinates (X : Y : Z : T), x = X/Z, y = Y/Z, xy = T/Z. -/
structure Point where
  X : Nat
  Y : Nat
  Z : Nat
  T : Nat

def identity : Point := ⟨0, 1, 1, 0⟩

/-- RFC 8032 §5.1.4 point addition (complete for edwards25519). -/
def add (P Q : Point) : Point :=
  let a := fmul (fsub P.Y P.X) (fsub Q.Y Q.X)
  let b := fmul (fadd P.Y P.X) (fadd Q.Y Q.X)
  let c := fmul (fmul P.T (2 * d % p)) Q.T
  let dd := fmul (2 * P.Z % p) Q.Z
  let e := fsub b a
  let f := fsub dd c
  let g := fadd dd c
  let h := fadd b a
  ⟨fmul e f, fmul g h, fmul f g, fmul e h⟩

def neg (P : Point) : Point := ⟨fsub 0 P.X, P.Y, P.Z, fsub 0 P.T⟩

/-- Double-and-add scalar multiplication over 256 bits. -/
def scalarMul (k : Nat) (P : Point) : Point := Id.run do
  let mut r := identity
  let mut q := P
  let mut n := k
  for _ in [0:256] do
    if n % 2 = 1 then r := add r q
    q := add q q
    n := n / 2
  return r

def baseX : Nat := 15112221349535400772501151409588531511454012693041857206046113283949847762202
def baseY : Nat := 46316835694926478169428394003475163141307993866256225615783033603165251855960
def B : Point := ⟨baseX, baseY, 1, fmul baseX baseY⟩

/-- Little-endian integer of a byte list. -/
def leNat (bs : List UInt8) : Nat := bs.foldr (fun b acc => b.toNat + 256 * acc) 0

def leBytes (n : Nat) (len : Nat) : List UInt8 :=
  (List.range len).map fun i => UInt8.ofNat (n / 256 ^ i)

/-- RFC 8032 §5.1.2 encoding. -/
def encode (P : Point) : List UInt8 :=
  let zi := finv P.Z
  let x := fmul P.X zi
  let y := fmul P.Y zi
  leBytes (y + (x % 2) * 2 ^ 255) 32

/-- RFC 8032 §5.1.3 decoding (rejects non-canonical y ≥ p and x = 0 with sign 1). -/
def decode (bs : List UInt8) : Option Point :=
  if bs.length ≠ 32 then none else
  let n := leNat bs
  let y := n % 2 ^ 255
  let sign := n / 2 ^ 255
  if y ≥ p then none else
  let u := fsub (fmul y y) 1
  let v := fadd (fmul d (fmul y y)) 1
  let v3 := fmul (fmul v v) v
  let v7 := fmul (fmul v3 v3) v
  let x0 := fmul (fmul u v3) (fpow (fmul u v7) ((p - 5) / 8))
  let vx2 := fmul v (fmul x0 x0)
  let x1 := if vx2 = u then some x0 else if vx2 = fsub 0 u then some (fmul x0 sqrtM1) else none
  match x1 with
  | none => none
  | some x =>
    if x = 0 ∧ sign = 1 then none else
    let x' := if x % 2 = sign then x else fsub 0 x
    some ⟨x', y, 1, fmul x' y⟩

/-- RFC 8032 §5.1.7 verification (cofactorless, encoding comparison). -/
def verify (pk msg sig : List UInt8) : Bool :=
  if sig.length ≠ 64 ∨ pk.length ≠ 32 then false else
  let rBytes := sig.take 32
  let s := leNat (sig.drop 32)
  if s ≥ L then false else
  match decode pk, decode rBytes with
  | some A, some _ =>
    let k := leNat (PCS.V2.SHA512.sha512 (rBytes ++ pk ++ msg)) % L
    decide (encode (add (scalarMul s B) (neg (scalarMul k A))) = rBytes)
  | _, _ => false

/-- Running the Lean checker with the Lean specification discharges hypothesis (A). -/
theorem ed25519ImplCorrect_self : PCS.V2.Signature.Ed25519ImplCorrect verify verify :=
  fun _ _ _ => rfl

/-- Structural facts of the verifier: wrong lengths and non-reduced `S` are rejected. -/
theorem verify_rejects_bad_length {pk msg sig : List UInt8} (h : sig.length ≠ 64) :
    verify pk msg sig = false := by
  unfold verify; simp [h]

theorem verify_rejects_bad_key_length {pk msg sig : List UInt8} (h : pk.length ≠ 32) :
    verify pk msg sig = false := by
  unfold verify; simp [h]

theorem verify_rejects_large_s {pk msg sig : List UInt8} (h : leNat (sig.drop 32) ≥ L) :
    verify pk msg sig = false := by
  unfold verify
  by_cases h1 : sig.length ≠ 64 ∨ pk.length ≠ 32
  · simp [h1]
  · simp only [h1, if_false]
    simp [h]

end PCS.V2.Ed25519
