/-
PCS ClaimCheck v1 — fixed reference checker for data-derived reported statistics.

RESEARCH SIDECAR. This file is not part of the PCS v0.6 production authority and
grants no production verification authority.

What this file defines
----------------------
A *closed, fixed* executable semantics, written against Lean core only, for one
narrow question:

    Given the exact bytes of a CSV file and a typed claim
    "statistic S of column C over the rows selected by filter F, multiplied by
    unit factor k, was reported as the decimal literal R",
    is R the value obtained by rounding the exact statistic to the precision
    with which R was printed?

Per-claim proof obligations have the single shape

    theorem claim : run src claim = <expected outcome literal> := by decide +kernel

so the Lean kernel itself re-parses the original bytes, selects the rows,
recomputes the statistic in exact rational arithmetic and compares.  No
untrusted party (model, Python, JavaScript) supplies a number that the kernel
takes on faith: an incorrect expected outcome makes the kernel reject.

What this file does NOT establish
---------------------------------
* that the bytes are the data the authors analysed (custody / provenance);
* that the typed claim is a faithful reading of the prose (semantic binding);
* that the statistic supports any scientific interpretation.
Those are separate questions with separate statuses in a ClaimCheck receipt.

Design notes
------------
* Only structural recursion and `Nat`/`Int`/`Rat` arithmetic are used so that
  kernel reduction (`decide +kernel`) terminates quickly.  No `partial`,
  `unsafe`, `implemented_by`, `extern`, `native_decide`, `sorry` or axioms.
* Standard deviations and correlations are irrational in general.  They are
  represented exactly as a *signed square root* `s·√q` with `s ∈ {-1,0,1}` and
  rational `q ≥ 0`, and compared against the reported rounding interval by
  squaring (`sqrtInInterval`).  `formal/real/ClaimCheckReal.lean` proves, with
  Mathlib, that this rational test is equivalent to the real-number statement.
-/

namespace PCS.ClaimCheck

/-! ## 1. Bytes from one big-endian numeral -/

/-- `k` little-endian base-`b` digits of `n`. -/
def digitsLE (b : Nat) : Nat → Nat → List Nat
  | 0, _ => []
  | k + 1, n => (n % b) :: digitsLE b k (n / b)

/-- Append the `k` little-endian base-256 digits of `n` in *big-endian* order in front of `acc`. -/
def pushBytesBE : Nat → Nat → List Nat → List Nat
  | 0, _, acc => acc
  | k + 1, n, acc => pushBytesBE k (n / 256) ((n % 256) :: acc)

/-- Bytes per chunk used when unpacking the numeral.  Any positive value gives the same bytes. -/
def chunk : Nat := 32

def unpackChunks : List Nat → List Nat → List Nat
  | [], acc => acc
  | c :: cs, acc => unpackChunks cs (pushBytesBE chunk c acc)

