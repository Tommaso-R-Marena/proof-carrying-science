import PCS.V2.ProofGatedStrongArtifacts
import PCS.V2.ProofGatedDeepCert

/-!
Runtime cross-checks and fixtures for the interval-error checker, the no-forgetting
checker, the deep certificate checker and the strong gate.

    CHK_MODE=generate lake env lean scripts/proof_gated_checker_vectors.lean
    CHK_MODE=check    lake env lean scripts/proof_gated_checker_vectors.lean

For deterministic pseudo-random networks and hand-picked edge cases (negative, zero and
large weights; breakpoints at exact integers; negative integer division; singleton and
empty intervals; intervals near `±10^12`), the run compares:
* `maxAbsErr` with a brute-force maximum over the whole interval;
* `findErrViolation` at the bounds `max - 1` and `max`;
* `findForgetting` with a brute-force search on a window (a returned point must be a real
  forgetting point; and if brute force finds one, the checker must return one);
* `certMaxErr` on the enumeration certificate and on a coarse certificate (when it is
  accepted) with brute force, for deep networks.

`generate` writes the TSV fixtures. `check` recomputes every line, compares it byte for
byte with the stored fixture, and repeats all brute-force comparisons.

These are runtime tests. They are not proofs. The universal statements are the
kernel-checked theorems `maxAbsErr_isMax`, `findErrViolation_complete`,
`noForgetting_iff`, `certMaxErr_isMax` and `acceptStrong_iff`.
-/

open PCS.V2.ProofGatedWide
open PCS.V2.ProofGatedRobust
open PCS.V2.ProofGatedNoForget
open PCS.V2.ProofGatedStrongGate
open PCS.V2.ProofGatedDeep (DeepNet DNeuron)
open PCS.V2.ProofGatedDeepCert

namespace CheckerVectors

def dir : System.FilePath := "fixtures/proof_gated"

/-- Linear congruential generator. -/
def lcg (s : Nat) : Nat := (s * 1103515245 + 12345) % 2147483648

