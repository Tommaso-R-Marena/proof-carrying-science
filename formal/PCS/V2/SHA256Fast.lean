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

def compressBlocksFast : List UInt8 → List UInt32 → List UInt32
  | [], hs => hs
  | a :: l, hs => compressBlocksFast ((a :: l).drop 64) (compressFast hs ((a :: l).take 64))
termination_by l => l.length
decreasing_by simp; omega

/-- Kernel-efficient SHA-256 (equal to `sha256`, see `sha256_eq_sha256Fast`). -/
def sha256Fast (msg : List UInt8) : List UInt8 :=
  (compressBlocksFast (pad msg) H0).flatMap wordBytes

/-! ## Equivalence proof -/

/-- Head-recursive form of `schedRev` (proof form). -/
def schedHead (r0 : List UInt32) : Nat → List UInt32
  | 0 => r0
  | n + 1 => nextW (schedHead r0 n) :: schedHead r0 n

theorem schedHead_shift (r : List UInt32) : ∀ n,
    schedHead (nextW r :: r) n = schedHead r (n + 1)
  | 0 => rfl
  | n + 1 => by
    simp only [schedHead]
    rw [schedHead_shift r n]
    rfl

theorem schedRev_eq_schedHead : ∀ (n : Nat) (r : List UInt32), schedRev n r = schedHead r n
  | 0, _ => rfl
  | n + 1, r => by
    rw [schedRev, schedRev_eq_schedHead n, schedHead_shift]

theorem schedHead_length (r0 : List UInt32) : ∀ n, (schedHead r0 n).length = r0.length + n
  | 0 => rfl
  | n + 1 => by simp [schedHead, schedHead_length r0 n]; omega

theorem words_length_fast : ∀ (l : List UInt8), (words l).length = l.length / 4
  | a :: b :: c :: d :: rest => by
    simp only [words, List.length_cons, words_length_fast rest]; omega
  | [] => by simp [words]
  | [_] => by simp [words]
  | [_, _] => by simp [words]
  | [_, _, _] => by simp [words]

theorem getD_reverse_eq {L : List UInt32} {i : Nat} (h : i < L.length) :
    L.reverse.getD (L.length - 1 - i) 0 = L.getD i 0 := by
  simp only [List.getD_eq_getElem?_getD]
  rw [List.getElem?_reverse (by omega)]
  congr 2
  omega

theorem array_getElem!_eq (A : Array UInt32) (i : Nat) : A[i]! = A.toList.getD i 0 := by
  rw [getElem!_def, List.getD_eq_getElem?_getD, Array.getElem?_toList]
  cases A[i]? <;> rfl

/-- The production schedule loop, as a fold. -/
def schedStep (w : Array UInt32) (t : Nat) : Array UInt32 :=
  w.push (ssig1 w[t-2]! + w[t-7]! + ssig0 w[t-15]! + w[t-16]!)

