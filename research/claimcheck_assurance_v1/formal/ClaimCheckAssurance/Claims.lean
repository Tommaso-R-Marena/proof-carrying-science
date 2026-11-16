import ClaimCheck
import ClaimCheckAssurance.Header

/-!
# The claims part of a proof file: canonical rendering, and a parser that inverts it

A ClaimCheck proof file is `CHECKER ++ MARKER ++ TAIL`, and `TAIL` is

    canon d ++ defsR 0 cs ++ batchR cs.length os ++ thmsR 0 os

`canon d` is the source header of `Header.lean`.  After it come one definition per claim
(`def pcs_c<i> : Claim := { … }`), the batch theorem, and one theorem per claim
(`theorem pcs_claim_<i> : run pcs_src pcs_c<i> = <outcome>`), exactly as
`claimcheck_v1/lean.py::batch_tail` writes them.  This module gives

* an abstract syntax for what a tail can say (`ClaimA`, `OutcomeA`, with rationals and byte strings
  as literals), a validity predicate `tailOk` (bytes below 256, data within `MAXD`, 1 to 256 claims,
  as many outcomes as claims, fractions in lowest terms with a positive denominator, `√` values with
  sign -1, 0 or 1 and a non-negative radicand);
* `renderTail`, written after the generator: the one spelling the generator uses for each value
  (`b "…"` exactly when every byte is a safe character, otherwise a list of numbers; decimal numerals
  without leading zeros; fractions as `((n : Rat) / d)`);
* `parseTail`, a parser for the whole tail.

Proved (Lean kernel):

* `parseTail_renderTail`  every valid tail the renderer writes is accepted and parsed back to its values;
* `parseTail_sound`       whatever is accepted is exactly the rendering of what is returned, and valid;
* `renderTail_injective`  two different valid values never have the same text;
* `parseTail_iff`         the accepted language is exactly the set of renderings of valid values.

So every accepted tail consists of the canonical header of its data, the definitions
`def pcs_c<i> : Claim := claimR (cs[i])`, the batch theorem `runAll pcs_src [pcs_c0, …] = [outR os[0], …]`,
and for every `i` the theorem `run pcs_src pcs_c<i> = outR os[i]`, proved by `run_of_runAll` from the
batch theorem, and nothing else: no other declaration, command, comment or spacing.

`ClaimA.den` and `OutcomeA.den` map the syntax to the checker's own values (`Claim`, `Outcome`).  Read
with the standard meaning of Lean's literals, the batch theorem of an accepted tail states
`runAll src (cs.map ClaimA.den) = os.map OutcomeA.den` and theorem `i` states
`run src (cs[i]).den = (os[i]).den`, about the reviewed checker's `run`, for the source `src` whose
bytes are exactly the decoded data (`parseTail_source`, from `Header.lean`).  Further proved:

* `batch_iff_claims`        the claim theorems say together exactly what the batch theorem says;
* `same_meaning_same_text`  two accepted tails with the same data, claims and outcomes in the checker
                            are the same text (one meaning, one spelling; `QLit.val_inj` for fractions).

Trusted, not proved: that Lean's elaborator gives the literals their standard meaning (numerals,
`-`, `((n : Rat) / d)`, string literals without backslash or quote, the structure instance and the
constructor names, which resolve to the checker's because an accepted tail declares nothing else).

Compared by test with the Python parser of the stand-alone runner (`conformance/test_claims_refinement.py`).
-/

namespace PCS.ClaimCheck.Assurance

open PCS.ClaimCheck

/-! ## 1. Abstract syntax -/

/-- The literal `((num : Rat) / den)`. -/
structure QLit where
  num : Int
  den : Nat
  deriving DecidableEq, Repr

/-- A row condition, with its byte strings and its rational as literals. -/
inductive CondA where
  | textEq (col val : List Nat)
  | textNe (col val : List Nat)
  | num (col : List Nat) (cmp : Cmp) (val : QLit)
  deriving DecidableEq, Repr

inductive StatA where
  | count
  | share (sub : List CondA)
  | sum | mean | median | min | max | varSample | sdSample | sdPop | sem
  | pearson (x : List Nat)
  | olsSlope (x : List Nat)
  | olsIntercept (x : List Nat)
  deriving DecidableEq, Repr

structure ClaimA where
  column : Option (List Nat)
  filter : List CondA
  stat : StatA
  naTokens : List (List Nat)
  scale : QLit
  reported : List Nat
  deriving DecidableEq, Repr

inductive ValueA where
  | rat (q : QLit)
  | sqrt (sign : Int) (radicand : QLit)
  deriving DecidableEq, Repr

inductive OutcomeA where
  | checked (verdict : Verdict) (value : ValueA) (used missing : Nat)
  | undefined (reason : Undefined)
  deriving DecidableEq, Repr

/-! ## 2. Fixed texts (UTF-8 bytes; `texts_are_utf8` checks each against its string) -/

/-- `b "` -/
def tBq : List Nat := [98, 32, 34]
/-- `((` -/
def tRat : List Nat := [40, 40]
/-- ` : Rat) / ` -/
def tRatDiv : List Nat := [32, 58, 32, 82, 97, 116, 41, 32, 47, 32]
/-- `.textEq (` -/
def tTextEq : List Nat := [46, 116, 101, 120, 116, 69, 113, 32, 40]
/-- `.textNe (` -/
def tTextNe : List Nat := [46, 116, 101, 120, 116, 78, 101, 32, 40]
/-- `.num (` -/
def tNum : List Nat := [46, 110, 117, 109, 32, 40]
/-- `) (` -/
def tCO : List Nat := [41, 32, 40]
/-- `) ` -/
def tCS : List Nat := [41, 32]
/-- `none` -/
def tNone : List Nat := [110, 111, 110, 101]
/-- `some (` -/
def tSome : List Nat := [115, 111, 109, 101, 32, 40]
/-- `{ column := ` -/
def tC1 : List Nat := [123, 32, 99, 111, 108, 117, 109, 110, 32, 58, 61, 32]
/-- `,⏎    filter := ` -/
def tC2 : List Nat := [44, 10, 32, 32, 32, 32, 102, 105, 108, 116, 101, 114, 32, 58, 61, 32]
/-- `,⏎    stat := ` -/
def tC3 : List Nat := [44, 10, 32, 32, 32, 32, 115, 116, 97, 116, 32, 58, 61, 32]
/-- `,⏎    naTokens := ` -/
def tC4 : List Nat := [44, 10, 32, 32, 32, 32, 110, 97, 84, 111, 107, 101, 110, 115, 32, 58, 61, 32]
/-- `,⏎    scale := ` -/
def tC5 : List Nat := [44, 10, 32, 32, 32, 32, 115, 99, 97, 108, 101, 32, 58, 61, 32]
/-- `,⏎    reported := ` -/
def tC6 : List Nat := [44, 10, 32, 32, 32, 32, 114, 101, 112, 111, 114, 116, 101, 100, 32, 58, 61, 32]
/-- ` }` -/
def tC7 : List Nat := [32, 125]
/-- `(.rat ` -/
def tValRat : List Nat := [40, 46, 114, 97, 116, 32]
/-- `(.sqrt (` -/
def tValSqrt : List Nat := [40, 46, 115, 113, 114, 116, 32, 40]
/-- ` : Int) ` -/
def tColonInt : List Nat := [32, 58, 32, 73, 110, 116, 41, 32]
/-- `.checked .` -/
def tChecked : List Nat := [46, 99, 104, 101, 99, 107, 101, 100, 32, 46]
/-- `.undefined .` -/
def tUndef : List Nat := [46, 117, 110, 100, 101, 102, 105, 110, 101, 100, 32, 46]
/-- `def pcs_c` -/
def tDefC : List Nat := [100, 101, 102, 32, 112, 99, 115, 95, 99]
/-- ` : Claim :=⏎  ` -/
def tDefEnd : List Nat := [32, 58, 32, 67, 108, 97, 105, 109, 32, 58, 61, 10, 32, 32]
/-- `⏎⏎` -/
def tNL2 : List Nat := [10, 10]
/-- `theorem pcs_batch : runAll pcs_src [` -/
def tBatch : List Nat := [116, 104, 101, 111, 114, 101, 109, 32, 112, 99, 115, 95, 98, 97, 116, 99, 104, 32, 58, 32, 114, 117, 110, 65, 108, 108, 32, 112, 99, 115, 95, 115, 114, 99, 32, 91]
/-- `pcs_c` -/
def tPcsC : List Nat := [112, 99, 115, 95, 99]
/-- `, ` -/
def tComma : List Nat := [44, 32]
/-- `] =⏎    [` -/
def tBatchMid : List Nat := [93, 32, 61, 10, 32, 32, 32, 32, 91]
/-- `,⏎    ` -/
def tSepOut : List Nat := [44, 10, 32, 32, 32, 32]
/-- `] := by decide +kernel⏎⏎` -/
def tBatchEnd : List Nat := [93, 32, 58, 61, 32, 98, 121, 32, 100, 101, 99, 105, 100, 101, 32, 43, 107, 101, 114, 110, 101, 108, 10, 10]
/-- `theorem pcs_claim_` -/
def tThm : List Nat := [116, 104, 101, 111, 114, 101, 109, 32, 112, 99, 115, 95, 99, 108, 97, 105, 109, 95]
/-- ` : run pcs_src pcs_c` -/
def tThmRun : List Nat := [32, 58, 32, 114, 117, 110, 32, 112, 99, 115, 95, 115, 114, 99, 32, 112, 99, 115, 95, 99]
/-- ` = ` -/
def tThmEq : List Nat := [32, 61, 32]
/-- ` :=⏎  run_of_runAll pcs_batch ` -/
def tThmBy : List Nat := [32, 58, 61, 10, 32, 32, 114, 117, 110, 95, 111, 102, 95, 114, 117, 110, 65, 108, 108, 32, 112, 99, 115, 95, 98, 97, 116, 99, 104, 32]
/-- ` rfl rfl⏎#print axioms pcs_claim_` -/
def tThmAx : List Nat := [32, 114, 102, 108, 32, 114, 102, 108, 10, 35, 112, 114, 105, 110, 116, 32, 97, 120, 105, 111, 109, 115, 32, 112, 99, 115, 95, 99, 108, 97, 105, 109, 95]
def n_count : List Nat := [99, 111, 117, 110, 116]
def n_share : List Nat := [115, 104, 97, 114, 101]
def n_sum : List Nat := [115, 117, 109]
def n_mean : List Nat := [109, 101, 97, 110]
def n_median : List Nat := [109, 101, 100, 105, 97, 110]
def n_min : List Nat := [109, 105, 110]
def n_max : List Nat := [109, 97, 120]
def n_varSample : List Nat := [118, 97, 114, 83, 97, 109, 112, 108, 101]
def n_sdSample : List Nat := [115, 100, 83, 97, 109, 112, 108, 101]
def n_sdPop : List Nat := [115, 100, 80, 111, 112]
def n_sem : List Nat := [115, 101, 109]
def n_pearson : List Nat := [112, 101, 97, 114, 115, 111, 110]
def n_olsSlope : List Nat := [111, 108, 115, 83, 108, 111, 112, 101]
def n_olsIntercept : List Nat := [111, 108, 115, 73, 110, 116, 101, 114, 99, 101, 112, 116]
def n_eq : List Nat := [101, 113]
def n_ne : List Nat := [110, 101]
def n_lt : List Nat := [108, 116]
def n_le : List Nat := [108, 101]
def n_gt : List Nat := [103, 116]
def n_ge : List Nat := [103, 101]
def n_consistent : List Nat := [99, 111, 110, 115, 105, 115, 116, 101, 110, 116]
def n_inconsistent : List Nat := [105, 110, 99, 111, 110, 115, 105, 115, 116, 101, 110, 116]
def n_sourceNotWellFormed : List Nat := [115, 111, 117, 114, 99, 101, 78, 111, 116, 87, 101, 108, 108, 70, 111, 114, 109, 101, 100]
def n_csvMalformed : List Nat := [99, 115, 118, 77, 97, 108, 102, 111, 114, 109, 101, 100]
def n_columnNotFound : List Nat := [99, 111, 108, 117, 109, 110, 78, 111, 116, 70, 111, 117, 110, 100]
def n_nonNumericCell : List Nat := [110, 111, 110, 78, 117, 109, 101, 114, 105, 99, 67, 101, 108, 108]
def n_emptySelection : List Nat := [101, 109, 112, 116, 121, 83, 101, 108, 101, 99, 116, 105, 111, 110]
def n_degenerate : List Nat := [100, 101, 103, 101, 110, 101, 114, 97, 116, 101]
def n_badReportedLiteral : List Nat := [98, 97, 100, 82, 101, 112, 111, 114, 116, 101, 100, 76, 105, 116, 101, 114, 97, 108]
def n_badScale : List Nat := [98, 97, 100, 83, 99, 97, 108, 101]
def n_missingColumn : List Nat := [109, 105, 115, 115, 105, 110, 103, 67, 111, 108, 117, 109, 110]
theorem texts_are_utf8 :
  tBq = b "b \"" ∧
  tRat = b "((" ∧
  tRatDiv = b " : Rat) / " ∧
  tTextEq = b ".textEq (" ∧
  tTextNe = b ".textNe (" ∧
  tNum = b ".num (" ∧
  tCO = b ") (" ∧
  tCS = b ") " ∧
  tNone = b "none" ∧
  tSome = b "some (" ∧
  tC1 = b "{ column := " ∧
  tC2 = b ",\n    filter := " ∧
  tC3 = b ",\n    stat := " ∧
  tC4 = b ",\n    naTokens := " ∧
  tC5 = b ",\n    scale := " ∧
  tC6 = b ",\n    reported := " ∧
  tC7 = b " }" ∧
  tValRat = b "(.rat " ∧
  tValSqrt = b "(.sqrt (" ∧
  tColonInt = b " : Int) " ∧
  tChecked = b ".checked ." ∧
  tUndef = b ".undefined ." ∧
  tDefC = b "def pcs_c" ∧
  tDefEnd = b " : Claim :=\n  " ∧
  tNL2 = b "\n\n" ∧
  tBatch = b "theorem pcs_batch : runAll pcs_src [" ∧
  tPcsC = b "pcs_c" ∧
  tComma = b ", " ∧
  tBatchMid = b "] =\n    [" ∧
  tSepOut = b ",\n    " ∧
  tBatchEnd = b "] := by decide +kernel\n\n" ∧
  tThm = b "theorem pcs_claim_" ∧
  tThmRun = b " : run pcs_src pcs_c" ∧
  tThmEq = b " = " ∧
  tThmBy = b " :=\n  run_of_runAll pcs_batch " ∧
  tThmAx = b " rfl rfl\n#print axioms pcs_claim_" := by
  decide +kernel

