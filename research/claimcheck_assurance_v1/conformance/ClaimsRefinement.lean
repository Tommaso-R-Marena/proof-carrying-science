import ClaimCheckAssurance.Claims

/-!
Runs the parser that `ClaimCheckAssurance.Claims` proves to accept exactly the canonical tails
(`parseTail_iff`) on every vector of a file and writes one line per vector, for comparison with the
stand-alone runner's Python parser (`test_claims_refinement.py`).  Input: records of a 4-byte
big-endian length `n`, then `n` bytes (a generated part, everything after the marker).  Output line:
`N` (rejected) or `A <data length> <hash of the data> <claims> <outcome texts joined by |>`.  This is
the same `parseTail` the theorems are about, executed, not a re-implementation.
-/

open PCS.ClaimCheck PCS.ClaimCheck.Assurance

def be32 (b : ByteArray) (i : Nat) : Nat :=
  (b.get! i).toNat * 16777216 + (b.get! (i + 1)).toNat * 65536 + (b.get! (i + 2)).toNat * 256 + (b.get! (i + 3)).toNat

def hashBytes (d : List Nat) : Nat := d.foldl (fun h x => (h * 257 + x + 1) % 2305843009213693951) 0

def text (l : List Nat) : String := String.ofList (l.map Char.ofNat)

partial def loop (b : ByteArray) (i : Nat) (out : Array String) : Array String :=
  if i + 4 > b.size then out else
  let n := be32 b i
  let buf := (b.extract (i + 4) (i + 4 + n)).data.toList.map UInt8.toNat
  let line := match parseTail buf with
    | none => "N"
    | some (d, cs, os) => s!"A {d.length} {hashBytes d} {cs.length} " ++ String.intercalate "|" (os.map (fun o => text (outR o)))
  loop b (i + 4 + n) (out.push line)

def main (args : List String) : IO Unit := do
  let b ← IO.FS.readBinFile args[0]!
  IO.FS.writeFile args[1]! (String.intercalate "\n" (loop b 0 #[]).toList ++ "\n")
