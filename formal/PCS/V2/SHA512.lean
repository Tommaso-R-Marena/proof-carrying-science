import PCS.V2.SHA256

/-!
# SHA-512 (FIPS 180-4 §4.1.3, §4.2.3, §5.1.2, §5.2.2, §5.3.5, §6.4.2)

Needed by Ed25519 (RFC 8032 §5.1.7: `k = SHA-512(R ‖ A ‖ M)`).  The round constants
are the first 64 bits of the fractional parts of the cube roots of the first 80
primes (initial values: square roots of the first 8 primes), exactly as FIPS 180-4
specifies; known-answer vectors are checked in `PCS.V2.Vectors`.
-/

namespace PCS.V2.SHA512

def K : List UInt64 := [
  0x428a2f98d728ae22, 0x7137449123ef65cd, 0xb5c0fbcfec4d3b2f, 0xe9b5dba58189dbbc,
  0x3956c25bf348b538, 0x59f111f1b605d019, 0x923f82a4af194f9b, 0xab1c5ed5da6d8118,
  0xd807aa98a3030242, 0x12835b0145706fbe, 0x243185be4ee4b28c, 0x550c7dc3d5ffb4e2,
  0x72be5d74f27b896f, 0x80deb1fe3b1696b1, 0x9bdc06a725c71235, 0xc19bf174cf692694,
  0xe49b69c19ef14ad2, 0xefbe4786384f25e3, 0x0fc19dc68b8cd5b5, 0x240ca1cc77ac9c65,
  0x2de92c6f592b0275, 0x4a7484aa6ea6e483, 0x5cb0a9dcbd41fbd4, 0x76f988da831153b5,
  0x983e5152ee66dfab, 0xa831c66d2db43210, 0xb00327c898fb213f, 0xbf597fc7beef0ee4,
  0xc6e00bf33da88fc2, 0xd5a79147930aa725, 0x06ca6351e003826f, 0x142929670a0e6e70,
  0x27b70a8546d22ffc, 0x2e1b21385c26c926, 0x4d2c6dfc5ac42aed, 0x53380d139d95b3df,
  0x650a73548baf63de, 0x766a0abb3c77b2a8, 0x81c2c92e47edaee6, 0x92722c851482353b,
  0xa2bfe8a14cf10364, 0xa81a664bbc423001, 0xc24b8b70d0f89791, 0xc76c51a30654be30,
  0xd192e819d6ef5218, 0xd69906245565a910, 0xf40e35855771202a, 0x106aa07032bbd1b8,
  0x19a4c116b8d2d0c8, 0x1e376c085141ab53, 0x2748774cdf8eeb99, 0x34b0bcb5e19b48a8,
  0x391c0cb3c5c95a63, 0x4ed8aa4ae3418acb, 0x5b9cca4f7763e373, 0x682e6ff3d6b2b8a3,
  0x748f82ee5defb2fc, 0x78a5636f43172f60, 0x84c87814a1f0ab72, 0x8cc702081a6439ec,
  0x90befffa23631e28, 0xa4506cebde82bde9, 0xbef9a3f7b2c67915, 0xc67178f2e372532b,
  0xca273eceea26619c, 0xd186b8c721c0c207, 0xeada7dd6cde0eb1e, 0xf57d4f7fee6ed178,
  0x06f067aa72176fba, 0x0a637dc5a2c898a6, 0x113f9804bef90dae, 0x1b710b35131c471b,
  0x28db77f523047d84, 0x32caab7b40c72493, 0x3c9ebe0a15c9bebc, 0x431d67c49c100d4c,
  0x4cc5d4becb3e42b6, 0x597f299cfc657e2a, 0x5fcb6fab3ad6faec, 0x6c44198c4a475817]

def H0 : List UInt64 :=
  [0x6a09e667f3bcc908, 0xbb67ae8584caa73b, 0x3c6ef372fe94f82b, 0xa54ff53a5f1d36f1, 0x510e527fade682d1, 0x9b05688c2b3e6c1f, 0x1f83d9abfb41bd6b, 0x5be0cd19137e2179]

def rotr (x : UInt64) (n : UInt64) : UInt64 := (x >>> n) ||| (x <<< (64 - n))

def ch (x y z : UInt64) : UInt64 := (x &&& y) ^^^ ((~~~x) &&& z)
def maj (x y z : UInt64) : UInt64 := (x &&& y) ^^^ (x &&& z) ^^^ (y &&& z)
def bsig0 (x : UInt64) : UInt64 := rotr x 28 ^^^ rotr x 34 ^^^ rotr x 39
def bsig1 (x : UInt64) : UInt64 := rotr x 14 ^^^ rotr x 18 ^^^ rotr x 41
def ssig0 (x : UInt64) : UInt64 := rotr x 1 ^^^ rotr x 8 ^^^ (x >>> 7)
def ssig1 (x : UInt64) : UInt64 := rotr x 19 ^^^ rotr x 61 ^^^ (x >>> 6)

/-- Big-endian 128-bit length field. -/
def be128 (n : Nat) : List UInt8 :=
  (List.range 16).reverse.map fun i => UInt8.ofNat (n / 256 ^ i)

def padZeros (len : Nat) : Nat := (239 - len % 128) % 128

def pad (msg : List UInt8) : List UInt8 :=
  msg ++ [0x80] ++ List.replicate (padZeros msg.length) 0 ++ be128 (8 * msg.length)

def chunks : List UInt8 → List (List UInt8)
  | [] => []
  | a :: l => (a :: l).take 128 :: chunks ((a :: l).drop 128)
termination_by l => l.length
decreasing_by simp; omega

def word (bs : List UInt8) : UInt64 :=
  bs.foldl (fun acc b => (acc <<< 8) ||| b.toUInt64) 0

def words : List UInt8 → List UInt64
  | [] => []
  | a :: l => word ((a :: l).take 8) :: words ((a :: l).drop 8)
termination_by l => l.length
decreasing_by simp; omega

def schedule (block : List UInt8) : Array UInt64 := Id.run do
  let mut w : Array UInt64 := (words block).toArray
  for t in [16:80] do
    w := w.push (ssig1 w[t-2]! + w[t-7]! + ssig0 w[t-15]! + w[t-16]!)
  return w

def round (s : List UInt64) (k w : UInt64) : List UInt64 :=
  match s with
  | [a, b, c, d, e, f, g, h] =>
    let t1 := h + bsig1 e + ch e f g + k + w
    let t2 := bsig0 a + maj a b c
    [t1 + t2, a, b, c, d + t1, e, f, g]
  | _ => s

def compress (hs : List UInt64) (block : List UInt8) : List UInt64 :=
  let w := schedule block
  let s := (List.range 80).foldl (fun s t => round s (K.getD t 0) w[t]!) hs
  List.zipWith (· + ·) hs s

def wordBytes (x : UInt64) : List UInt8 :=
  (List.range 8).reverse.map fun i => (x >>> (8 * i).toUInt64).toUInt8

/-- SHA-512 of a byte list. -/
def sha512 (msg : List UInt8) : List UInt8 :=
  ((chunks (pad msg)).foldl compress H0).flatMap wordBytes

theorem pad_length_mod (msg : List UInt8) : (pad msg).length % 128 = 0 := by
  simp [pad, be128, padZeros]
  omega

theorem pad_prefix (msg : List UInt8) : (pad msg).take msg.length = msg := by
  simp [pad]

end PCS.V2.SHA512
