import PCS.V2.ProofGatedArtifacts
import PCS.V2.ProofGatedNetArtifacts

/-!
Test-vector generator and replayer for the `PGSI1` and `PGSI2-WIDE` artifact codecs.

Run from the project root:

    PGSI_MODE=generate lake env lean scripts/proof_gated_vectors.lean
    PGSI_MODE=check    lake env lean scripts/proof_gated_vectors.lean

`generate` writes the fixture files under `fixtures/proof_gated/`. `check` reads them
back and compares each line with the current Lean `encode` / `decode` / `acceptWire`.
It exits with a nonzero code on the first mismatch.

These are runtime tests. They are not proofs. The universal statements are the
kernel-checked theorems `ProofGatedArtifacts.decode_encode_of_bounded`,
`ProofGatedArtifacts.decode_eq_some_iff`, `ProofGatedNetArtifacts.decode_iff` and
related ones. The comparison against `encodeLegacy` / `decodeLegacy` (the original
`toString` / `splitOn` / `toInt?` code) runs the compiled legacy code. It does not
discharge the separate assumption, used in `ProofGatedV1Analysis`, that the opaque
`String.Internal.append` is concatenation.
-/

open PCS.V2.ProofGatedSelfImprovement (Neuron)

namespace ProofGatedVectors

def dir : System.FilePath := "fixtures/proof_gated"

def range32 : List Int := (List.range 65).map fun n => Int.ofNat n - 32

def actChar (b : Bool) : String := if b then "R" else "L"

/-- All 2 × 65 × 65 = 8,450 canonical `PGSI1` artifacts. -/
def allNeurons : List Neuron :=
  [true, false].flatMap fun r => range32.flatMap fun w => range32.map fun b => ⟨r, w, b⟩

/-- Wire strings that the `PGSI1` decoder must reject. -/
def pgsi1Negative : List String :=
  [ "PGSI1|R|33|0", "PGSI1|R|-33|0", "PGSI1|L|0|33", "PGSI1|L|0|-33",
    "PGSI1|R|-0|0", "PGSI1|R|0|-0", "PGSI1|R|00|0", "PGSI1|R|01|1", "PGSI1|R|1|01",
    "PGSI1|R|-01|1", "PGSI1|R|+1|1", "PGSI1|R| 1|1", "PGSI1|R|1|1 ", "PGSI1|R|1|1|",
    "|PGSI1|R|1|1", "PGSI1|R|1", "PGSI1|R||1", "PGSI1|X|1|1", "PGSI1|r|1|1",
    "PGSI1|RR|1|1", "PGSI2|R|1|1", "pgsi1|R|1|1", "PGSI1|R|1|1\n", "PGSI1|R|--1|1",
    "PGSI1|R|1-|1", "PGSI1|R|0x1|1", "PGSI1|R|1.0|1", "" ]

/-- Wide networks used as `PGSI2-WIDE` roundtrip fixtures (all valid for `arch3`). -/
def wideFixtures : List PCS.V2.ProofGatedWide.WideNet :=
  [ ⟨[], 0⟩, ⟨[], -32⟩, ⟨[], 32⟩,
    PCS.V2.ProofGatedWide.gen1, PCS.V2.ProofGatedWide.gen2, PCS.V2.ProofGatedWide.gen3,
    ⟨[⟨-32, 32, -32⟩, ⟨32, -32, 32⟩], 0⟩,
    ⟨[⟨0, 0, 0⟩, ⟨-1, -1, -1⟩, ⟨10, -10, 7⟩, ⟨1, 1, 1⟩], -5⟩ ]

def wideNegative : List String :=
  [ "PGSI2-WIDE|33", "PGSI2-WIDE|0|-33|0|0", "PGSI2-WIDE|007", "PGSI2-WIDE|-0",
    "PGSI2-WIDE|0|1|2", "PGSI1-WIDE|0", "PGSI2-WIDE|0|", "PGSI2-WIDE",
    "PGSI2-WIDE|0|1|1|1|1|1|1|1|1|1|1|1|1|1|1|1|1|1|1|1|1|1|1|1|1|1|1", "" ]

