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

def pcs_src : Source := ⟨0x4861706c6f747970652c42494e2c53697465732c6e2073657175656e6365732c436f6c6c656374696f6e20436f64652c457861637420536974650d0a4e432d3030312c424f4c443a414355353038342c4e2c392c47494e5630312c47494e5630310d0a4e432d3030312c424f4c443a414355353038342c512c312c475452432c475452430d0a4e432d3030322c424f4c443a414355343530322c4d2c322c47494e5630322c47494e5630320d0a4e432d3030322c424f4c443a414355343530322c4d2c312c4e4231362d3034382c5369746530380d0a4e432d3030332c424f4c443a414355353038342c4d2c312c47494e5630322c47494e5630320d0a4e432d3030342c424f4c443a414355343235332c4d2c322c47494e5630322c47494e5630320d0a4e432d3030352c424f4c443a414355343430352c4d2c312c47494e5630322c47494e5630320d0a4e432d3030362c424f4c443a414355343231332c462c312c47494e5631322c47494e5631320d0a4e432d3030362c424f4c443a414355343231332c472c312c47494e5631342c47494e5631340d0a4e432d3030372c424f4c443a414355353136342c472c312c47494e5631332c47494e5631330d0a4e432d3030382c424f4c443a414355353136362c472c312c47494e5631332c47494e5631330d0a4e432d3030392c424f4c443a414355353136352c472c312c47494e5631332c47494e5631330d0a4e432d3031302c424f4c443a414357353630382c472c322c47494e5631332c47494e5631330d0a4e432d3031312c424f4c443a414355353136362c472c312c47494e5631332c47494e5631330d0a4e432d3031322c424f4c443a414355353035342c472c312c47494e5631342c47494e5631340d0a4e432d3031332c424f4c443a414355353237332c472c312c47494e5631342c47494e5631340d0a4e432d3031342c424f4c443a414355353237332c472c312c47494e5631342c47494e5631340d0a4e432d3031352c424f4c443a414355353237332c472c312c47494e5631342c47494e5631340d0a4e432d3031352c424f4c443a414355353237332c4f2c362c4e4231362d3030352c5369746530320d0a4e432d3031362c424f4c443a414355353035342c472c312c47494e5631342c47494e5631340d0a4e432d3031372c424f4c443a414355353237332c472c312c47494e5631342c47494e5631340d0a4e432d3031382c424f4c443a414355343231332c472c312c47494e5631342c47494e5631340d0a4e432d3031392c424f4c443a414357353234302c472c312c47494e5631332c47494e5631330d0a4e432d3032302c424f4c443a414355353136342c472c312c47494e5631332c47494e5631330d0a4e432d3032312c424f4c443a414357353631352c472c312c47494e5631332c47494e5631330d0a4e432d3032322c424f4c443a414357353630382c472c332c47494e5631332c47494e5631330d0a4e432d3032332c424f4c443a414357353630372c472c312c4e4231362d3033342c4331342d31340d0a4e432d3032332c424f4c443a414357353630372c472c322c47494e5631332c47494e5631330d0a4e432d3032342c424f4c443a414357353630362c472c332c47494e5631332c47494e5631330d0a4e432d3032352c424f4c443a414357353535342c472c312c47494e5631332c47494e5631330d0a4e432d3032362c424f4c443a414355353136342c472c312c47494e5631332c47494e5631330d0a4e432d3032372c424f4c443a414355353136352c472c312c47494e5631332c47494e5631330d0a4e432d3032382c424f4c443a414355353136362c472c312c47494e5631332c47494e5631330d0a4e432d3032392c424f4c443a414357353535332c472c312c47494e5631332c47494e5631330d0a4e432d3033302c424f4c443a414442363633322c502c312c4e4231362d3030372c5369746530330d0a4e432d3033302c424f4c443a414442363633322c502c392c4e4231362d3030382c5369746530330d0a4e432d3033312c424f4c443a414442353730312c4f2c312c4e4231362d3030362c5369746530320d0a4e432d3033322c424f4c443a414442353730312c4f2c312c4e4231362d3030362c5369746530320d0a4e432d3033322c424f4c443a414442353730312c502c312c4e4231362d3030372c5369746530330d0a4e432d3033332c424f4c443a414442353730312c4f2c312c4e4231362d3030352c5369746530320d0a4e432d3033332c424f4c443a414442353730312c4f2c342c4e4231362d3030362c5369746530320d0a4e432d3033342c424f4c443a414442363338312c502c312c4e4231362d3030372c5369746530330d0a4e432d3033352c424f4c443a414442363633322c502c312c4e4231362d3030372c5369746530330d0a4e432d3033362c424f4c443a414355353237332c4f2c322c4e4231362d3030352c5369746530320d0a4e432d3033372c424f4c443a414355343231332c4f2c332c4e4231362d3030352c5369746530320d0a4e432d3033382c424f4c443a414442353730312c432c312c4e4231362d3032352c4331342d30380d0a4e432d3033392c424f4c443a414442363330352c432c312c4e4231362d3032352c4331342d30380d0a4e432d3033392c424f4c443a414442363330352c432c312c4e4231362d3032362c4331342d30380d0a4e432d3034302c424f4c443a414442363330352c432c342c4e4231362d3032352c4331342d30380d0a4e432d3034302c424f4c443a414442363330352c432c332c4e4231362d3032362c4331342d30380d0a4e432d3034302c424f4c443a414442363330352c4a2c312c4e4231362d3034362c5369746530360d0a4e432d3034312c424f4c443a414442363330352c432c312c4e4231362d3032352c4331342d30380d0a4e432d3034322c424f4c443a414355343430352c4c2c312c4e4231362d3034372c5369746530370d0a4e432d3034322c424f4c443a414355343430352c4d2c322c4e4231362d3034382c5369746530380d0a4e432d3034332c424f4c443a414355343430352c4d2c322c4e4231362d3034382c5369746530380d0a4e432d3034342c424f4c443a414355343530322c4d2c312c4e4231362d3034382c5369746530380d0a4e432d3034352c424f4c443a414355343530322c4d2c312c4e4231362d3034382c5369746530380d0a4e432d3034362c424f4c443a414442363338342c412c312c4e4231362d3031382c4331342d30320d0a4e432d3034372c424f4c443a414442363633332c442c332c4e4231362d3032392c4331342d31300d0a4e432d3034382c424f4c443a414442363338322c442c332c4e4231362d3032382c4331342d31300d0a4e432d3034382c424f4c443a414442363338322c442c312c4e4231362d3032392c4331342d31300d0a4e432d3034392c424f4c443a414442363633322c422c382c4e4231362d3032332c4331342d30360d0a4e432d3035302c424f4c443a414442363633322c422c312c4e4231362d3032332c4331342d30360d0a4e432d3035312c424f4c443a414442363633322c422c322c4e4231362d3032332c4331342d30360d0a4e432d3035322c424f4c443a414442363633322c422c312c4e4231362d3032332c4331342d30360d0a4e432d3035332c424f4c443a414442353730312c432c322c4e4231362d3032362c4331342d30380d0a4e432d3035342c424f4c443a414442353730312c432c312c4e4231362d3032362c4331342d30380d0a4e432d3035352c424f4c443a414442353730312c432c332c4e4231362d3032362c4331342d30380d0a4e432d3035362c424f4c443a414442353730312c432c352c4e4231362d3032362c4331342d30380d0a4e432d3035372c424f4c443a414442363338332c432c312c4e4231362d3032362c4331342d30380d0a4e432d3035382c424f4c443a414442353730312c432c312c4e4231362d3032362c4331342d30380d0a4e432d3035392c424f4c443a414442363338332c432c312c4e4231362d3032362c4331342d30380d0a4e432d3036302c424f4c443a414355343430352c4c2c312c4e4231362d3034372c5369746530370d0a4e432d3036312c424f4c443a414355343430352c4c2c332c4e4231362d3034372c5369746530370d0a4e432d3036322c424f4c443a414442363338332c4c2c322c4e4231362d3034372c5369746530370d0a4e432d3036332c424f4c443a414355343430352c4c2c312c4e4231362d3034372c5369746530370d0a4e432d3036342c424f4c443a414355343430352c4c2c322c4e4231362d3034372c5369746530370d0a4e432d3036352c424f4c443a414355343530322c4c2c322c4e4231362d3034372c5369746530370d0a4e432d3036362c424f4c443a414355343530322c4c2c312c4e4231362d3034372c5369746530370d0a4e432d3036372c424f4c443a414355343530322c4c2c312c4e4231362d3034372c5369746530370d0a4e432d3036382c424f4c443a414355343530322c4c2c312c4e4231362d3034372c5369746530370d0a4e432d3036392c424f4c443a414355343530322c4c2c312c4e4231362d3034372c5369746530370d0a4e432d3037302c424f4c443a414355343530322c4c2c312c4e4231362d3034372c5369746530370d0a4e432d3037312c424f4c443a414355343530322c4c2c312c4e4231362d3034372c5369746530370d0a4e432d3037322c424f4c443a414355343530322c4c2c312c4e4231362d3034372c5369746530370d0a4e432d3037332c424f4c443a414355343430352c4c2c312c4e4231362d3034372c5369746530370d0a4e432d3037342c424f4c443a414442353730312c522c31352c4e4231362d3035352c5369746531330d0a4e432d3037352c424f4c443a414442353730312c522c322c4e4231362d3035352c5369746531330d0a4e432d3037362c424f4c443a414355343430352c4d2c312c4e4231362d3034382c5369746530380d0a4e432d3037372c424f4c443a414355343430352c4d2c322c4e4231362d3034382c5369746530380d0a4e432d3037382c424f4c443a414355343430352c4d2c332c4e4231362d3034382c5369746530380d0a4e432d3037392c424f4c443a414355343530322c4d2c312c4e4231362d3034382c5369746530380d0a4e432d3038302c424f4c443a414355343430352c4d2c312c4e4231362d3034382c5369746530380d0a4e432d3038312c424f4c443a414355343430352c4d2c312c4e4231362d3034382c5369746530380d0a4e432d3038322c424f4c443a414355343430352c4d2c312c4e4231362d3034382c5369746530380d0a4e432d3038332c424f4c443a414355343530322c4d2c342c4e4231362d3034382c5369746530380d0a4e432d3038342c424f4c443a414442353730312c4d2c312c4e4231362d3034382c5369746530380d0a4e432d3038352c424f4c443a414355343430352c4d2c312c4e4231362d3034382c5369746530380d0a4e432d3038362c424f4c443a414442363633322c502c312c4e4231362d3030382c5369746530330d0a4e432d3038372c424f4c443a414442363633322c502c312c4e4231362d3030382c5369746530330d0a4e432d3038382c424f4c443a414442353730312c522c342c4e4231362d3035352c5369746531330d0a4e432d3038392c424f4c443a414442353730312c522c322c4e4231362d3035352c5369746531330d0a4e432d3039302c424f4c443a414355343530322c4c2c322c4e4231362d3034372c5369746530370d0a4e432d3039312c424f4c443a414355343530322c4c2c312c4e4231362d3034372c5369746530370d0a4e432d3039322c424f4c443a414355343530322c4c2c312c4e4231362d3034372c5369746530370d0a4e432d3039332c424f4c443a414442363337382c4b2c392c4e4231362d3034332c4331342d32300d0a4e432d3039332c424f4c443a414442363337382c4b2c362c4e4231362d3034352c4331342d32300d0a4e432d3039342c424f4c443a414442363330302c4b2c372c4e4231362d3034332c4331342d32300d0a4e432d3039352c424f4c443a414442353731342c492c31312c4e4231362d3034322c4331342d31380d0a4e432d3039362c424f4c443a414442353731342c492c322c4e4231362d3034322c4331342d31380d0a4e432d3039372c424f4c443a414443303438332c492c322c4e4231362d3034322c4331342d31380d0a4e432d3039382c424f4c443a414443303438332c492c312c4e4231362d3034322c4331342d31380d0a4e432d3039392c424f4c443a414442363330322c482c312c4e4231362d3033392c4331342d31360d0a4e432d3130302c424f4c443a414442363239392c482c322c4e4231362d3033382c4331342d31360d0a4e432d3130312c424f4c443a414442363330322c482c322c4e4231362d3033382c4331342d31360d0a4e432d3130322c424f4c443a414442363330312c482c342c4e4231362d3033382c4331342d31360d0a4e432d3130332c424f4c443a414442363034372c472c312c4e4231362d3033362c4331342d31340d0a4e432d3130342c424f4c443a414442363034372c472c352c4e4231362d3033362c4331342d31340d0a4e432d3130352c424f4c443a414442363034372c472c332c4e4231362d3033362c4331342d31340d0a4e432d3130362c424f4c443a414442363034372c472c312c4e4231362d3033362c4331342d31340d0a4e432d3130372c424f4c443a414442363034372c472c312c4e4231362d3033362c4331342d31340d0a4e432d3130382c424f4c443a414442363034372c472c322c4e4231362d3033362c4331342d31340d0a4e432d3130392c424f4c443a414355353035342c472c312c4e4231362d3033352c4331342d31340d0a4e432d3131302c424f4c443a414355353035342c472c322c4e4231362d3033352c4331342d31340d0a4e432d3131312c424f4c443a414355353035342c472c322c4e4231362d3033352c4331342d31340d0a4e432d3131322c424f4c443a414355353035342c472c312c4e4231362d3033352c4331342d31340d0a4e432d3131332c424f4c443a414355353035342c472c312c4e4231362d3033342c4331342d31340d0a4e432d3131332c424f4c443a414355353035342c472c312c4e4231362d3033352c4331342d31340d0a4e432d3131342c424f4c443a414355353035342c472c312c4e4231362d3033352c4331342d31340d0a4e432d3131352c424f4c443a414355353035342c472c312c4e4231362d3033352c4331342d31340d0a4e432d3131362c424f4c443a414355353035342c472c312c4e4231362d3033352c4331342d31340d0a4e432d3131372c424f4c443a414443303533342c4b2c312c4e4231362d3034352c4331342d32300d0a4e432d3131382c424f4c443a414443303533332c4b2c312c4e4231362d3034352c4331342d32300d0a4e432d3131392c424f4c443a414442363337392c4b2c312c4e4231362d3034352c4331342d32300d0a4e432d3132302c424f4c443a414443303533352c4b2c312c4e4231362d3034352c4331342d32300d0a4e432d3132312c424f4c443a414443303533342c4b2c312c4e4231362d3034352c4331342d32300d0a4e432d3132322c424f4c443a414442363338322c442c322c4e4231362d3032382c4331342d31300d0a4e432d3132332c424f4c443a414442363338322c442c322c4e4231362d3032382c4331342d31300d0a4e432d3132342c424f4c443a414442363338322c442c312c4e4231362d3032382c4331342d31300d0a4e432d3132352c424f4c443a414442363338322c442c312c4e4231362d3032382c4331342d31300d0a4e432d3132362c424f4c443a414442363338322c442c312c4e4231362d3032382c4331342d31300d0a4e432d3132372c424f4c443a414442363338322c442c312c4e4231362d3032382c4331342d31300d0a4e432d3132382c424f4c443a414442363338322c432c322c4e4231362d3032372c4331342d30380d0a4e432d3132392c424f4c443a414443303533362c4b2c312c4e4231362d3034342c4331342d32300d0a4e432d3133302c424f4c443a414355353035342c472c312c4e4231362d3033342c4331342d31340d0a4e432d3133312c424f4c443a414357353630382c472c312c4e4231362d3033342c4331342d31340d0a4e432d3133322c424f4c443a414357353630382c472c312c4e4231362d3033342c4331342d31340d0a4e432d3133332c424f4c443a414357353535332c472c312c4e4231362d3033342c4331342d31340d0a4e432d3133342c424f4c443a414357353630382c472c312c4e4231362d3033342c4331342d31340d0a4e432d3133352c424f4c443a414442393930342c472c312c4e4231362d3033342c4331342d31340d0a4e432d3133362c424f4c443a414357353630382c472c312c4e4231362d3033342c4331342d31340d0a4e432d3133372c424f4c443a414355353035342c472c312c4e4231362d3033342c4331342d31340d0a4e432d3133382c424f4c443a414442363337392c4b2c322c4e4231362d3034332c4331342d32300d0a4e432d3133382c424f4c443a414442363337392c4b2c332c4e4231362d3034352c4331342d32300d0a4e432d3133392c424f4c443a414442363034382c4b2c322c4e4231362d3034352c4331342d32300d0a4e432d3134302c424f4c443a414442363337392c4b2c312c4e4231362d3034332c4331342d32300d0a4e432d3134302c424f4c443a414442363337392c4b2c312c4e4231362d3034352c4331342d32300d0a4e432d3134312c424f4c443a414442363337392c4b2c322c4e4231362d3034332c4331342d32300d0a4e432d3134312c424f4c443a414442363337392c4b2c322c4e4231362d3034352c4331342d32300d0a4e432d3134322c424f4c443a414442363330332c4b2c312c4e4231362d3034352c4331342d32300d0a4e432d3134332c424f4c443a414442363337392c4b2c312c4e4231362d3034352c4331342d32300d0a4e432d3134342c424f4c443a414442363337392c4b2c312c4e4231362d3034352c4331342d32300d0a4e432d3134352c424f4c443a414442363337392c4b2c312c4e4231362d3034352c4331342d32300d0a4e432d3134362c424f4c443a414442363337392c4b2c312c4e4231362d3034352c4331342d32300d0a4e432d3134372c424f4c443a414442363337392c4b2c322c4e4231362d3034332c4331342d32300d0a4e432d3134382c424f4c443a414442363337392c4b2c312c4e4231362d3034332c4331342d32300d0a4e432d3134392c424f4c443a414442353731342c492c312c4e4231362d3034322c4331342d31380d0a4e432d3135302c424f4c443a414442363737332c492c312c4e4231362d3034322c4331342d31380d0a4e432d3135312c424f4c443a414442363535352c482c312c4e4231362d3033382c4331342d31360d0a4e432d3135322c424f4c443a414442363330322c482c312c4e4231362d3033382c4331342d31360d0a4e432d3135332c424f4c443a414355353035342c472c312c4e4231362d3033352c4331342d31340d0a4e432d3135342c424f4c443a414442363034372c472c312c4e4231362d3033362c4331342d31340d0a4e432d3135352c424f4c443a414442363034372c472c312c4e4231362d3033362c4331342d31340d0a4e432d3135362c424f4c443a414442363034372c472c312c4e4231362d3033362c4331342d31340d0a4e432d3135372c424f4c443a414442363034372c472c312c4e4231362d3033362c4331342d31340d0a4e432d3135382c424f4c443a414442363034372c472c312c4e4231362d3033362c4331342d31340d0a4e432d3135392c424f4c443a414442363034372c472c312c4e4231362d3033362c4331342d31340d0a4e432d3136302c424f4c443a414442363034372c472c312c4e4231362d3033362c4331342d31340d0a4e432d3136312c424f4c443a414442363034372c472c312c4e4231362d3033362c4331342d31340d0a4e432d3136322c424f4c443a414442353730312c452c312c4e4231362d3033332c4331342d31320d0a4e432d3136332c424f4c443a414355343430352c452c312c4e4231362d3033332c4331342d31320d0a4e432d3136342c424f4c443a414442363338332c452c312c4e4231362d3033332c4331342d31320d0a4e432d3136352c424f4c443a414355343430352c4d2c312c4e4231362d3034382c5369746530380d0a4e432d3136362c424f4c443a414355343530322c4d2c322c4e4231362d3034382c5369746530380d0a4e432d3136372c424f4c443a414355343530322c4d2c312c4e4231362d3034382c5369746530380d0a4e432d3136382c424f4c443a414355343430352c4d2c312c4e4231362d3034382c5369746530380d0a4e432d3136392c424f4c443a414355343430352c4d2c312c4e4231362d3034382c5369746530380d0a4e432d3137302c424f4c443a414355343530322c4d2c312c4e4231362d3034382c5369746530380d0a4e432d3137312c424f4c443a414355343430352c4d2c312c4e4231362d3034382c5369746530380d0a4e432d3137322c424f4c443a414355343530322c4d2c312c4e4231362d3034382c5369746530380d0a4e432d3137332c424f4c443a414355343430352c4d2c312c4e4231362d3034382c5369746530380d0a4e432d3137342c424f4c443a414355343430352c4d2c312c4e4231362d3034382c5369746530380d0a4e432d3137352c424f4c443a414355343430352c4d2c312c4e4231362d3034382c5369746530380d0a, 7909⟩

def pcs_c0 : Claim :=
  { column := some (b "n sequences"),
    filter := [],
    stat := .sum,
    naTokens := [b "", b "NA"],
    scale := ((1 : Rat) / 1),
    reported := b "341" }

def pcs_c1 : Claim :=
  { column := some (b "n sequences"),
    filter := [],
    stat := .max,
    naTokens := [b "", b "NA"],
    scale := ((1 : Rat) / 1),
    reported := b "015" }

theorem pcs_batch : runAll pcs_src [pcs_c0, pcs_c1] =
    [.checked .consistent (.rat ((341 : Rat) / 1)) 193 0,
    .checked .consistent (.rat ((15 : Rat) / 1)) 193 0] := by decide +kernel

theorem pcs_claim_0 : run pcs_src pcs_c0 = .checked .consistent (.rat ((341 : Rat) / 1)) 193 0 :=
  run_of_runAll pcs_batch 0 rfl rfl
#print axioms pcs_claim_0

theorem pcs_claim_1 : run pcs_src pcs_c1 = .checked .consistent (.rat ((15 : Rat) / 1)) 193 0 :=
  run_of_runAll pcs_batch 1 rfl rfl
#print axioms pcs_claim_1

