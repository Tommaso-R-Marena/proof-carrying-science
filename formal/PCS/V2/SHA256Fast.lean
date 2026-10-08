import PCS.V2.SHA256

/-!
# A kernel-efficient SHA-256, proved equal to the production `sha256`

`PCS.V2.SHA256.sha256` builds the message schedule in an `Array` with `push` and
`w[t]!` and runs the 64 rounds as a fold over `List.range 64` with `K.getD t 0` and
`w[t]!`.  Inside Lean's kernel an `Array` is a `List`, so every `push` and every
indexed read is linear, which made one compression cost ≈ 1.7 s of kernel time.

`sha256Fast` performs the same computation with the same `UInt32` operations, but

* builds the schedule as a reversed list, reading only the first 16 entries of it
  (`schedRev`, sliding window), and
* runs the rounds by structural recursion over `K` and the schedule (`roundsL`).

`sha256_eq_sha256Fast : sha256 = sha256Fast` is proved for **every** message, so kernel
evaluations of `sha256Fast` are evaluations of the production function.  Nothing about
SHA-256 itself is assumed.
-/

set_option autoImplicit false

namespace PCS.V2.SHA256

/-! ## The fast formulation -/

/-- Next schedule word from the reversed schedule `[w_{t-1}, w_{t-2}, …]`. -/
def nextW (r : List UInt32) : UInt32 :=
  ssig1 (r.getD 1 0) + r.getD 6 0 + ssig0 (r.getD 14 0) + r.getD 15 0

/-- Tail-recursive reversed-schedule extension (kernel evaluation form). -/
def schedRev : Nat → List UInt32 → List UInt32
  | 0, r => r
  | n + 1, r => schedRev n (nextW r :: r)

/-- The 64 rounds by structural recursion over the constants and the schedule. -/
def roundsL : List UInt32 → List UInt32 → State → State
  | k :: ks, w :: ws, s => roundsL ks ws (round s k w)
  | _, _, s => s

def scheduleFast (block : List UInt8) : List UInt32 :=
  (schedRev 48 (words block).reverse).reverse

def compressFast (hs : List UInt32) (block : List UInt8) : List UInt32 :=
  List.zipWith (· + ·) hs (toList (roundsL K (scheduleFast block) (ofList hs)))

def compressBlocksFast : List UInt8 → List UInt32 ��PЀL@��}vr