def lineOf (m : Neuron) : String :=
  s!"{actChar m.useReLU}\t{m.weight}\t{m.bias}\t{PCS.V2.ProofGatedArtifacts.encode m}"

/-- Accepting/rejecting two-file pairs for the file-based `PGSI1` authority. -/
def acceptPairs : List (Neuron × Neuron) :=
  [ (⟨true, 0, 0⟩, ⟨true, 1, 1⟩), (⟨true, 0, 0⟩, ⟨true, 2, 1⟩), (⟨false, 0, 0⟩, ⟨true, 2, 1⟩) ]

def rejectPairs : List (Neuron × Neuron) :=
  [ (⟨true, 2, 1⟩, ⟨true, 0, 0⟩), (⟨true, 0, 0⟩, ⟨true, 0, 0⟩), (⟨true, 0, 0⟩, ⟨true, 1, 2⟩) ]

def generate : IO UInt32 := do
  IO.FS.createDirAll dir
  IO.FS.writeFile (dir / "pgsi1_canonical.tsv")
    (String.intercalate "\n" (allNeurons.map lineOf) ++ "\n")
  -- one vector per file so that bytes such as a trailing newline survive
  IO.FS.createDirAll (dir / "pgsi1_negative")
  for (raw, i) in pgsi1Negative.zipIdx do
    IO.FS.writeFile (dir / "pgsi1_negative" / s!"neg_{i}.txt") raw
  IO.FS.createDirAll (dir / "pgsi1_pairs")
  for ((o, n), i) in acceptPairs.zipIdx do
    IO.FS.writeFile (dir / "pgsi1_pairs" / s!"accept_{i}_old.txt") (PCS.V2.ProofGatedArtifacts.encode o)
    IO.FS.writeFile (dir / "pgsi1_pairs" / s!"accept_{i}_new.txt") (PCS.V2.ProofGatedArtifacts.encode n)
  for ((o, n), i) in rejectPairs.zipIdx do
    IO.FS.writeFile (dir / "pgsi1_pairs" / s!"reject_{i}_old.txt") (PCS.V2.ProofGatedArtifacts.encode o)
    IO.FS.writeFile (dir / "pgsi1_pairs" / s!"reject_{i}_new.txt") (PCS.V2.ProofGatedArtifacts.encode n)
  IO.FS.writeFile (dir / "pgsi2_wide_canonical.txt")
    (String.intercalate "\n" (wideFixtures.map PCS.V2.ProofGatedNetArtifacts.encode) ++ "\n")
  IO.FS.createDirAll (dir / "pgsi2_wide_negative")
  for (raw, i) in wideNegative.zipIdx do
    IO.FS.writeFile (dir / "pgsi2_wide_negative" / s!"neg_{i}.txt") raw
  IO.println s!"wrote {allNeurons.length} PGSI1 canonical vectors, {pgsi1Negative.length} PGSI1 negative vectors, {wideFixtures.length} PGSI2-WIDE vectors, {wideNegative.length} PGSI2-WIDE negative vectors"
  return 0

def fail (msg : String) : IO UInt32 := do
  IO.eprintln s!"FAIL: {msg}"
  return 1

