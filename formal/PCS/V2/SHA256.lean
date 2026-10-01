import PCS.V2.Hex

/-!
# SHA-256 (FIPS 180-4) in Lean

A direct transcription of FIPS 180-4 §4.1.2, §4.2.2, §5.1.1, §5.2.1, §5.3.3 and
§6.2.2, used by the Lean v0.6/v2 checker to recompute every domain-separated
digest.  The Lean checker therefore does **not** trust Python `hashlib` / OpenSSL
for its own acceptance decision.

Proved here (structural, implementation-level facts):

* `pad_length_mod` : the padded message length is a multiple of 64 bytes;
* `pad_prefix`     : the padded message starts with the exact message bytes;
* `pad_marker`     : the byte after the message is `0x80`;
* `pad_length_field` : the last 8 bytes are the big-endian bit length;
* `chunks_join`    : block parsing loses/duplicates no byte;
* `sha256_length`  : every digest is exactly 32 bytes;

Known-answer vectors are checked in `PCS.V2.Vectors` (tests, not proofs).

What is *not* proved: that Python's `hashlib.sha256` (OpenSSL) computes this same
function.  That is the named boundary `Sha256ProductionAgrees` in `PCS.V2.TCB`;
it matters only for *completeness* (accepting honestly produced artifacts), never
for the soundness of the Lean checker, which recomputes digests itself.
Collision resistance is not a theorem; it appears only as explicit collision
witnesses in the hash-binding theorems (`PCS.V2.Domains.digest_binding`, `PCS.V2.Binding`).
-/

namespace PCS.V2.SHA256

def K : List UInt32 := [
  0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
  0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
  0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
  0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
  0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
  0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
  0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
  0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2]

def H0 : List UInt32 :=
  [0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a, 0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19]

def rotr (x : UInt32) (n : UInt32) : UInt32 := (x >>> n) ||| (x <<< (32 - n))

def ch (x y z : UInt32) : UInt32 := (x &&& y) ^^^ ((~~~x) &&& z)
def maj (x y z : UInt32) : UInt32 := (x &&& y) ^^^ (x &&& z) ^^^ (y &&& z)
def bsig0 (x : UInt32) : UInt32 := rotr x 2 ^^^ rotr x 13 ^^^ rotr x 22
def bsig1 (x : UInt32) : UInt32 := rotr x 6 ^^^ rotr x 11 ^^^ rotr x 25
def ssig0 (x : UInt32) : UInt32 := rotr x 7 ^^^ rotr x 18 ^^^ (x >>> 3)
def ssig1 (x : UInt32) : UInt32 := rotr x 17 ^^^ rotr x 19 ^^^ (x >>> 10)

/-- Big-endian 64-bit encoding of a natural number (mod 2^64). -/
def be64 (n : Nat) : List UInt8 :=
  (List.range 8).reverse.map fun i => UInt8.ofNat (n / 256 ^ i)

/-- Number of zero bytes after the `0x80` marker (FIPS 180-4 §5.1.1). -/
def padZeros (len : Nat) : Nat := (119 - len % 64) % 64

/-- FIPS 180-4 §5.1.1 padding. -/
def pad (msg : List UInt8) : List UInt8 :=
  msg ++ [0x80] ++ List.replicate (padZeros msg.length) 0 ++ be64 (8 * msg.length)

/-- Split into 64-byte blocks (FIPS 180-4 §5.2.1). -/
def chunks : List UInt8 → List (List UInt8)
  | [] => []
  | a :: l => (a :: l).take 64 :: chunks ((a :: l).drop 64)
termination_by l => l.length
decreasing_by simp; omega

def word (a b c d : UInt8) : UInt32 :=
  (a.toUInt32 <<< 24) ||| (b.toUInt32 <<< 16) ||| (c.toUInt32 <<< 8) ||| d.toUInt32

def words : List UInt8 → List UInt32
  | a :: b :: c :: d :: rest => word a b c d :: words rest
  | _ => []

/-- Message schedule W₀..W₆₃ (FIPS 180-4 §6.2.2 step 1). -/
def schedule (block : List UInt8) : Array UInt32 := Id.run do
  let mut w : Array UInt32 := (words block).toArray
  for t in [16:64] do
    w := w.push (ssig1 w[t-2]! + w[t-7]! + ssig0 w[t-15]! + w[t-16]!)
  return w

structure State where
  a : UInt32
  b : UInt32
  c : UInt32
  d : UInt32
  e : UInt32
  f : UInt32
  g : UInt32
  h : UInt32

/-- One round of the compression function (FIPS 180-4 §6.2.2 step 3). -/
def round (s : State) (k w : UInt32) : State :=
  let t1 := s.h + bsig1 s.e + ch s.e s.f s.g + k + w
  let t2 := bsig0 s.a + maj s.a s.b s.c
  { a := t1 + t2, b := s.a, c := s.b, d := s.c, e := s.d + t1, f := s.e, g := s.f, h := s.g }

def ofList (hs : List UInt32) : State :=
  { a := hs.getD 0 0, b := hs.getD 1 0, c := hs.getD 2 0, d := hs.getD 3 0,
    e := hs.getD 4 0, f := hs.getD 5 0, g := hs.getD 6 0, h := hs.getD 7 0 }

def toList (s : State) : List UInt32 := [s.a, s.b, s.c, s.d, s.e, s.f, s.g, s.h]