/-! ## 3. Characters -/

def isAlpha (c : Nat) : Bool := (decide (65 ≤ c) && decide (c ≤ 90)) || (decide (97 ≤ c) && decide (c ≤ 122))

/-- The punctuation allowed inside `b "…"` (the generator's `_SAFE_STRING`, besides letters and digits). -/
def safeExtra : List Nat :=
  [32, 95, 46, 44, 58, 59, 40, 41, 91, 93, 37, 47, 43, 45, 35, 61, 60, 62, 38, 42, 33, 63, 64, 94, 124, 126]

def isSafe (c : Nat) : Bool := isAlpha c || isDig c || safeExtra.contains c

/-! ## 4. Rendering (after `claimcheck_v1/lean.py`) -/

/-- `sep y₁ sep y₂ …` -/
def sepTail (sep : List Nat) : List (List Nat) → List Nat
  | [] => []
  | y :: ys => sep ++ y ++ sepTail sep ys

/-- `x₀ sep x₁ sep …` -/
def sepBy (sep : List Nat) : List (List Nat) → List Nat
  | [] => []
  | x :: xs => x ++ sepTail sep xs

/-- `lean_bytes`: `b "…"` exactly when every byte is a safe character, otherwise `[n, n, …]`. -/
def bytesR (s : List Nat) : List Nat :=
  if s.all isSafe then tBq ++ s ++ [34] else 91 :: sepBy tComma (s.map decStr) ++ [93]

def intR : Int → List Nat
  | .ofNat n => decStr n
  | .negSucc n => 45 :: decStr (n + 1)

/-- `lean_rat`: `((n : Rat) / d)`. -/
def qR (q : QLit) : List Nat := tRat ++ intR q.num ++ tRatDiv ++ decStr q.den ++ [41]

def cmpName : Cmp → List Nat
  | .eq => n_eq | .ne => n_ne | .lt => n_lt | .le => n_le | .gt => n_gt | .ge => n_ge

def condR : CondA → List Nat
  | .textEq c v => tTextEq ++ bytesR c ++ tCO ++ bytesR v ++ [41]
  | .textNe c v => tTextNe ++ bytesR c ++ tCO ++ bytesR v ++ [41]
  | .num c k q => tNum ++ bytesR c ++ tCS ++ 46 :: cmpName k ++ 32 :: qR q

def listR (xs : List (List Nat)) : List Nat := 91 :: sepBy tComma xs ++ [93]

def statR : StatA → List Nat
  | .count => 46 :: n_count
  | .share sub => 46 :: n_share ++ 32 :: listR (sub.map condR)
  | .sum => 46 :: n_sum
  | .mean => 46 :: n_mean
  | .median => 46 :: n_median
  | .min => 46 :: n_min
  | .max => 46 :: n_max
  | .varSample => 46 :: n_varSample
  | .sdSample => 46 :: n_sdSample
  | .sdPop => 46 :: n_sdPop
  | .sem => 46 :: n_sem
  | .pearson x => 46 :: n_pearson ++ 32 :: 40 :: bytesR x ++ [41]
  | .olsSlope x => 46 :: n_olsSlope ++ 32 :: 40 :: bytesR x ++ [41]
  | .olsIntercept x => 46 :: n_olsIntercept ++ 32 :: 40 :: bytesR x ++ [41]

def colR : Option (List Nat) → List Nat
  | none => tNone
  | some c => tSome ++ bytesR c ++ [41]

/-- `lean_claim`. -/
def claimR (a : ClaimA) : List Nat :=
  tC1 ++ colR a.column ++ tC2 ++ listR (a.filter.map condR) ++ tC3 ++ statR a.stat ++ tC4 ++
    listR (a.naTokens.map bytesR) ++ tC5 ++ qR a.scale ++ tC6 ++ bytesR a.reported ++ tC7

def verdictName : Verdict → List Nat
  | .consistent => n_consistent
  | .inconsistent => n_inconsistent

def undefName : Undefined → List Nat
  | .sourceNotWellFormed => n_sourceNotWellFormed
  | .csvMalformed => n_csvMalformed
  | .columnNotFound => n_columnNotFound
  | .nonNumericCell => n_nonNumericCell
  | .emptySelection => n_emptySelection
  | .degenerate => n_degenerate
  | .badReportedLiteral => n_badReportedLiteral
  | .badScale => n_badScale
  | .missingColumn => n_missingColumn

def valR : ValueA → List Nat
  | .rat q => tValRat ++ qR q ++ [41]
  | .sqrt s q => tValSqrt ++ intR s ++ tColonInt ++ qR q ++ [41]

/-- `lean_outcome`. -/
def outR : OutcomeA → List Nat
  | .checked v x u m => tChecked ++ verdictName v ++ 32 :: valR x ++ 32 :: decStr u ++ 32 :: decStr m
  | .undefined r => tUndef ++ undefName r

def defHead (i : Nat) : List Nat := tDefC ++ decStr i ++ tDefEnd

def defsR : Nat → List ClaimA → List Nat
  | _, [] => []
  | i, a :: as => defHead i ++ claimR a ++ tNL2 ++ defsR (i + 1) as

def namesR (n : Nat) : List Nat := sepBy tComma ((List.range n).map (fun i => tPcsC ++ decStr i))

def batchHead (n : Nat) : List Nat := tBatch ++ namesR n ++ tBatchMid

def batchR (n : Nat) (os : List OutcomeA) : List Nat :=
  batchHead n ++ sepBy tSepOut (os.map outR) ++ tBatchEnd

def thmR (i : Nat) (o : OutcomeA) : List Nat :=
  tThm ++ decStr i ++ tThmRun ++ decStr i ++ tThmEq ++ outR o ++ tThmBy ++ decStr i ++ tThmAx ++ decStr i ++ tNL2

def thmsR : Nat → List OutcomeA → List Nat
  | _, [] => []
  | i, o :: os => thmR i o ++ thmsR (i + 1) os

/-- `batch_tail`: the whole generated part for data `d`, claims `cs` and expected outcomes `os`. -/
def renderTail (d : List Nat) (cs : List ClaimA) (os : List OutcomeA) : List Nat :=
  canon d ++ defsR 0 cs ++ batchR cs.length os ++ thmsR 0 os

/-! ## 5. Validity -/

def bytesOk (s : List Nat) : Bool := s.all (fun x => decide (x < 256))

/-- Lowest terms, positive denominator (so `0` is `((0 : Rat) / 1)` and there is no `-0`). -/
def QLit.ok (q : QLit) : Bool := decide (0 < q.den) && decide (Nat.gcd q.num.natAbs q.den = 1)

def CondA.ok : CondA → Bool
  | .textEq c v => bytesOk c && bytesOk v
  | .textNe c v => bytesOk c && bytesOk v
  | .num c _ q => bytesOk c && q.ok

def StatA.ok : StatA → Bool
  | .share sub => sub.all CondA.ok
  | .pearson x => bytesOk x
  | .olsSlope x => bytesOk x
  | .olsIntercept x => bytesOk x
  | _ => true

def colOk : Option (List Nat) → Bool
  | none => true
  | some c => bytesOk c

def ClaimA.ok (a : ClaimA) : Bool :=
  colOk a.column && a.filter.all CondA.ok && a.stat.ok && a.naTokens.all bytesOk && a.scale.ok &&
    bytesOk a.reported

def ValueA.ok : ValueA → Bool
  | .rat q => q.ok
  | .sqrt s q => (decide (s = -1) || decide (s = 0) || decide (s = 1)) && decide (0 ≤ q.num) && q.ok

def OutcomeA.ok : OutcomeA → Bool
  | .checked _ x _ _ => x.ok
  | .undefined _ => true

def tailOk (d : List Nat) (cs : List ClaimA) (os : List OutcomeA) : Bool :=
  bytesOk d && decide (d.length ≤ MAXD) && decide (0 < cs.length) && decide (cs.length ≤ 256) &&
    decide (os.length = cs.length) && cs.all ClaimA.ok && os.all OutcomeA.ok

/-! ## 6. The parser -/

/-- A parser returns a value and the rest of the input. -/
abbrev P (α : Type) := List Nat → Option (α × List Nat)

def startsWith (t s : List Nat) : Bool := decide (s.take t.length = t)

def pureP {α : Type} (a : α) : P α := fun s => some (a, s)

def failP {α : Type} : P α := fun _ => none

def seqP {α β : Type} (p : P α) (q : α → P β) : P β := fun s =>
  match p s with
  | none => none
  | some (a, r) => q a r

def litP {α : Type} (t : List Nat) (p : P α) : P α := fun s =>
  if startsWith t s then p (s.drop t.length) else none

def optP {α : Type} : Option α → P α
  | none => failP
  | some a => pureP a

/-- A decimal numeral (the canonical spelling is enforced by the final comparison). -/
def natP : P Nat := fun s =>
  if (s.takeWhile isDig).isEmpty then none else some (decVal (s.takeWhile isDig), s.drop (s.takeWhile isDig).length)

def intP : P Int := fun s =>
  if startsWith [45] s then seqP natP (fun n => pureP (-(n : Int))) (s.drop 1)
  else seqP natP (fun n => pureP (n : Int)) s

/-- A word of letters (possibly empty). -/
def nameP : P (List Nat) := fun s => some (s.takeWhile isAlpha, s.drop (s.takeWhile isAlpha).length)

def natsTail : Nat → P (List Nat)
  | 0 => pureP []
  | f + 1 => fun s =>
    if startsWith tComma s then seqP natP (fun n => seqP (natsTail f) (fun ns => pureP (n :: ns))) (s.drop 2)
    else some ([], s)

def bytesP : P (List Nat) := fun s =>
  if startsWith tBq s then
    litP [34] (pureP ((s.drop 3).takeWhile isSafe)) ((s.drop 3).drop ((s.drop 3).takeWhile isSafe).length)
  else if startsWith [91] s then
    seqP natP (fun n r => seqP (natsTail r.length) (fun ns => litP [93] (pureP (n :: ns))) r) (s.drop 1)
  else none

def listTail {α : Type} (p : P α) : Nat → P (List α)
  | 0 => pureP []
  | f + 1 => fun s =>
    if startsWith tComma s then seqP p (fun a => seqP (listTail p f) (fun as => pureP (a :: as))) (s.drop 2)
    else some ([], s)

def listP {α : Type} (p : P α) : P (List α) := fun s =>
  if startsWith [91, 93] s then some ([], s.drop 2)
  else if startsWith [91] s then
    seqP p (fun a r => seqP (listTail p r.length) (fun as => litP [93] (pureP (a :: as))) r) (s.drop 1)
  else none

def qP : P QLit :=
  litP tRat (seqP intP fun n => litP tRatDiv (seqP natP fun d => litP [41] (pureP ⟨n, d⟩)))

def cmpOf (w : List Nat) : Option Cmp :=
  if w = n_eq then some .eq else if w = n_ne then some .ne else if w = n_lt then some .lt
  else if w = n_le then some .le else if w = n_gt then some .gt else if w = n_ge then some .ge else none

def condP : P CondA := fun s =>
  if startsWith tTextEq s then
    seqP bytesP (fun c => litP tCO (seqP bytesP fun v => litP [41] (pureP (.textEq c v)))) (s.drop tTextEq.length)
  else if startsWith tTextNe s then
    seqP bytesP (fun c => litP tCO (seqP bytesP fun v => litP [41] (pureP (.textNe c v)))) (s.drop tTextNe.length)
  else if startsWith tNum s then
    seqP bytesP (fun c => litP tCS (litP [46] (seqP nameP fun w => seqP (optP (cmpOf w)) fun k =>
      litP [32] (seqP qP fun q => pureP (.num c k q))))) (s.drop tNum.length)
  else none

/-- What may follow the name of a statistic. -/
def statArgs (w : List Nat) : P StatA :=
  if w = n_count then pureP .count
  else if w = n_share then litP [32] (seqP (listP condP) fun sub => pureP (.share sub))
  else if w = n_sum then pureP .sum
  else if w = n_mean then pureP .mean
  else if w = n_median then pureP .median
  else if w = n_min then pureP .min
  else if w = n_max then pureP .max
  else if w = n_varSample then pureP .varSample
  else if w = n_sdSample then pureP .sdSample
  else if w = n_sdPop then pureP .sdPop
  else if w = n_sem then pureP .sem
  else if w = n_pearson then litP [32, 40] (seqP bytesP fun x => litP [41] (pureP (.pearson x)))
  else if w = n_olsSlope then litP [32, 40] (seqP bytesP fun x => litP [41] (pureP (.olsSlope x)))
  else if w = n_olsIntercept then litP [32, 40] (seqP bytesP fun x => litP [41] (pureP (.olsIntercept x)))
  else failP

def statP : P StatA := litP [46] (seqP nameP statArgs)

def colP : P (Option (List Nat)) := fun s =>
  if startsWith tNone s then some (none, s.drop tNone.length)
  else litP tSome (seqP bytesP fun c => litP [41] (pureP (some c))) s

def claimP : P ClaimA :=
  litP tC1 (seqP colP fun col => litP tC2 (seqP (listP condP) fun fl => litP tC3 (seqP statP fun st =>
    litP tC4 (seqP (listP bytesP) fun na => litP tC5 (seqP qP fun sc => litP tC6 (seqP bytesP fun rep =>
      litP tC7 (pureP ⟨col, fl, st, na, sc, rep⟩)))))))

def verdictOf (w : List Nat) : Option Verdict :=
  if w = n_consistent then some .consistent else if w = n_inconsistent then some .inconsistent else none

def undefOf (w : List Nat) : Option Undefined :=
  if w = n_sourceNotWellFormed then some .sourceNotWellFormed
  else if w = n_csvMalformed then some .csvMalformed
  else if w = n_columnNotFound then some .columnNotFound
  else if w = n_nonNumericCell then some .nonNumericCell
  else if w = n_emptySelection then some .emptySelection
  else if w = n_degenerate then some .degenerate
  else if w = n_badReportedLiteral then some .badReportedLiteral
  else if w = n_badScale then some .badScale
  else if w = n_missingColumn then some .missingColumn
  else none

def valP : P ValueA := fun s =>
  if startsWith tValRat s then seqP qP (fun q => litP [41] (pureP (.rat q))) (s.drop tValRat.length)
  else litP tValSqrt (seqP intP fun z => litP tColonInt (seqP qP fun q => litP [41] (pureP (.sqrt z q)))) s

def outP : P OutcomeA := fun s =>
  if startsWith tChecked s then
    seqP nameP (fun w => seqP (optP (verdictOf w)) fun v => litP [32] (seqP valP fun x => litP [32]
      (seqP natP fun u => litP [32] (seqP natP fun m => pureP (.checked v x u m))))) (s.drop tChecked.length)
  else litP tUndef (seqP nameP fun w => seqP (optP (undefOf w)) fun r => pureP (.undefined r)) s

def outsTail : Nat → P (List OutcomeA)
  | 0 => pureP []
  | f + 1 => fun s =>
    if startsWith tSepOut s then seqP outP (fun o => seqP (outsTail f) (fun os => pureP (o :: os))) (s.drop tSepOut.length)
    else some ([], s)

def batchP (n : Nat) : P (List OutcomeA) :=
  litP (batchHead n) (seqP outP fun o => seqP (outsTail 255) fun os => litP tBatchEnd (pureP (o :: os)))

def defsP : Nat → Nat → P (List ClaimA)
  | 0, _ => pureP []
  | f + 1, i => fun s =>
    if startsWith (defHead i) s then
      seqP claimP (fun a => litP tNL2 (seqP (defsP f (i + 1)) fun as => pureP (a :: as))) (s.drop (defHead i).length)
    else some ([], s)

/-- Reads the values out of a tail; `parseTail` then insists that the tail is their rendering. -/
def readTail (t : List Nat) : Option (List Nat × List ClaimA × List OutcomeA) :=
  match decode t MAXD with
  | none => none
  | some (d, L) =>
    match defsP 256 0 (t.drop L) with
    | none => none
    | some (cs, r) =>
      match batchP cs.length r with
      | none => none
      | some (os, _) => some (d, cs, os)

/-- **The parser.**  Accepts `t` exactly when `t` is the rendering of valid values, and returns them. -/
def parseTail (t : List Nat) : Option (List Nat × List ClaimA × List OutcomeA) :=
  match readTail t with
  | none => none
  | some (d, cs, os) => if tailOk d cs os = true ∧ renderTail d cs os = t then some (d, cs, os) else none


/-! ## 7. Examples evaluated by the kernel -/

/-- A small tail: data `a,b⏎1,2⏎`, the mean of column `a` reported as `1`. -/
def exClaim : ClaimA := ⟨some [97], [], .mean, [[], [78, 65]], ⟨1, 1⟩, [49]⟩
def exOut : OutcomeA := .checked .consistent (.rat ⟨1, 1⟩) 1 0
def exData : List Nat := [97, 44, 98, 10, 49, 44, 50, 10]

example : tailOk exData [exClaim] [exOut] = true := by decide +kernel
example : parseTail (renderTail exData [exClaim] [exOut]) = some (exData, [exClaim], [exOut]) := by decide +kernel


/-! ## 8. Lemmas: the parser reads what the renderer writes -/

/-- `s` does not begin with a digit, a letter. -/
def noDig (s : List Nat) : Prop := ∀ c, s.head? = some c → isDig c = false
def noAlpha (s : List Nat) : Prop := ∀ c, s.head? = some c → isAlpha c = false

theorem noDig_cons {c : Nat} {s : List Nat} (h : isDig c = false) : noDig (c :: s) := by
  intro x hx; simp at hx; subst hx; exact h
theorem noAlpha_cons {c : Nat} {s : List Nat} (h : isAlpha c = false) : noAlpha (c :: s) := by
  intro x hx; simp at hx; subst hx; exact h

theorem startsWith_nil (s : List Nat) : startsWith [] s = true := by simp [startsWith]
theorem startsWith_cons_nil (a : Nat) (t : List Nat) : startsWith (a :: t) [] = false := by simp [startsWith]
theorem startsWith_cons_cons (a b : Nat) (t s : List Nat) :
    startsWith (a :: t) (b :: s) = (decide (b = a) && startsWith t s) := by
  simp only [startsWith, List.length_cons, List.take_succ_cons, List.cons.injEq]
  by_cases h : b = a <;> simp [h]

theorem startsWith_append (t r : List Nat) : startsWith t (t ++ r) = true := by
  simp [startsWith]

theorem litP_append {α : Type} (t r : List Nat) (p : P α) : litP t p (t ++ r) = p r := by
  simp [litP, startsWith_append]

theorem seqP_some {α β : Type} {p : P α} {s r : List Nat} {a : α} (q : α → P β) (h : p s = some (a, r)) :
    seqP p q s = q a r := by
  simp [seqP, h]

theorem takeWhile_all_true {p : Nat → Bool} {l : List Nat} (hl : ∀ x ∈ l, p x = true) : l.takeWhile p = l := by
  induction l with
  | nil => rfl
  | cons x l ih =>
    have hx : p x = true := hl x (by simp)
    simp [hx, ih (fun z hz => hl z (by simp [hz]))]

theorem takeWhile_append_noStop {p : Nat → Bool} {l r : List Nat} (hl : ∀ x ∈ l, p x = true)
    (hr : ∀ c, r.head? = some c → p c = false) : (l ++ r).takeWhile p = l := by
  cases r with
  | nil => simpa using takeWhile_all_true hl
  | cons y r => exact takeWhile_append_stop hl (hr y rfl)

theorem natP_decStr (n : Nat) {r : List Nat} (hr : noDig r) : natP (decStr n ++ r) = some (n, r) := by
  have h1 : (decStr n ++ r).takeWhile isDig = decStr n := takeWhile_append_noStop (decStr_digits n) hr
  have hne : (decStr n).isEmpty = false := by
    cases h : decStr n with
    | nil => exact absurd h (decStr_ne_nil n)
    | cons _ _ => rfl
  simp [natP, h1, hne, decVal_decStr]

theorem decStr_head (n : Nat) : ∃ c t, decStr n = c :: t ∧ isDig c = true := by
  cases h : decStr n with
  | nil => exact absurd h (decStr_ne_nil n)
  | cons c t => exact ⟨c, t, rfl, decStr_digits n c (by simp [h])⟩

theorem intP_intR (z : Int) {r : List Nat} (hr : noDig r) : intP (intR z ++ r) = some (z, r) := by
  cases z with
  | ofNat n =>
    obtain ⟨c, t, hc, hd⟩ := decStr_head n
    have h45 : startsWith [45] (intR (.ofNat n) ++ r) = false := by
      simp only [intR, hc, List.cons_append, startsWith_cons_cons, startsWith_nil, Bool.and_true]
      have : c ≠ 45 := by intro e; subst e; simp [isDig] at hd
      simp [this]
    simp only [intP, h45, Bool.false_eq_true, if_false]
    rw [show intR (Int.ofNat n) = decStr n from rfl, seqP_some _ (natP_decStr n hr)]
    rfl
  | negSucc n =>
    have h45 : startsWith [45] (intR (.negSucc n) ++ r) = true := by simp [intR, startsWith]
    simp only [intP, h45, if_true]
    have hd : (intR (.negSucc n) ++ r).drop 1 = decStr (n + 1) ++ r := by simp [intR]
    rw [hd, seqP_some _ (natP_decStr (n + 1) hr)]
    rfl

theorem nameP_word {w r : List Nat} (hw : ∀ x ∈ w, isAlpha x = true) (hr : noAlpha r) :
    nameP (w ++ r) = some (w, r) := by
  have h1 : (w ++ r).takeWhile isAlpha = w := takeWhile_append_noStop hw hr
  simp [nameP, h1]

theorem sepTail_length (sep : List Nat) (hs : sep ≠ []) (ys : List (List Nat)) :
    ys.length ≤ (sepTail sep ys).length := by
  induction ys with
  | nil => simp [sepTail]
  | cons y ys ih =>
    have : 0 < sep.length := List.length_pos_iff.mpr hs
    simp [sepTail]; omega

theorem natsTail_sep (xs : List Nat) : ∀ (f : Nat), xs.length ≤ f → ∀ {r : List Nat}, noDig r →
    startsWith tComma r = false → natsTail f (sepTail tComma (xs.map decStr) ++ r) = some (xs, r) := by
  induction xs with
  | nil =>
    intro f _ r _ hc
    cases f with
    | zero => rfl
    | succ f => simp [natsTail, sepTail, hc]
  | cons x xs ih =>
    intro f hf r hd hc
    cases f with
    | zero => simp at hf
    | succ f =>
      have hrest : noDig (sepTail tComma (xs.map decStr) ++ r) := by
        cases xs with
        | nil => simpa [sepTail] using hd
        | cons y ys => exact noDig_cons (by decide)
      have e : sepTail tComma ((x :: xs).map decStr) ++ r = tComma ++ (decStr x ++ (sepTail tComma (xs.map decStr) ++ r)) := by
        simp [sepTail, List.append_assoc]
      rw [e]
      simp only [natsTail, startsWith_append, if_true]
      have hdrop : (tComma ++ (decStr x ++ (sepTail tComma (xs.map decStr) ++ r))).drop 2 =
          decStr x ++ (sepTail tComma (xs.map decStr) ++ r) := by simp [tComma]
      rw [hdrop, seqP_some _ (natP_decStr x hrest), seqP_some _ (ih f (by simp at hf; omega) hd hc)]
      rfl

theorem isSafe_quote : isSafe 34 = false := by decide

theorem bytesP_bytesR (s r : List Nat) : bytesP (bytesR s ++ r) = some (s, r) := by
  by_cases hs : s.all isSafe = true
  · have hsafe : ∀ x ∈ s, isSafe x = true := by simpa using hs
    have e : bytesR s ++ r = tBq ++ (s ++ (34 :: r)) := by simp [bytesR, hs, List.append_assoc]
    rw [e]
    simp only [bytesP, startsWith_append, if_true]
    have hd : (tBq ++ (s ++ (34 :: r))).drop 3 = s ++ (34 :: r) := by simp [tBq]
    rw [hd, takeWhile_append_stop hsafe isSafe_quote, List.drop_left]
    exact litP_append [34] r (pureP s)
  · cases s with
    | nil => simp at hs
    | cons x xs =>
      have hs' : (x :: xs).all isSafe = false := by simpa using hs
      have e : bytesR (x :: xs) ++ r = 91 :: (decStr x ++ (sepTail tComma (xs.map decStr) ++ (93 :: r))) := by
        simp [bytesR, hs', sepBy, List.append_assoc]
      rw [e]
      have hbq : startsWith tBq (91 :: (decStr x ++ (sepTail tComma (xs.map decStr) ++ (93 :: r)))) = false := by
        simp [tBq, startsWith_cons_cons]
      have h91 : startsWith [91] (91 :: (decStr x ++ (sepTail tComma (xs.map decStr) ++ (93 :: r)))) = true := by
        simp [startsWith]
      simp only [bytesP, hbq, h91, Bool.false_eq_true, if_false, if_true, List.drop_succ_cons, List.drop_zero]
      have hrest : noDig (sepTail tComma (xs.map decStr) ++ (93 :: r)) := by
        cases xs with
        | nil => exact noDig_cons (by decide)
        | cons y ys => exact noDig_cons (by decide)
      rw [seqP_some _ (natP_decStr x hrest)]
      have hfuel : xs.length ≤ (sepTail tComma (xs.map decStr) ++ (93 :: r)).length := by
        have := sepTail_length tComma (by decide) (xs.map decStr)
        simp at this ⊢; omega
      rw [seqP_some _ (natsTail_sep xs _ hfuel (noDig_cons (by decide)) (by simp [tComma, startsWith_cons_cons]))]
      exact litP_append [93] r (pureP (x :: xs))


theorem noDig_of_head {t : List Nat} (s : List Nat) {c : Nat} (ht : t.head? = some c) (hc : isDig c = false) :
    noDig (t ++ s) := by
  cases t with
  | nil => simp at ht
  | cons x t => simp at ht; subst ht; exact noDig_cons hc

theorem noAlpha_of_head {t : List Nat} (s : List Nat) {c : Nat} (ht : t.head? = some c) (hc : isAlpha c = false) :
    noAlpha (t ++ s) := by
  cases t with
  | nil => simp at ht
  | cons x t => simp at ht; subst ht; exact noAlpha_cons hc

theorem listTail_sep {α : Type} (p : P α) (rd : α → List Nat)
    (hp : ∀ (x : α) (r : List Nat), p (rd x ++ r) = some (x, r)) (xs : List α) :
    ∀ (f : Nat), xs.length ≤ f → ∀ {r : List Nat}, startsWith tComma r = false →
      listTail p f (sepTail tComma (xs.map rd) ++ r) = some (xs, r) := by
  induction xs with
  | nil =>
    intro f _ r hc
    cases f with
    | zero => rfl
    | succ f => simp [listTail, sepTail, hc]
  | cons x xs ih =>
    intro f hf r hc
    cases f with
    | zero => simp at hf
    | succ f =>
      have e : sepTail tComma ((x :: xs).map rd) ++ r = tComma ++ (rd x ++ (sepTail tComma (xs.map rd) ++ r)) := by
        simp [sepTail, List.append_assoc]
      rw [e]
      simp only [listTail, startsWith_append, if_true]
      have hdrop : (tComma ++ (rd x ++ (sepTail tComma (xs.map rd) ++ r))).drop 2 =
          rd x ++ (sepTail tComma (xs.map rd) ++ r) := by simp [tComma]
      rw [hdrop, seqP_some _ (hp x _), seqP_some _ (ih f (by simp at hf; omega) hc)]
      rfl

theorem listP_listR {α : Type} (p : P α) (rd : α → List Nat)
    (hp : ∀ (x : α) (r : List Nat), p (rd x ++ r) = some (x, r))
    (hhead : ∀ x : α, ∃ c t, rd x = c :: t ∧ c ≠ 93) (xs : List α) (r : List Nat) :
    listP p (listR (xs.map rd) ++ r) = some (xs, r) := by
  cases xs with
  | nil => simp [listP, listR, sepBy, startsWith]
  | cons x xs =>
    obtain ⟨c, t, hct, hc93⟩ := hhead x
    have e : listR ((x :: xs).map rd) ++ r = 91 :: (rd x ++ (sepTail tComma (xs.map rd) ++ (93 :: r))) := by
      simp [listR, sepBy, List.append_assoc]
    rw [e]
    have h1 : startsWith [91, 93] (91 :: (rd x ++ (sepTail tComma (xs.map rd) ++ (93 :: r)))) = false := by
      rw [hct]; simp [startsWith_cons_cons, hc93]
    have h2 : startsWith [91] (91 :: (rd x ++ (sepTail tComma (xs.map rd) ++ (93 :: r)))) = true := by
      simp [startsWith]
    simp only [listP, h1, h2, Bool.false_eq_true, if_false, if_true, List.drop_succ_cons, List.drop_zero]
    rw [seqP_some _ (hp x _)]
    have hfuel : xs.length ≤ (sepTail tComma (xs.map rd) ++ (93 :: r)).length := by
      have := sepTail_length tComma (by decide) (xs.map rd)
      simp at this ⊢; omega
    rw [seqP_some _ (listTail_sep p rd hp xs _ hfuel (by simp [tComma, startsWith_cons_cons]))]
    exact litP_append [93] r (pureP (x :: xs))

theorem qP_qR (q : QLit) (r : List Nat) : qP (qR q ++ r) = some (q, r) := by
  have e : qR q ++ r = tRat ++ (intR q.num ++ (tRatDiv ++ (decStr q.den ++ ([41] ++ r)))) := by
    simp only [qR, List.append_assoc]
  rw [e]
  have h1 := intP_intR q.num (noDig_of_head (decStr q.den ++ ([41] ++ r)) (t := tRatDiv) (c := 32) rfl (by decide))
  have h2 := natP_decStr q.den (r := [41] ++ r) (noDig_cons (by decide))
  simp only [qP, litP_append, seqP, h1, h2, pureP]

theorem bytesR_head (s : List Nat) : ∃ c t, bytesR s = c :: t ∧ c ≠ 93 ∧ c ≠ 46 := by
  unfold bytesR
  split
  · exact ⟨98, _, rfl, by decide, by decide⟩
  · exact ⟨91, _, rfl, by decide, by decide⟩

theorem condR_head (c : CondA) : ∃ x t, condR c = x :: t ∧ x ≠ 93 := by
  cases c <;> exact ⟨46, _, rfl, by decide⟩

theorem cmpOf_cmpName (k : Cmp) : cmpOf (cmpName k) = some k := by
  cases k <;> decide

theorem cmpName_alpha (k : Cmp) : ∀ x ∈ cmpName k, isAlpha x = true := by
  cases k <;> decide

theorem condP_condR (c : CondA) (r : List Nat) : condP (condR c ++ r) = some (c, r) := by
  cases c with
  | textEq col val =>
    have e : condR (.textEq col val) ++ r = tTextEq ++ (bytesR col ++ (tCO ++ (bytesR val ++ ([41] ++ r)))) := by
      simp only [condR, List.append_assoc]
    rw [e]
    simp only [condP, startsWith_append, if_true, List.drop_left, seqP, bytesP_bytesR, litP_append, pureP]
  | textNe col val =>
    have e : condR (.textNe col val) ++ r = tTextNe ++ (bytesR col ++ (tCO ++ (bytesR val ++ ([41] ++ r)))) := by
      simp only [condR, List.append_assoc]
    rw [e]
    have h1 : startsWith tTextEq (tTextNe ++ (bytesR col ++ (tCO ++ (bytesR val ++ ([41] ++ r))))) = false := by
      simp [tTextEq, tTextNe, startsWith_cons_cons]
    simp only [condP, h1, Bool.false_eq_true, if_false, startsWith_append, if_true, List.drop_left, seqP,
      bytesP_bytesR, litP_append, pureP]
  | num col k q =>
    have e : condR (.num col k q) ++ r = tNum ++ (bytesR col ++ (tCS ++ ([46] ++ (cmpName k ++ ([32] ++ (qR q ++ r)))))) := by
      simp [condR, List.append_assoc]
    rw [e]
    have h1 : startsWith tTextEq (tNum ++ (bytesR col ++ (tCS ++ ([46] ++ (cmpName k ++ ([32] ++ (qR q ++ r))))))) = false := by
      simp [tTextEq, tNum, startsWith_cons_cons]
    have h2 : startsWith tTextNe (tNum ++ (bytesR col ++ (tCS ++ ([46] ++ (cmpName k ++ ([32] ++ (qR q ++ r))))))) = false := by
      simp [tTextNe, tNum, startsWith_cons_cons]
    have h3 := nameP_word (cmpName_alpha k) (r := [32] ++ (qR q ++ r)) (noAlpha_cons (by decide))
    simp only [condP, h1, h2, Bool.false_eq_true, if_false, startsWith_append, if_true, List.drop_left, seqP,
      bytesP_bytesR, litP_append, h3, cmpOf_cmpName, optP, pureP, qP_qR]


theorem statP_plain {w : List Nat} {res : StatA} {r : List Nat} (hw : ∀ x ∈ w, isAlpha x = true) (hr : noAlpha r)
    (ha : statArgs w = pureP res) : statP ([46] ++ (w ++ r)) = some (res, r) := by
  simp only [statP, litP_append, seqP, nameP_word hw hr, ha, pureP]

theorem statP_statR (st : StatA) (r : List Nat) (hr : noAlpha r) : statP (statR st ++ r) = some (st, r) := by
  cases st with
  | count => exact statP_plain (w := n_count) (res := .count) (by decide) hr (by simp [statArgs, n_count])
  | sum => exact statP_plain (w := n_sum) (res := .sum) (by decide) hr (by simp [statArgs, n_count, n_share, n_sum])
  | mean => exact statP_plain (w := n_mean) (res := .mean) (by decide) hr (by simp [statArgs, n_count, n_share, n_sum, n_mean])
  | median => exact statP_plain (w := n_median) (res := .median) (by decide) hr (by simp [statArgs, n_count, n_share, n_sum, n_mean, n_median])
  | min => exact statP_plain (w := n_min) (res := .min) (by decide) hr (by simp [statArgs, n_count, n_share, n_sum, n_mean, n_median, n_min])
  | max => exact statP_plain (w := n_max) (res := .max) (by decide) hr (by simp [statArgs, n_count, n_share, n_sum, n_mean, n_median, n_min, n_max])
  | varSample => exact statP_plain (w := n_varSample) (res := .varSample) (by decide) hr (by simp [statArgs, n_count, n_share, n_sum, n_mean, n_median, n_min, n_max, n_varSample])
  | sdSample => exact statP_plain (w := n_sdSample) (res := .sdSample) (by decide) hr (by simp [statArgs, n_count, n_share, n_sum, n_mean, n_median, n_min, n_max, n_varSample, n_sdSample])
  | sdPop => exact statP_plain (w := n_sdPop) (res := .sdPop) (by decide) hr (by simp [statArgs, n_count, n_share, n_sum, n_mean, n_median, n_min, n_max, n_varSample, n_sdSample, n_sdPop])
  | sem => exact statP_plain (w := n_sem) (res := .sem) (by decide) hr (by simp [statArgs, n_count, n_share, n_sum, n_mean, n_median, n_min, n_max, n_varSample, n_sdSample, n_sdPop, n_sem])
  | share sub =>
    have e : statR (.share sub) ++ r = [46] ++ (n_share ++ ([32] ++ (listR (sub.map condR) ++ r))) := by
      simp [statR, List.append_assoc]
    rw [e]
    have hn := nameP_word (w := n_share) (r := [32] ++ (listR (sub.map condR) ++ r)) (by decide) (noAlpha_cons (by decide))
    have ha : statArgs n_share = litP [32] (seqP (listP condP) fun sub => pureP (.share sub)) := by
      simp [statArgs, n_count, n_share]
    have hl := listP_listR condP condR condP_condR condR_head sub r
    simp only [statP, litP_append, seqP, hn, ha, hl, pureP]
  | pearson x =>
    have e : statR (.pearson x) ++ r = [46] ++ (n_pearson ++ ([32, 40] ++ (bytesR x ++ ([41] ++ r)))) := by
      simp [statR, List.append_assoc]
    rw [e]
    have hn := nameP_word (w := n_pearson) (r := [32, 40] ++ (bytesR x ++ ([41] ++ r))) (by decide) (noAlpha_cons (by decide))
    have ha : statArgs n_pearson = litP [32, 40] (seqP bytesP fun x => litP [41] (pureP (.pearson x))) := by
      simp [statArgs, n_count, n_share, n_sum, n_mean, n_median, n_min, n_max, n_varSample, n_sdSample, n_sdPop, n_sem,
        n_pearson]
    simp only [statP, litP_append, seqP, hn, ha, bytesP_bytesR, pureP]
  | olsSlope x =>
    have e : statR (.olsSlope x) ++ r = [46] ++ (n_olsSlope ++ ([32, 40] ++ (bytesR x ++ ([41] ++ r)))) := by
      simp [statR, List.append_assoc]
    rw [e]
    have hn := nameP_word (w := n_olsSlope) (r := [32, 40] ++ (bytesR x ++ ([41] ++ r))) (by decide) (noAlpha_cons (by decide))
    have ha : statArgs n_olsSlope = litP [32, 40] (seqP bytesP fun x => litP [41] (pureP (.olsSlope x))) := by
      simp [statArgs, n_count, n_share, n_sum, n_mean, n_median, n_min, n_max, n_varSample, n_sdSample, n_sdPop, n_sem,
        n_pearson, n_olsSlope]
    simp only [statP, litP_append, seqP, hn, ha, bytesP_bytesR, pureP]
  | olsIntercept x =>
    have e : statR (.olsIntercept x) ++ r = [46] ++ (n_olsIntercept ++ ([32, 40] ++ (bytesR x ++ ([41] ++ r)))) := by
      simp [statR, List.append_assoc]
    rw [e]
    have hn := nameP_word (w := n_olsIntercept) (r := [32, 40] ++ (bytesR x ++ ([41] ++ r))) (by decide)
      (noAlpha_cons (by decide))
    have ha : statArgs n_olsIntercept = litP [32, 40] (seqP bytesP fun x => litP [41] (pureP (.olsIntercept x))) := by
      simp [statArgs, n_count, n_share, n_sum, n_mean, n_median, n_min, n_max, n_varSample, n_sdSample, n_sdPop, n_sem,
        n_pearson, n_olsSlope, n_olsIntercept]
    simp only [statP, litP_append, seqP, hn, ha, bytesP_bytesR, pureP]

theorem colP_colR (c : Option (List Nat)) (r : List Nat) : colP (colR c ++ r) = some (c, r) := by
  cases c with
  | none => simp [colP, colR, startsWith_append]
  | some x =>
    have e : colR (some x) ++ r = tSome ++ (bytesR x ++ ([41] ++ r)) := by simp only [colR, List.append_assoc]
    rw [e]
    have h1 : startsWith tNone (tSome ++ (bytesR x ++ ([41] ++ r))) = false := by
      simp [tNone, tSome, startsWith_cons_cons]
    simp only [colP, h1, Bool.false_eq_true, if_false, litP_append, seqP, bytesP_bytesR, pureP]

theorem claimP_claimR (a : ClaimA) (r : List Nat) : claimP (claimR a ++ r) = some (a, r) := by
  have e : claimR a ++ r = tC1 ++ (colR a.column ++ (tC2 ++ (listR (a.filter.map condR) ++ (tC3 ++ (statR a.stat ++
      (tC4 ++ (listR (a.naTokens.map bytesR) ++ (tC5 ++ (qR a.scale ++ (tC6 ++ (bytesR a.reported ++ (tC7 ++ r)))))))))))) := by
    simp only [claimR, List.append_assoc]
  rw [e]
  have hs := statP_statR a.stat (tC4 ++ (listR (a.naTokens.map bytesR) ++ (tC5 ++ (qR a.scale ++ (tC6 ++
    (bytesR a.reported ++ (tC7 ++ r))))))) (noAlpha_of_head _ (t := tC4) (c := 44) rfl (by decide))
  have hf := listP_listR condP condR condP_condR condR_head a.filter
  have hn := listP_listR bytesP bytesR bytesP_bytesR
    (fun s => by obtain ⟨c, t, h, h93, _⟩ := bytesR_head s; exact ⟨c, t, h, h93⟩) a.naTokens
  simp only [claimP, litP_append, seqP, colP_colR, hf, hs, hn, qP_qR, bytesP_bytesR, pureP]

theorem verdictOf_verdictName (v : Verdict) : verdictOf (verdictName v) = some v := by
  cases v <;> decide

theorem verdictName_alpha (v : Verdict) : ∀ x ∈ verdictName v, isAlpha x = true := by
  cases v <;> decide

theorem undefOf_undefName (u : Undefined) : undefOf (undefName u) = some u := by
  cases u <;> decide

theorem undefName_alpha (u : Undefined) : ∀ x ∈ undefName u, isAlpha x = true := by
  cases u <;> decide

theorem valP_valR (x : ValueA) (r : List Nat) : valP (valR x ++ r) = some (x, r) := by
  cases x with
  | rat q =>
    have e : valR (.rat q) ++ r = tValRat ++ (qR q ++ ([41] ++ r)) := by simp only [valR, List.append_assoc]
    rw [e]
    simp only [valP, startsWith_append, if_true, List.drop_left, seqP, qP_qR, litP_append, pureP]
  | sqrt z q =>
    have e : valR (.sqrt z q) ++ r = tValSqrt ++ (intR z ++ (tColonInt ++ (qR q ++ ([41] ++ r)))) := by
      simp only [valR, List.append_assoc]
    rw [e]
    have h1 : startsWith tValRat (tValSqrt ++ (intR z ++ (tColonInt ++ (qR q ++ ([41] ++ r))))) = false := by
      simp [tValRat, tValSqrt, startsWith_cons_cons]
    have h2 := intP_intR z (noDig_of_head (qR q ++ ([41] ++ r)) (t := tColonInt) (c := 32) rfl (by decide))
    simp only [valP, h1, Bool.false_eq_true, if_false, litP_append, seqP, h2, qP_qR, pureP]

theorem outP_outR (o : OutcomeA) (r : List Nat) (hd : noDig r) (ha : noAlpha r) : outP (outR o ++ r) = some (o, r) := by
  cases o with
  | checked v x u m =>
    have e : outR (.checked v x u m) ++ r =
        tChecked ++ (verdictName v ++ ([32] ++ (valR x ++ ([32] ++ (decStr u ++ ([32] ++ (decStr m ++ r))))))) := by
      simp [outR, List.append_assoc]
    rw [e]
    have hn := nameP_word (verdictName_alpha v) (r := [32] ++ (valR x ++ ([32] ++ (decStr u ++ ([32] ++ (decStr m ++ r))))))
      (noAlpha_cons (by decide))
    have hu := natP_decStr u (r := [32] ++ (decStr m ++ r)) (noDig_cons (by decide))
    have hm := natP_decStr m hd
    simp only [outP, startsWith_append, if_true, List.drop_left, seqP, hn, verdictOf_verdictName, optP, pureP,
      litP_append, valP_valR, hu, hm]
  | undefined u =>
    have e : outR (.undefined u) ++ r = tUndef ++ (undefName u ++ r) := by simp only [outR, List.append_assoc]
    rw [e]
    have h1 : startsWith tChecked (tUndef ++ (undefName u ++ r)) = false := by
      simp [tChecked, tUndef, startsWith_cons_cons]
    have hn := nameP_word (undefName_alpha u) ha
    simp only [outP, h1, Bool.false_eq_true, if_false, litP_append, seqP, hn, undefOf_undefName, optP, pureP]


theorem sepTail_out_head (os : List OutcomeA) {r : List Nat} (hd : noDig r) (ha : noAlpha r) :
    noDig (sepTail tSepOut (os.map outR) ++ r) ∧ noAlpha (sepTail tSepOut (os.map outR) ++ r) := by
  cases os with
  | nil => simpa [sepTail] using And.intro hd ha
  | cons o os =>
    have e : sepTail tSepOut ((o :: os).map outR) ++ r = tSepOut ++ (outR o ++ (sepTail tSepOut (os.map outR) ++ r)) := by
      simp [sepTail, List.append_assoc]
    rw [e]
    exact ⟨noDig_of_head _ (t := tSepOut) (c := 44) rfl (by decide), noAlpha_of_head _ (t := tSepOut) (c := 44) rfl (by decide)⟩

theorem outsTail_sep (os : List OutcomeA) : ∀ (f : Nat), os.length ≤ f → ∀ {r : List Nat}, noDig r → noAlpha r →
    startsWith tSepOut r = false → outsTail f (sepTail tSepOut (os.map outR) ++ r) = some (os, r) := by
  induction os with
  | nil =>
    intro f _ r _ _ hc
    cases f with
    | zero => rfl
    | succ f => simp [outsTail, sepTail, hc]
  | cons o os ih =>
    intro f hf r hd ha hc
    cases f with
    | zero => simp at hf
    | succ f =>
      have e : sepTail tSepOut ((o :: os).map outR) ++ r = tSepOut ++ (outR o ++ (sepTail tSepOut (os.map outR) ++ r)) := by
        simp [sepTail, List.append_assoc]
      rw [e]
      obtain ⟨hd', ha'⟩ := sepTail_out_head os hd ha
      simp only [outsTail, startsWith_append, if_true, List.drop_left]
      rw [seqP_some _ (outP_outR o _ hd' ha'), seqP_some _ (ih f (by simp at hf; omega) hd ha hc)]
      rfl

theorem batchP_batchR (n : Nat) (os : List OutcomeA) (hne : os ≠ []) (hlen : os.length ≤ 256) (r : List Nat) :
    batchP n (batchR n os ++ r) = some (os, r) := by
  cases os with
  | nil => exact absurd rfl hne
  | cons o os =>
    have e : batchR n (o :: os) ++ r = batchHead n ++ (outR o ++ (sepTail tSepOut (os.map outR) ++ (tBatchEnd ++ r))) := by
      simp [batchR, sepBy, List.append_assoc]
    rw [e]
    have hE1 : noDig (tBatchEnd ++ r) := noDig_of_head r (t := tBatchEnd) (c := 93) rfl (by decide)
    have hE2 : noAlpha (tBatchEnd ++ r) := noAlpha_of_head r (t := tBatchEnd) (c := 93) rfl (by decide)
    have hE3 : startsWith tSepOut (tBatchEnd ++ r) = false := by simp [tSepOut, tBatchEnd, startsWith_cons_cons]
    obtain ⟨hd', ha'⟩ := sepTail_out_head os hE1 hE2
    have ho := outP_outR o _ hd' ha'
    have hos := outsTail_sep os 255 (by simp at hlen; omega) hE1 hE2 hE3
    simp only [batchP, litP_append, seqP, ho, hos, pureP]

theorem defHead_ne_tBatch (i : Nat) (x : List Nat) : startsWith (defHead i) (tBatch ++ x) = false := by
  simp [defHead, tDefC, tBatch, startsWith_cons_cons]

theorem defsP_defsR (cs : List ClaimA) : ∀ (f i : Nat), cs.length ≤ f → ∀ {r : List Nat},
    startsWith (defHead (i + cs.length)) r = false → defsP f i (defsR i cs ++ r) = some (cs, r) := by
  induction cs with
  | nil =>
    intro f i _ r hr
    cases f with
    | zero => rfl
    | succ f => simp only [List.length_nil, Nat.add_zero] at hr; simp [defsP, defsR, hr]
  | cons a as ih =>
    intro f i hf r hr
    cases f with
    | zero => simp at hf
    | succ f =>
      have e : defsR i (a :: as) ++ r = defHead i ++ (claimR a ++ (tNL2 ++ (defsR (i + 1) as ++ r))) := by
        simp [defsR, List.append_assoc]
      rw [e]
      simp only [defsP, startsWith_append, if_true, List.drop_left]
      have hidx : i + 1 + as.length = i + (a :: as).length := by simp; omega
      have h2 := ih f (i + 1) (by simp at hf; omega) (r := r) (by rw [hidx]; exact hr)
      rw [seqP_some _ (claimP_claimR a _)]
      simp only [litP_append, seqP, h2, pureP]

/-! ## 9. Main theorems -/

theorem tailOk_parts {d : List Nat} {cs : List ClaimA} {os : List OutcomeA} (h : tailOk d cs os = true) :
    (∀ x ∈ d, x < 256) ∧ d.length ≤ MAXD ∧ 0 < cs.length ∧ cs.length ≤ 256 ∧ os.length = cs.length := by
  simp only [tailOk, Bool.and_eq_true, decide_eq_true_eq] at h
  obtain ⟨⟨⟨⟨⟨⟨hb, hm⟩, h0⟩, h256⟩, hl⟩, _⟩, _⟩ := h
  exact ⟨by simpa [bytesOk] using hb, hm, h0, h256, hl⟩

theorem readTail_renderTail {d : List Nat} {cs : List ClaimA} {os : List OutcomeA} (hv : tailOk d cs os = true) :
    readTail (renderTail d cs os) = some (d, cs, os) := by
  obtain ⟨hb, hm, h0, h256, hl⟩ := tailOk_parts hv
  have e : renderTail d cs os = canon d ++ (defsR 0 cs ++ (batchR cs.length os ++ thmsR 0 os)) := by
    simp only [renderTail, List.append_assoc]
  have hdec := decode_canon d (defsR 0 cs ++ (batchR cs.length os ++ thmsR 0 os)) MAXD hb hm hm
  have hbh : startsWith (defHead (0 + cs.length)) (batchR cs.length os ++ thmsR 0 os) = false := by
    simp only [batchR, batchHead, List.append_assoc]; exact defHead_ne_tBatch _ _
  have hdefs := defsP_defsR cs 256 0 h256 hbh
  have hne : os ≠ [] := by intro h; subst h; simp at hl; omega
  have hbat := batchP_batchR cs.length os hne (by omega) (thmsR 0 os)
  rw [e]
  simp only [readTail, hdec, List.drop_left, hdefs, hbat]

/-- **Every valid tail the renderer writes is accepted and parsed back to its values.** -/
theorem parseTail_renderTail {d : List Nat} {cs : List ClaimA} {os : List OutcomeA} (hv : tailOk d cs os = true) :
    parseTail (renderTail d cs os) = some (d, cs, os) := by
  simp [parseTail, readTail_renderTail hv, hv]

/-- **Whatever is accepted is exactly the rendering of what is returned, and valid.** -/
theorem parseTail_sound {t d : List Nat} {cs : List ClaimA} {os : List OutcomeA}
    (h : parseTail t = some (d, cs, os)) : t = renderTail d cs os ∧ tailOk d cs os = true := by
  unfold parseTail at h
  cases hr : readTail t with
  | none => rw [hr] at h; cases h
  | some x =>
    obtain ⟨d', cs', os'⟩ := x
    rw [hr] at h
    simp only at h
    split at h
    · rename_i hc
      cases h
      exact ⟨hc.2.symm, hc.1⟩
    · cases h

/-- **The accepted language is exactly the set of renderings of valid values.** -/
theorem parseTail_iff {t d : List Nat} {cs : List ClaimA} {os : List OutcomeA} :
    parseTail t = some (d, cs, os) ↔ tailOk d cs os = true ∧ t = renderTail d cs os := by
  constructor
  · intro h; exact ⟨(parseTail_sound h).2, (parseTail_sound h).1⟩
  · rintro ⟨hv, rfl⟩; exact parseTail_renderTail hv

/-- **Two different valid values never have the same text.** -/
theorem renderTail_injective {d₁ d₂ : List Nat} {cs₁ cs₂ : List ClaimA} {os₁ os₂ : List OutcomeA}
    (h₁ : tailOk d₁ cs₁ os₁ = true) (h₂ : tailOk d₂ cs₂ os₂ = true)
    (h : renderTail d₁ cs₁ os₁ = renderTail d₂ cs₂ os₂) : d₁ = d₂ ∧ cs₁ = cs₂ ∧ os₁ = os₂ := by
  have e₁ := parseTail_renderTail h₁
  rw [h, parseTail_renderTail h₂] at e₁
  cases e₁
  exact ⟨rfl, rfl, rfl⟩

/-- An accepted tail begins with the canonical header of its data, so `Header.lean` applies to it:
the header's numerals denote a well-formed `Source` whose bytes are exactly `d`. -/
theorem parseTail_header {t d : List Nat} {cs : List ClaimA} {os : List OutcomeA}
    (h : parseTail t = some (d, cs, os)) : decode t MAXD = some (d, (canon d).length) := by
  obtain ⟨ht, hv⟩ := parseTail_sound h
  obtain ⟨hb, hm, -⟩ := tailOk_parts hv
  rw [ht]
  simp only [renderTail, List.append_assoc]
  exact decode_canon d _ MAXD hb hm hm

theorem parseTail_source {t d : List Nat} {cs : List ClaimA} {os : List OutcomeA}
    (h : parseTail t = some (d, cs, os)) :
    (Source.mk (hexValue (hexOf d)) (decVal (decStr d.length))).wellFormed = true ∧
      (Source.mk (hexValue (hexOf d)) (decVal (decStr d.length))).bytes = d := by
  obtain ⟨-, -, -, hw, hb⟩ := accepted_header_denotes_data (parseTail_header h)
  exact ⟨hw, hb⟩


/-! ## 10. What the syntax denotes in the checker -/

/-- The value of the literal `((n : Rat) / d)`. -/
def QLit.val (q : QLit) : Rat := mkRat q.num q.den

def CondA.den : CondA → Cond
  | .textEq c v => .textEq c v
  | .textNe c v => .textNe c v
  | .num c k q => .num c k q.val

def StatA.den : StatA → Stat
  | .count => .count
  | .share sub => .share (sub.map CondA.den)
  | .sum => .sum
  | .mean => .mean
  | .median => .median
  | .min => .min
  | .max => .max
  | .varSample => .varSample
  | .sdSample => .sdSample
  | .sdPop => .sdPop
  | .sem => .sem
  | .pearson x => .pearson x
  | .olsSlope x => .olsSlope x
  | .olsIntercept x => .olsIntercept x

/-- The checker's `Claim` that the text `claimR a` denotes. -/
def ClaimA.den (a : ClaimA) : Claim :=
  { column := a.column, filter := a.filter.map CondA.den, stat := a.stat.den, naTokens := a.naTokens,
    scale := a.scale.val, reported := a.reported }

def ValueA.den : ValueA → Value
  | .rat q => .rat q.val
  | .sqrt s q => .sqrt s q.val

/-- The checker's `Outcome` that the text `outR o` denotes. -/
def OutcomeA.den : OutcomeA → Outcome
  | .checked v x u m => .checked v x.den u m
  | .undefined r => .undefined r

theorem QLit.val_num_den {q : QLit} (h : q.ok = true) : q.val.num = q.num ∧ q.val.den = q.den := by
  simp only [QLit.ok, Bool.and_eq_true, decide_eq_true_eq] at h
  obtain ⟨hpos, hg⟩ := h
  have hd : q.den ≠ 0 := by omega
  have hg' : q.den.gcd q.num.natAbs = 1 := by rw [Nat.gcd_comm]; exact hg
  constructor
  · simp [QLit.val, Rat.num_mkRat, hd, hg']
  · simp [QLit.val, Rat.den_mkRat, hd, hg']

/-- A fraction in lowest terms is determined by its value. -/
theorem QLit.val_inj {q₁ q₂ : QLit} (h₁ : q₁.ok = true) (h₂ : q₂.ok = true) (h : q₁.val = q₂.val) : q₁ = q₂ := by
  obtain ⟨n₁, d₁⟩ := QLit.val_num_den h₁
  obtain ⟨n₂, d₂⟩ := QLit.val_num_den h₂
  rw [h] at n₁ d₁
  cases q₁; cases q₂
  simp only [QLit.mk.injEq]
  exact ⟨n₁.symm.trans n₂, d₁.symm.trans d₂⟩

theorem map_inj_of {α β : Type} (f : α → β) (ok : α → Bool)
    (hf : ∀ a b, ok a = true → ok b = true → f a = f b → a = b) :
    ∀ (xs ys : List α), xs.all ok = true → ys.all ok = true → xs.map f = ys.map f → xs = ys
  | [], [], _, _, _ => rfl
  | [], _ :: _, _, _, h => by simp at h
  | _ :: _, [], _, _, h => by simp at h
  | x :: xs, y :: ys, hx, hy, h => by
    simp only [List.all_cons, Bool.and_eq_true] at hx hy
    simp only [List.map_cons, List.cons.injEq] at h
    rw [hf x y hx.1 hy.1 h.1, map_inj_of f ok hf xs ys hx.2 hy.2 h.2]

theorem CondA.den_inj (c₁ c₂ : CondA) (h₁ : c₁.ok = true) (h₂ : c₂.ok = true) (h : c₁.den = c₂.den) : c₁ = c₂ := by
  cases c₁ with
  | textEq a b => cases c₂ <;> simp_all [CondA.den]
  | textNe a b => cases c₂ <;> simp_all [CondA.den]
  | num a k q =>
    cases c₂ with
    | textEq _ _ => simp [CondA.den] at h
    | textNe _ _ => simp [CondA.den] at h
    | num a' k' q' =>
      simp only [CondA.den, Cond.num.injEq] at h
      obtain ⟨ha, hk, hq⟩ := h
      simp only [CondA.ok, Bool.and_eq_true] at h₁ h₂
      rw [ha, hk, QLit.val_inj h₁.2 h₂.2 hq]

theorem StatA.den_inj (s₁ s₂ : StatA) (h₁ : s₁.ok = true) (h₂ : s₂.ok = true) (h : s₁.den = s₂.den) : s₁ = s₂ := by
  cases s₁ <;> cases s₂ <;> simp only [StatA.den, reduceCtorEq, Stat.share.injEq, Stat.pearson.injEq,
    Stat.olsSlope.injEq, Stat.olsIntercept.injEq] at h <;> try rfl
  all_goals first
    | (subst h; rfl)
    | (simp only [StatA.ok] at h₁ h₂; rw [map_inj_of CondA.den CondA.ok CondA.den_inj _ _ h₁ h₂ h])

theorem ClaimA.den_inj (a₁ a₂ : ClaimA) (h₁ : a₁.ok = true) (h₂ : a₂.ok = true) (h : a₁.den = a₂.den) : a₁ = a₂ := by
  obtain ⟨c₁, f₁, s₁, n₁, q₁, r₁⟩ := a₁
  obtain ⟨c₂, f₂, s₂, n₂, q₂, r₂⟩ := a₂
  simp only [ClaimA.den, Claim.mk.injEq] at h
  obtain ⟨hc, hf, hs, hn, hq, hr⟩ := h
  simp only [ClaimA.ok, Bool.and_eq_true] at h₁ h₂
  obtain ⟨⟨⟨⟨⟨_, hf₁⟩, hs₁⟩, _⟩, hq₁⟩, _⟩ := h₁
  obtain ⟨⟨⟨⟨⟨_, hf₂⟩, hs₂⟩, _⟩, hq₂⟩, _⟩ := h₂
  rw [hc, map_inj_of CondA.den CondA.ok CondA.den_inj _ _ hf₁ hf₂ hf, StatA.den_inj _ _ hs₁ hs₂ hs, hn,
    QLit.val_inj hq₁ hq₂ hq, hr]

theorem ValueA.den_inj (x₁ x₂ : ValueA) (h₁ : x₁.ok = true) (h₂ : x₂.ok = true) (h : x₁.den = x₂.den) : x₁ = x₂ := by
  cases x₁ with
  | rat q =>
    cases x₂ with
    | rat q' =>
      simp only [ValueA.den, Value.rat.injEq] at h
      simp only [ValueA.ok] at h₁ h₂
      rw [QLit.val_inj h₁ h₂ h]
    | sqrt _ _ => simp [ValueA.den] at h
  | sqrt s q =>
    cases x₂ with
    | rat _ => simp [ValueA.den] at h
    | sqrt s' q' =>
      simp only [ValueA.den, Value.sqrt.injEq] at h
      simp only [ValueA.ok, Bool.and_eq_true] at h₁ h₂
      rw [h.1, QLit.val_inj h₁.2 h₂.2 h.2]

theorem OutcomeA.den_inj (o₁ o₂ : OutcomeA) (h₁ : o₁.ok = true) (h₂ : o₂.ok = true) (h : o₁.den = o₂.den) : o₁ = o₂ := by
  cases o₁ with
  | checked v x u m =>
    cases o₂ with
    | checked v' x' u' m' =>
      simp only [OutcomeA.den, Outcome.checked.injEq] at h
      simp only [OutcomeA.ok] at h₁ h₂
      obtain ⟨hv, hx, hu, hm⟩ := h
      rw [hv, ValueA.den_inj _ _ h₁ h₂ hx, hu, hm]
    | undefined _ => simp [OutcomeA.den] at h
  | undefined r =>
    cases o₂ with
    | checked _ _ _ _ => simp [OutcomeA.den] at h
    | undefined r' => simp only [OutcomeA.den, Outcome.undefined.injEq] at h; rw [h]

theorem tailOk_all {d : List Nat} {cs : List ClaimA} {os : List OutcomeA} (h : tailOk d cs os = true) :
    cs.all ClaimA.ok = true ∧ os.all OutcomeA.ok = true := by
  simp only [tailOk, Bool.and_eq_true] at h
  exact ⟨h.1.2, h.2⟩

/-- **One meaning, one text.**  Accepted tails that denote the same data, the same claims and the
same expected outcomes in the checker are the same text: the accepted spelling of a statement about
the checker is unique. -/
theorem same_meaning_same_text {t₁ t₂ d₁ d₂ : List Nat} {cs₁ cs₂ : List ClaimA}
    {os₁ os₂ : List OutcomeA} (h₁ : parseTail t₁ = some (d₁, cs₁, os₁)) (h₂ : parseTail t₂ = some (d₂, cs₂, os₂))
    (hd : d₁ = d₂) (hc : cs₁.map ClaimA.den = cs₂.map ClaimA.den)
    (ho : os₁.map OutcomeA.den = os₂.map OutcomeA.den) : t₁ = t₂ := by
  obtain ⟨ht₁, hv₁⟩ := parseTail_sound h₁
  obtain ⟨ht₂, hv₂⟩ := parseTail_sound h₂
  have hcs := map_inj_of ClaimA.den ClaimA.ok ClaimA.den_inj cs₁ cs₂ (tailOk_all hv₁).1 (tailOk_all hv₂).1 hc
  have hos := map_inj_of OutcomeA.den OutcomeA.ok OutcomeA.den_inj os₁ os₂ (tailOk_all hv₁).2 (tailOk_all hv₂).2 ho
  rw [ht₁, ht₂, hd, hcs, hos]

/-- **The claim theorems of an accepted tail say exactly what its batch theorem says.**  `runAll` on
the denoted claims equals the denoted outcomes iff, for every `i`, `run` on claim `i` equals outcome
`i`, which is the statement of `theorem pcs_claim_<i>`. -/
theorem batch_iff_claims (src : Source) (cs : List ClaimA) (os : List OutcomeA) (hl : os.length = cs.length) :
    runAll src (cs.map ClaimA.den) = os.map OutcomeA.den ↔
      ∀ (i : Nat) (hi : i < cs.length), run src (cs[i]).den = (os[i]'(by omega)).den := by
  rw [runAll_eq_map, List.map_map]
  constructor
  · intro h i hi
    have := congrArg (fun l => l[i]?) h
    simp only [List.getElem?_map] at this
    rw [List.getElem?_eq_getElem hi, List.getElem?_eq_getElem (by omega)] at this
    simpa using this
  · intro h
    apply List.ext_getElem
    · simp [hl]
    · intro i h1 h2
      simp only [List.getElem_map, Function.comp]
      exact h i (by simpa using h1)

/-! ## 11. Negative controls, evaluated by the kernel -/

/-- Replace the first occurrence of `pat` in `s` by `new`. -/
def replaceFirst (pat new : List Nat) : List Nat → List Nat
  | [] => []
  | c :: s => if (c :: s).take pat.length = pat then new ++ (c :: s).drop pat.length else c :: replaceFirst pat new s

def exTail : List Nat := renderTail exData [exClaim] [exOut]

/-- `[97]` for `b "a"`: a byte string that has a quoted spelling, written as numbers. -/
example : parseTail (replaceFirst (b "b \"a\"") (b "[97]") exTail) = none := by decide +kernel
/-- An unreduced fraction. -/
example : parseTail (replaceFirst (b "scale := ((1 : Rat) / 1)") (b "scale := ((2 : Rat) / 2)") exTail) = none := by
  decide +kernel
/-- `-0`. -/
example : parseTail (replaceFirst (b "(.rat ((1 : Rat) / 1))") (b "(.rat ((-0 : Rat) / 1))") exTail) = none := by
  decide +kernel
/-- A leading zero. -/
example : parseTail (replaceFirst (b "(.rat ((1 : Rat) / 1))") (b "(.rat ((01 : Rat) / 1))") exTail) = none := by
  decide +kernel
/-- An extra definition before the claims (where a forged `run` would go). -/
example : parseTail (replaceFirst (b "def pcs_c0") (b "def helper : Nat := 0\n\ndef pcs_c0") exTail) = none := by
  decide +kernel
/-- The forgery of `findings/RUNNER_TAIL_FORGERY.md`: its own type and its own `run`. -/
example : parseTail (canon exData ++ b "structure Decoy where\n  n : Nat\n\ndef pcs_c0 : Decoy := ⟨0⟩\n\n" ++
    b "def run (_ : Source) (_ : Decoy) : Outcome := .checked .consistent (.rat ((999 : Rat) / 1)) 2 0\n\n" ++
    b "theorem pcs_claim_0 : run pcs_src pcs_c0 = .checked .consistent (.rat ((999 : Rat) / 1)) 2 0 :=\n  rfl\n" ++
    b "#print axioms pcs_claim_0\n\n") = none := by decide +kernel
/-- Text after the last theorem. -/
example : parseTail (exTail ++ b "theorem extra : True := trivial\n") = none := by decide +kernel
/-- A comment inside a claim. -/
example : parseTail (replaceFirst (b ",\n    stat := ") (b " -- note\n    stat := ") exTail) = none := by decide +kernel
/-- The claim theorem states another outcome than the batch theorem. -/
example : parseTail (canon exData ++ defsR 0 [exClaim] ++ batchR 1 [exOut] ++
    thmsR 0 [.checked .inconsistent (.rat ⟨1, 1⟩) 1 0]) = none := by decide +kernel
/-- A `√` value with sign 2, a negative radicand, an unknown reason. -/
example : parseTail (renderTail exData [exClaim] [.checked .consistent (.sqrt 2 ⟨1, 1⟩) 1 0]) = none := by decide +kernel
example : parseTail (renderTail exData [exClaim] [.checked .consistent (.sqrt 1 ⟨-1, 1⟩) 1 0]) = none := by decide +kernel
example : parseTail (replaceFirst (b ".checked .consistent (.rat ((1 : Rat) / 1)) 1 0]") (b ".undefined .foo]") exTail) = none := by
  decide +kernel
/-- A byte string with a quote is written as numbers and accepted; the same with `b "…"` is refused. -/
example : parseTail (renderTail exData [{ exClaim with reported := [34] }] [exOut]) =
    some (exData, [{ exClaim with reported := [34] }], [exOut]) := by decide +kernel
example : bytesR [34] = b "[34]" := by decide +kernel
/-- Several claims, a `√` outcome and an undefined one, round trip. -/
example : parseTail (renderTail exData [exClaim, { exClaim with stat := .sdSample }, { exClaim with column := some [122] }]
    [exOut, .checked .inconsistent (.sqrt 1 ⟨1, 2⟩) 2 0, .undefined .columnNotFound]) =
    some (exData, [exClaim, { exClaim with stat := .sdSample }, { exClaim with column := some [122] }],
      [exOut, .checked .inconsistent (.sqrt 1 ⟨1, 2⟩) 2 0, .undefined .columnNotFound]) := by decide +kernel

end PCS.ClaimCheck.Assurance