def check : IO UInt32 := do
  let mut n := 0
  -- 1. canonical PGSI1 table: regenerate from Lean and compare byte-for-byte
  let tsv ← IO.FS.readFile (dir / "pgsi1_canonical.tsv")
  if tsv != String.intercalate "\n" (allNeurons.map lineOf) ++ "\n" then
    return ← fail "pgsi1_canonical.tsv differs from the current Lean encoder"
  for m in allNeurons do
    let raw := PCS.V2.ProofGatedArtifacts.encode m
    if PCS.V2.ProofGatedArtifacts.decode raw != some m then
      return ← fail s!"decode (encode m) ≠ some m for {raw}"
    -- runtime comparison with the original encoder / decoder
    if PCS.V2.ProofGatedArtifacts.encodeLegacy m != raw then
      return ← fail s!"legacy encoder differs on {raw}"
    if PCS.V2.ProofGatedArtifacts.decodeLegacy raw != some m then
      return ← fail s!"legacy decoder differs on {raw}"
    n := n + 1
  for w in [-33, 33, -100, 100] do
    let m : Neuron := ⟨true, w, 0⟩
    if PCS.V2.ProofGatedArtifacts.decode (PCS.V2.ProofGatedArtifacts.encode m) != none then
      return ← fail s!"out-of-range weight {w} decoded"
  -- 2. negative PGSI1 vectors
  for i in List.range pgsi1Negative.length do
    let raw ← IO.FS.readFile (dir / "pgsi1_negative" / s!"neg_{i}.txt")
    if PCS.V2.ProofGatedArtifacts.decode raw != none then
      return ← fail s!"PGSI1 negative vector {i} ({raw.quote}) was accepted"
    if PCS.V2.ProofGatedArtifacts.decodeLegacy raw != none then
      return ← fail s!"legacy decoder accepts PGSI1 negative vector {i} ({raw.quote})"
    n := n + 1
  -- 3. file pairs through acceptWire
  for i in List.range acceptPairs.length do
    let o ← IO.FS.readFile (dir / "pgsi1_pairs" / s!"accept_{i}_old.txt")
    let c ← IO.FS.readFile (dir / "pgsi1_pairs" / s!"accept_{i}_new.txt")
    if !PCS.V2.ProofGatedArtifacts.acceptWire o c then return ← fail s!"accept pair {i} rejected"
    n := n + 1
  for i in List.range rejectPairs.length do
    let o ← IO.FS.readFile (dir / "pgsi1_pairs" / s!"reject_{i}_old.txt")
    let c ← IO.FS.readFile (dir / "pgsi1_pairs" / s!"reject_{i}_new.txt")
    if PCS.V2.ProofGatedArtifacts.acceptWire o c then return ← fail s!"reject pair {i} accepted"
    n := n + 1
  -- 4. PGSI2-WIDE
  let wide ← IO.FS.readFile (dir / "pgsi2_wide_canonical.txt")
  let lines := (wide.splitOn "\n").filter (· ≠ "")
  if lines.length != wideFixtures.length then return ← fail "PGSI2-WIDE fixture count"
  for (raw, m) in lines.zip wideFixtures do
    if PCS.V2.ProofGatedNetArtifacts.encode m != raw then
      return ← fail s!"PGSI2-WIDE encoding differs: {raw}"
    if PCS.V2.ProofGatedNetArtifacts.decode PCS.V2.ProofGatedWide.arch3 raw != some m then
      return ← fail s!"PGSI2-WIDE roundtrip fails: {raw}"
    n := n + 1
  for i in List.range wideNegative.length do
    let raw ← IO.FS.readFile (dir / "pgsi2_wide_negative" / s!"neg_{i}.txt")
    if PCS.V2.ProofGatedNetArtifacts.decode PCS.V2.ProofGatedWide.arch3 raw != none then
      return ← fail s!"PGSI2-WIDE negative vector {i} ({raw.quote}) was accepted"
    n := n + 1
  IO.println s!"OK: {n} vector checks passed"
  return 0

end ProofGatedVectors

/-- Mode is taken from the environment variable `PGSI_MODE` (`generate` or `check`).
Any failure raises an error, so `lake env lean` exits with a nonzero code. -/
def runVectors : IO Unit := do
  let mode ← IO.getEnv "PGSI_MODE"
  let code ← match mode with
    | some "generate" => ProofGatedVectors.generate
    | _ => ProofGatedVectors.check
  if code != 0 then throw (IO.userError s!"proof_gated_vectors failed with code {code}")

#eval runVectors