/-- Compression of one block (FIPS 180-4 §6.2.2 steps 2–4). -/
def compress (hs : List UInt32) (block : List UInt8) : List UInt32 :=
  let w := schedule block
  let s := (List.range 64).foldl (fun s t => round s (K.getD t 0) w[t]!) (ofList hs)
  List.zipWith (· + ·) hs (toList s)

def wordBytes (x : UInt32) : List UInt8 :=
  [(x >>> 24).toUInt8, (x >>> 16).toUInt8, (x >>> 8).toUInt8, x.toUInt8]

/-- Tail-recursive block compression.  Unlike `chunks l |>.foldl`, this does
    not retain a second whole-message list of 64-byte blocks while hashing large
    artifacts. -/
def compressBlocks : List UInt8 → List UInt32 → List UInt32
  | [], hs => hs
  | a :: l, hs =>
      compressBlocks ((a :: l).drop 64) (compress hs ((a :: l).take 64))
termination_by l => l.length
decreasing_by simp; omega

/-- The tail-recursive block fold is extensionally identical to the original
    `chunks(...).foldl compress` specification. -/
theorem compressBlocks_eq_chunks_foldl : ∀ (l : List UInt8) (hs : List UInt32),
    compressBlocks l hs = (chunks l).foldl compress hs
  | [], hs => by simp [compressBlocks, chunks]
  | a :: l, hs => by
      rw [compressBlocks.eq_def, chunks.eq_def]
      simp only [List.foldl_cons]
      exact compressBlocks_eq_chunks_foldl ((a :: l).drop 64)
        (compress hs ((a :: l).take 64))
termination_by l hs => l.length
decreasing_by simp; omega

/-- SHA-256 of a byte list.  Runtime evaluation uses the tail-recursive block fold;
    `compressBlocks_eq_chunks_foldl` fixes its semantics to the original direct
    FIPS transcription. -/
def sha256 (msg : List UInt8) : List UInt8 :=
  (compressBlocks (pad msg) H0).flatMap wordBytes

/-- Lower-case hex SHA-256, i.e. Python `hashlib.sha256(b).hexdigest()`. -/
def sha256Hex (msg : ByteArray) : String := PCS.V2.Hex.hexEncode (sha256 msg.data.toList)

/-! ## Structural facts -/

theorem be64_length (n : Nat) : (be64 n).length = 8 := by simp [be64]

theorem pad_length (msg : List UInt8) :
    (pad msg).length = msg.length + 1 + padZeros msg.length + 8 := by
  simp [pad, be64_length]; omega

theorem pad_length_mod (msg : List UInt8) : (pad msg).length % 64 = 0 := by
  rw [pad_length]; unfold padZeros; omega

theorem pad_prefix (msg : List UInt8) : (pad msg).take msg.length = msg := by
  simp [pad]

theorem pad_marker (msg : List UInt8) : (pad msg)[msg.length]? = some 0x80 := by
  simp [pad, List.append_assoc]

theorem pad_length_field (msg : List UInt8) :
    (pad msg).drop (msg.length + 1 + padZeros msg.length) = be64 (8 * msg.length) := by
  unfold pad
  apply List.drop_left'
  simp; omega

theorem chunks_join : ∀ l : List UInt8, (chunks l).flatten = l
  | [] => by rw [chunks.eq_def]; rfl
  | a :: l => by
    rw [chunks.eq_def]
    simp only [List.flatten_cons]
    rw [chunks_join ((a :: l).drop 64)]
    exact List.take_append_drop 64 (a :: l)
termination_by l => l.length
decreasing_by simp; omega

theorem chunks_length_of_mod : ∀ l : List UInt8, l.length % 64 = 0 →
    ∀ c ∈ chunks l, c.length = 64
  | [] => by intro _ c hc; rw [chunks.eq_def] at hc; cases hc
  | a :: l => by
    intro hmod c hc
    simp only [List.length_cons] at hmod
    rw [chunks.eq_def] at hc
    simp only [List.mem_cons] at hc
    rcases hc with rfl | hc
    · simp only [List.length_take, List.length_cons]; omega
    · exact chunks_length_of_mod ((a :: l).drop 64) (by simp; omega) c hc
termination_by l => l.length
decreasing_by simp; omega

/-- Every padded block is exactly 512 bits. -/
theorem pad_blocks_64 (msg : List UInt8) : ∀ c ∈ chunks (pad msg), c.length = 64 :=
  chunks_length_of_mod _ (pad_length_mod msg)

theorem compress_length (hs : List UInt32) (block : List UInt8) (h : hs.length = 8) :
    (compress hs block).length = 8 := by
  simp [compress, toList, h]

theorem foldl_compress_length : ∀ (bs : List (List UInt8)) (hs : List UInt32),
    hs.length = 8 → (bs.foldl compress hs).length = 8
  | [], hs, h => by simpa using h
  | b :: bs, hs, h => by
    simp only [List.foldl_cons]
    exact foldl_compress_length bs _ (compress_length hs b h)

theorem sha256_length (msg : List UInt8) : (sha256 msg).length = 32 := by
  unfold sha256
  rw [compressBlocks_eq_chunks_foldl]
  have h8 := foldl_compress_length (chunks (pad msg)) H0 (by simp [H0])
  generalize (chunks (pad msg)).foldl compress H0 = hs at h8
  match hs, h8 with
  | [a, b, c, d, e, f, g, h], _ => simp [wordBytes]

end PCS.V2.SHA256