/-- Draw an integer in `[-k, k]`. -/
def draw (s : Nat) (k : Nat) : Int × Nat :=
  let s' := lcg s
  (Int.ofNat ((s' / 65536) % (2 * k + 1)) - k, s')

def drawUnit (s : Nat) (kw kb ko : Nat) : HiddenUnit × Nat :=
  let (w, s) := draw s kw
  let (b, s) := draw s kb
  let (o, s) := draw s ko
  (⟨w, b, o⟩, s)

def drawNet (s : Nat) (width : Nat) (kw kb ko : Nat) : WideNet × Nat := Id.run do
  let mut st := s
  let mut hs : List HiddenUnit := []
  for _ in [0:width] do
    let (u, st') := drawUnit st kw kb ko
    hs := hs ++ [u]
    st := st'
  let (ob, st') := draw st kb
  return (⟨hs, ob⟩, st')

/-- Integer range `[L, U]` as a list (empty if `L > U`). -/
def ivl (L U : Int) : List Int :=
  (List.range (U - L + 1).toNat).map fun n => L + Int.ofNat n

def bruteMax (f t : WideNet) (L U : Int) : Nat :=
  (ivl L U).foldl (fun acc x => max acc (errAt f t x)) 0

structure Case where
  name : String
  f : WideNet
  t : WideNet
  lo : Int
  hi : Int

/-- Hand-picked edge cases. -/
def edgeCases : List Case :=
  [ ⟨"zero-weights", ⟨[⟨0, 5, 3⟩, ⟨0, -5, 7⟩], 1⟩, ⟨[], 0⟩, -10, 10⟩,
    ⟨"negative-weights", ⟨[⟨-3, 7, 2⟩, ⟨-5, -11, -1⟩], 0⟩, ⟨[⟨2, -3, 1⟩], 4⟩, -20, 20⟩,
    ⟨"exact-zero-activation", ⟨[⟨3, -6, 1⟩, ⟨-4, 8, 1⟩], 0⟩, ⟨[], 0⟩, -5, 7⟩,
    ⟨"negative-division", ⟨[⟨-7, -3, 5⟩, ⟨7, 3, -5⟩, ⟨-2, -1, 3⟩], 0⟩, ⟨[⟨1, 0, 1⟩], 0⟩, -9, 9⟩,
    ⟨"singleton", ⟨[⟨2, 1, 1⟩], 0⟩, ⟨[], 3⟩, 4, 4⟩,
    ⟨"empty", ⟨[⟨2, 1, 1⟩], 0⟩, ⟨[], 3⟩, 5, 4⟩,
    ⟨"large-positive", ⟨[⟨3, -3000000000000, 2⟩, ⟨-1, 1000000000001, 1⟩], 0⟩,
      ⟨[⟨1, -1000000000000, 5⟩], -7⟩, 999999999950, 1000000000050⟩,
    ⟨"large-negative", ⟨[⟨-3, -3000000000000, 2⟩, ⟨1, 1000000000001, -1⟩], 9⟩,
      ⟨[⟨-1, -1000000000000, 5⟩], 0⟩, -1000000000060, -999999999940⟩,
    ⟨"large-weights", ⟨[⟨1000000007, -999999999, 3⟩, ⟨-999999937, 12345, -2⟩], 0⟩,
      ⟨[⟨1, 0, 1⟩], 0⟩, -30, 30⟩,
    ⟨"target3-gen1", gen1, gen3, -50, 50⟩,
    ⟨"target3-ood", PCS.V2.ProofGatedLimits.oodCandidate, gen3, -50, 50⟩ ]

/-- Deterministic pseudo-random cases. -/
def randomCases (n : Nat) : List Case := Id.run do
  let mut st := 20261017
  let mut out : List Case := []
  for i in [0:n] do
    let (wf, s1) := draw st 3
    let (f, s2) := drawNet s1 wf.natAbs 6 25 5
    let (wt, s3) := draw s2 3
    let (t, s4) := drawNet s3 wt.natAbs 6 25 5
    let (lo, s5) := draw s4 60
    let (len, s6) := draw s5 60
    out := out ++ [⟨s!"random-{i}", f, t, lo, lo + len.natAbs - 3⟩]
    st := s6
  return out

def enc (m : WideNet) : String := PCS.V2.ProofGatedNetArtifacts.encode m

def optStr : Option Int → String
  | some x => toString x
  | none => "none"

/-- One TSV line per case (recomputed by `check`). -/
def caseLine (c : Case) : String :=
  let mx := maxAbsErr c.f c.t c.lo c.hi
  let w1 := if mx = 0 then none else findErrViolation c.f c.t c.lo c.hi (mx - 1)
  s!"{c.name}\t{enc c.f}\t{enc c.t}\t{c.lo}\t{c.hi}\t{mx}\t{optStr w1}\t{(errProbes c.f c.t c.lo c.hi).length}"

/-- Brute-force agreement for one case; returns an error message on failure. -/
def caseCheck (c : Case) : Option String :=
  let mx := maxAbsErr c.f c.t c.lo c.hi
  let bm := bruteMax c.f c.t c.lo c.hi
  if mx != bm then some s!"{c.name}: maxAbsErr {mx} ≠ brute {bm}" else
  let okHi := findErrViolation c.f c.t c.lo c.hi mx == none
  let okLo := if mx = 0 then true else
    match findErrViolation c.f c.t c.lo c.hi (mx - 1) with
    | some x => decide (c.lo ≤ x ∧ x ≤ c.hi ∧ mx - 1 < errAt c.f c.t x)
    | none => false
  if !(okHi && okLo) then some s!"{c.name}: witness mismatch" else none

/-- No-forgetting cross-check on a window `[-W, W]` with incumbent `f`, candidate `g`. -/
def nfCheck (name : String) (f g t : WideNet) (W : Int) : Option String :=
  let brute := (ivl (-W) W).find? (fun x => forgets f g t x)
  match findForgetting f g t, brute with
  | some x, _ =>
    if forgets f g t x then none else some s!"{name}: returned non-forgetting point {x}"
  | none, some x => some s!"{name}: checker missed forgetting point {x}"
  | none, none => none

/-! Deep networks -/

def drawDNeuron (s : Nat) (inW : Nat) : DNeuron × Nat := Id.run do
  let mut st := s
  let mut ws : List Int := []
  for _ in [0:inW] do
    let (w, st') := draw st 3
    ws := ws ++ [w]
    st := st'
  let (b, st') := draw st 6
  return (⟨ws, b⟩, st')

def drawDeep (s : Nat) (depth width : Nat) : DeepNet × Nat := Id.run do
  let mut st := s
  let mut layers : List (List DNeuron) := []
  let mut inW := 1
  for _ in [0:depth] do
    let mut L : List DNeuron := []
    for _ in [0:width] do
      let (n, st') := drawDNeuron st inW
      L := L ++ [n]
      st := st'
    layers := layers ++ [L]
    inW := width
  let (r, st') := drawDNeuron st inW
  return (⟨layers, r⟩, st')

def dBrute (f t : DeepNet) (L U : Int) : Nat :=
  (ivl L U).foldl (fun acc x => max acc (derr f t x)) 0

/-- A coarse certificate: every `k`-th point, then `U`. -/
def coarse (L U : Int) (k : Nat) : List Int :=
  ((ivl (L + 1) U).filter fun x => (x - L) % (k : Int) == 0 || x == U)

def deepLine (i : Nat) (f t : DeepNet) (L U : Int) : String × Option String :=
  let n := (U - L).toNat
  let e := enumCert L n
  let okE := chainOK f t L e
  let mE := certMaxErr f t L e
  let b := dBrute f t L U
  let c := coarse L U 4
  let okC := chainOK f t L c
  let mC := certMaxErr f t L c
  let err :=
    if !okE then some s!"deep-{i}: enumeration certificate rejected"
    else if mE != b then some s!"deep-{i}: enumeration max {mE} ≠ brute {b}"
    else if okC && mC != b then some s!"deep-{i}: coarse max {mC} ≠ brute {b}"
    else none
  (s!"deep-{i}\t{L}\t{U}\t{b}\t{okC}\t{c.length}", err)

def deepCases : List (Nat × DeepNet × DeepNet × Int × Int) := Id.run do
  let mut st := 777
  let mut out := []
  for i in [0:40] do
    let (d, s1) := draw st 2
    let (w, s2) := draw s1 2
    let (f, s3) := drawDeep s2 (d.natAbs + 1) (w.natAbs + 1)
    let (t, s4) := drawDeep s3 1 2
    let (lo, s5) := draw s4 30
    out := out ++ [(i, f, t, lo, lo + 40)]
    st := s5
  return out

/-! Strong gate decisions -/

def strongCases : List (String × StrongSpec × WideNet × WideNet) :=
  [ ("growth1-narrow", specNarrow, gen0, gen1), ("growth2-narrow", specNarrow, gen1, gen2),
    ("growth3-narrow", specNarrow, gen2, gen3), ("growth1-mid", specMid, gen0, gen1),
    ("robust1-wide", specWide, gen0, r1), ("robust2-wide", specWide, r1, r2),
    ("robust3-wide", specWide, r2, gen3), ("blindForget-narrow", specNarrow, gen2, blindForget),
    ("ood-mid", specMid, gen2, PCS.V2.ProofGatedLimits.oodCandidate),
    ("ood-narrow", specNarrow, gen2, PCS.V2.ProofGatedLimits.oodCandidate),
    ("noProgress-mid", specMid, gen2, gen2swap) ]

def strongLine (c : String × StrongSpec × WideNet × WideNet) : String :=
  let (name, S, a, m) := c
  let A := PCS.V2.ProofGatedGeneric.accept S.corpusSpec a m
  let B := noForgetting a m S.target
  let C := robustB a m S.target S.lo S.hi
  s!"{name}\t{S.lo}\t{S.hi}\t{enc a}\t{enc m}\t{A}\t{B}\t{C}\t{acceptStrong S a m}\t{optStr (findForgetting a m S.target)}\t{optStr (findRobustViolation a m S.target S.lo S.hi)}"

def allCases : List Case := edgeCases ++ randomCases 300

def robustTsv : String :=
  "name\tf\tt\tlo\thi\tmaxAbsErr\twitness_at_max_minus_1\tprobes\n" ++
    String.intercalate "\n" (allCases.map caseLine) ++ "\n"

def deepTsv : String :=
  "name\tlo\thi\tbrute_max\tcoarse_accepted\tcoarse_len\n" ++
    String.intercalate "\n" (deepCases.map fun (i, f, t, L, U) => (deepLine i f t L U).1) ++ "\n"

def strongTsv : String :=
  "name\tlo\thi\tincumbent\tcandidate\tA_progress\tB_noForget\tC_robust\taccept\tforget_witness\trobust_witness\n" ++
    String.intercalate "\n" (strongCases.map strongLine) ++ "\n"

def generate : IO UInt32 := do
  IO.FS.createDirAll dir
  IO.FS.writeFile (dir / "robust_vectors.tsv") robustTsv
  IO.FS.writeFile (dir / "deep_cert_vectors.tsv") deepTsv
  IO.FS.writeFile (dir / "strong_gate_cases.tsv") strongTsv
  IO.println "generated robust_vectors.tsv, deep_cert_vectors.tsv, strong_gate_cases.tsv"
  return 0

def check : IO UInt32 := do
  let mut n := 0
  for (file, content) in [("robust_vectors.tsv", robustTsv), ("deep_cert_vectors.tsv", deepTsv),
      ("strong_gate_cases.tsv", strongTsv)] do
    let stored ← IO.FS.readFile (dir / file)
    if stored != content then
      IO.eprintln s!"FAIL: {file} differs from recomputed content"; return 1
    n := n + 1
  for c in allCases do
    match caseCheck c with
    | some e => IO.eprintln s!"FAIL: {e}"; return 1
    | none => n := n + 1
  -- no-forgetting cross-checks: every ordered pair among the first 60 random networks
  let nets := (randomCases 60).map (·.f)
  let tgt := gen3
  let mut nf := 0
  for f in nets.take 20 do
    for g in nets.take 20 do
      match nfCheck "nf" f g tgt 150 with
      | some e => IO.eprintln s!"FAIL: {e}"; return 1
      | none => nf := nf + 1
  n := n + nf
  for (i, f, t, L, U) in deepCases do
    match (deepLine i f t L U).2 with
    | some e => IO.eprintln s!"FAIL: {e}"; return 1
    | none => n := n + 1
  IO.println s!"OK: {n} checker vector checks passed ({allCases.length} interval cases, {nf} no-forgetting pairs, {deepCases.length} deep cases, {strongCases.length} strong-gate cases)"
  return 0

end CheckerVectors

def runCheckerVectors : IO Unit := do
  let mode ← IO.getEnv "CHK_MODE"
  let code ← match mode with
    | some "generate" => CheckerVectors.generate
    | _ => CheckerVectors.check
  if code != 0 then throw (IO.userError s!"proof_gated_checker_vectors failed with code {code}")

#eval runCheckerVectors