theorem schedule_eq_foldl (block : List UInt8) :
    schedule block = (List.range' 16 48).foldl schedStep (words block).toArray := by
  simp [schedule]; rfl

theorem schedFold_toList (r0 : List UInt32) (h0 : r0.length = 16) : ∀ n,
    ((List.range' 16 n).foldl schedStep r0.reverse.toArray).toList = (schedHead r0 n).reverse
  | 0 => by simp [schedHead]
  | n + 1 => by
    rw [List.range'_concat, List.foldl_append, List.foldl_cons, List.foldl_nil]
    generalize hA : (List.range' 16 n).foldl schedStep r0.reverse.toArray = A
    have hA' : A.toList = (schedHead r0 n).reverse := by rw [← hA]; exact schedFold_toList r0 h0 n
    have hlen : (schedHead r0 n).length = 16 + n := by rw [schedHead_length, h0]
    simp only [schedStep, Array.toList_push, array_getElem!_eq, hA', schedHead, List.reverse_cons]
    congr 1
    simp only [nextW]
    have e : ∀ i, i < 16 → (schedHead r0 n).reverse.getD (16 + 1 * n - (i + 1)) 0 =
        (schedHead r0 n).getD i 0 := by
      intro i hi
      have := getD_reverse_eq (L := schedHead r0 n) (i := i) (by omega)
      rw [hlen] at this
      rw [← this]; congr 1; omega
    rw [show 16 + 1 * n - 2 = 16 + 1 * n - (1 + 1) by omega, e 1 (by omega),
      show 16 + 1 * n - 7 = 16 + 1 * n - (6 + 1) by omega, e 6 (by omega),
      show 16 + 1 * n - 15 = 16 + 1 * n - (14 + 1) by omega, e 14 (by omega),
      show 16 + 1 * n - 16 = 16 + 1 * n - (15 + 1) by omega, e 15 (by omega)]

theorem schedule_toList (block : List UInt8) (hb : block.length = 64) :
    (schedule block).toList = scheduleFast block := by
  have hw : (words block).length = 16 := by rw [words_length_fast, hb]
  rw [schedule_eq_foldl, scheduleFast, schedRev_eq_schedHead]
  have := schedFold_toList (words block).reverse (by simp [hw]) 48
  simpa using this

theorem roundsL_append (s : State) : ∀ (ks ws : List UInt32) (k w : UInt32),
    ks.length = ws.length → roundsL (ks ++ [k]) (ws ++ [w]) s = round (roundsL ks ws s) k w
  | [], [], k, w, _ => rfl
  | k' :: ks, w' :: ws, k, w, h => by
    simp only [List.cons_append, roundsL]
    exact roundsL_append (round s k' w') ks ws k w (by simpa using h)
  | [], _ :: _, _, _, h => by simp at h
  | _ :: _, [], _, _, h => by simp at h

theorem take_succ_getD (L : List UInt32) (n : Nat) (h : n < L.length) :
    L.take (n + 1) = L.take n ++ [L.getD n 0] := by
  rw [List.take_add_one, List.getElem?_eq_getElem h, List.getD_eq_getElem?_getD,
    List.getElem?_eq_getElem h]
  rfl

theorem foldl_range_rounds (Ks Ws : List UInt32) (s0 : State) : ∀ n, n ≤ Ks.length →
    n ≤ Ws.length →
    (List.range n).foldl (fun s t => round s (Ks.getD t 0) (Ws.getD t 0)) s0 =
      roundsL (Ks.take n) (Ws.take n) s0
  | 0, _, _ => by simp [roundsL]
  | n + 1, h1, h2 => by
    rw [List.range_succ, List.foldl_append, List.foldl_cons, List.foldl_nil,
      foldl_range_rounds Ks Ws s0 n (by omega) (by omega),
      take_succ_getD Ks n (by omega), take_succ_getD Ws n (by omega), roundsL_append]
    simp; omega

theorem compress_eq_compressFast (hs : List UInt32) (block : List UInt8)
    (hb : block.length = 64) : compress hs block = compressFast hs block := by
  have hsched := schedule_toList block hb
  have hlen : (scheduleFast block).length = 64 := by
    rw [scheduleFast, List.length_reverse, schedRev_eq_schedHead, schedHead_length,
      List.length_reverse, words_length_fast, hb]
  have hK : K.length = 64 := rfl
  simp only [compress, compressFast, array_getElem!_eq, hsched]
  rw [foldl_range_rounds K (scheduleFast block) _ 64 (by omega) (by omega)]
  rw [List.take_of_length_le (by omega), List.take_of_length_le (by omega)]

theorem compressBlocks_eq_fast : ∀ (l : List UInt8) (hs : List UInt32), l.length % 64 = 0 →
    compressBlocks l hs = compressBlocksFast l hs
  | [], hs, _ => by simp [compressBlocks, compressBlocksFast]
  | a :: l, hs, h => by
    rw [compressBlocks.eq_def, compressBlocksFast.eq_def]
    simp only
    have h64 : ((a :: l).take 64).length = 64 := by
      simp only [List.length_take, List.length_cons] at h ⊢; omega
    rw [compress_eq_compressFast hs _ h64]
    have hd : ((a :: l).drop 64).length % 64 = 0 := by
      simp only [List.length_drop, List.length_cons] at h ⊢; omega
    exact compressBlocks_eq_fast ((a :: l).drop 64) _ hd
termination_by l _ => l.length
decreasing_by simp; omega

/-- **The kernel-efficient SHA-256 is the production SHA-256.** -/
theorem sha256_eq_sha256Fast : sha256 = sha256Fast := by
  funext msg
  rw [sha256, sha256Fast, compressBlocks_eq_fast _ _ (pad_length_mod msg)]

end PCS.V2.SHA256