/-- A source artifact: `len` bytes given as the big-endian numeral `num`
(the numeral is exactly the file's hexadecimal dump). -/
structure Source where
  num : Nat
  len : Nat

/-- The numeral fits in `len` bytes (no bytes are silently dropped). -/
def Source.wellFormed (s : Source) : Bool :=
  Nat.beq (s.num / 256 ^ s.len) 0

/-- The `len` bytes of the source, first byte first. -/
def Source.bytes (s : Source) : List Nat :=
  let nChunks := (s.len + chunk - 1) / chunk
  let all := unpackChunks (digitsLE (256 ^ chunk) nChunks s.num) []
  -- `all` has `nChunks * chunk` bytes; the surplus leading bytes are zero padding.
  all.drop (nChunks * chunk - s.len)

/-! ## 2. Strict CSV (RFC 4180 subset) -/

abbrev Field := List Nat
abbrev Row := List Field

/--
Line-end normalisation: CR LF and a lone CR both become LF.  (This also applies
inside quoted fields; a cell containing a line break can never equal a claim's
text value, a missing-value token or a decimal, so no verdict depends on it.)
-/
def normEol : List Nat → List Nat
  | [] => []
  | 13 :: 10 :: rest => 10 :: normEol rest
  | 13 :: rest => 10 :: normEol rest
  | b :: rest => b :: normEol rest

/--
Byte-level CSV automaton.

modes: 0 = at start of a field, 1 = inside an unquoted field,
       2 = inside a quoted field, 3 = just read a `"` inside a quoted field.
`fld` is the current field reversed, `row` the current row reversed, `acc` the
finished rows reversed.  Rows end at LF (line ends are normalised by `normEol`
first).  Returns `none` on any malformed input (fail closed).
-/
def csvGo : List Nat → Nat → Field → Row → List Row → Option (List Row)
  | [], mode, fld, row, acc =>
    match mode with
    | 0 => match row with
           | [] => some acc.reverse                       -- file ended after a line break
           | _ => some (((fld.reverse :: row).reverse) :: acc).reverse
    | 2 => none                                           -- unterminated quoted field
    | _ => some (((fld.reverse :: row).reverse) :: acc).reverse
  | b :: bs, mode, fld, row, acc =>
    match mode with
    | 0 =>
      if Nat.beq b 34 then csvGo bs 2 [] row acc
      else if Nat.beq b 44 then csvGo bs 0 [] ([] :: row) acc
      else if Nat.beq b 10 then
        match row with
        | [] => none                                      -- blank line
        | _ => csvGo bs 0 [] [] ((([] :: row).reverse) :: acc)
      else csvGo bs 1 [b] row acc
    | 1 =>
      if Nat.beq b 44 then csvGo bs 0 [] (fld.reverse :: row) acc
      else if Nat.beq b 10 then csvGo bs 0 [] [] (((fld.reverse :: row).reverse) :: acc)
      else if Nat.beq b 34 then none                      -- quote inside unquoted field
      else csvGo bs 1 (b :: fld) row acc
    | 2 =>
      if Nat.beq b 34 then csvGo bs 3 fld row acc
      else csvGo bs 2 (b :: fld) row acc
    | _ =>
      if Nat.beq b 34 then csvGo bs 2 (34 :: fld) row acc
      else if Nat.beq b 44 then csvGo bs 0 [] (fld.reverse :: row) acc
      else if Nat.beq b 10 then csvGo bs 0 [] [] (((fld.reverse :: row).reverse) :: acc)
      else none

def stripBom : List Nat → List Nat
  | 239 :: 187 :: 191 :: rest => rest
  | bs => bs

def lengthIs : List α → Nat → Bool
  | [], 0 => true
  | [], _ + 1 => false
  | _ :: _, 0 => false
  | _ :: xs, n + 1 => lengthIs xs n

def allRowsWidth (w : Nat) : List Row → Bool
  | [] => true
  | r :: rs => lengthIs r w && allRowsWidth w rs

/-- A parsed table: header plus rectangular data rows. -/
structure Table where
  header : Row
  rows : List Row

def parseTable (bytes : List Nat) : Option Table :=
  match csvGo (normEol (stripBom bytes)) 0 [] [] [] with
  | some (h :: rs) => if allRowsWidth h.length rs then some ⟨h, rs⟩ else none
  | _ => none

/-! ## 3. Cells -/

def isSpace (b : Nat) : Bool := Nat.beq b 32 || Nat.beq b 9

def dropSpaces : List Nat → List Nat
  | [] => []
  | b :: bs => if isSpace b then dropSpaces bs else b :: bs

/-- Remove leading and trailing ASCII spaces/tabs. -/
def trim (bs : List Nat) : List Nat :=
  (dropSpaces (dropSpaces bs).reverse).reverse

def bytesEq : List Nat → List Nat → Bool
  | [], [] => true
  | a :: as, b :: bs => Nat.beq a b && bytesEq as bs
  | _, _ => false

def memBytes (x : List Nat) : List (List Nat) → Bool
  | [] => false
  | y :: ys => bytesEq x y || memBytes x ys

def isDigit (b : Nat) : Bool := Nat.ble 48 b && Nat.ble b 57

/-- Largest decimal exponent magnitude accepted (keeps kernel work bounded). -/
def maxExp : Nat := 400

/--
Decimal scanner.  phases: 0 integer digits, 1 fraction digits,
2 just after `e`/`E` (sign allowed), 3 exponent digits.
Returns `(mantissa, fractionDigits, exponentNegative, exponent)`.
-/
def decGo : List Nat → Nat → Nat → Nat → Bool → Bool → Nat → Bool →
    Option (Nat × Nat × Bool × Nat)
  | [], phase, mant, frac, md, eneg, e, ed =>
    match phase with
    | 0 => if md then some (mant, frac, false, 0) else none
    | 1 => if md then some (mant, frac, false, 0) else none
    | 2 => none
    | _ => if ed && Nat.ble e maxExp then some (mant, frac, eneg, e) else none
  | b :: bs, phase, mant, frac, md, eneg, e, ed =>
    match phase with
    | 0 =>
      if isDigit b then decGo bs 0 (mant * 10 + (b - 48)) frac true eneg e ed
      else if Nat.beq b 46 then decGo bs 1 mant frac md eneg e ed
      else if (Nat.beq b 101 || Nat.beq b 69) && md then decGo bs 2 mant frac md eneg e ed
      else none
    | 1 =>
      if isDigit b then decGo bs 1 (mant * 10 + (b - 48)) (frac + 1) true eneg e ed
      else if (Nat.beq b 101 || Nat.beq b 69) && md then decGo bs 2 mant frac md eneg e ed
      else none
    | 2 =>
      if Nat.beq b 45 then decGo bs 3 mant frac md true e ed
      else if Nat.beq b 43 then decGo bs 3 mant frac md false e ed
      else if isDigit b then decGo bs 3 mant frac md eneg (b - 48) true
      else none
    | _ =>
      if isDigit b then
        (if Nat.ble e maxExp then decGo bs 3 mant frac md eneg (e * 10 + (b - 48)) true else none)
      else none

/-- `m · 10^(±e) / 10^frac` as an exact rational. -/
def scaleDec (neg : Bool) (mant frac : Nat) (eneg : Bool) (e : Nat) : Rat :=
  let num : Int := if neg then -(Int.ofNat mant) else Int.ofNat mant
  if eneg then mkRat num (10 ^ (frac + e))
  else if Nat.ble frac e then ((num * Int.ofNat (10 ^ (e - frac)) : Int) : Rat)
  else mkRat num (10 ^ (frac - e))

/-- Split an optional leading sign. -/
def splitSign : List Nat → Bool × List Nat
  | 45 :: rest => (true, rest)
  | 43 :: rest => (false, rest)
  | bs => (false, bs)

/-- Exact value of a decimal literal such as `-12.50`, `.5`, `3`, `1.2e-3`. -/
def parseDecimal (bs : List Nat) : Option Rat :=
  match splitSign (trim bs) with
  | (neg, body) =>
    match decGo body 0 0 0 false false 0 false with
    | some (mant, frac, eneg, e) => some (scaleDec neg mant frac eneg e)
    | none => none

/--
A *reported* literal: its exact value together with half a unit in its last
printed place.  `12.50` ↦ `(25/2, 1/200)`, `7` ↦ `(7, 1/2)`, `1.2e-3` ↦ `(3/2500, 1/20000)`.
-/
def parseReported (bs : List Nat) : Option (Rat × Rat) :=
  match splitSign (trim bs) with
  | (neg, body) =>
    match decGo body 0 0 0 false false 0 false with
    | some (mant, frac, eneg, e) =>
      some (scaleDec neg mant frac eneg e, scaleDec false 1 frac eneg e / 2)
    | none => none

/-! ## 4. Claims -/

inductive Cmp where
  | eq | ne | lt | le | gt | ge
  deriving DecidableEq, Repr

def Cmp.holds (c : Cmp) (a b : Rat) : Bool :=
  match c with
  | .eq => decide (a = b)
  | .ne => !decide (a = b)
  | .lt => decide (a < b)
  | .le => decide (a ≤ b)
  | .gt => decide (b < a)
  | .ge => decide (b ≤ a)

/-- One row condition.  Column names and text values are byte strings. -/
inductive Cond where
  /-- trimmed cell bytes equal `val` -/
  | textEq (col : List Nat) (val : List Nat)
  /-- trimmed cell bytes differ from `val` -/
  | textNe (col : List Nat) (val : List Nat)
  /-- cell parses as a decimal `x` with `x cmp val`; a missing (NA) cell fails the condition -/
  | num (col : List Nat) (cmp : Cmp) (val : Rat)
  deriving Repr

inductive Stat where
  /-- number of selected rows -/
  | count
  /-- fraction of selected rows that also satisfy `sub` (use `scale := 100` for a percentage) -/
  | share (sub : List Cond)
  | sum | mean | median | min | max
  /-- variance with denominator `n - 1` -/
  | varSample
  /-- standard deviation with denominator `n - 1` -/
  | sdSample
  /-- standard deviation with denominator `n` -/
  | sdPop
  /-- standard error of the mean: `sdSample / √n` -/
  | sem
  /-- Pearson correlation between the claim column (y) and column `x` -/
  | pearson (x : List Nat)
  /-- least-squares slope of the claim column (y) on column `x` -/
  | olsSlope (x : List Nat)
  /-- least-squares intercept of the claim column (y) on column `x` -/
  | olsIntercept (x : List Nat)
  deriving Repr

structure Claim where
  /-- target column name (ignored by `count`/`share` when `none`) -/
  column : Option (List Nat)
  /-- conjunction of row conditions -/
  filter : List Cond
  stat : Stat
  /-- cells (after trimming) treated as missing values -/
  naTokens : List (List Nat)
  /-- unit factor: the statistic is multiplied by `scale` before comparison (must be positive) -/
  scale : Rat
  /-- the reported literal exactly as printed in the source -/
  reported : List Nat
  deriving Repr

/-! ## 5. Row selection -/

def findCol (name : List Nat) : Row → Nat → Option Nat
  | [], _ => none
  | h :: hs, i => if bytesEq (trim h) name then some i else findCol name hs (i + 1)

def countCol (name : List Nat) : Row → Nat
  | [] => 0
  | h :: hs => (if bytesEq (trim h) name then 1 else 0) + countCol name hs

/-- Index of a column that occurs exactly once in the header. -/
def colIndex (hdr : Row) (name : List Nat) : Option Nat :=
  if Nat.beq (countCol name hdr) 1 then findCol name hdr 0 else none

def cellAt : Row → Nat → Field
  | [], _ => []
  | c :: _, 0 => c
  | _ :: cs, i + 1 => cellAt cs i

/-- Tri-state result of evaluating something on a row. -/
inductive Tri where
  | yes | no | bad
  deriving DecidableEq, Repr

def condRow (hdr : Row) (na : List (List Nat)) (row : Row) : Cond → Tri
  | .textEq col val =>
    match colIndex hdr col with
    | some i => if bytesEq (trim (cellAt row i)) val then .yes else .no
    | none => .bad
  | .textNe col val =>
    match colIndex hdr col with
    | some i => if bytesEq (trim (cellAt row i)) val then .no else .yes
    | none => .bad
  | .num col cmp val =>
    match colIndex hdr col with
    | some i =>
      let cell := trim (cellAt row i)
      if memBytes cell na then .no
      else match parseDecimal cell with
        | some x => if cmp.holds x val then .yes else .no
        | none => .bad
    | none => .bad

def condsRow (hdr : Row) (na : List (List Nat)) (row : Row) : List Cond → Tri
  | [] => .yes
  | c :: cs =>
    match condRow hdr na row c with
    | .yes => condsRow hdr na row cs
    | .no => .no
    | .bad => .bad

/-- Every column named by the conditions occurs exactly once in the header. -/
def condsResolve (hdr : Row) : List Cond → Bool
  | [] => true
  | .textEq col _ :: cs => (colIndex hdr col).isSome && condsResolve hdr cs
  | .textNe col _ :: cs => (colIndex hdr col).isSome && condsResolve hdr cs
  | .num col _ _ :: cs => (colIndex hdr col).isSome && condsResolve hdr cs

/-- Rows satisfying every condition; `none` if any condition is ill-typed on any row. -/
def selectRows (hdr : Row) (na : List (List Nat)) (conds : List Cond) : List Row → Option (List Row)
  | [] => some []
  | r :: rs =>
    match condsRow hdr na r conds, selectRows hdr na conds rs with
    | .yes, some out => some (r :: out)
    | .no, some out => some out
    | _, _ => none

/-- Numeric values of column `i`; missing cells are skipped and counted. -/
def numericCol (na : List (List Nat)) (i : Nat) : List Row → Option (List Rat × Nat)
  | [] => some ([], 0)
  | r :: rs =>
    let cell := trim (cellAt r i)
    match numericCol na i rs with
    | none => none
    | some (xs, k) =>
      if memBytes cell na then some (xs, k + 1)
      else match parseDecimal cell with
        | some x => some (x :: xs, k)
        | none => none

/-- Complete numeric pairs `(x, y)`; a row with either cell missing is skipped and counted. -/
def numericPairs (na : List (List Nat)) (ix iy : Nat) : List Row → Option (List (Rat × Rat) × Nat)
  | [] => some ([], 0)
  | r :: rs =>
    let cx := trim (cellAt r ix)
    let cy := trim (cellAt r iy)
    match numericPairs na ix iy rs with
    | none => none
    | some (ps, k) =>
      if memBytes cx na || memBytes cy na then some (ps, k + 1)
      else match parseDecimal cx, parseDecimal cy with
        | some x, some y => some ((x, y) :: ps, k)
        | _, _ => none

/-- Rows whose cell in column `i` is not missing. -/
def presentCount (na : List (List Nat)) (i : Nat) : List Row → Nat
  | [] => 0
  | r :: rs => (if memBytes (trim (cellAt r i)) na then 0 else 1) + presentCount na i rs

/-! ## 6. Exact statistics -/

def sumQ : List Rat → Rat
  | [] => 0
  | x :: xs => x + sumQ xs

def lenQ (xs : List α) : Rat := (xs.length : Nat)

def meanQ (xs : List Rat) : Rat := sumQ xs / lenQ xs

def minQ : Rat → List Rat → Rat
  | m, [] => m
  | m, x :: xs => minQ (if decide (x < m) then x else m) xs

def maxQ : Rat → List Rat → Rat
  | m, [] => m
  | m, x :: xs => maxQ (if decide (m < x) then x else m) xs

def insertQ (x : Rat) : List Rat → List Rat
  | [] => [x]
  | y :: ys => if decide (x ≤ y) then x :: y :: ys else y :: insertQ x ys

def sortQ : List Rat → List Rat
  | [] => []
  | x :: xs => insertQ x (sortQ xs)

def nthQ : List Rat → Nat → Rat
  | [], _ => 0
  | x :: _, 0 => x
  | _ :: xs, i + 1 => nthQ xs i

/-- Median: middle order statistic, or the mean of the two middle ones. -/
def medianQ (xs : List Rat) : Rat :=
  let s := sortQ xs
  let n := xs.length
  if Nat.beq (n % 2) 1 then nthQ s (n / 2) else (nthQ s (n / 2 - 1) + nthQ s (n / 2)) / 2

/-- Sum of squared deviations from the mean. -/
def ssQ (xs : List Rat) : Rat :=
  let m := meanQ xs
  sumQ (xs.map (fun x => (x - m) * (x - m)))

def sxyQ (ps : List (Rat × Rat)) : Rat :=
  let mx := meanQ (ps.map Prod.fst)
  let my := meanQ (ps.map Prod.snd)
  sumQ (ps.map (fun p => (p.1 - mx) * (p.2 - my)))

/-- An exactly represented statistic value. -/
inductive Value where
  /-- a rational number -/
  | rat (q : Rat)
  /-- `sign · √radicand` with `sign ∈ {-1, 0, 1}` and `radicand ≥ 0` -/
  | sqrt (sign : Int) (radicand : Rat)
  deriving DecidableEq, Repr

/-- Reason codes for a claim whose statistic is undefined on the given bytes. -/
inductive Undefined where
  | sourceNotWellFormed      -- numeral does not fit the stated length
  | csvMalformed             -- not a rectangular strict CSV
  | columnNotFound           -- a named column is absent or duplicated
  | nonNumericCell           -- a needed cell is neither a decimal nor a declared NA token
  | emptySelection           -- too few rows for the statistic
  | degenerate               -- zero variance where a quotient needs it
  | badReportedLiteral       -- the reported literal is not a decimal
  | badScale                 -- unit factor is not positive
  | missingColumn            -- statistic needs a target column but none was given
  deriving DecidableEq, Repr

def signQ (q : Rat) : Int := if decide (0 < q) then 1 else if decide (q < 0) then -1 else 0

/-- The statistic of a claim over selected rows: value, rows used, rows skipped as missing. -/
def statValue (hdr : Row) (na : List (List Nat)) (rows : List Row) (col : Option (List Nat)) :
    Stat → Except Undefined (Value × Nat × Nat)
  | .count =>
    match col with
    | none => .ok (.rat (lenQ rows), rows.length, 0)
    | some c =>
      match colIndex hdr c with
      | none => .error .columnNotFound
      | some i =>
        let n := presentCount na i rows
        .ok (.rat ((n : Nat) : Rat), n, rows.length - n)
  | .share sub =>
    match rows with
    | [] => .error .emptySelection
    | _ =>
      if !condsResolve hdr sub then .error .columnNotFound
      else match selectRows hdr na sub rows with
        | none => .error .nonNumericCell
        | some hit => .ok (.rat (lenQ hit / lenQ rows), rows.length, 0)
  | .pearson xcol => bivariate hdr na rows col xcol 0
  | .olsSlope xcol => bivariate hdr na rows col xcol 1
  | .olsIntercept xcol => bivariate hdr na rows col xcol 2
  | s =>
    match col with
    | none => .error .missingColumn
    | some c =>
      match colIndex hdr c with
      | none => .error .columnNotFound
      | some i =>
        match numericCol na i rows with
        | none => .error .nonNumericCell
        | some (xs, k) =>
          match xs with
          | [] => .error .emptySelection
          | x0 :: rest =>
            let n := xs.length
            match s with
            | .sum => .ok (.rat (sumQ xs), n, k)
            | .mean => .ok (.rat (meanQ xs), n, k)
            | .median => .ok (.rat (medianQ xs), n, k)
            | .min => .ok (.rat (minQ x0 rest), n, k)
            | .max => .ok (.rat (maxQ x0 rest), n, k)
            | .sdPop => .ok (.sqrt 1 (ssQ xs / lenQ xs), n, k)
            | .varSample =>
              match rest with
              | [] => .error .emptySelection
              | _ => .ok (.rat (ssQ xs / (lenQ xs - 1)), n, k)
            | .sdSample =>
              match rest with
              | [] => .error .emptySelection
              | _ => .ok (.sqrt 1 (ssQ xs / (lenQ xs - 1)), n, k)
            | .sem =>
              match rest with
              | [] => .error .emptySelection
              | _ => .ok (.sqrt 1 (ssQ xs / (lenQ xs - 1) / lenQ xs), n, k)
            | _ => .error .missingColumn
where
  /-- `which`: 0 Pearson r, 1 OLS slope, 2 OLS intercept (y = claim column, x = `xcol`). -/
  bivariate (hdr : Row) (na : List (List Nat)) (rows : List Row) (col : Option (List Nat))
      (xcol : List Nat) (which : Nat) : Except Undefined (Value × Nat × Nat) :=
    match col with
    | none => .error .missingColumn
    | some c =>
      match colIndex hdr xcol, colIndex hdr c with
      | some ix, some iy =>
        match numericPairs na ix iy rows with
        | none => .error .nonNumericCell
        | some (ps, k) =>
          match ps with
          | [] => .error .emptySelection
          | [_] => .error .emptySelection
          | _ =>
            let xs := ps.map Prod.fst
            let ys := ps.map Prod.snd
            let sxx := ssQ xs
            let syy := ssQ ys
            let sxy := sxyQ ps
            let n := ps.length
            if decide (sxx = 0) then .error .degenerate
            else match which with
              | 0 =>
                if decide (syy = 0) then .error .degenerate
                else .ok (.sqrt (signQ sxy) (sxy * sxy / (sxx * syy)), n, k)
              | 1 => .ok (.rat (sxy / sxx), n, k)
              | _ => .ok (.rat (meanQ ys - sxy / sxx * meanQ xs), n, k)
      | _, _ => .error .columnNotFound

/-! ## 7. Rounding relation -/

/--
`lo ≤ s·√q ≤ hi`, decided in rational arithmetic (requires `q ≥ 0`, `s ∈ {-1,0,1}`).
`ClaimCheckReal.sqrtInInterval_iff` proves the equivalence with the real-number statement.
-/
def sqrtInInterval (lo hi : Rat) (s : Int) (q : Rat) : Bool :=
  if decide (s = 0) || decide (q = 0) then decide (lo ≤ 0) && decide (0 ≤ hi)
  else if decide (0 < s) then
    (decide (lo ≤ 0) || decide (lo * lo ≤ q)) && (decide (0 ≤ hi) && decide (q ≤ hi * hi))
  else
    (decide (lo ≤ 0) && decide (q ≤ lo * lo)) && (decide (0 ≤ hi) || decide (hi * hi ≤ q))

/-- Does `scale · value` lie in the closed interval `[lo, hi]`? (`scale > 0`.) -/
def Value.within (v : Value) (scale lo hi : Rat) : Bool :=
  match v with
  | .rat q => decide (lo ≤ q * scale) && decide (q * scale ≤ hi)
  | .sqrt s q => sqrtInInterval (lo / scale) (hi / scale) s q

/-! ## 8. The checker -/

inductive Verdict where
  /-- the reported literal equals the exact statistic rounded to the printed precision -/
  | consistent
  /-- it does not -/
  | inconsistent
  deriving DecidableEq, Repr

/-- Everything the kernel establishes about one claim on one byte string. -/
inductive Outcome where
  /-- verdict, exact statistic (before the unit factor), rows used, rows skipped as missing -/
  | checked (verdict : Verdict) (value : Value) (used : Nat) (missing : Nat)
  /-- the statistic is not defined for these bytes -/
  | undefined (reason : Undefined)
  deriving DecidableEq, Repr

def runTable (t : Table) (c : Claim) : Outcome :=
  match parseReported c.reported with
  | none => .undefined .badReportedLiteral
  | some (r, half) =>
    if !decide (0 < c.scale) then .undefined .badScale
    else if !condsResolve t.header c.filter then .undefined .columnNotFound
    else match selectRows t.header c.naTokens c.filter t.rows with
      | none => .undefined .nonNumericCell
      | some rows =>
        match statValue t.header c.naTokens rows c.column c.stat with
        | .error e => .undefined e
        | .ok (v, used, missing) =>
          .checked (if v.within c.scale (r - half) (r + half) then .consistent else .inconsistent)
            v used missing

/-- The single entry point used by every per-claim theorem. -/
def run (src : Source) (c : Claim) : Outcome :=
  if !src.wellFormed then .undefined .sourceNotWellFormed
  else match parseTable src.bytes with
    | none => .undefined .csvMalformed
    | some t => runTable t c

/-- All claims about one source, sharing a single parse of its bytes. -/
def runAll (src : Source) (cs : List Claim) : List Outcome :=
  if !src.wellFormed then cs.map (fun _ => .undefined .sourceNotWellFormed)
  else match parseTable src.bytes with
    | none => cs.map (fun _ => .undefined .csvMalformed)
    | some t => cs.map (runTable t)

/-- `runAll` is exactly `run` applied to each claim: batching changes cost, not meaning. -/
theorem runAll_eq_map (src : Source) (cs : List Claim) : runAll src cs = cs.map (run src) := by
  unfold runAll
  by_cases hw : src.wellFormed = true
  · cases hp : parseTable src.bytes with
    | none =>
      simp only [hw, Bool.not_true, Bool.false_eq_true, if_false]
      apply List.map_congr_left
      intro c _
      simp [run, hw, hp]
    | some t =>
      simp only [hw, Bool.not_true, Bool.false_eq_true, if_false]
      apply List.map_congr_left
      intro c _
      simp [run, hw, hp]
  · have hw' : src.wellFormed = false := by simpa using hw
    simp only [hw', Bool.not_false, if_true]
    apply List.map_congr_left
    intro c _
    simp [run, hw']

/-- From one batch theorem, the statement about its `i`-th claim alone. -/
theorem run_of_runAll {src : Source} {cs : List Claim} {outs : List Outcome}
    (h : runAll src cs = outs) (i : Nat) {c : Claim} {o : Outcome}
    (hc : cs[i]? = some c) (ho : outs[i]? = some o) : run src c = o := by
  have h2 : (cs.map (run src))[i]? = outs[i]? := by rw [← runAll_eq_map, h]
  rw [List.getElem?_map, hc, ho] at h2
  exact Option.some.inj h2

/-- UTF-8 bytes of a string literal (used for column names, text values and reported literals). -/
def b (s : String) : List Nat := s.toUTF8.data.toList.map UInt8.toNat

end PCS.ClaimCheck

-- ===== generated obligations (data numeral, claims, expected outcomes) =====
open PCS.ClaimCheck

def pcs_src : Source := ⟨0x6269726449442c736974652c626f782c706169722c796561722c74726561746d656e742c7365782c6167652c6566666f72742c6865616462696c6c2c666361726f2c7061746f632c706361726f2c706d64612c6d6173732c6c6179646174652c6e686174636865642c6e666c65646765642c636869636b5f6167652c636869636b5f6d6173732c636869636b5f6865616462696c6c0d0a563237373537322c31412c314130332c314130332d30382c323030382c756e6665642c4d2c3e312c39312c32342e37352c4e412c4e412c4e412c372e32312c31312e382c33382c372c362c31322c31302e32332c32302e32350d0a563237373439322c31412c314131332c314131332d30382c323030382c756e6665642c4d2c312c3130322c32342e33352c4e412c4e412c4e412c392e35352c31302e34322c33302c362c362c31332c31312e38312c32302e380d0a563237373535372c31412c314131382c314131382d30382c323030382c756e6665642c462c3e312c35342e352c32332e37352c3331322e33312c392e31352c31302e35312c4e412c31312e39332c33372c352c312c31312c382e38322c31392e36340d0a563237373537332c31412c314131382c314131382d30382c323030382c756e6665642c4d2c3e312c35342e352c32342e39352c4e412c392e31322c32342e312c372e31362c31322e31362c33372c352c312c31312c382e38322c31392e36340d0a563237373536322c31412c314132302c314132302d30382c323030382c756e6665642c4d2c3e312c35352c32342e3432352c3439352e36372c4e412c4e412c4e412c31322e30312c34302c352c332c31312c382e32362c31382e37330d0a563237373536332c31412c314132352c314132352d30382c323030382c756e6665642c4d2c312c35312c32342c3632372e36322c392e31322c32362e39392c4e412c31312e33312c33372c352c332c31332c31312e32392c32312e30350d0a563237373537352c31412c314132352c314132352d30382c323030382c756e6665642c462c3e312c35372c32332e372c3139392e372c392e31322c31332e382c342e36382c31312e312c33372c352c332c31332c31312e32392c32312e30350d0a563237373434332c31422c314230312c314230312d30382c323030382c6661742c4d2c3e312c3133372c32342e3432352c3332302e33392c4e412c4e412c4e412c392e37362c32342c392c382c31332c31312e32332c32302e37350d0a563237373537362c31422c314231302c314231302d30382c323030382c6661742c462c3e312c34382c32332e3932352c3235342e35362c4e412c4e412c4e412c31302e37382c33382c352c322c31312c372e38362c31382e31340d0a563237373533302c31422c314231312c314231312d30382c323030382c6661742c462c3e312c3132382c32342e3137352c3230352e392c4e412c4e412c4e412c31302e37332c32372c382c382c31312c31302e332c31392e35320d0a563237373537372c31422c314231322c314231322d30382c323030382c6661742c4d2c3e312c37392c32342e352c3335332e37352c4e412c4e412c4e412c31312e33322c33312c382c352c31312c31302e31352c32302e39350d0a563237373538312c31422c314231322c314231322d30382c323030382c6661742c462c312c37392c32342e352c3333362c392e34362c32312e30312c4e412c31312e35362c33312c382c352c31312c31302e31352c32302e39350d0a563237373539382c31422c314232322c314232322d30382c323030382c6661742c462c3e312c39352e352c32342e382c3331312e36312c4e412c4e412c4e412c31312e39382c33392c382c362c31322c31312e35352c32312e31350d0a563237373539392c31422c314232322c314232322d30382c323030382c6661742c4d2c3e312c39352e352c32342e352c3235322e31352c392e31322c32372e38312c31352e31312c31312e36362c33392c382c362c31322c31312e35352c32312e31350d0a563237373534342c31422c314232342c314232342d30382c323030382c6661742c4d2c3e312c3136372c32342e3532352c3234342e35332c4e412c4e412c4e412c392e35362c32392c31302c392c31322c31312e33382c32302e34310d0a563237373534332c31422c314233302c314233302d30382c323030382c6661742c462c3e312c3130322c32342e3237352c3231302e30372c4e412c4e412c4e412c392e38392c33342c362c362c31322c31312e36362c32302e31360d0a563237373538352c31422c314234302c314234302d30382c323030382c6661742c4d2c3e312c3130332c32342e3532352c3334382e39322c4e412c4e412c4e412c31312e37332c31392c372c362c31322c392e38342c32302e39370d0a563237373630302c31422c314234302c314234302d30382c323030382c6661742c462c312c3131362c32342e382c3230332e37372c4e412c4e412c4e412c31312e32342c31392c372c362c31322c392e38342c32302e39370d0a563237373134352c31422c314234322c314234322d30382c323030382c6661742c462c3e312c3132332c32352e3037352c3631382e38342c31352e392c32342e33312c4e412c392e39352c31342c31312c362c31322c382e35352c32302e350d0a563237373239332c31432c314330342c314330342d30382c323030382c6661742b56452c4d2c312c34322c32342e3637352c3236342e392c4e412c4e412c4e412c392e38382c32382c342c332c31322c4e412c32302e35310d0a583239343031332c31432c314330362c314330362d30382c323030382c6661742b56452c4d2c3e312c35322c32352c3231382e37312c4e412c4e412c4e412c31312e33382c34362c342c312c31322c31312e34322c32312e32360d0a563237373436332c31432c314332302c314332302d30382c323030382c6661742b56452c462c3e312c39382c32342e322c3235362e37352c4e412c4e412c4e412c31302e33382c33332c392c362c31312c382e392c31392e38340d0a563237373436372c31432c314332302c314332302d30382c323030382c6661742b56452c4d2c312c39382c32342e35352c3330382e312c4e412c4e412c362e30322c31302e35312c33332c392c362c31312c382e392c31392e38340d0a563237373436362c31432c314332322c314332322d30382c323030382c6661742b56452c462c3e312c3131342c32342e3932352c3332302e30312c31322e37352c32312e30312c382c392e39382c32382c31302c322c31342c31302e35312c32322e30350d0a563237373436382c31432c314332332c314332332d30382c323030382c6661742b56452c462c3e312c39312c32342e342c3330322e31392c4e412c4e412c372e34352c392e34372c33302c372c332c31332c382e39392c32302e37370d0a563237373131312c32412c324130312c324130312d30382c323030382c756e6665642c462c312c36302c32342e3337352c3335352e37362c4e412c4e412c4e412c392e37382c31352c352c352c31322c31302e39372c32312e35390d0a563237373131342c32412c324130312c324130312d30382c323030382c756e6665642c4d2c3e312c36302c32342e31352c4e412c4e412c4e412c4e412c31302e33352c31352c352c352c31322c31302e39372c32312e35390d0a563237373131332c32412c324131352c324131352d30382c323030382c756e6665642c4d2c3e312c37342c32352e3237352c4e412c32332e39362c32322e38372c352e31392c31312e30312c31362c372c302c31322c382e382c32302e340d0a563237373137392c32412c324132322c324132322d30382c323030382c756e6665642c4d2c312c36302c32352e33352c3338322e32372c4e412c4e412c4e412c31312e30342c32302c352c352c31322c31312e32352c32312e32350d0a563237373138392c32412c324132322c324132322d30382c323030382c756e6665642c462c312c36352c32342e342c3332342e37382c4e412c4e412c4e412c31302c32302c352c352c31322c31312e32352c32312e32350d0a563237373139372c32412c324132342c324132342d30382c323030382c756e6665642c462c3e312c37332c32342e3637352c3334352e35312c31322e38372c33322e39362c4e412c31302e312c31382c382c372c31322c392e34392c32302e370d0a563237373139382c32412c324132352c324132352d30382c323030382c756e6665642c4d2c3e312c3130312c32342e36352c3331362e342c4e412c4e412c4e412c31302e34392c31372c382c362c31322c31302e37382c32312e31330d0a563237373139392c32412c324132352c324132352d30382c323030382c756e6665642c462c312c3130312c32342e39352c3230332e32362c32312e30392c31382e35342c352e39382c31302e31382c31372c382c362c31322c31302e37382c32312e31330d0a563237373438302c32412c324132392c324132392d30382c323030382c756e6665642c462c312c3132362c32332e382c3233312e35382c4e412c4e412c4e412c382e38312c32322c382c362c31332c31302e37382c32312e30390d0a563237373139322c32412c324133322c324133322d30382c323030382c756e6665642c4d2c3e312c37352c32342e39352c4e412c4e412c4e412c4e412c392e37332c32302c372c362c31322c31302e33372c32312e30330d0a563237373335382c32412c324133352c324133352d30382c323030382c756e6665642c462c312c36342c32342e33352c3738362e312c31332e38332c34332e34372c342e37392c392e37352c32382c342c342c31322c31312e34372c32302e37360d0a563237373336322c32412c324133362c324133362d30382c323030382c756e6665642c4d2c3e312c3132382c32342e372c3934312e34322c4e412c4e412c4e412c392e362c32342c382c382c31322c392e36332c32302e37380d0a563237373531302c32422c324231322c324231322d30382c323030382c6661742c4d2c3e312c33392c32342e34352c3333312e39362c4e412c4e412c392e33312c31302e34352c33352c332c332c31322c31312e33392c32312e32340d0a563237373531322c32422c324231322c324231322d30382c323030382c6661742c462c3e312c33392c32352e3532352c3431332e36362c4e412c4e412c4e412c31312e31342c33352c332c332c31322c31312e33392c32312e32340d0a563237373433342c32422c324231362c324231362d30382c323030382c6661742c4d2c312c3131392c32352e34352c3537372e36392c4e412c4e412c4e412c31312e32372c32372c372c372c31322c31312e35362c32312e31390d0a563237373434322c32422c324231382c324231382d30382c323030382c6661742c4d2c312c3130382c32352e36352c3231352e33342c4e412c4e412c4e412c31302e35332c33312c382c372c31342c31302e37352c32322e34350d0a563237373531332c32422c324231382c324231382d30382c323030382c6661742c462c3e312c3132322c32332e35352c3137322e36332c31312e39372c31352e38362c4e412c392e32382c33312c382c372c31342c31302e37352c32322e34350d0a563237373531312c32422c324232322c324232322d30382c323030382c6661742c462c3e312c39302c32342e3637352c3337362e35372c4e412c4e412c4e412c392e362c33342c392c332c31322c31302e33372c32302e35340d0a563237373136372c32422c324232382c324232382d30382c323030382c6661742c462c312c35322c32352e3332352c3837322e31342c31332e32362c32302e38312c4e412c31312e35312c31392c342c342c31322c31312e30382c32302e36360d0a563237373136382c32422c324233302c324233302d30382c323030382c6661742c462c312c39362c32342e32362c3530382e33322c31372e32342c32312e34322c362e31322c31302e34382c31382c382c382c31322c392e332c32302e310d0a563237373136392c32422c324233302c324233302d30382c323030382c6661742c4d2c3e312c39362c32352e322c3839312e352c392e32342c33322e37352c4e412c31302e33342c31382c382c382c31322c392e332c32302e310d0a563237373239372c32422c324233322c324233322d30382c323030382c6661742c4d2c3e312c38302c32342e3632352c4e412c4e412c4e412c4e412c31302e33382c31392c352c352c31322c31312e31382c32302e380d0a563237373138372c32432c324330312c324330312d30382c323030382c6661742b56452c462c3e312c35352c32342e37352c3335362e362c4e412c4e412c4e412c31302e30362c32352c362c342c31322c372e37382c31392e37330d0a563237373138382c32432c324330342c324330342d30382c323030382c6661742b56452c462c312c33312c32352e30352c3434382e332c4e412c4e412c4e412c31312e33352c32352c362c312c31312c4e412c4e410d0a563237373537302c32432c324331342c324331342d30382c323030382c6661742b56452c4d2c3e312c36382c32342e3737352c3533372e39362c4e412c4e412c332e30332c31322e32342c33352c342c332c31322c392e32392c32302e30320d0a563237373130362c32432c324331382c324331382d30382c323030382c6661742b56452c4d2c3e312c36302c32352e3032352c3833342e38322c31322e31342c34332e38382c4e412c31312e30312c392c352c322c31322c372e34332c31392e330d0a563237373133332c32432c324331392c324331392d30382c323030382c6661742b56452c462c3e312c38392c32342e35322c4e412c4e412c4e412c4e412c31302e30382c392c382c302c31322c362e30342c31382e34320d0a563237373536352c32432c324332302c324332302d30382c323030382c6661742b56452c4d2c3e312c3132392c32352c4e412c4e412c34302e33382c4e412c31312e37372c32382c31302c342c31332c382e38342c31392e36350d0a563237373432342c32432c324332322c324332322d30382c323030382c6661742b56452c462c312c36332c32342e32352c313231322e34342c4e412c4e412c4e412c392e32342c32362c372c332c31322c31302e31322c31392e30380d0a563237373431302c32432c324332362c324332362d30382c323030382c6661742b56452c462c3e312c35382c32332e3937352c3437392e37392c4e412c4e412c4e412c392e34382c32332c31302c302c31322c372e30342c31372e34320d0a563237373431312c32432c324332372c324332372d30382c323030382c6661742b56452c4d2c3e312c39362c32352e30352c3437342e34362c4e412c4e412c4e412c392e32392c32372c372c332c31322c31302e30352c31392e330d0a563237373138342c32432c324332382c324332382d30382c323030382c6661742b56452c462c312c37322c32342e33352c3233382e32392c4e412c4e412c4e412c31302e36332c32312c382c362c31312c4e412c4e410d0a563237373138352c32432c324332382c324332382d30382c323030382c6661742b56452c4d2c312c37322c32342e3132352c4e412c4e412c4e412c4e412c392e33342c32312c382c362c31312c4e412c4e410d0a563237373138362c32432c324333302c324333302d30382c323030382c6661742b56452c462c3e312c35392c32352e3032352c3336352e31362c32342e33352c32312e34322c372e32392c31302e37382c32322c382c352c31322c392e32332c31392e380d0a563237373135362c32432c324333372c324333372d30382c323030382c6661742b56452c462c312c36382e352c32342e3037352c3430382e392c4e412c4e412c4e412c392e37312c31392c362c342c31322c382e31312c31392e31320d0a563237373133302c32432c324333382c324333382d30382c323030382c6661742b56452c4d2c312c34342e352c32342e37352c4e412c4e412c4e412c4e412c31302e37382c31362c372c312c31322c382e33322c31382e36340d0a563237373536372c32432c324333392c324333392d30382c323030382c6661742b56452c462c3e312c38352c32342e36352c3432372e39322c392e31322c31362e38392c4e412c31312c33302c362c342c31322c392e37392c32312e31360d0a563237373536382c32432c324333392c324333392d30382c323030382c6661742b56452c4d2c3e312c38352c32342e37352c3331382e35362c4e412c4e412c4e412c31322e33322c33302c362c342c31322c392e37392c32312e31360d0a563237373536362c32432c324334302c324334302d30382c323030382c6661742b56452c4d2c3e312c38352c32342e38352c3435362e34352c4e412c4e412c4e412c31312e36382c33332c352c352c31322c382e38322c31392e33350d0a563237373536392c32432c324334302c324334302d30382c323030382c6661742b56452c462c3e312c38352c32342e312c3232342e34322c4e412c4e412c4e412c31302e36342c33332c352c352c31322c382e38322c31392e33350d0a563237373131362c32432c324334312c324334312d30382c323030382c6661742b56452c462c312c38392c32342e36352c313035352e35332c4e412c4e412c4e412c31302e352c31382c382c302c31322c362e35322c31382e34360d0a563237373132332c32432c324334312c324334312d30382c323030382c6661742b56452c4d2c3e312c38392c32342e372c4e412c4e412c4e412c4e412c31302e36362c31382c382c302c31322c362e35322c31382e34360d0a563237373436342c33412c334130332c334130332d30382c323030382c756e6665642c462c3e312c37392c32342e392c4e412c31332e39362c32342e312c352e37372c392e38352c33312c362c352c31332c31312e332c32312e35310d0a563237373436322c33412c334130362c334130362d30382c323030382c756e6665642c462c312c3130352c32342e34352c3137312e31372c4e412c4e412c4e412c392e37382c32382c372c362c31322c31312e34342c32302e360d0a545630372e4d2c33412c334130372c334130372d30382c323030382c756e6665642c4d2c3e312c37392e352c32342e33352c3138332e33392c4e412c4e412c4e412c392e36342c32352c362c332c31322c31302e37332c32302e32370d0a563237373436352c33412c334130372c334130372d30382c323030382c756e6665642c462c3e312c37392e352c32342e3637352c3231312e31312c392e31322c34332e32362c362e32322c392e362c32352c362c332c31322c31302e37332c32302e32370d0a563237373230362c33412c334130382c334130382d30382c323030382c756e6665642c462c3e312c37352c32342e382c3331362c4e412c4e412c4e412c31302e39362c32342c372c302c31322c392e32332c32302e30380d0a563237373537342c33412c334132352c334132352d30382c323030382c756e6665642c462c312c37302c32342e3432352c3336382e30312c4e412c4e412c4e412c31302e37382c33382c352c352c31322c392e36372c32302e35390d0a583239343031342c33422c334230322c334230322d30382c323030382c6661742c4d2c3e312c38392e352c32342e38352c3235302e33312c31362e39312c32312e32322c31312e32372c31322e33382c34352c372c342c31322c392e34352c31392e38370d0a583239343031352c33422c334230322c334230322d30382c323030382c6661742c462c312c38392e352c32342e312c3631372e32342c31342e34322c31362e32372c4e412c31312e39332c34352c372c342c31322c392e34352c31392e38370d0a563237373333352c33422c334230352c334230352d30382c323030382c6661742c4d2c3e312c36382c32342e322c3439352e33352c31302e35372c31372e39322c382e31322c31312e33382c32352c362c332c31322c31312e30382c32302e32350d0a544c31302e462c33422c334231302c334231302d30382c323030382c6661742c462c3e312c37382e352c32342e35342c4e412c4e412c4e412c4e412c31312e32332c32342c362c302c31322c382e39392c31392e35340d0a563237373436312c33422c334232302c334232302d30382c323030382c6661742c462c3e312c36342c32342e3432352c3236352e31342c31362e352c33312e31312c362e30342c31302e35312c33302c342c342c31332c31312e30342c32312e32310d0a563237373538362c33422c334233352c334233352d30382c323030382c6661742c462c3e312c32352c32342e36352c3332342e30382c31302e34372c31382e37352c352e37392c31322e31312c34312c352c302c31322c372e312c31372e35350d0a583239343030352c33432c334330352c334330352d30382c323030382c6661742b56452c462c312c3130332c32342e33352c3139312e30312c4e412c4e412c4e412c31322e31382c34312c372c362c31322c31312e38322c32302e31360d0a563237373531342c33432c334331372c334331372d30382c323030382c6661742b56452c4d2c3e312c3131322c32352e35352c3232332e30342c4e412c4e412c4e412c31302e33332c33322c372c372c31332c31302e39382c32312e35330d0a563237373435302c33432c334331392c334331392d30382c323030382c6661742b56452c462c312c3133362c32342e32352c3237392e32372c4e412c4e412c352e36352c392e31382c32382c382c382c31322c31312e34342c32302e380d0a563237373531352c33432c334333302c334333302d30382c323030382c6661742b56452c462c312c3133322c32342e312c3136302e30372c4e412c4e412c4e412c392e34392c32392c31302c362c31332c31302e31382c32312e32330d0a563237373531362c33432c334333302c334333302d30382c323030382c6661742b56452c4d2c312c3133322c32352e332c3338332e30392c4e412c4e412c4e412c31302e32352c32392c31302c362c31332c31302e31382c32312e32330d0a583239343331352c31412c314130312c314130312d30392c323030392c6661742c462c3e312c36352c32342e362c3233322e36312c4e412c4e412c4e412c31302c32382c352c342c31332c31302e33362c32302e33350d0a583831303437312c31412c314130382c314130382d30392c323030392c6661742c4d2c3e312c37332c32342e3537352c3834372e32382c32302e30342c32302e31362c382e31312c31302e332c32352c352c332c31332c31312e33372c32312e33350d0a583239343035372c31412c314131302c314131302d30392c323030392c6661742c462c312c34322c32342e3532352c3139332e34392c4e412c4e412c4e412c31302e352c32322c372c302c31322c4e412c4e410d0a583239343035382c31412c314131302c314131302d30392c323030392c6661742c4d2c312c34322c32342e3537352c3535312e35342c4e412c4e412c4e412c31302e352c32322c372c302c31322c4e412c4e410d0a583831303431372c31412c314131382c314131382d30392c323030392c6661742c462c312c37302e352c32342e372c3336372e36392c34342e36322c32392e36362c352e34372c392e372c33312c372c302c31332c382e362c31392e32370d0a583831303431362c31412c314132322c314132322d30392c323030392c6661742c4d2c312c37342c32342e37352c3336362e37392c31312e362c32302e33392c4e412c31302e332c33322c362c322c31332c382e342c31392e37370d0a583239343036302c31412c314132362c314132362d30392c323030392c6661742c462c312c33332c32342c3234352c4e412c4e412c4e412c31312e352c32342c362c332c31322c372e362c31392e33350d0a583831303431342c31412c314132382c314132382d30392c323030392c6661742c462c312c35322e352c32342e382c3333372e31352c32382e30342c32352e37322c4e412c31302e372c33352c352c302c31322c362e342c31382e310d0a583239343333302c31412c314132392c314132392d30392c323030392c6661742c4d2c312c37362c32352e312c3233362c31352e38342c32362e38382c31322e34372c392e362c32352c382c362c31312c362e39322c31382e36380d0a583831303431352c31412c314132392c314132392d30392c323030392c6661742c462c312c3131322c32342e39352c3338322e36312c4e412c4e412c392e37332c31302e322c32352c382c362c31312c362e39322c31382e36380d0a583239343135382c31412c314133352c314133352d30392c323030392c6661742c462c312c37352e352c32342e3032352c3333302e39322c4e412c4e412c382e39362c31302e332c32372c372c322c31322c362e31372c31372e340d0a583239343035392c31412c314133382c314133382d30392c323030392c6661742c462c3e312c33332c32352c3331302e32342c4e412c4e412c4e412c31312c32332c362c302c31322c4e412c4e410d0a563237373034312c31412c314134302c314134302d30392c323030392c6661742c462c312c38322e352c32342e36352c3236362e32362c32392e34322c32352e39362c4e412c392e372c34302c372c302c31312c372e34372c31382e39380d0a543937333236342c31422c314230312c314230312d30392c323030392c6661742b56452c462c3e312c3131392c32342c3236342e392c32342e31332c31332e34342c4e412c31302e342c33382c372c372c31332c392e36372c32302e39330d0a563237373434332c31422c314230312c314230312d30392c323030392c6661742b56452c4d2c3e312c3131392c32352e32352c3136362e34312c31352e38362c32352e37322c352e36372c392e382c33382c372c372c31332c392e36372c32302e39330d0a563237373034322c31422c314230332c314230332d30392c323030392c6661742b56452c4d2c312c39352c32342e3432352c3139302e31392c32352e32342c33382e30312c342e34312c31302e322c32352c31302c372c31332c382e38342c32302e30350d0a563237373035362c31422c314230332c314230332d30392c323030392c6661742b56452c462c312c3130372e352c32342e382c3236382e33372c4e412c4e412c4e412c31302e332c32352c31302c372c31332c382e38342c32302e30350d0a563237373539302c31422c314230342c314230342d30392c323030392c6661742b56452c4d2c312c39312c32342e3837352c3333362e36332c4e412c4e412c4e412c31302e372c32352c372c372c31332c392e39342c32312e30350d0a563237373337302c31422c314231352c314231352d30392c323030392c6661742b56452c462c312c39382c32342e352c3539302e39342c4e412c4e412c4e412c392e322c32322c372c362c31342c31302e34372c32312e34330d0a563237373031332c31422c314232352c314232352d30392c323030392c6661742b56452c4d2c3e312c3132382c32342e3737352c3233382e30362c32382e32352c32352e39362c372e372c31302e322c32392c382c382c31342c31302e35362c32312e340d0a563237373031342c31422c314232352c314232352d30392c323030392c6661742b56452c462c312c3132382c32342e3932352c3336352e35382c4e412c4e412c372e37372c31302e312c32392c382c382c31342c31302e35362c32312e340d0a583831303436322c31422c314232382c314232382d30392c323030392c6661742b56452c4d2c3e312c3133362c32362e30352c3439362e31342c352e37322c31312e35392c342e35312c31312e312c33312c382c372c31322c392e39392c32302e37320d0a563237373031352c31422c314233302c314233302d30392c323030392c6661742b56452c4d2c312c39312e352c32352e34352c3538382e33392c33392e32312c32352e32362c4e412c31302e312c33342c372c352c31332c31302e30372c32312e30320d0a563237373630302c31422c314233382c314233382d30392c323030392c6661742b56452c462c3e312c35322c32342e372c3335302e34392c31392e332c31352e39392c372e37372c31302e362c32332c362c352c31322c31302e36382c32312e30310d0a583239343039382c31422c314234302c314234302d30392c323030392c6661742b56452c462c312c31322c32342e34352c3538382e31312c4e412c4e412c4e412c31302e322c32322c332c312c31302c362e372c31382e37340d0a583239343136312c31422c314234312c314234312d30392c323030392c6661742b56452c462c312c36342c32342e3732352c3234382e31392c32362e36392c31332e34342c382e37332c31302e312c32322c382c302c31312c4e412c4e410d0a583239343136332c31422c314234312c314234312d30392c323030392c6661742b56452c4d2c3e312c36342c32342e3632352c3233342e33342c33372e37392c32332e38372c4e412c31302e312c32322c382c302c31312c4e412c4e410d0a583239343136322c31422c314234322c314234322d30392c323030392c6661742b56452c462c312c35362c32342e34352c3237382e39342c4e412c4e412c31332e34332c392e342c32302c362c342c31332c382e35352c32302e31330d0a583239343136352c31422c314234322c314234322d30392c323030392c6661742b56452c4d2c312c35362c32342e3532352c3331382e37332c33382e36382c33342e332c31302c31302e332c32302c362c342c31332c382e35352c32302e31330d0a583239343136362c31422c314234332c314234332d30392c323030392c6661742b56452c462c3e312c36342c32342e3732352c3330352e30332c31322e32372c31302e322c392e37352c31302e322c32312c382c312c31312c372e322c31390d0a583239343136342c31422c314234342c314234342d30392c323030392c6661742b56452c462c312c35362c32342c3333372e31352c4e412c4e412c31312e39312c392e322c32312c372c372c31312c382e34342c31382e39380d0a563237373735372c31432c314330322c314330322d30392c323030392c756e6665642c4d2c3e312c3132382c32352e3732352c3335392e34352c35312e37322c34372e32382c352e35392c31302e392c32352c382c382c31322c31312e31392c32312e38330d0a583239343039332c31432c314330342c314330342d30392c323030392c756e6665642c462c3e312c34322c32342e322c3631342e34352c4e412c4e412c4e412c31312e332c32322c372c372c31322c31302e35332c32302e34380d0a583239343135372c31432c314330342c314330342d30392c323030392c756e6665642c4d2c312c35362c32342e3337352c3434372e34342c33322e35352c34322e38372c352e38392c31302e342c32322c372c372c31322c31302e35332c32302e34380d0a563237373436332c31432c314332302c314332302d30392c323030392c756e6665642c462c3e312c34382c32342e38352c3539332e33382c33312e382c34382e36372c352e30342c31302e332c33312c332c332c31342c31302e382c32312e31380d0a583831303430322c31432c314332312c314332312d30392c323030392c756e6665642c462c3e312c3130362e352c32352e31352c3937352e36362c33362e37322c31322e35312c362e37312c31302e352c32392c372c362c31342c392e392c32312e31340d0a563237373739352c32412c324130322c324130322d30392c323030392c6661742c4d2c3e312c3132322e352c32342e3932352c3530352e37322c35302e342c32322e37312c372e332c392e382c32322c382c372c31332c392e38372c32302e360d0a563237373739362c32412c324130322c324130322d30392c323030392c6661742c462c3e312c3132322e352c32342e3332352c3534332e32372c4e412c4e412c4e412c31302e342c32322c382c372c31332c392e38372c32302e360d0a583239343136382c32412c324130332c324130332d30392c323030392c6661742c462c312c38302c32342e3037352c3330352e32352c4e412c4e412c31322e32372c392e372c31372c382c352c31322c372e31322c31392e310d0a563237373739372c32412c324130342c324130342d30392c323030392c6661742c4d2c312c37362e352c32352e32352c3334392e30352c34322e31352c35342e36392c352e35392c31312e322c33322c362c342c31302c372e38322c31382e38380d0a583239343136392c32412c324130372c324130372d30392c323030392c6661742c462c312c3130352c32342e312c3731332e322c33352e39342c32392e322c382e36362c31302e342c31362c382c362c31312c372e38352c31382e38370d0a583239343034332c32412c324131342c324131342d30392c323030392c6661742c4d2c312c36372c32342e33352c3335342e35362c4e412c4e412c4e412c31302e342c31312c382c362c31312c382e37322c31392e34360d0a583239343034342c32412c324131342c324131342d30392c323030392c6661742c462c312c36372c32332e37352c3437392e32372c33352e36362c31312e33362c382e31362c31302e362c31312c382c362c31312c382e37322c31392e34360d0a583239343037392c32412c324131382c324131382d30392c323030392c6661742c462c3e312c35362e352c32342e3732352c3336352e31362c31392e34382c34312e32352c392e32362c31302e352c31362c352c342c31322c31312e31322c32312e37360d0a563237373136312c32412c324132392c324132392d30392c323030392c6661742c462c312c38352c32342e3532352c4e412c4e412c4e412c4e412c31302e312c32382c352c352c31332c31302e352c32312e33350d0a563237373131332c32412c324133322c324133322d30392c323030392c6661742c4d2c3e312c36322e352c32342e3237352c3635332e35352c31342e31392c31312e33362c31332e32362c31302e372c31382c382c342c31322c392e30392c31392e370d0a583239343034352c32412c324133322c324133322d30392c323030392c6661742c462c3e312c36322e352c32342e3437352c3434392e37332c4e412c4e412c4e412c31302e352c31382c382c342c31322c392e30392c31392e370d0a583239343034362c32412c324133362c324133362d30392c323030392c6661742c462c312c33302c32342e362c3339362e32322c32312e332c32342e35372c372e34392c31302e392c31362c332c332c31322c31312c32312e36340d0a563237373830302c32412c324134302c324134302d30392c323030392c6661742c462c312c37372e352c32342e342c3636382e38322c4e412c4e412c362e38322c392e352c32322c352c342c31332c392e35372c32302e390d0a583831303430312c32412c324134302c324134302d30392c323030392c6661742c4d2c312c37372e352c32342e392c3732372e34362c34332e32382c35382e342c372e37372c31302e352c32322c352c342c31332c392e35372c32302e390d0a563237373033302c32422c324230312c324230312d30392c323030392c6661742b56452c462c312c36302e352c32342e3437352c3230342e34352c33382e35322c31392e32342c362e36342c392e372c33382c342c332c31332c31312e32332c32302e36350d0a563237373033342c32422c324230312c324230312d30392c323030392c6661742b56452c4d2c3e312c36302e352c32352e352c3236322e34362c33312e342c35342e36392c362e35352c31302e392c33382c342c332c31332c31312e32332c32302e36350d0a563237373033332c32422c324230332c324230332d30392c323030392c6661742b56452c462c312c3130352c32342e3437352c3136382e38392c32372e35332c31392e32342c382e36312c392e372c33342c392c332c31332c372e382c31392e33380d0a563237373033312c32422c324230342c324230342d30392c323030392c6661742b56452c4d2c312c3132382c32352e3532352c3138392e35372c33302e31382c32322e37312c372e33342c31302e362c33332c382c382c31322c31302e35372c32302e33350d0a563237373033322c32422c324230342c324230342d30392c323030392c6661742b56452c462c312c3132382c32342e35352c3233392e36332c32352e362c31322e30352c372e32312c31302e322c33332c382c382c31322c31302e35372c32302e33350d0a583831303434312c32422c324230392c324230392d30392c323030392c6661742b56452c462c312c39302c32342e34352c3436372e33322c33352e37312c31342e362c372e392c31302e322c33332c362c362c31332c31312e37372c32312e32350d0a563237373032392c32422c324231312c324231312d30392c323030392c6661742b56452c462c312c3131322c32342c3236362e32362c4e412c4e412c4e412c392e352c33342c372c372c31332c31302e39372c32302e37370d0a563237373434312c32422c324231312c324231312d30392c323030392c6661742b56452c4d2c312c3131322c32352e362c3138352e34332c33352e38362c34362e33352c362e32342c31302e332c33342c372c372c31332c31302e39372c32302e37370d0a583831303431332c32422c324231342c324231342d30392c323030392c6661742b56452c4d2c3e312c38332c32342e392c3634322e38332c34302e33332c32302e31362c392e382c31302e392c32322c362c352c31322c31312e312c32302e37340d0a583239343138392c32422c324231362c324231362d30392c323030392c6661742b56452c4d2c312c34302c32342e352c3431362e30332c33322e34342c35302e39382c382e31372c392e382c32362c352c352c31322c31312e32382c32302e38330d0a563237373033352c32422c324232362c324232362d30392c323030392c6661742b56452c4d2c3e312c39362c32352e3232352c3231332e39362c32392e36382c34322e38372c372e32342c31302e342c33332c362c362c31322c31312e33352c32312e32320d0a563237373034332c32422c324233322c324233322d30392c323030392c6661742b56452c4d2c312c37302c32342e38352c3233362e37382c33312e38352c37312e31352c372e30372c31302e362c34302c352c352c31332c31312e30362c32312e33360d0a563237373034342c32422c324233322c324233322d30392c323030392c6661742b56452c462c312c37302c32342e3537352c3135382e38332c33322e38372c31372e33382c352e37382c31302e312c34302c352c352c31332c31312e30362c32312e33360d0a563237373738312c32432c324330392c324330392d30392c323030392c756e6665642c462c3e312c39332e352c32342e36352c3439312e34322c4e412c4e412c4e412c392e392c32372c372c362c31332c392e372c32302e30360d0a563237373430322c32432c324331322c324331322d30392c323030392c756e6665642c4d2c312c32392e352c32332e39352c3332302e32352c31302e30332c32352e30332c362e30342c31302e342c33382c342c302c31312c4e412c4e410d0a563237373738322c32432c324331322c324331322d30392c323030392c756e6665642c462c3e312c32392e352c32342c3433302e38372c33302e34342c31352e35332c382e32392c31302e362c33382c342c302c31312c4e412c4e410d0a583831303437362c32432c324331342c324331342d30392c323030392c756e6665642c4d2c312c37322e352c32342e322c3339302e31392c4e412c4e412c4e412c392e322c32342c352c342c31322c31302e30352c32302e340d0a583831303437382c32432c324331342c324331342d30392c323030392c756e6665642c462c312c37322e352c32342e382c3433332e322c4e412c4e412c392e38372c392e382c32342c352c342c31322c31302e30352c32302e340d0a583831303437372c32432c324331352c324331352d30392c323030392c756e6665642c4d2c3e312c36342c32352e34352c3638372e32362c32352e382c34352e34322c352e312c31302e332c33352c362c342c31342c31302e39352c32312e390d0a583831303437392c32432c324331352c324331352d30392c323030392c756e6665642c462c3e312c36342c32352e31352c3432362e34322c4e412c4e412c4e412c31302e332c33352c362c342c31342c31302e39352c32312e390d0a563237373738372c32432c324331362c324331362d30392c323030392c756e6665642c4d2c3e312c3131322c32342c3531332e352c4e412c4e412c4e412c31302e362c32362c372c372c31342c31302e34332c32312e32370d0a563237373739342c32432c324331392c324331392d30392c323030392c756e6665642c4d2c3e312c3135332c32352e32352c3332322e36362c4e412c4e412c4e412c31302e342c31372c31312c382c31342c392e34362c32312e31340d0a563237373034382c32432c324332302c324332302d30392c323030392c756e6665642c462c3e312c3135322e352c32342e39352c3232302e33352c31302e38362c382e35372c362e37312c31302e322c33382c31302c392c31322c382e37392c31392e39340d0a583239343136372c32432c324332322c324332322d30392c323030392c756e6665642c4d2c3e312c32352c32342e3732352c3334302e37312c31342e39342c33352e36392c392e32372c31312e322c32342c362c312c31322c31302e38342c32312e33330d0a583239343034322c32432c324333352c324333352d30392c323030392c756e6665642c462c312c32372c32342e332c3239392e35342c4e412c4e412c4e412c31312c31372c352c302c31322c4e412c4e410d0a563237373739332c32432c324333382c324333382d30392c323030392c756e6665642c4d2c3e312c34382c32342e3632352c3333312e36342c4e412c4e412c382e31332c31302e352c33352c362c342c31362c4e412c4e410d0a563237373536382c32432c324333392c324333392d30392c323030392c756e6665642c4d2c3e312c3131342c32352e312c3432322e32312c4e412c4e412c382e35362c31302e332c32362c372c352c31332c372e38332c31392e35340d0a563237373536392c32432c324333392c324333392d30392c323030392c756e6665642c462c3e312c3131342c32342e332c3537302e35362c4e412c4e412c31322e33382c392e332c32362c372c352c31332c372e38332c31392e35340d0a563237373734372c33412c334130312c334130312d30392c323030392c6661742c4d2c312c39382c32342e36352c3534392e38312c4e412c33342e332c382e31392c392e342c32392c372c372c31322c31302e31392c31392e35350d0a563237373436322c33412c334130362c334130362d30392c323030392c6661742c462c3e312c37302c32342e3437352c3333342e31382c4e412c4e412c4e412c392e372c32332c372c372c31332c31302e32312c32312e30320d0a583239343137342c33412c334130362c334130362d30392c323030392c6661742c4d2c3e312c37302c32342e35352c3338372e33382c33312e30362c31352e35332c31302e31332c31302e382c32332c372c372c31332c31302e32312c32312e30320d0a563237373734362c33412c334130382c334130382d30392c323030392c6661742c4d2c3e312c37352c32342e3132352c3631342e34352c4e412c31312e38322c4e412c31302e392c32352c352c352c31332c31302e372c32302e38310d0a583239343135352c33412c334131312c334131312d30392c323030392c6661742c462c3e312c34332c32342e3737352c3430372e39352c4e412c4e412c4e412c31302e382c32342c352c342c31322c392e39372c32302e35370d0a583239343135362c33412c334131312c334131312d30392c323030392c6661742c4d2c3e312c34332c32342e352c3435302e37342c32342e32392c32352e37322c31312e39372c31302e352c32342c352c342c31322c392e39372c32302e35370d0a583831303439362c33412c334131362c334131362d30392c323030392c6661742c4d2c312c3131392c32342e38352c3134392e37372c4e412c4e412c4e412c31302e312c33322c372c372c31312c382e392c31392e330d0a583831303439372c33412c334131362c334131362d30392c323030392c6661742c462c312c3131392c32342e3237352c3230392e32312c4e412c4e412c4e412c392e382c33322c372c372c31312c382e392c31392e330d0a563237373034372c33412c334132342c334132342d30392c323030392c6661742c4d2c3e312c3133392c32342e382c3233322e31362c31352e35382c31362e36392c372e36362c392e392c33322c392c382c31322c31302e31352c32310d0a583831303439352c33412c334132342c334132342d30392c323030392c6661742c462c312c39392c32342e322c3138392e33322c4e412c4e412c4e412c392e362c33322c392c382c31322c31302e31352c32310d0a563237373034352c33412c334132352c334132352d30392c323030392c6661742c4d2c3e312c36362c32352e3437352c3235352e36312c4e412c4e412c31312e34392c392e392c34352c362c362c31322c31302e37382c32312e31380d0a563237373034362c33412c334132352c334132352d30392c323030392c6661742c462c312c36362c32342e36352c3330352e30332c4e412c4e412c392e31352c31302c34352c362c362c31322c31302e37382c32312e31380d0a583239343039322c33412c334133312c334133312d30392c323030392c6661742c4d2c312c37352e352c32342e32352c3638382e32342c4e412c4e412c4e412c31302e322c32312c392c382c31332c392e39342c32302e34370d0a563237373637332c33422c334230362c334230362d30392c323030392c6661742b56452c4d2c3e312c3130332c32352e3032352c3139302e31392c33352e33342c34342e32362c342e33332c31312e352c32312c382c342c31322c382e36382c32302e31340d0a583239343233332c33422c334230392c334230392d30392c323030392c6661742b56452c462c3e312c3130342c32342e3037352c3239332e30362c32352e32312c31312e38322c4e412c392c31392c392c372c31332c392e30392c32302e35380d0a583239343233352c33422c334230392c334230392d30392c323030392c6661742b56452c4d2c3e312c3130342c32342e32352c3234342e37392c4e412c4e412c31312e37392c392e342c31392c392c372c31332c392e30392c32302e35380d0a583239343136302c33422c334231322c334231322d30392c323030392c6661742b56452c462c3e312c32322e352c32332e3832352c3236302e38332c4e412c4e412c4e412c31302e342c33302c352c332c31312c372e37372c31382e34320d0a583239343035362c33422c334231342c334231342d30392c323030392c6661742b56452c4d2c312c37302c32342e332c3334392e30352c4e412c4e412c4e412c392e392c31372c372c332c31322c392e33362c32312e31370d0a563237373637342c33422c334231372c334231372d30392c323030392c6661742b56452c4d2c3e312c34322c32352e3432352c3236342e33362c33332e33382c36392e30362c352e37342c31312c32362c332c332c31322c31312e35372c32302e37350d0a583239343035332c33432c334330312c334330312d30392c323030392c756e6665642c4d2c3e312c36312c32342e332c3335382e31382c4e412c4e412c31342e33342c31302e342c31372c372c362c31322c31302e34322c32312e33380d0a583239343033362c33432c334330342c334330342d30392c323030392c756e6665642c462c312c34382c32342e3537352c3230352e342c33312e372c32342e382c392e31322c31312e312c32322c362c362c31312c362e34322c31372e39310d0a583239343035342c33432c334330342c334330342d30392c323030392c756e6665642c4d2c312c34382c32342c3633352e37372c32312e36382c34302e35362c372e37342c392e362c32322c362c362c31312c362e34322c31372e39310d0a583239343132302c33432c334330362c334330362d30392c323030392c756e6665642c462c3e312c36342c32342e3732352c3532302e30392c4e412c4e412c4e412c31302e332c32312c382c302c4e412c4e412c4e410d0a583239343033382c33432c334330382c334330382d30392c323030392c756e6665642c4d2c312c3130322e352c32342e362c3138312e38372c4e412c4e412c31312e36372c31302e362c31312c31302c362c31332c372e38332c31392e37370d0a583239343033392c33432c334330382c334330382d30392c323030392c756e6665642c462c3e312c3130322e352c32332e37352c3237312e38352c34322e30392c33302e33362c31312e30342c31302e392c31312c31302c362c31332c372e38332c31392e37370d0a583239343035352c33432c334331302c334331302d30392c323030392c756e6665642c462c312c38312c32352c3238392e30382c4e412c4e412c31302c31302e372c32302c392c382c31322c392e37342c32302e33380d0a583239343139342c33432c334331302c334331302d30392c323030392c756e6665642c4d2c312c3133332c32342e36352c3338322e32372c33322e33342c34382e34342c392e37312c392e382c32302c392c382c31322c392e37342c32302e33380d0a583239343139312c33432c334331322c334331322d30392c323030392c756e6665642c462c312c35342c32342e3237352c3335382e31382c31342e33332c31372e38342c372e38382c31322c31382c362c362c31322c31302e31382c32302e31350d0a583239343139332c33432c334331322c334331322d30392c323030392c756e6665642c4d2c3e312c35342c32342e3332352c3330392e37332c4e412c4e412c392e35382c31302e312c31382c362c362c31322c31302e31382c32302e31350d0a583239343033372c33432c334332332c334332332d30392c323030392c756e6665642c462c312c33362c32342e3332352c3237352e37372c32322e37362c31382e35342c372e31362c31312e352c31372c382c312c31322c392e362c32302e320d0a563237373435302c33432c334332342c334332342d30392c323030392c756e6665642c462c3e312c36332c32332e37352c3438302e32322c4e412c4e412c31312e362c392e372c32342c372c302c31322c4e412c4e410d0a583239343139322c33432c334332342c334332342d30392c323030392c756e6665642c4d2c312c36332c32342e342c3437362e38322c33392e36362c34352e31392c4e412c31302c32342c372c302c31322c4e412c4e410d0a4c3232353735322c31412c314130372c314130372d31302c323031302c6661742b56452c462c3e312c36352c32352c3137382e39352c4e412c4e412c342e33382c31302e30322c35312c352c352c31322c31302e30392c32302e36390d0a583831303437312c31412c314130372c314130372d31302c323031302c6661742b56452c4d2c3e312c36352c32352e30352c3238352e32382c4e412c4e412c4e412c31302e372c35312c352c352c31322c31302e30392c32302e36390d0a583239343035372c31412c314131322c314131322d31302c323031302c6661742b56452c462c3e312c36372e352c32342e37352c3234362e30352c4e412c4e412c332e32312c31302e32362c32382c362c332c31322c382e36342c31392e320d0a4c3232353532362c31412c314131332c314131332d31302c323031302c6661742b56452c4d2c312c37372c32342e3732352c3238332e36352c4e412c4e412c4e412c31302e31332c33332c362c342c31332c392e34362c32302e34350d0a4c3232353631302c31412c314131332c314131332d31302c323031302c6661742b56452c462c3e312c38362c32342e352c3331342e37392c4e412c4e412c4e412c392e30392c33332c362c342c31332c392e34362c32302e34350d0a4c3232353532372c31412c314131352c314131352d31302c323031302c6661742b56452c4d2c312c37392e352c32352e39352c3237332e38372c4e412c4e412c332e34372c392e38382c33362c362c332c31322c31302e30332c32302e360d0a4c3232353631342c31412c314131352c314131352d31302c323031302c6661742b56452c462c312c38382e352c32342e3032352c3231332e39362c32392e34312c33392e342c332c392e34362c33362c362c332c31322c31302e30332c32302e360d0a4c3232353631362c31412c314132352c314132352d31302c323031302c6661742b56452c462c3e312c35312c32342e3232352c3235342e38352c4e412c4e412c342e36352c31302e32342c33342c332c332c31332c31312e35322c32302e39330d0a583831303431362c31412c314132352c314132352d31302c323031302c6661742b56452c4d2c3e312c35312c32342e3737352c3331312e34392c4e412c4e412c322e36332c31302e37362c33342c332c332c31332c31312e35322c32302e39330d0a4c3232353631332c31412c314132382c314132382d31302c323031302c6661742b56452c462c312c32382c32342e35352c3335392e36332c31372e31322c32342e35372c332e32362c31302e32322c34372c342c302c31312c4e412c4e410d0a4c3232353631352c31412c314132382c314132382d31302c323031302c6661742b56452c4d2c312c32382c32352e322c3232352e30352c4e412c4e412c322e38312c31312e31362c34372c342c302c31312c4e412c4e410d0a4c3232353436392c31412c314133312c314133312d31302c323031302c6661742b56452c4d2c3e312c34382c32352e3232352c3236342e37342c4e412c4e412c342e312c31312e39362c33302c332c332c31322c31302e31362c32302e37310d0a4c3232353435322c31412c314133352c314133352d31302c323031302c6661742b56452c462c3e312c36332c32352e312c3330302e30372c31312e37372c31372e33382c332e37362c31302e35352c33302c372c372c31332c392e39372c32302e39340d0a4c3232353732362c31412c314133352c314133352d31302c323031302c6661742b56452c4d2c3e312c3131392c32352c3331322e31332c4e412c4e412c342e32392c392e37392c33302c372c372c31332c392e39372c32302e39340d0a4c3232353631312c31412c314133382c314133382d31302c323031302c6661742b56452c4d2c3e312c3130322e352c32352e342c3332382e30372c4e412c4e412c332e30352c31302e31332c33362c372c362c31312c392e35312c31392e37310d0a4c3232353631322c31412c314133382c314133382d31302c323031302c6661742b56452c462c312c3130322e352c32342e3332352c3234302e392c4e412c4e412c4e412c382e39362c33362c372c362c31312c392e35312c31392e37310d0a4c3232353031312c31422c314230332c314230332d31302c323031302c756e6665642c4d2c3e312c36312c32352e3037352c3537392e33342c4e412c31352e37362c4e412c31302e39392c32302c372c352c31322c392e36332c32302e33320d0a4c3232353531392c31422c314230352c314230352d31302c323031302c756e6665642c4d2c312c3132332c32342e3437352c3331362e39382c4e412c4e412c342e34372c31302e32332c33302c392c382c31312c31302e32332c32302e31310d0a4c3232353532302c31422c314230392c314230392d31302c323031302c756e6665642c462c312c34382c32352c3231312e33322c32382e32342c32362e34322c332e36362c392e35392c34322c362c362c31322c392e33322c32302e36330d0a583239343230312c31422c314230392c314230392d31302c323031302c756e6665642c4d2c312c34382c32352e3332352c3234352e35312c4e412c4e412c352e30342c31302e35382c34322c362c362c31322c392e33322c32302e36330d0a4c3232353532312c31422c314231312c314231312d31302c323031302c756e6665642c4d2c312c39362c32342e3732352c3334322e33342c4e412c4e412c4e412c392e34342c32392c362c362c31322c31302e39382c32312e33330d0a563237373730392c31422c314231312c314231312d31302c323031302c756e6665642c462c312c39362c32352c3238362e37342c4e412c4e412c4e412c31302e31382c32392c362c362c31322c31302e39382c32312e33330d0a4c3232353532342c31422c314232312c314232312d31302c323031302c756e6665642c462c3e312c39392c32342e3337352c3138312e38372c332e332c31302e36362c322e37342c392e36372c32382c31302c342c31342c382e36332c32312e34340d0a4c3232353532322c31422c314232322c314232322d31302c323031302c756e6665642c4d2c3e312c38302c32332e3932352c3334362e34312c4e412c4e412c4e412c392e30362c33322c382c382c31322c382e342c32302e35340d0a4c3232353532332c31422c314232322c314232322d31302c323031302c756e6665642c462c3e312c38302c32342e3637352c3236322e34362c4e412c4e412c342e36362c31302e30372c33322c382c382c31322c382e342c32302e35340d0a4c3232353735332c31422c314232362c314232362d31302c323031302c756e6665642c462c3e312c36302c32342e362c3231332e39362c4e412c4e412c332e34352c392e37382c35322c352c352c31332c392e39352c32312e32350d0a4c3232353035382c31422c314232372c314232372d31302c323031302c756e6665642c462c312c37352c32342e34352c3334322e33342c31362e39372c31322e30352c4e412c31302e35372c32342c392c302c31312c4e412c4e410d0a4c3232353035392c31422c314232392c314232392d31302c323031302c756e6665642c462c312c36302c32342e3832352c3332392e36362c4e412c4e412c4e412c392e36322c32372c362c362c31312c31302e36312c32302e39310d0a583239343139382c31422c314232392c314232392d31302c323031302c756e6665642c4d2c312c36302c32352e34352c3436342e362c4e412c4e412c4e412c31302e33322c32372c362c362c31312c31302e36312c32302e39310d0a563237373534332c31422c314233322c314233322d31302c323031302c756e6665642c462c3e312c36362e352c32342e362c3332382e30372c352e34332c31342e31342c332e37322c31302e372c32392c352c342c31312c31312e322c32312e30390d0a4c3232353532352c31422c314233332c314233332d31302c323031302c756e6665642c462c3e312c39362c32342e3732352c3235302e33312c4e412c4e412c4e412c392e36382c33312c362c362c31322c31302e32392c32302e37330d0a4c3232353036302c31422c314233372c314233372d31302c323031302c756e6665642c4d2c3e312c39322e352c32352e322c3333302e39322c4e412c4e412c4e412c31312e33382c32342c31302c392c31312c392e30352c32302e34340d0a583239343136352c31422c314234302c314234302d31302c323031302c756e6665642c4d2c3e312c36302c32342e372c3233382e39322c4e412c4e412c362e35312c392e32362c33332c362c312c31332c392e32312c32302e380d0a583239343135372c31432c314330332c314330332d31302c323031302c6661742c4d2c3e312c38342c32352e31352c3233382e32392c31332e31332c32332e31372c342e38362c31302e37342c33302c362c362c31322c392e382c32302e36310d0a4c3232353338372c31432c314330352c314330352d31302c323031302c6661742c462c312c38352e352c32342e36352c3139312e34312c4e412c4e412c4e412c31302e33342c33312c362c332c31332c382e36342c32302e37370d0a4c3232353536342c31432c314331302c314331302d31302c323031302c6661742c4d2c312c34382c32352e32352c3439392e32342c33362e35342c35382e342c332e38362c31302e36382c32392c332c332c31322c31312e31372c32302e38350d0a4c3232353537362c31432c314331302c314331302d31302c323031302c6661742c462c312c34382c32342e36352c3139392e372c32392e30352c33312e32392c332e35362c31302e322c32392c332c332c31322c31312e31372c32302e38350d0a4c3232353439312c31432c314332302c314332302d31302c323031302c6661742c4d2c312c35392c32352e352c3239352e31322c33372e30342c35372e39342c4e412c31302e382c32392c352c342c31322c31302e38362c32312e34350d0a4c3232353537382c31432c314332302c314332302d31302c323031302c6661742c462c312c36372c32342e34352c3236362e32362c4e412c4e412c302e36352c392e33332c32392c352c342c31322c31302e38362c32312e34350d0a4c3232353339322c31432c314332312c314332312d31302c323031302c6661742c4d2c3e312c37382c32342e39352c3234302e30332c31352e38382c31392e32342c322e39362c31312e33332c33312c31312c392c31322c382e37312c31392e390d0a4c3232353430312c31432c314332312c314332312d31302c323031302c6661742c462c312c37382c32342e3937352c3233372e33352c4e412c4e412c4e412c31302e37312c33312c31312c392c31322c382e37312c31392e390d0a4c3232353731392c31432c314332322c314332322d31302c323031302c6661742c462c312c34362c32342e3837352c3237392e37362c4e412c4e412c372e37382c392e33382c34352c362c342c31322c392e31382c32302e32390d0a4c3232353537342c31432c314332332c314332332d31302c323031302c6661742c462c312c3133352c32352e3032352c3334322e33342c31322e37362c32352e39362c322e37342c392e32332c32392c392c382c31332c31302e30382c32312e34320d0a4c3232353537352c31432c314332332c314332332d31302c323031302c6661742c4d2c312c3133352c32342e39352c3339352e38332c4e412c33302e38322c342e30332c392e38372c32392c392c382c31332c31302e30382c32312e34320d0a4c3232353537392c31432c314332352c314332352d31302c323031302c6661742c4d2c3e312c3132382c32342e3637352c3239302e382c4e412c4e412c4e412c392e392c32382c382c382c31322c31302e32372c32312e31330d0a4c3232353537372c31432c314332362c314332362d31302c323031302c6661742c4d2c3e312c35392c32352e392c3237362e352c4e412c4e412c342e37342c31312e31362c33352c352c342c31322c31312e36392c32322e32370d0a4c3232353637302c31432c314332362c314332362d31302c323031302c6661742c462c312c36372c32342e39352c3234332e39362c31312e32342c32362e31392c332e392c31302e30312c33352c352c342c31322c31312e36392c32322e32370d0a4c3232353732302c31432c314333382c314333382d31302c323031302c6661742c4d2c312c38342c32352e322c3236372e35372c32322e30382c33312e35322c342e38352c392e392c33352c362c362c31322c31302e38362c32312e34350d0a4c3232353734312c31432c314333382c314333382d31302c323031302c6661742c462c312c39362c32342e372c3237362e30382c4e412c4e412c332e31382c392e37352c33352c362c362c31322c31302e38362c32312e34350d0a4c3232353731372c31432c314333392c314333392d31302c323031302c6661742c4d2c312c3132332e352c32342e3632352c3237392e33382c4e412c4e412c4e412c31302e34312c33342c392c382c31332c31302e33332c32312e33380d0a4c3232353731382c31432c314333392c314333392d31302c323031302c6661742c462c312c3132332e352c32342e362c3231382e34342c4e412c4e412c342e35332c392e35312c33342c392c382c31332c31302e33332c32312e33380d0a4c3232353132342c32412c324130382c324130382d31302c323031302c6661742b56452c4d2c312c35302c32342e352c3333332e32312c4e412c4e412c4e412c31302e32342c33312c352c352c31322c31302e332c32302e38320d0a4c3232353632342c32412c324130392c324130392d31302c323031302c6661742b56452c4d2c312c3130372e352c32352e31352c3236382e37312c4e412c4e412c4e412c392e37372c32382c382c362c31322c392e35332c32312e30310d0a4c3232353632382c32412c324130392c324130392d31302c323031302c6661742b56452c462c312c3130372e352c32342e36352c3330302e30372c4e412c4e412c332e31372c392e35322c32382c382c362c31322c392e35332c32312e30310d0a583239343034332c32412c324131312c324131312d31302c323031302c6661742b56452c4d2c3e312c39362c32342e39352c3231322e34382c4e412c4e412c352e31352c31302e37392c33362c362c362c31322c31302e38392c32312e36370d0a563237373136352c32412c324132312c324132312d31302c323031302c6661742b56452c462c3e312c37302c32352e3237352c3332382e30372c4e412c4e412c4e412c31302e38342c32372c392c302c31322c362e312c31382e30380d0a563237373136342c32412c324132322c324132322d31302c323031302c6661742b56452c462c3e312c35342c32352e31352c3237352e34342c4e412c32362e36352c4e412c31312e31392c33302c362c362c31312c31302e35352c32302e35380d0a563237373137392c32412c324132322c324132322d31302c323031302c6661742b56452c4d2c3e312c35342c32342e39352c3238392e36372c32312e34312c32352e39362c4e412c31302e39362c33302c362c362c31312c31302e35352c32302e35380d0a563237373131332c32412c324133342c324133342d31302c323031302c6661742b56452c4d2c3e312c34392c32342e3932352c3232382e32322c4e412c4e412c4e412c31312e30382c32302c372c342c31322c31302e33372c32302e35380d0a4c3232353433352c32412c324133352c324133352d31302c323031302c6661742b56452c462c3e312c39382c32342e312c3232342e36362c4e412c4e412c332e31382c4e412c33312c372c372c31322c31302e35352c32302e36350d0a583831303330382c32412c324133352c324133352d31302c323031302c6661742b56452c4d2c312c35362c32342e3732352c3332302e362c4e412c4e412c4e412c392e38352c33312c372c372c31322c31302e35352c32302e36350d0a4c3232353433362c32412c324133362c324133362d31302c323031302c6661742b56452c4d2c312c3131392c32342e3937352c3231312e31312c4e412c4e412c342e31382c31302e39392c32352c372c372c31312c392e39352c31392e38390d0a4c3232353433372c32412c324133362c324133362d31302c323031302c6661742b56452c462c312c3131392c32342e3537352c3333372e37372c4e412c4e412c4e412c392e342c32352c372c372c31312c392e39352c31392e38390d0a4c3232353433342c32412c324134302c324134302d31302c323031302c6661742b56452c4d2c312c32342c32342e3937352c3236352e31342c4e412c4e412c322e38332c31302e372c33332c332c312c31322c392e30342c31392e34360d0a4c3232353433382c32412c324134302c324134302d31302c323031302c6661742b56452c462c312c32342c32342e3632352c3237302e32362c4e412c4e412c342e34312c31302e33352c33332c332c312c31322c392e30342c31392e34360d0a4c3232353133382c32412c324134322c324134322d31302c323031302c6661742b56452c462c312c37372c32342e392c3330302e30372c4e412c4e412c4e412c31302e38332c32362c372c372c31312c392e342c32302e35390d0a4c3232353433392c32412c324134322c324134322d31302c323031302c6661742b56452c4d2c3e312c3131392c32362e3132352c3334322e33342c4e412c4e412c4e412c31302e33312c32362c372c372c31312c392e342c32302e35390d0a4c3232353732312c32422c324230312c324230312d31302c323031302c756e6665642c4d2c312c36352c32342e3732352c3237322e362c32312e33392c35302e32392c332e30392c31312e31352c34322c352c352c31312c31302e35362c32302e38340d0a4c3232353732322c32422c324230312c324230312d31302c323031302c756e6665642c462c312c36352c32352e30352c3331382e31332c4e412c4e412c332e34372c31312e31392c34322c352c352c31312c31302e35362c32302e38340d0a563237373033322c32422c324230322c324230322d31302c323031302c756e6665642c462c3e312c39302c32352e312c3330312e35382c4e412c4e412c4e412c31302e38342c32392c392c392c31322c31302e37392c32312e36370d0a4c3232353238362c32422c324230352c324230352d31302c323031302c756e6665642c4d2c312c36362c32352e31352c3339372e31312c4e412c4e412c4e412c31302e33382c33312c362c362c31332c31312e38382c32322e31360d0a4c3232353635332c32422c324230382c324230382d31302c323031302c756e6665642c4d2c312c33322c32342e362c3331362e35372c4e412c4e412c352e37312c392e392c34312c342c342c31322c31302e36372c32302e39380d0a4c3232353635342c32422c324230382c324230382d31302c323031302c756e6665642c462c312c33322c32342e3637352c3235312e38332c31352e32322c33312e32392c322e38392c31302e33352c34312c342c342c31322c31302e36372c32302e39380d0a563237373032392c32422c324230392c324230392d31302c323031302c756e6665642c462c3e312c37352c32342e3537352c3235332e31392c4e412c4e412c342e35382c31302c33382c352c352c31332c31302e37382c32312e36370d0a563237373434312c32422c324230392c324230392d31302c323031302c756e6665642c4d2c3e312c37352c32352e3832352c3238382e36342c4e412c4e412c332e37352c31302e372c33382c352c352c31332c31302e37382c32312e36370d0a4c3232353031392c32422c324231322c324231322d31302c323031302c756e6665642c462c312c39382c32352e30352c3537302e35362c4e412c31352e39392c4e412c31302e37342c32382c372c372c31322c31302e34352c32302e38330d0a563237373531302c32422c324231322c324231322d31302c323031302c756e6665642c4d2c3e312c39382c32352c3332342e37382c4e412c4e412c4e412c31302e34342c32382c372c372c31322c31302e34352c32302e38330d0a4c3232353635352c32422c324231362c324231362d31302c323031302c756e6665642c462c312c39382c32342e372c3236342e37342c4e412c4e412c4e412c31302e31392c33342c372c362c31322c382e36322c32302e30390d0a4c3232353237372c32422c324231382c324231382d31302c323031302c756e6665642c462c3e312c35332c32342e35352c3438322e37382c4e412c32372e38312c4e412c392e37342c33302c362c352c31322c31312e30332c32302e36340d0a4c3232353237382c32422c324232302c324232302d31302c323031302c756e6665642c4d2c312c34302c32342e39352c3137312e31372c32392e382c33372e33312c4e412c392e37352c33352c352c352c31322c31302e38322c32312e38310d0a4c3232353635362c32422c324232302c324232302d31302c323031302c756e6665642c462c3e312c38302c32342e392c3236322e382c4e412c4e412c4e412c392e36382c33352c352c352c31322c31302e38322c32312e38310d0a563237373136372c32422c324232352c324232352d31302c323031302c756e6665642c462c3e312c39362c32352e3532352c3138392c31322e37372c31352e37362c4e412c31312e30342c32372c362c362c31322c31302e36372c32302e360d0a4c3232353732332c32422c324232362c324232362d31302c323031302c756e6665642c462c3e312c38342c32342e35352c3233312e392c31382e35382c32342e35372c342e31352c392e39382c33342c362c362c31322c31302e39372c32302e39350d0a4c3232353732352c32422c324232362c324232362d31302c323031302c756e6665642c4d2c312c38342c32352e3337352c3139392e372c4e412c4e412c362e32342c31302e33322c33342c362c362c31322c31302e39372c32302e39350d0a4c3232353538372c32422c324232382c324232382d31302c323031302c756e6665642c462c312c3131322c32342e35372c3232342e34322c4e412c4e412c4e412c392e36372c33302c382c382c31322c31312e30372c32312e33320d0a583239343337332c32422c324232382c324232382d31302c323031302c756e6665642c4d2c312c3132382c32352e3037352c3238312e34382c32302e32342c32372e35382c352e32362c31302e36352c33302c382c382c31322c31312e30372c32312e33320d0a4c3232353636332c32422c324233302c324233302d31302c323031302c756e6665642c4d2c312c38342c32352e322c3231382e34342c4e412c4e412c4e412c31302e38352c33302c362c362c31322c31312e39372c32322e30360d0a4c3232353732342c32422c324233302c324233302d31302c323031302c756e6665642c462c312c39362c32352e32352c3235352e33392c4e412c4e412c332e39332c31312e35312c33302c362c362c31322c31312e39372c32322e30360d0a4c3232353330382c32432c324330332c324330332d31302c323031302c6661742c4d2c312c33392e352c32342e322c3338332e30392c4e412c4e412c4e412c392e37362c33302c352c332c31332c31302e30342c32302e36330d0a563237373431302c32432c324330332c324330332d31302c323031302c6661742c462c3e312c36392c32342e312c3433302e36382c4e412c4e412c332e31332c392e32372c33302c352c332c31332c31302e30342c32302e36330d0a4c3232353331342c32432c324330362c324330362d31302c323031302c6661742c462c3e312c36332c32342e382c3236362e32362c4e412c4e412c4e412c392e37342c33322c372c362c31322c392e382c32302e37370d0a4c3232353331372c32432c324330362c324330362d31302c323031302c6661742c4d2c3e312c36332c32352e3437352c3233322e31362c4e412c4e412c4e412c31302e38352c33322c372c362c31322c392e382c32302e37370d0a4c3232353434362c32432c324330372c324330372d31302c323031302c6661742c4d2c312c38322e352c32352e3237352c3237322e31312c4e412c4e412c4e412c392e38362c32382c372c332c31322c382e34312c31382e39310d0a563237373738312c32432c324330372c324330372d31302c323031302c6661742c462c3e312c38322e352c32342e372c3235382e34332c4e412c4e412c362e38312c31302e31312c32382c372c332c31322c382e34312c31382e39310d0a4c3232353331302c32432c324330382c324330382d31302c323031302c6661742c4d2c312c36332c32342e37352c3332342e30382c31382e33362c32332e38372c4e412c392e39362c33342c372c372c31332c31302e37362c32302e38380d0a4c3232353331382c32432c324330382c324330382d31302c323031302c6661742c462c312c36332c32342e3732352c3238302e33392c37302e39312c31342e33372c4e412c31302e31362c33342c372c372c31332c31302e37362c32302e38380d0a583831303437382c32432c324331332c324331332d31302c323031302c6661742c462c3e312c34382c32342e38352c3339372e31312c4e412c4e412c332e36362c392e35392c32362c332c332c31322c31302e33382c32302e38380d0a583831303437372c32432c324331352c324331352d31302c323031302c6661742c4d2c3e312c3131362e352c32352e332c3237302e30362c4e412c4e412c342e33332c392e34352c33352c372c362c31332c392e34342c32312e31370d0a4c3232353535322c32432c324331362c324331362d31302c323031302c6661742c462c3e312c39362c32332e38352c3232352e30352c31382e33342c31332e36372c332e31372c392e31352c33382c362c362c31322c392e39342c32302e35350d0a4c3232353730392c32432c324331362c324331362d31302c323031302c6661742c4d2c3e312c39362c32352e3032352c3234352c4e412c4e412c4e412c31302e30362c33382c362c362c31322c392e39342c32302e35350d0a4c3232353235392c32432c324331382c324331382d31302c323031302c6661742c462c3e312c39322c32342e372c4e412c4e412c4e412c332e36382c392e37332c32342c392c352c31322c382e37362c31392e35340d0a563237373130362c32432c324331382c324331382d31302c323031302c6661742c4d2c3e312c39322c32352e3432352c313032372e30312c32372e32372c33322e34342c4e412c31312e30332c32342c392c352c31322c382e37362c31392e35340d0a563237373133332c32432c324331392c324331392d31302c323031302c6661742c462c3e312c38372c32342e36352c3236322e34362c32302e34332c32312e37382c332e37372c392e35312c32342c372c362c31322c31302e312c32302e36330d0a4c3232353732372c32432c324332312c324332312d31302c323031302c6661742c4d2c312c39382c32342e3832352c3239382e31362c4e412c4e412c4e412c392e38392c33392c372c372c31322c392e39312c32302e36350d0a563237373034382c32432c324332312c324332312d31302c323031302c6661742c462c3e312c39382c32342e3937352c3234372e32342c4e412c4e412c322e35322c31302e34352c33392c372c372c31322c392e39312c32302e36350d0a4c3232353332322c32432c324332362c324332362d31302c323031302c6661742c4d2c3e312c3132392c32352e3337352c3239352e35322c4e412c4e412c4e412c31302e32312c32362c392c352c31322c392e35342c31392e39350d0a563237373138362c32432c324332362c324332362d31302c323031302c6661742c462c3e312c3132392c32342e3837352c3239342e37392c4e412c4e412c322e38392c31302e31362c32362c392c352c31322c392e35342c31392e39350d0a4c3232353235322c32432c324333312c324333312d31302c323031302c6661742c462c312c33302c32342e322c3539312e36392c4e412c4e412c4e412c392e39352c33362c352c352c31322c31302e342c32312e35350d0a4c3232353730382c32432c324333312c324333312d31302c323031302c6661742c4d2c312c38302c32352c3334322e33342c4e412c4e412c372e30342c392e34342c33362c352c352c31322c31302e342c32312e35350d0a4c3232353030382c32432c324333352c324333352d31302c323031302c6661742c4d2c3e312c34332e352c32342e3432352c3336312e33352c4e412c32392e36362c4e412c31302e35322c31392c362c322c31332c362e39322c31382e33390d0a4c3232353332382c32432c324333372c324333372d31302c323031302c6661742c4d2c312c34392c32352e3032352c3331322e37352c4e412c4e412c342e31352c31302e322c33342c382c352c31322c372e372c31392e31390d0a4c3232353731302c32432c324333372c324333372d31302c323031302c6661742c462c3e312c38392c32342e3332352c3331382e37332c4e412c4e412c352e32332c392e35312c33342c382c352c31322c372e372c31392e31390d0a4c3232353535382c32432c324333382c324333382d31302c323031302c6661742c462c3e312c31362c32342e352c3234312e36352c372e30332c31332e34342c332e38332c31302e39342c34302c322c322c31322c31312e34372c32312e32390d0a563237373536382c32432c324334302c324334302d31302c323031302c6661742c4d2c3e312c33352c32342e3937352c3337362e35372c4e412c4e412c4e412c31302e36362c33332c352c342c31322c382e31372c31382e39360d0a4c3232353030362c33412c334130332c334130332d31302c323031302c6661742b56452c462c3e312c33382e352c32342e342c3334322e33342c4e412c4e412c4e412c31302e322c32312c362c352c31332c392e32362c32302e34360d0a4c3232353035372c33412c334130332c334130332d31302c323031302c6661742b56452c4d2c312c37382e352c32342e38352c3331362e342c32302c32302e31362c4e412c31302e33392c32312c362c352c31332c392e32362c32302e34360d0a4c3232353337332c33412c334130362c334130362d31302c323031302c6661742b56452c4d2c312c3131322c32342c3236322e382c4e412c4e412c332e38382c392e34312c32392c372c372c31322c392e34312c32302e36380d0a563237373436322c33412c334130362c334130362d31302c323031302c6661742b56452c462c3e312c3131322c32342e3337352c3139362e35332c392c31312e35392c342e34362c392e36372c32392c372c372c31322c392e34312c32302e36380d0a4c3232353336372c33412c334130372c334130372d31302c323031302c6661742b56452c4d2c312c36342c32342e372c3233382e32392c4e412c4e412c312e37392c392e35312c33302c382c382c31322c382e39362c32302e34390d0a4c3232353336382c33412c334130372c334130372d31302c323031302c6661742b56452c462c312c36342c32342e3932352c3230312e322c4e412c4e412c332e332c31302e31372c33302c382c382c31322c382e39362c32302e34390d0a4c3232353630322c33412c334130382c334130382d31302c323031302c6661742b56452c4d2c312c3130322c32342e35352c3231372e31382c4e412c4e412c332e30392c392e30322c32392c362c362c31332c392e38342c32302e38370d0a4c3232353733362c33412c334131322c334131322d31302c323031302c6661742b56452c462c312c35332e352c32352e322c3238352e32382c4e412c4e412c342e30322c31302e34312c34382c362c302c31332c4e412c4e410d0a4c3232353337362c33412c334131342c334131342d31302c323031302c6661742b56452c4d2c312c38352c32342e392c3233342e33392c4e412c4e412c372e31372c392e37312c32392c362c302c31312c372e33342c31382e39370d0a4c3232353639362c33412c334131352c334131352d31302c323031302c6661742b56452c4d2c312c37382c32352e3032352c3238392e30382c4e412c4e412c4e412c31302e33352c34302c362c362c31322c31302e38372c32302e39310d0a4c3232353732382c33412c334131352c334131352d31302c323031302c6661742b56452c462c3e312c39362c32342e3737352c3235392e33352c4e412c4e412c342e34352c392e33362c34302c362c362c31322c31302e38372c32302e39310d0a4c3232353337372c33412c334131362c334131362d31302c323031302c6661742b56452c462c312c39362c32352e3137352c3230362e38332c4e412c4e412c332e33322c392e39392c32372c362c362c31322c31302e36322c32302e37370d0a4c3232353639382c33412c334131392c334131392d31302c323031302c6661742b56452c4d2c3e312c33312e352c32332e39352c3233322e31362c4e412c4e412c4e412c392e35352c34372c362c302c31312c4e412c4e410d0a583831303439372c33412c334131392c334131392d31302c323031302c6661742b56452c462c3e312c33312e352c32342e38352c3332342e37382c4e412c4e412c4e412c31302e31392c34372c362c302c31312c4e412c4e410d0a4c3232353639372c33412c334133302c334133302d31302c323031302c6661742b56452c4d2c312c37382c32352e3637352c3232342e38372c31312e33312c31362e32322c332e30312c31302e38382c33382c362c362c31322c31302e38362c32302e37350d0a563237373034362c33412c334133302c334133302d31302c323031302c6661742b56452c462c3e312c37382c32352e312c3233352e35392c4e412c4e412c4e412c31302e342c33382c362c362c31322c31302e38362c32302e37350d0a4c3232353639352c33412c334133332c334133332d31302c323031302c6661742b56452c462c312c36332c32342e32352c3236362e32362c32392e31342c32392e322c322e33332c392e32322c33332c372c372c31322c31302e30392c32312e33350d0a4c3232353734362c33412c334133332c334133332d31302c323031302c6661742b56452c4d2c3e312c3130352c32352e3232352c3232342e39362c4e412c4e412c4e412c392e38332c33332c372c372c31322c31302e30392c32312e33350d0a4c3232353039332c33422c334230322c334230322d31302c323031302c756e6665642c4d2c312c39302c32352e31352c3338392e35352c32362e30332c32332e38372c4e412c31302e39372c32322c362c362c31312c392e34382c31392e38320d0a4c3232353039342c33422c334230322c334230322d31302c323031302c756e6665642c462c312c39302c32342e342c3335372e32322c32322e30312c31392e34372c4e412c31302e30312c32322c362c362c31312c392e34382c31392e38320d0a4c3232353030372c33422c334230332c334230332d31302c323031302c756e6665642c462c3e312c38302c32342e3637352c3331352e31372c4e412c4e412c4e412c31302e32392c32332c372c352c31312c392e35322c31392e38340d0a4c3232353039352c33422c334230332c334230332d31302c323031302c756e6665642c4d2c3e312c38302c32352e32352c3331352e37312c4e412c4e412c4e412c31302e34372c32332c372c352c31312c392e35322c31392e38340d0a4c3232353039362c33422c334230382c334230382d31302c323031302c756e6665642c462c312c35372e352c32342e36352c3338362e37312c4e412c4e412c4e412c31302e31352c32392c372c362c31332c31312e322c32312e33320d0a4c3232353437302c33422c334231372c334231372d31302c323031302c756e6665642c4d2c3e312c34302c32352e35352c3338342e362c31372e372c32362e38382c342e35392c31312e30322c33392c352c302c31322c4e412c4e410d0a4c3232353437312c33422c334231372c334231372d31302c323031302c756e6665642c462c3e312c34302c32352e342c3139382e39362c4e412c4e412c4e412c31302e31362c33392c352c302c31322c4e412c4e410d0a563237373637342c33422c334231382c334231382d31302c323031302c756e6665642c4d2c3e312c38362e352c32342e392c3330382e312c4e412c4e412c4e412c31302e34332c32362c392c362c31332c31302e31382c32302e31310d0a4c3232353039372c33422c334231392c334231392d31302c323031302c756e6665642c462c3e312c34332c32342e35352c3330342e332c4e412c4e412c332e37332c31302e35332c33312c352c342c31322c31302e31322c32302e32370d0a563237373436312c33422c334232302c334232302d31302c323031302c756e6665642c462c3e312c33322c32342e3932352c3231362e38312c4e412c4e412c332e34382c31302e35392c33322c322c322c31322c31322e30342c32312e36340d0a583239343035332c33432c334330312c334330312d31302c323031302c6661742c4d2c3e312c34342c32342e36352c3437362e31322c31372e32332c32322e39342c4e412c31302e34352c32322c342c342c31322c31302e352c32312e33390d0a4c3232353031322c33432c334330352c334330352d31302c323031302c6661742c462c312c35332c32342e3432352c3335342e33352c4e412c4e412c4e412c392e38392c32352c362c342c31322c382c31392e30340d0a4c3232353031332c33432c334330352c334330352d31302c323031302c6661742c4d2c312c35332c32342e39352c3238392e36372c4e412c4e412c4e412c31302e33382c32352c362c342c31322c382c31392e30340d0a4c3232353437322c33432c334330392c334330392d31302c323031302c6661742c462c312c39382e352c32352e352c3338322e30332c4e412c4e412c4e412c31302e31382c33362c372c362c31312c31302e30382c32302e39310d0a583831303239362c33432c334330392c334330392d31302c323031302c6661742c4d2c312c38302e352c32352e3237352c3330382e312c33382e33322c32342e312c4e412c31302e38392c33362c372c362c31312c31302e30382c32302e39310d0a583239343035352c33432c334331302c334331302d31302c323031302c6661742c462c3e312c37302c32352e352c3532382e35322c31332e30332c31312e31322c4e412c31302e36312c32372c372c372c31312c392e33372c32302e32330d0a583239343139342c33432c334331302c334331302d31302c323031302c6661742c4d2c3e312c37302c32342e3837352c3638342e36372c4e412c4e412c4e412c392e35372c32372c372c372c31312c392e33372c32302e32330d0a583239343033382c33432c334331312c334331312d31302c323031302c6661742c4d2c3e312c3130382c32342e36352c3239322e34312c4e412c31382e35342c4e412c31302e31342c32312c392c362c31322c382e35382c32302e33310d0a583239343033392c33432c334331312c334331312d31302c323031302c6661742c462c3e312c3130382c32342e392c3835302e31332c4e412c4e412c362e32332c31302e32322c32312c392c362c31322c382e35382c32302e33310d0a583239343131342c33432c334331372c334331372d31302c323031302c6661742c4d2c312c3130322c32352e34352c3332302e39342c31342e34332c32362e36352c342e35372c31302e34362c33342c362c362c31322c31302e35342c32312e31330d0a4c3232353035352c33432c334332302c334332302d31302c323031302c6661742c462c3e312c38332c32342e3537352c3532382e35322c4e412c4e412c4e412c31302e31382c32322c392c302c31322c382e36342c31392e38380d0a583239343139332c33432c334332302c334332302d31302c323031302c6661742c4d2c3e312c38332c32342e34352c3436362e38322c4e412c31362e34352c4e412c31302e32322c32322c392c302c31322c382e36342c31392e38380d0a4c3232353035362c33432c334332362c334332362d31302c323031302c6661742c462c312c31382c32342e3432352c3337312e37382c4e412c4e412c4e412c31302e34352c32362c322c322c31332c31312e32352c32312e32310d0a583239343131322c33432c334332362c334332362d31302c323031302c6661742c4d2c312c31382c32352e362c3432352e37322c4e412c4e412c4e412c31302e342c32362c322c322c31332c31312e32352c32312e32310d0a4c3232353037332c33432c334333322c334333322d31302c323031302c6661742c462c312c34382e352c32342e3832352c3336332e30382c4e412c32302e31362c4e412c31302e39362c33302c372c332c31332c352e37322c31382e32340d0a, 33339⟩

def pcs_c0 : Claim :=
  { column := some (b "patoc"),
    filter := [],
    stat := .min,
    naTokens := [b "", b "NA"],
    scale := ((1 : Rat) / 1),
    reported := b "3.30" }

def pcs_c1 : Claim :=
  { column := some (b "patoc"),
    filter := [],
    stat := .max,
    naTokens := [b "", b "NA"],
    scale := ((1 : Rat) / 1),
    reported := b "70.91" }

theorem pcs_batch : runAll pcs_src [pcs_c0, pcs_c1] =
    [.checked .consistent (.rat ((33 : Rat) / 10)) 124 227,
    .checked .consistent (.rat ((7091 : Rat) / 100)) 124 227] := by decide +kernel

theorem pcs_claim_0 : run pcs_src pcs_c0 = .checked .consistent (.rat ((33 : Rat) / 10)) 124 227 :=
  run_of_runAll pcs_batch 0 rfl rfl
#print axioms pcs_claim_0

theorem pcs_claim_1 : run pcs_src pcs_c1 = .checked .consistent (.rat ((7091 : Rat) / 100)) 124 227 :=
  run_of_runAll pcs_batch 1 rfl rfl
#print axioms pcs_claim_1

