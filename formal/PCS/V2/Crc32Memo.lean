import PCS.V2.Zip

/-!
# Proof-carrying CRC-32 evaluation

`PCS.V2.Zip.crc32` is a left fold over the input.  Kernel reduction is lazy, so evaluating
the fold over a kilobyte-sized input builds a chain of unevaluated accumulator thunks that
is forced only at the end, which overflows the kernel's recursion limit
("(kernel) deep recursion detected").

`crcChunksOK s cs` checks a list of *checkpoints* `(chunk, state after chunk)`: comparing
each fold result with the claimed state (`==`) forces the accumulator after every chunk, so
the kernel's recursion depth is bounded by the chunk size.  `foldl_of_crcChunksOK` proves
that a successful check yields the fold over the concatenated chunks; a wrong checkpoint
makes the check (and hence the proof) fail.  `crc32_eq_crc32Memo` then lets a whole
encoding be evaluated with proved CRC values (cf. `PCS.V2.SHA256Memo`).
-/

set_option autoImplicit false

namespace PCS.V2.Crc32Memo

open PCS.V2.Zip

/-- Check CRC-32 fold checkpoints. -/
def crcChunksOK : UInt32 → List (List UInt8 × UInt32) → Bool
  | _, [] => true
  | s, (c, s') :: rest => (c.foldl crcByte s == s') && crcChunksOK s' rest

/-- The final state of a checkpoint list. -/
def chunksFinal : UInt32 → List (List UInt8 × UInt32) → UInt32
  | s, [] => s
  | _, (_, s') :: rest => chunksFinal s' rest

/-- The bytes covered by a checkpoint list. -/
def chunksBytes (cs : List (List UInt8 × UInt32)) : List UInt8 := cs.flatMap (·.1)

theorem foldl_of_crcChunksOK :
    ∀ (s : UInt32) (cs : List (List UInt8 × UInt32)), crcChunksOK s cs = true →
      (chunksBytes cs).foldl crcByte s = chunksFinal s cs
  | _, [], _ => rfl
  | s, (c, s') :: rest, h => by
    simp only [crcChunksOK, Bool.and_eq_true, beq_iff_eq] at h
    simp only [chunksBytes, List.flatMap_cons, List.foldl_append, chunksFinal]
    rw [h.1]
    exact foldl_of_crcChunksOK s' rest h.2

theorem crc32_of_crcChunksOK {cs : List (List UInt8 × UInt32)}
    (h : crcChunksOK 0xFFFFFFFF cs = true) :
    crc32 (chunksBytes cs) = chunksFinal 0xFFFFFFFF cs ^^^ 0xFFFFFFFF := by
  rw [crc32, foldl_of_crcChunksOK _ _ h]

/-- Look `l` up in a table of proved `(input, crc)` facts. -/
def crcFind (l : List UInt8) : List (List UInt8 × UInt32) → Option UInt32
  | [] => none
  | p :: ps => if p.1 = l then some p.2 else crcFind l ps

/-- CRC-32 with a memo table (falls back to `crc32` on a miss). -/
def crc32Memo (table : List (List UInt8 × UInt32)) (l : List UInt8) : UInt32 :=
  match crcFind l table with
  | some c => c
  | none => crc32 l

def CrcMemoCorrect (table : List (List UInt8 × UInt32)) : Prop :=
  ∀ p ∈ table, crc32 p.1 = p.2

theorem crcFind_sound {l : List UInt8} :
    ∀ {table : List (List UInt8 × UInt32)} {c : UInt32},
      CrcMemoCorrect table → crcFind l table = some c → crc32 l = c
  | [], _, _, h => by simp [crcFind] at h
  | p :: ps, c, hc, h => by
    unfold crcFind at h
    split at h
    · rename_i hp
      subst hp
      rw [hc p (List.mem_cons_self ..)]; exact Option.some.inj h
    · exact crcFind_sound (fun q hq => hc q (List.mem_cons_of_mem _ hq)) h

theorem crc32_eq_crc32Memo {table : List (List UInt8 × UInt32)} (hc : CrcMemoCorrect table) :
    crc32 = crc32Memo table := by
  funext l
  unfold crc32Memo
  split
  · rename_i c h; exact crcFind_sound hc h
  · rfl

theorem crcMemoCorrect_nil : CrcMemoCorrect [] := by simp [CrcMemoCorrect]

theorem crcMemoCorrect_cons {x : List UInt8} {c : UInt32} {ps : List (List UInt8 × UInt32)}
    (h : crc32 x = c) (hs : CrcMemoCorrect ps) : CrcMemoCorrect ((x, c) :: ps) := by
  intro p hp
  rcases List.mem_cons.1 hp with rfl | hp
  · exact h
  · exact hs p hp

end PCS.V2.Crc32Memo
