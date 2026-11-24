import ClaimCheckAssurance.Header

/-!
Runs the decoder that `ClaimCheckAssurance.Header` proves correct on every vector of a file and
writes one line per vector, for comparison with the C and Python decoders
(`test_header_refinement.py`).  Input: records of 4-byte big-endian `cap`, 4-byte big-endian length
`n`, then `n` bytes.  Output line: `N` (rejected) or `L m h` (header length, data length, hash of
the data).  This is the same `decode` the theorems are about, executed, not a re-implementation.
-/

open PCS.ClaimCheck.Assurance

def be32 (b : ByteArray) (i : Nat) : Nat :=
  (b.get! i).toNat * 16777216 + (b.get! (i + 1)).toNat * 65536 + (b.get! (i + 2)).toNat * 256 + (b.get! (i + 3)).toNat

def hashBytes (d : List Nat) : Nat := d.foldl (fun h x => (h * 257 + x + 1) % 2305843009213693951) 0

partial def loop (b : ByteArray) (i : Nat) (out : Array String) : Array String :=
  if i + 8 > b.size then out else
  let cap := be32 b i
  let n := be32 b (i + 4)
  let buf := (b.extract (i + 8) (i + 8 + n)).data.toList.map UInt8.toNat
  let line := match decode buf cap with
    | none => "N"
    | some (d, L) => s!"{L} {d.length} {hashBytes d}"
  loop b (i + 8 + n) (out.push line)

def main (args : List String) : IO Unit := do
  let b ← IO.FS.readBinFile args[0]!
  IO.FS.writeFile args[1]! (String.intercalate "\n" (loop b 0 #[]).toList ++ "\n")
