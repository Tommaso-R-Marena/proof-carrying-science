import PCS.V2.SHA256

/-!
# Proof-carrying SHA-256 memo tables

Kernel evaluation of SHA-256 on kilobyte-sized inputs is the dominant cost of evaluating
the package checker on a concrete archive.  Once `sha256 x = d` has been *proved* for the
concrete inputs `x` that occur (each such fact is itself kernel-checked, once), the checker
can be evaluated with `sha256` replaced by `sha256Memo table`, which looks the input up in
the table and only falls back to `sha256` on a miss.

`sha256_eq_sha256Memo` is an equality of functions, valid for every table all of whose
entries are proved correct, so the replacement changes nothing semantically: an incorrect
table entry cannot be used (its correctness is a hypothesis), and a missing entry simply
falls back to the real hash.
-/

set_option autoImplicit false

namespace PCS.V2.SHA256Memo

open PCS.V2.SHA256

/-- Look `l` up in a table of `(input, digest)` pairs. -/
def memoFind (l : List UInt8) : List (List UInt8 × List UInt8) → Option (List UInt8)
  | [] => none
  | p :: ps => if p.1 = l then some p.2 else memoFind l ps

/-- SHA-256 with a memo table (falls back to `sha256` on a miss). -/
def sha256Memo (table : List (List UInt8 × List UInt8)) (l : List UInt8) : List UInt8 :=
  match memoFind l table with
  | some d => d
  | none => sha256 l

/-- Every entry of the table is a correct SHA-256 fact. -/
def MemoCorrect (table : List (List UInt8 × List UInt8)) : Prop :=
  ∀ p ∈ table, sha256 p.1 = p.2

theorem memoFind_sound {l : List UInt8} :
    ∀ {table : List (List UInt8 × List UInt8)} {d : List UInt8},
      MemoCorrect table → memoFind l table = some d → sha256 l = d
  | [], _, _, h => by simp [memoFind] at h
  | p :: ps, d, hc, h => by
    unfold memoFind at h
    split at h
    · rename_i hp
      subst hp
      have := hc p (List.mem_cons_self ..)
      rw [this]; exact Option.some.inj h
    · exact memoFind_sound (fun q hq => hc q (List.mem_cons_of_mem _ hq)) h

theorem sha256_eq_sha256Memo {table : List (List UInt8 × List UInt8)} (hc : MemoCorrect table) :
    sha256 = sha256Memo table := by
  funext l
  unfold sha256Memo
  split
  · rename_i d h; exact memoFind_sound hc h
  · rfl

theorem memoCorrect_nil : MemoCorrect [] := by simp [MemoCorrect]

theorem memoCorrect_cons {x d : List UInt8} {ps : List (List UInt8 × List UInt8)}
    (h : sha256 x = d) (hs : MemoCorrect ps) : MemoCorrect ((x, d) :: ps) := by
  intro p hp
  rcases List.mem_cons.1 hp with rfl | hp
  · exact h
  · exact hs p hp

end PCS.V2.SHA256Memo
