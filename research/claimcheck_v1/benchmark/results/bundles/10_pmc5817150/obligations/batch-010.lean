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

def pcs_src : Source := ⟨0x7569642c796561722c6167652c6167655f73712c545444332c76616c6c65792c6c6966657370616e2c7765616e65642c6d6173736a756e2c6d6173736175670d0a393836362c313938382c332c392c332c75762c372c302c323238372e383334382c333535342e363235350d0a393836362c313938392c342c31362c332c75762c372c302c323337372e3438362c333339312e333338350d0a393836362c313939302c352c32352c322c75762c372c312c323231352e363032362c333139322e323634330d0a393836362c313939312c362c33362c312c75762c372c312c323336342e313331352c333131382e343931330d0a393836362c313939322c372c34392c302c75762c372c302c323534342e313735342c4e410d0a363039362c313938372c332c392c332c75762c382c312c323239352e373539392c333139302e383034320d0a363039362c313938382c342c31362c332c75762c382c312c323331392e3234322c333138352e383034390d0a363039362c313938392c352c32352c332c75762c382c312c323434362e323230392c333439362e313835310d0a363039362c313939302c362c33362c322c75762c382c312c323335332e343138382c333233382e333135380d0a363039362c313939312c372c34392c312c75762c382c312c323332372e333736392c333030372e383336370d0a363039362c313939322c382c36342c302c75762c382c302c323932362e393333322c333835352e373430370d0a323133372c313937352c352c32352c302c75762c352c302c323034302e333033372c323738302e3132320d0a323537332c313937382c382c36342c312c75762c392c302c323237382e383834332c4e410d0a323537332c313937392c392c38312c302c75762c392c312c323332322e3330322c323734372e333431370d0a393630372c323030322c332c392c302c75762c332c302c323933392e353932352c343038342e353935310d0a323330392c313938392c332c392c302c64762c332c312c323333332e313932332c333235312e363938330d0a3939302c313938392c352c32352c322c64762c372c302c323435382e363532322c4e410d0a3939302c313939302c362c33362c312c64762c372c312c323432312e393839342c333238382e393033370d0a383037362c313938362c332c392c332c75762c372c302c313931332e343432392c4e410d0a383037362c313938372c342c31362c332c75762c372c312c323130312e313835322c323933312e323738320d0a383037362c313938382c352c32352c322c75762c372c312c323034352e373737322c323634372e353631340d0a383037362c313938392c362c33362c312c75762c372c302c323237352e323738322c4e410d0a383037362c313939302c372c34392c302c75762c372c302c323135362e393435322c4e410d0a383035312c313937382c372c34392c332c75762c31302c302c323232312e313736372c4e410d0a383035312c313937392c382c36342c322c75762c31302c312c323336312e313634382c333231312e303733310d0a383035312c313938302c392c38312c312c75762c31302c302c323430382e313730352c333836332e383633340d0a383035312c313938312c31302c3130302c302c75762c31302c312c323532392e333830312c333138372e373235380d0a393131312c313939352c332c392c322c64762c352c302c323435332e343635312c4e410d0a393131312c313939362c342c31362c312c64762c352c302c323337362e383435392c333539322e353332340d0a393131312c313939372c352c32352c302c64762c352c312c333036372e333037312c333736342e3439380d0a393038322c313939352c332c392c332c64762c362c312c323436312e353336332c333639312e383933330d0a393038322c313939362c342c31362c322c64762c362c302c323335332e333432382c343034372e333331340d0a393038322c313939372c352c32352c312c64762c362c312c323733322e303333372c343130352e383437360d0a393038322c313939382c362c33362c302c64762c362c302c333139362e303537322c343732342e343834320d0a393431372c313939352c332c392c322c64762c352c302c323532322e323030362c333835332e343530350d0a393431372c313939362c342c31362c312c64762c352c302c313936392e313133392c343031332e383636390d0a393431372c313939372c352c32352c302c64762c352c312c323737312e303632332c333832352e3332370d0a3537322c313939352c332c392c312c64762c342c312c323435372e333732352c333539332e353733380d0a323639302c313937362c332c392c302c64762c332c302c323238382e353739312c4e410d0a363830362c313938392c332c392c322c75762c352c302c323237332e323337392c333135342e343236310d0a363830362c313939302c342c31362c312c75762c352c302c323237352e323530312c333330392e353938350d0a363830362c313939312c352c32352c302c75762c352c312c323230362e393234382c323930332e393630350d0a313636302c313938382c332c392c302c75762c332c302c323131302e333436332c323735312e343737370d0a393730372c313939362c332c392c332c64762c31322c312c323139392e3130382c333239322e393635370d0a393730372c313939372c342c31362c332c64762c31322c312c323737352e313435382c333631392e323635360d0a393730372c323030302c372c34392c332c64762c31322c312c333136382e303336332c333637350d0a393730372c323030312c382c36342c332c64762c31322c312c333139372e373830392c333937392e303930340d0a393730372c323030322c392c38312c332c64762c31322c312c333233352e343935372c333633332e313639350d0a393730372c323030332c31302c3130302c322c64762c31322c312c323932322e373439362c333831352e323933330d0a393730372c323030342c31312c3132312c312c64762c31322c312c323936392e333435332c333537352e353039390d0a393730372c323030352c31322c3134342c302c64762c31322c312c323834372e3731322c333135300d0a373230382c313938312c332c392c302c75762c332c302c323734312e313731362c4e410d0a343535352c313939352c332c392c332c64762c31322c302c323238332e343135312c333631372e393035390d0a343535352c313939362c342c31362c332c64762c31322c302c323230312e34312c333730362e313534350d0a343535352c313939372c352c32352c332c64762c31322c302c323830382e333339382c343232382e3434340d0a343535352c313939382c362c33362c332c64762c31322c312c333130392e303934392c343231342e383833320d0a343535352c313939392c372c34392c332c64762c31322c312c323739362e323135362c343236392e323434330d0a343535352c323030302c382c36342c332c64762c31322c312c333233302e353133312c343133362e393333320d0a343535352c323030312c392c38312c332c64762c31322c312c333134302e303737382c333838372e333733350d0a343535352c323030322c31302c3130302c322c64762c31322c312c323936352e383339352c4e410d0a343535352c323030332c31312c3132312c312c64762c31322c312c323733322e303038382c333838332e383439360d0a343535352c323030342c31322c3134342c302c64762c31322c312c323636382e303537372c333235382e3433380d0a333332312c313937392c332c392c332c64762c362c302c323738332e343130382c4e410d0a333332312c313938302c342c31362c322c64762c362c312c323637392e3834322c333738362e353839370d0a333332312c313938312c352c32352c312c64762c362c312c333237362e323432322c4e410d0a383233382c323030322c332c392c302c75762c332c312c323635322e373335352c333136382e333037340d0a393033382c313938322c342c31362c332c75762c392c312c323535352e393938372c333931312e323230330d0a393033382c313938332c352c32352c332c75762c392c302c323234382e313832362c333135352e303236320d0a393033382c313938362c382c36342c312c64762c392c312c323632382e333036382c333437382e323238370d0a393033382c313938372c392c38312c302c64762c392c312c323634302e373432352c333537342e313433330d0a353839352c313939362c332c392c332c75762c372c312c4e412c333232342e353539330d0a353839352c313939372c342c31362c332c75762c372c302c333033302e373230362c4e410d0a353839352c313939382c352c32352c322c75762c372c302c333035342e303536362c333836362e363438320d0a353839352c313939392c362c33362c312c75762c372c312c323937372e373733342c333531322e363732320d0a353839352c323030302c372c34392c302c75762c372c312c333236382e3439372c333734312e313731350d0a313237372c313938312c332c392c322c75762c352c302c323236342e343134362c323932332e313536360d0a313237372c313938332c352c32352c302c75762c352c302c313932322e353737362c323738372e303737390d0a313635362c313938312c332c392c302c75762c332c302c323434342e3838312c4e410d0a343136302c313938392c332c392c322c75762c352c302c323337362e393839332c333133312e353438310d0a343136302c313939302c342c31362c312c75762c352c302c323534312e343038342c4e410d0a343136302c313939312c352c32352c302c75762c352c302c323332332e303933372c4e410d0a383734312c313938312c332c392c332c75762c362c312c323035312e32312c323537352e303734380d0a383734312c313938322c342c31362c322c75762c362c302c313932362e333834382c323531302e333037340d0a383734312c313938332c352c32352c312c75762c362c312c4e412c323433362e363639380d0a383734312c313938342c362c33362c302c75762c362c302c313837352e353732342c4e410d0a343036312c313938312c332c392c302c75762c332c302c323339382e3431392c333036382e393230370d0a353132332c313938392c332c392c312c64762c342c302c323935342e363939352c343331372e3232330d0a353132332c313939302c342c31362c302c64762c342c312c323731372e373931352c333635372e383635370d0a393736332c323030322c332c392c332c75762c392c312c323838392e363035312c333332392e3933330d0a393736332c323030332c342c31362c332c75762c392c302c323834302e313735372c343030382e3035310d0a393736332c323030342c352c32352c332c75762c392c312c333230322e313136342c333533382e353138350d0a393736332c323030352c362c33362c332c75762c392c302c323737382e303233372c4e410d0a393736332c323030362c372c34392c322c75762c392c312c333030372e3732372c343030300d0a393736332c323030372c382c36342c312c75762c392c312c323936362e343530332c343133332e373437370d0a393736332c323030382c392c38312c302c75762c392c302c323835312e373431342c343330382e333537360d0a313834322c313939372c332c392c332c75762c31342c312c323333312e303730312c4e410d0a313834322c313939382c342c31362c332c75762c31342c302c323731342e303632382c333134312e333337350d0a313834322c313939392c352c32352c332c75762c31342c312c323533332e353333332c333438362e383333330d0a313834322c323030302c362c33362c332c75762c31342c312c323936302e333835342c333830342e353632330d0a313834322c323030312c372c34392c332c75762c31342c312c333131312e363130332c333637392e323931330d0a313834322c323030322c382c36342c332c75762c31342c312c323931312e323335382c333639302e323330380d0a313834322c323030332c392c38312c332c75762c31342c312c323735392e303935382c333839302e333832340d0a313834322c323030342c31302c3130302c332c75762c31342c312c333134382e383138392c333939342e383035370d0a313834322c323030352c31312c3132312c332c75762c31342c302c323731332e343437382c333934392e303339380d0a313834322c323030362c31322c3134342c322c75762c31342c312c323935322e383133382c333531332e313336360d0a323330332c313939372c332c392c332c75762c362c312c323835352e313435332c333637372e393538310d0a323330332c313939382c342c31362c322c75762c362c312c323932352e313830322c343339372e313738310d0a323330332c313939392c352c32352c312c75762c362c312c333235312e313937312c343336382e393836370d0a323330332c323030302c362c33362c302c75762c362c312c333437342e343136342c333737350d0a343333352c313939372c332c392c332c75762c372c312c323732392e363137352c343135342e333035310d0a343333352c313939382c342c31362c332c75762c372c302c333135302e3331332c333933392e353630370d0a343333352c313939392c352c32352c322c75762c372c302c323937382e343537372c343039382e303431340d0a343333352c323030302c362c33362c312c75762c372c302c333531332e363339342c343139362e323235380d0a363435332c313939392c332c392c312c64762c342c302c323536352e353032392c333830372e393339330d0a363435332c323030302c342c31362c302c64762c342c302c333037372e333931352c4e410d0a333131372c313939392c332c392c302c75762c332c302c323531322e353031352c333039302e333431310d0a353137312c313939392c332c392c332c75762c31302c312c323238352e363835342c323635392e343136330d0a353137312c323030302c342c31362c332c75762c31302c302c323636392e383839312c333830372e323034360d0a353137312c323030312c352c32352c332c75762c31302c312c323738372e3436372c323938352e393139320d0a353137312c323030322c362c33362c332c75762c31302c312c323730382e323737322c323937372e303734330d0a353137312c323030332c372c34392c332c75762c31302c312c323639342e383738372c333137342e363235330d0a353137312c323030342c382c36342c322c75762c31302c312c323731312e313031382c333133392e303931370d0a353137312c323030352c392c38312c312c75762c31302c302c323435312e343934352c333435322e383236370d0a353137312c323030362c31302c3130302c302c75762c31302c312c323931302e303433332c333136352e333334390d0a343434362c313939392c332c392c302c64762c332c302c323332322e353535362c323938322e373134330d0a373139352c313939392c332c392c312c64762c342c302c323638342e333433312c4e410d0a373139352c323030302c342c31362c302c64762c342c312c333032302e333731332c333638352e303739360d0a363732302c313938362c332c392c332c75762c372c312c313839382e353331372c323434302e363932380d0a363732302c313938372c342c31362c332c75762c372c302c323032312e353733392c4e410d0a363732302c313938382c352c32352c322c75762c372c312c313936392e343338352c323536382e313630370d0a363732302c313938392c362c33362c312c75762c372c302c323135322e313133372c4e410d0a363732302c313939302c372c34392c302c75762c372c302c323133372e313334312c323836362e343332310d0a3338322c313939392c342c31362c332c75762c372c312c323234302e333730342c333330352e373237360d0a3338322c323030302c352c32352c322c75762c372c312c323434392e333432312c333130362e373333370d0a3338322c323030312c362c33362c312c75762c372c312c323531382e323235322c333237352e3331370d0a3338322c323030322c372c34392c302c75762c372c302c323733302e3735332c4e410d0a383233362c313939382c342c31362c332c75762c372c312c323634392e343336312c333431392e323234350d0a383233362c323030312c372c34392c302c75762c372c302c333030372e323232322c4e410d0a333037382c313939392c332c392c302c64762c332c302c323831302e333030362c4e410d0a313232352c323030312c332c392c332c64762c392c312c333039382e373831352c333931342e343932390d0a313232352c323030322c342c31362c332c64762c392c312c333038312e383638332c343230392e343036350d0a313232352c323030332c352c32352c332c64762c392c312c333130302e3638362c343231312e383837320d0a313232352c323030342c362c33362c332c64762c392c312c333632302e303534332c343437332e313034330d0a313232352c323030352c372c34392c322c64762c392c302c333133392e393930332c4e410d0a313232352c323030362c382c36342c312c64762c392c312c323337382e3032312c343534352e323835380d0a313232352c323030372c392c38312c302c64762c392c302c323336372e333239342c4e410d0a343033312c313939312c332c392c332c75762c362c302c323431392e353739342c333932352e383933320d0a343033312c313939332c352c32352c312c75762c362c312c323630312e333130372c333636372e363234360d0a343033312c313939342c362c33362c302c75762c362c302c323935302e333535332c4e410d0a333531302c323030312c332c392c302c64762c332c302c323831322e313134322c4e410d0a363430362c313938362c332c392c332c64762c392c302c323230342e373137312c323635300d0a363430362c313938372c342c31362c332c64762c392c302c323132322e383632382c4e410d0a363430362c313938382c352c32352c332c64762c392c302c323236392e383531312c323735332e353637380d0a363430362c313938392c362c33362c332c64762c392c312c323332302e313233312c323932382e303430370d0a363430362c313939312c382c36342c312c64762c392c302c323435322e373836362c333132342e363336390d0a363430362c313939322c392c38312c302c64762c392c312c323435392e323031382c323832332e343637340d0a333038302c323030322c332c392c332c75762c372c312c323639322e343933312c333230342e313238330d0a333038302c323030332c342c31362c332c75762c372c312c323732342e383031362c333334322e313334380d0a333038302c323030342c352c32352c322c75762c372c302c333039352e343536322c4e410d0a333038302c323030352c362c33362c312c75762c372c302c4e412c343137322e373635390d0a333734322c323030322c332c392c302c75762c332c302c323636362e313434372c4e410d0a343035322c313939322c332c392c332c64762c382c312c323533312e393639372c333234332e383538340d0a343035322c313939332c342c31362c332c64762c382c312c323330342e30322c333331342e373736330d0a343035322c313939352c362c33362c322c64762c382c312c323334352e373738312c333334382e383939310d0a343035322c313939362c372c34392c312c64762c382c302c313930322e343137332c333537332e373235360d0a343035322c313939372c382c36342c302c64762c382c312c323637372e3239332c333730362e343332390d0a3436322c323030322c342c31362c332c75762c382c312c323835312e333031332c333135332e313633360d0a3436322c323030332c352c32352c332c75762c382c302c323435322e323032322c343238382e323831310d0a3436322c323030342c362c33362c322c75762c382c312c323936322e393435362c333331372e343736320d0a3436322c323030352c372c34392c312c75762c382c312c323733322e343239362c333730302e353337380d0a3436322c323030362c382c36342c302c75762c382c312c333039312e393338382c333139362e373732390d0a353135302c313938332c332c392c332c75762c362c302c313838302e353130382c323934392e383633370d0a353135302c313938342c342c31362c322c75762c362c302c323132332e343338342c333233322e373936360d0a353135302c313938352c352c32352c312c75762c362c312c323436312e363539372c333337362e303736320d0a353135302c313938362c362c33362c302c75762c362c302c323437332e393934322c333033302e303731320d0a393338352c323030312c332c392c302c75762c332c312c323638332e303238352c333339362e353538380d0a353530372c323030332c332c392c332c64762c362c302c323631322e383438382c4e410d0a353530372c323030342c342c31362c322c64762c362c312c333033352e393238372c333439382e3839360d0a353530372c323030352c352c32352c312c64762c362c312c333032332e313135312c4e410d0a353530372c323030362c362c33362c302c64762c362c312c333333342e393833342c333731342e393438380d0a363737312c313939322c332c392c302c75762c332c312c323230372e373436332c333239352e343237380d0a363135312c323030342c342c31362c302c75762c342c312c323639372e373537342c333334312e393235350d0a383835372c323030352c332c392c312c64762c342c312c323336362e373335312c4e410d0a343233382c323030352c332c392c332c75762c362c312c323335312e363438372c333038362e333836340d0a343233382c323030362c342c31362c322c75762c362c312c323539332e393032322c333131362e353232360d0a343233382c323030372c352c32352c312c75762c362c302c323732332e363530362c343135372e303133320d0a343233382c323030382c362c33362c302c75762c362c312c323530372e393137322c333935302e353635360d0a333530322c323030332c332c392c332c75762c382c312c323333392e333635372c323637362e353733340d0a333530322c323030342c342c31362c332c75762c382c312c323530392e323431312c333137352e343235350d0a333530322c323030352c352c32352c332c75762c382c302c4e412c333636322e3636390d0a333530322c323030362c362c33362c322c75762c382c312c323436382e363332342c323736302e373238330d0a333530322c323030372c372c34392c312c75762c382c312c323633302e323035392c333334302e393637330d0a333530322c323030382c382c36342c302c75762c382c312c323333362e373738342c333533362e343733380d0a313334392c323030352c332c392c312c75762c342c312c323134312e303535392c323937302e313237310d0a313334392c323030362c342c31362c302c75762c342c312c323436362e343439312c4e410d0a333836332c323030352c332c392c332c75762c362c302c323634392e373038392c333936332e333134350d0a333836332c323030362c342c31362c322c75762c362c312c323932322e393237332c4e410d0a333836332c323030372c352c32352c312c75762c362c312c323735342e363337372c333539332e353631390d0a333836332c323030382c362c33362c302c75762c362c312c323731342e303537332c343136372e363635330d0a363537372c323030342c332c392c302c75762c332c312c323432312e343733342c4e410d0a393931342c323030302c332c392c332c64762c31332c312c323934382e303437332c333633362e303632380d0a393931342c323030312c342c31362c332c64762c31332c312c333032332e363932362c333836302e353938340d0a393931342c323030322c352c32352c332c64762c31332c312c333234392e343033352c4e410d0a393931342c323030342c372c34392c332c64762c31332c312c333432332e38312c4e410d0a393931342c323030352c382c36342c332c64762c31332c312c333039392e3336342c343337362e323135360d0a393931342c323030362c392c38312c332c64762c31332c312c333234322e343632322c4e410d0a393931342c323030372c31302c3130302c332c64762c31332c312c4e412c343135372e343938390d0a393931342c323030382c31312c3132312c322c64762c31332c312c323930342e363638362c343033312e393830330d0a393931342c323030392c31322c3134342c312c64762c31332c312c333033302e373333382c4e410d0a333531312c323030342c332c392c332c75762c362c312c323638342e303933392c323938372e333338370d0a333531312c323030352c342c31362c322c75762c362c312c323537392e3131382c333431332e333234360d0a333531312c323030362c352c32352c312c75762c362c312c323935362e363237352c333235362e373336340d0a333531312c323030372c362c33362c302c75762c362c302c323835332e323833362c4e410d0a383835332c323030302c332c392c332c64762c31322c302c333239332e363631382c343334392e373330370d0a383835332c323030312c342c31362c332c64762c31322c312c333137332e323233392c333834302e3232350d0a383835332c323030322c352c32352c332c64762c31322c312c333131352e353935352c343130362e333339390d0a383835332c323030332c362c33362c332c64762c31322c312c333139352e3534342c343032302e313733310d0a383835332c323030342c372c34392c332c64762c31322c312c333239322e313434372c333836362e363635370d0a383835332c323030352c382c36342c332c64762c31322c312c333138382e3139322c333535392e383036340d0a383835332c323030362c392c38312c332c64762c31322c312c333634332e353336332c333937302e383237390d0a383835332c323030372c31302c3130302c322c64762c31322c312c333331372e373130372c4e410d0a383835332c323030382c31312c3132312c312c64762c31322c312c323834352e323635342c333832392e353232380d0a383835332c323030392c31322c3134342c302c64762c31322c302c333039342e3430382c4e410d0a393539372c313939322c332c392c332c64762c31302c302c333332312e343435322c343235302e353834350d0a393539372c313939332c342c31362c332c64762c31302c302c333037352e333937332c343138362e303330370d0a393539372c313939342c352c32352c332c64762c31302c302c333130312e323936362c333939352e363032370d0a393539372c313939352c362c33362c332c64762c31302c302c323831312e3939362c343233372e373732310d0a393539372c313939362c372c34392c332c64762c31302c302c333036332e313536392c343437302e393237390d0a393539372c313939372c382c36342c322c64762c31302c302c333139362e393935352c333935382e3737340d0a393539372c313939382c392c38312c312c64762c31302c302c333230342e363234352c343531372e343630310d0a393539372c313939392c31302c3130302c302c64762c31302c312c333033382e343131372c333339312e353532330d0a313230352c323030352c332c392c332c75762c392c302c323337332e393934352c333331392e303737320d0a313230352c323030362c342c31362c332c75762c392c312c323639332e343930322c333133332e363534330d0a313230352c323030372c352c32352c332c75762c392c302c323934312e303532392c343530320d0a313230352c323030392c372c34392c322c75762c392c302c323836362e353134372c333339322e373338320d0a313230352c323031302c382c36342c312c75762c392c312c323937342e363136312c333534302e383038310d0a323637302c323030332c332c392c302c75762c332c312c323534352e373633382c333237362e353231350d0a383338352c313938362c332c392c332c64762c382c312c323130392e373435372c323737322e363439320d0a383338352c313938372c342c31362c332c64762c382c312c323233352e383438332c333030312e333637320d0a383338352c313938382c352c32352c332c64762c382c312c323137332e393236352c323832372e373736380d0a383338352c313938392c362c33362c322c64762c382c302c323338302e323637372c333232372e393233350d0a383338352c313939302c372c34392c312c64762c382c302c323435372e353334312c333234342e373330320d0a333932392c323030352c332c392c302c64762c332c302c323636392e333434322c333438332e333935390d0a333737302c323030352c332c392c322c75762c352c312c323334362e383333392c333037392e363330350d0a333737302c323030362c342c31362c312c75762c352c312c323730352e3537352c333131342e353231360d0a333737302c323030372c352c32352c302c75762c352c312c323833312e333632372c333030322e353430310d0a393335342c313939322c332c392c332c64762c31302c302c333230322e333532362c333932372e343139390d0a393335342c313939332c342c31362c332c64762c31302c312c323733322e343535322c343234312e383538360d0a393335342c313939342c352c32352c332c64762c31302c302c333036352e363637342c343039332e313934330d0a393335342c313939352c362c33362c332c64762c31302c302c323832332e363635322c333730312e313730340d0a393335342c313939362c372c34392c332c64762c31302c302c323935372e303132332c343434382e343536380d0a393335342c313939372c382c36342c322c64762c31302c302c333339362e353039332c343533392e323436310d0a393335342c313939382c392c38312c312c64762c31302c302c333138332e303839352c343231352e353331340d0a393335342c313939392c31302c3130302c302c64762c31302c302c323838332e313638372c4e410d0a363633392c323030352c332c392c332c75762c382c312c323239332e353932342c333439362e333935380d0a363633392c323030362c342c31362c332c75762c382c302c323838342e343938322c333933332e393136360d0a363633392c323030372c352c32352c332c75762c382c302c323935362e303033332c333838382e363938370d0a363633392c323030382c362c33362c322c75762c382c302c323731392e333833362c343530362e303932380d0a363633392c323030392c372c34392c312c75762c382c312c323737392e363735312c333236332e393934330d0a363633392c323031302c382c36342c302c75762c382c312c323934322e3532352c333939372e323933380d0a3138382c323030352c332c392c302c75762c332c312c323732322e343338352c333832322e323433360d0a323535392c313939322c332c392c332c64762c362c302c323935342e353139312c343030362e373837310d0a323535392c313939332c342c31362c322c64762c362c302c323735392e383936312c333530322e333838370d0a323535392c313939342c352c32352c312c64762c362c302c323738352e333937322c4e410d0a323535392c313939352c362c33362c302c64762c362c302c323533332e343934342c4e410d0a393037352c323030342c332c392c332c64762c382c312c333233332e373430372c333932372e373535330d0a393037352c323030352c342c31362c332c64762c382c312c333032352e333433332c4e410d0a393037352c323030362c352c32352c332c64762c382c312c333338392e383534372c4e410d0a393037352c323030372c362c33362c322c64762c382c312c333431382e383637312c4e410d0a393037352c323030392c382c36342c302c64762c382c312c333239312e343138372c4e410d0a323435342c323030342c332c392c322c64762c352c312c323730332e353934312c333433372e353339310d0a323435342c323030352c342c31362c312c64762c352c302c323733352e323530362c4e410d0a323435342c323030362c352c32352c302c64762c352c302c323832352e353234342c4e410d0a363230332c313938332c332c392c322c75762c352c302c313438372e303037352c4e410d0a363230332c313938352c352c32352c302c75762c352c312c323037392e313531352c323738372e333238380d0a343531322c323030352c332c392c302c64762c332c312c323434382e3532352c4e410d0a3335342c323030302c332c392c332c64762c362c302c333037342e303637362c343133302e333035350d0a3335342c323030312c342c31362c322c64762c362c302c333331362e343435382c333736352e333636340d0a3335342c323030322c352c32352c312c64762c362c302c333031362e363439312c343139382e313130320d0a323936362c313937352c342c31362c302c75762c342c302c313930312e313235392c4e410d0a343430312c313937372c332c392c332c75762c382c302c323438372e373537362c4e410d0a363933332c323030352c332c392c332c75762c362c312c323437332e323535372c333737332e383432370d0a363933332c323030362c342c31362c322c75762c362c312c333037392e303735382c4e410d0a363933332c323030372c352c32352c312c75762c362c312c333033342e393430382c343233322e353435330d0a3131372c323030352c332c392c302c75762c332c302c323732352e353333372c343130392e343033320d0a353637382c323030352c332c392c332c75762c362c302c323435332e313635332c333937352e3432330d0a353637382c323030362c342c31362c322c75762c362c312c323931322e383432322c333536382e313837350d0a353637382c323030372c352c32352c312c75762c362c312c333030322e393339332c333934382e383135350d0a353637382c323030382c362c33362c302c75762c362c302c323730362e333834332c343636312e303532360d0a3138302c323030352c332c392c332c64762c362c302c323839322e383433352c343036302e353135360d0a3138302c323030362c342c31362c322c64762c362c312c333335302e343838342c333636362e323535340d0a3138302c323030372c352c32352c312c64762c362c312c333236342e303839362c333737362e353931370d0a383638312c313938372c332c392c332c75762c362c312c323438322e323231382c333431322e3530310d0a383638312c313938392c352c32352c312c75762c362c312c323637392e303031322c333538322e353333390d0a383638312c313939302c362c33362c302c75762c362c302c323739382e323835382c4e410d0a393534302c313939372c332c392c312c64762c342c312c323533352e333238372c333334322e383134390d0a393534302c313939382c342c31362c302c64762c342c312c323737342e313734332c333431392e323230360d0a363530332c313938372c332c392c322c75762c352c302c323038312e333138342c4e410d0a363530332c313938382c342c31362c312c75762c352c312c323233312e323837372c333037382e393939310d0a363530332c313938392c352c32352c302c75762c352c302c323434322e353636322c4e410d0a3739392c313937362c332c392c332c75762c362c302c323431342e363035312c4e410d0a3739392c313937382c352c32352c312c75762c362c302c323435332e353032342c4e410d0a3739392c313937392c362c33362c302c75762c362c302c323534382e353835392c4e410d0a353535372c313937372c332c392c312c75762c342c302c323733342e3136382c4e410d0a333630352c313939372c332c392c302c64762c332c312c323634372e373430392c333736352e393931310d0a34312c323030322c332c392c332c75762c382c312c323436382e333831382c333032352e393738310d0a34312c323030332c342c31362c332c75762c382c302c323237392e393633382c333832382e323134320d0a34312c323030342c352c32352c332c75762c382c302c323731312e373836322c333930362e353138360d0a34312c323030352c362c33362c322c75762c382c302c323536352e343236342c333335342e3635350d0a34312c323030362c372c34392c312c75762c382c302c323830362e393337322c333930352e333735310d0a34312c323030372c382c36342c302c75762c382c312c323839322e353335332c333537372e333130390d0a323931392c313938302c332c392c332c75762c31302c302c4e412c333332302e383030370d0a323931392c313938312c342c31362c332c75762c31302c302c323432332e353437332c4e410d0a323931392c313938322c352c32352c332c75762c31302c302c323230362e373933322c333337392e383834350d0a323931392c313938332c362c33362c332c75762c31302c302c4e412c323730322e373638360d0a323931392c313938342c372c34392c332c75762c31302c302c4e412c333233372e383334390d0a323931392c313938352c382c36342c322c75762c31302c302c323432372e3436382c333133342e353136370d0a323931392c313938362c392c38312c312c75762c31302c302c323432312e3135312c333238332e363233340d0a323931392c313938372c31302c3130302c302c75762c31302c302c323535362e353432382c333534372e343933310d0a323039392c323030322c332c392c312c75762c342c302c323633382e3531372c4e410d0a393032352c313939302c332c392c322c64762c352c302c323537392e363639392c4e410d0a393032352c313939322c352c32352c302c64762c352c302c333037342e363637352c333737302e313036390d0a343233362c313939312c332c392c312c75762c342c312c323130352e393730312c323633362e303938330d0a343233362c313939322c342c31362c302c75762c342c302c323434342e303735352c333732322e373038390d0a323032322c323030372c342c31362c322c64762c362c302c323933322e373232382c4e410d0a323032322c323030382c352c32352c312c64762c362c302c323437352e353530312c4e410d0a323032322c323030392c362c33362c302c64762c362c312c323935322e333034392c4e410d0a323037312c323030362c332c392c302c64762c332c312c323632332e313333342c333138392e393834310d0a363635362c323030362c332c392c332c64762c372c312c333035382e393430372c333730332e3031340d0a363635362c323030372c342c31362c332c64762c372c312c333237372e3434372c343133382e363636310d0a363635362c323030382c352c32352c322c64762c372c312c4e412c333231372e353031330d0a363635362c323030392c362c33362c312c64762c372c312c333232362e333931382c4e410d0a363635362c323031302c372c34392c302c64762c372c312c4e412c343336302e393937340d0a3730392c323031302c332c392c312c75762c342c312c323339302e323434392c333135382e363635340d0a3730392c323031312c342c31362c302c75762c342c302c323234332e3839382c4e410d0a363132342c323030352c332c392c332c75762c362c312c313936372e303839362c323731322e303532380d0a363132342c323030362c342c31362c322c75762c362c312c323230302e303133382c323631322e323739320d0a363132342c323030382c362c33362c302c75762c362c312c323037312e323937322c323832382e313836380d0a323439382c323030362c332c392c332c64762c392c312c333434312e353932332c343133382e373036390d0a323439382c323030372c342c31362c332c64762c392c312c333433322e313036322c343336332e3738340d0a323439382c323030382c352c32352c332c64762c392c312c333131312e303431382c343436342e373132320d0a323439382c323030392c362c33362c332c64762c392c312c333238342e3538372c343530372e303637380d0a323439382c323031302c372c34392c322c64762c392c312c333535392e363038312c343339332e333736390d0a323439382c323031312c382c36342c312c64762c392c302c4e412c343639382e323132320d0a323439382c323031322c392c38312c302c64762c392c312c333133332e373632392c343131322e313837330d0a393831392c313938302c332c392c302c75762c332c302c313934302e363039332c4e410d0a3634372c323030362c332c392c312c75762c342c312c323838362e393338362c333833392e393736310d0a373530332c323030372c332c392c302c64762c332c312c323636322e393931362c333234352e303633310d0a333531382c323030382c342c31362c302c75762c342c302c323231322e353133382c4e410d0a3239382c323030372c332c392c312c75762c342c312c323638352e373133342c333339302e343737320d0a3239382c323030382c342c31362c302c75762c342c302c323434362e303538342c333930382e353231350d0a393836392c323030372c332c392c332c64762c372c312c323835332e303735312c343136332e393533390d0a393836392c323030392c352c32352c322c64762c372c312c4e412c333931312e383639390d0a393036332c323030372c332c392c322c75762c352c302c323937302e303334372c333937372e373539350d0a393036332c323030382c342c31362c312c75762c352c302c323633302e353836352c333931352e313639350d0a393036332c323030392c352c32352c302c75762c352c312c323437322e363631362c333735322e313737330d0a3432392c323030372c332c392c332c64762c382c302c333538362e363230362c343834392e363233360d0a3432392c323030382c342c31362c332c64762c382c312c333135362e303935382c343633352e303638330d0a3432392c323030392c352c32352c332c64762c382c312c333333362e373039322c343630312e313231330d0a3432392c323031302c362c33362c322c64762c382c312c333532342e303632342c333839300d0a3432392c323031312c372c34392c312c64762c382c302c333234332e383233342c343939372e323832390d0a353939382c313938302c332c392c302c75762c332c302c323039332e303338322c4e410d0a3734362c313939312c342c31362c322c64762c362c302c323430332e3231332c4e410d0a3734362c313939322c352c32352c312c64762c362c302c323934392e393137382c4e410d0a393032372c313939302c332c392c332c64762c31312c302c323637302e333030322c333839312e303330310d0a393032372c313939312c342c31362c332c64762c31312c302c323536332e313935382c4e410d0a393032372c313939322c352c32352c332c64762c31312c312c323937392e303437382c333339332e333937370d0a393032372c313939332c362c33362c332c64762c31312c302c4e412c343134322e303730310d0a393032372c313939352c382c36342c332c64762c31312c312c4e412c333632392e323638330d0a393032372c313939382c31312c3132312c302c64762c31312c312c333133322e333732322c4e410d0a353230382c323030372c332c392c302c75762c332c312c323536382e333035362c4e410d0a393233312c323030372c332c392c302c75762c332c312c323531392e303933342c333232362e303037320d0a363139382c323030372c332c392c332c64762c362c312c323534302e323737352c333339342e363337340d0a363139382c323030382c342c31362c322c64762c362c312c323431372e3433372c333432302e3436390d0a363139382c323030392c352c32352c312c64762c362c312c323636302e373531372c333434352e323736340d0a353734392c323030372c332c392c332c75762c392c302c323932322e323232332c343434352e393539320d0a353734392c323030382c342c31362c332c64762c392c312c323533322e353434392c343235302e323534360d0a353734392c323030392c352c32352c332c75762c392c312c323233302e313634362c4e410d0a353734392c323031302c362c33362c332c75762c392c312c333035382e373836362c333537352e393839390d0a353734392c323031332c392c38312c302c75762c392c302c323839362e333833362c343331302e343833370d0a363737372c323030382c332c392c322c64762c352c312c333237332e323135372c343334372e323936390d0a363737372c323030392c342c31362c312c64762c352c312c333439322e323433392c343333392e373636360d0a363737372c323031302c352c32352c302c64762c352c312c333537342e363032322c343432312e323134360d0a363032322c313938332c342c31362c302c64762c342c302c313633362e363030312c4e410d0a333438332c323030392c332c392c302c75762c332c312c313631392e303638342c4e410d0a323733352c323031302c332c392c302c64762c332c302c323838392e343331312c4e410d0a393930312c323030372c332c392c322c64762c352c312c323835352e383230352c333735302e323839340d0a393930312c323030382c342c31362c312c64762c352c302c323736302e323339362c4e410d0a353738302c323030372c332c392c312c75762c342c302c323538342e393433342c333539392e383834380d0a353738302c323030382c342c31362c302c75762c342c302c323435352e3530312c333130372e383739310d0a363234352c323030372c332c392c332c64762c362c312c333137332e323535312c343033372e343231390d0a363234352c323030382c342c31362c322c64762c362c312c323832372e333934392c343133342e303635390d0a363234352c323030392c352c32352c312c64762c362c312c323835392e323731352c343132352e323637340d0a363234352c323031302c362c33362c302c64762c362c312c333033302e3330362c333937382e3036320d0a353732332c323030372c332c392c332c64762c362c312c323933332e303430322c343135362e353237390d0a353732332c323030382c342c31362c322c64762c362c302c323730302e373631362c343033342e3639340d0a353732332c323030392c352c32352c312c64762c362c312c323633302e383333332c343136342e333738380d0a353732332c323031302c362c33362c302c64762c362c312c333038312e333031382c4e410d0a393838372c323030372c332c392c332c75762c362c312c323538342e3737372c333337302e323838330d0a393838372c323030382c342c31362c322c75762c362c302c323432312e373734312c333635302e353636390d0a393838372c323030392c352c32352c312c75762c362c312c323337372e343431362c333238382e353138350d0a393838372c323031302c362c33362c302c75762c362c312c323734322e333438392c333334392e323736350d0a313432392c323030362c332c392c322c64762c352c312c323738382e393233372c333333322e333332380d0a313432392c323030372c342c31362c312c64762c352c312c323330362e343839382c333532312e343330320d0a313432392c323030382c352c32352c302c64762c352c312c323238302e373637312c333531352e343438330d0a343838342c323030362c332c392c332c64762c372c312c333333312e353739392c333837302e393931350d0a343838342c323030372c342c31362c332c64762c372c312c333333312e3036392c343432392e313832380d0a343838342c323030392c362c33362c312c64762c372c312c333332312e333138372c343039342e323639310d0a343838342c323031302c372c34392c302c64762c372c312c333435392e393831322c343237322e383037390d0a363530302c323030372c332c392c302c75762c332c312c323831302e3434322c333636312e313738330d0a393336372c323030372c332c392c312c75762c342c312c323532312e353934372c333738362e313430350d0a393336372c323030382c342c31362c302c75762c342c312c323430382e343432372c323838372e383439370d0a3630302c323030372c332c392c302c75762c332c302c333034322e333535322c4e410d0a3337372c313938392c332c392c332c75762c392c302c323337392e393134362c333039362e383438340d0a3337372c313939302c342c31362c332c75762c392c302c323330342e333931392c333139342e363630350d0a3337372c313939312c352c32352c332c75762c392c312c323438352e353634362c333331322e313335320d0a3337372c313939322c362c33362c332c75762c392c302c323938342e353433362c333837392e323833330d0a3337372c313939332c372c34392c322c75762c392c302c323333352e363439382c343038382e303136350d0a3337372c313939352c392c38312c302c75762c392c302c323335392e313936332c4e410d0a353539392c323030322c332c392c332c75762c392c312c323434342e3937312c333432372e343333320d0a353539392c323030332c342c31362c332c75762c392c302c323335312e343833312c333431382e353131320d0a353539392c323030342c352c32352c332c75762c392c312c323537342e333231322c333431382e353135370d0a353539392c323030352c362c33362c332c75762c392c302c323431352e343837372c333539392e343738360d0a353539392c323030362c372c34392c322c75762c392c302c323638352e373939392c333835332e3231310d0a353539392c323030372c382c36342c312c75762c392c302c323830352e303839352c343130332e343939330d0a313633392c323030372c342c31362c312c75762c352c312c323332352e303033352c323837362e363236370d0a313633392c323030382c352c32352c302c75762c352c312c323235312e393730322c4e410d0a353737332c313938322c332c392c302c75762c332c302c323434312e373131332c333839362e393430360d0a393637382c323030362c332c392c332c64762c372c302c323931302e3035382c343334322e373731320d0a393637382c323030372c342c31362c332c64762c372c312c323939382e313938372c333637362e353738310d0a393637382c323030382c352c32352c322c64762c372c302c323738332e353137352c333735322e323539370d0a393637382c323030392c362c33362c312c64762c372c312c323935392e343936322c333931392e3538360d0a393637382c323031302c372c34392c302c64762c372c312c333135372e363138372c333937312e313137390d0a313037352c323030382c332c392c322c75762c352c302c323239362e363931392c4e410d0a313037352c323030392c342c31362c312c75762c352c312c323537322e343039322c333437302e373531380d0a313037352c323031302c352c32352c302c75762c352c302c323830372e363037312c4e410d0a393430302c313938382c332c392c302c75762c332c302c313933392e383734392c323437382e313732390d0a313635312c323030382c332c392c322c64762c352c312c323836382e3839392c333839372e3336350d0a313635312c323030392c342c31362c312c64762c352c312c333032362e393731372c4e410d0a373335322c323030382c332c392c332c64762c362c312c323134312e343733332c333338362e393432330d0a373335322c323030392c342c31362c322c64762c362c312c323736342e343636372c333038312e353733380d0a373335322c323031302c352c32352c312c64762c362c302c333132372e383531352c343331382e373738310d0a373335322c323031312c362c33362c302c64762c362c312c323436302e373134322c333639322e353332390d0a393436332c313938322c332c392c302c75762c332c302c323235302e393533372c4e410d0a363138332c313938392c332c392c322c75762c352c302c323435332e353337382c333239332e323639380d0a363138332c313939302c342c31362c312c75762c352c302c323338392e313436322c333132312e363339340d0a363138332c313939312c352c32352c302c75762c352c312c323434362e323834312c333235362e343635350d0a3330362c313939332c332c392c322c64762c352c302c313931332e353034312c4e410d0a393937352c323030392c332c392c302c75762c332c312c323531362e383538322c333232392e373538310d0a393935352c313938322c332c392c312c75762c342c302c323037342e393735362c4e410d0a393935352c313938332c342c31362c302c64762c342c302c313834372e383336392c323339352e383431390d0a363033372c323031302c332c392c322c75762c352c312c323339332e3139352c333237302e333334330d0a363033372c323031312c342c31362c312c75762c352c302c323135342e353931362c343033362e333034320d0a363033372c323031322c352c32352c302c75762c352c312c333135362e363139322c4e410d0a333135342c323031302c332c392c302c75762c332c312c323833372e353030382c333631392e3732340d0a353139312c313938332c332c392c332c64762c382c302c313934342e353339392c323831382e393238390d0a353139312c313938342c342c31362c332c64762c382c302c323231352e303039382c333233342e373231310d0a353139312c313938352c352c32352c332c64762c382c312c323334372e353931392c323932332e303933370d0a353139312c313938362c362c33362c322c64762c382c302c323432312e3431332c333530362e383932390d0a353139312c313938372c372c34392c312c64762c382c312c323634302e333533322c333639342e373534310d0a353139312c313938382c382c36342c302c64762c382c312c323631392e353239332c333731342e313737380d0a353231372c313938332c332c392c322c75762c352c312c313934372e373435382c323730342e313534310d0a353231372c313938342c342c31362c312c75762c352c302c323238392e3237352c4e410d0a333231372c323030392c332c392c302c75762c332c312c323033362e323337342c323539332e363730310d0a363530322c313938332c332c392c302c64762c332c312c313939362e353435392c323939392e343535390d0a383036342c323031302c332c392c322c75762c352c312c323430372e353431372c333137322e343737330d0a383036342c323031312c342c31362c312c75762c352c302c323133332e333431392c4e410d0a383036342c323031322c352c32352c302c75762c352c312c323832302e323136392c333630382e363938360d0a343937302c313939332c332c392c312c75762c342c302c323134392e3837332c333033312e323434320d0a343937302c313939342c342c31362c302c75762c342c302c323339352e383535322c4e410d0a3834302c313938332c332c392c322c75762c352c302c323230322e333632352c4e410d0a3834302c313938342c342c31362c312c75762c352c302c323534332e363534312c333033332e343430390d0a3834302c313938352c352c32352c302c75762c352c312c323535312e303339322c323736382e363135360d0a383832342c323030392c332c392c302c75762c332c312c323433382e353631382c323834302e383935350d0a343939392c313938342c342c31362c322c75762c362c312c313939372e343138352c323733392e373332370d0a343939392c313938362c362c33362c302c75762c362c302c4e412c323932352e393838330d0a313837332c313938332c332c392c332c75762c392c312c4e412c323333362e383333320d0a313837332c313938342c342c31362c332c75762c392c302c313935322e353638312c4e410d0a313837332c313938352c352c32352c332c75762c392c312c323331392e393835312c323834332e373031360d0a313837332c313938362c362c33362c332c75762c392c312c4e412c323730392e303330330d0a313837332c313938372c372c34392c322c75762c392c302c323638362e3835372c4e410d0a313837332c313938382c382c36342c312c75762c392c312c323335302e373839322c333235312e353236350d0a313837332c313938392c392c38312c302c75762c392c302c323536352e373434312c333535372e3234340d0a373830302c323030382c332c392c312c75762c342c302c323339362e303138382c333332322e333434350d0a373830302c323030392c342c31362c302c75762c342c312c323238312e383130352c333133302e323430310d0a383237382c313938322c332c392c302c75762c332c302c313832352e383231372c323738322e373733350d0a393934372c323031302c332c392c302c75762c332c312c323136302e363137332c323833372e373037330d0a393631362c323030382c332c392c332c75762c362c312c323039352e33342c323935332e343530310d0a393631362c323030392c342c31362c322c75762c362c302c323137332e393431362c333134332e383332380d0a393631362c323031302c352c32352c312c75762c362c312c323530312e313530342c333234312e363232330d0a393631362c323031312c362c33362c302c75762c362c302c313932342e373631352c4e410d0a343732372c313938332c332c392c332c64762c382c302c323334362e373033392c333335352e323835310d0a343732372c313938342c342c31362c332c64762c382c302c323533372e323031322c333635342e313730360d0a343732372c313938352c352c32352c332c64762c382c312c323833332e343435322c333730332e303033330d0a343732372c313938362c362c33362c322c64762c382c312c323931392e333438382c333932302e343230380d0a343732372c313938372c372c34392c312c64762c382c312c323934382e353436392c333933392e323534340d0a363331392c323030382c332c392c302c75762c332c302c323632382e343439362c343630332e32360d0a363638332c313938332c332c392c332c75762c382c302c4e412c323534372e303334330d0a363638332c313938342c342c31362c332c75762c382c302c4e412c323832342e343933310d0a363638332c313938352c352c32352c332c75762c382c302c323331352e3332392c333032362e303834380d0a363638332c313938362c362c33362c322c75762c382c302c323237332e363537332c323935392e383233380d0a363638332c313938372c372c34392c312c75762c382c302c323430312e373230312c333533392e393633320d0a363638332c313938382c382c36342c302c75762c382c312c323333362e333730352c333133342e333538330d0a373234352c313937372c352c32352c332c64762c382c302c323830312e303730362c333731302e323339370d0a373234352c313937392c372c34392c312c64762c382c312c323232322e373135362c323739332e333336350d0a373234352c313938302c382c36342c302c64762c382c312c323130332e323431322c323636362e313735310d0a313632342c313938352c352c32352c322c64762c372c302c323531392e323639372c4e410d0a323435302c313939322c332c392c302c75762c332c302c323638342e363837332c4e410d0a343535312c313939312c332c392c302c75762c332c312c323438342e303238382c333432352e313939340d0a363632332c313939302c332c392c302c75762c332c302c323133332e353135332c333239302e363130310d0a313439362c313939302c332c392c312c75762c342c312c323134312e303737342c333130302e333235350d0a313439362c313939312c342c31362c302c75762c342c312c323239362e343035332c333133362e323131360d0a383933372c313939302c332c392c312c75762c342c302c323536332e363138332c4e410d0a383933372c313939312c342c31362c302c75762c342c302c323731342e393433332c343039372e333133330d0a393438332c313939302c332c392c312c75762c342c312c323237352e393331352c333037382e363830320d0a393430322c313938342c332c392c302c75762c332c312c323237352e313231342c4e410d0a383932302c313939302c332c392c312c64762c342c302c333235372e393537372c343236352e373036380d0a383932302c313939312c342c31362c302c64762c342c302c333034332e313434362c4e410d0a323539372c313939302c332c392c322c64762c352c312c4e412c323132352e383139370d0a323539372c313939312c342c31362c312c64762c352c312c323236352e393737342c333234382e323436310d0a323539372c313939322c352c32352c302c64762c352c312c323530342e373831372c333030312e303732340d0a3532352c313939312c342c31362c302c64762c342c312c323131352e383532322c323738332e343234320d0a323535342c313939312c342c31362c332c64762c31302c302c323338312e313538342c4e410d0a323535342c313939322c352c32352c332c64762c31302c302c333032362e343432382c4e410d0a323535342c313939342c372c34392c332c64762c31302c302c323839322e343033352c4e410d0a323535342c313939372c31302c3130302c302c64762c31302c302c323738342e3734352c4e410d0a343939352c313939302c332c392c312c64762c342c302c323931352e333134322c343336382e373032330d0a343939352c313939312c342c31362c302c64762c342c312c4e412c333833342e333232380d0a363138362c313938362c332c392c312c64762c342c312c313930322e333538392c323331382e3731310d0a363138362c313938372c342c31362c302c64762c342c302c323334332e3837382c4e410d0a363332342c313938302c332c392c312c75762c342c302c313834332e383532342c4e410d0a363332342c313938312c342c31362c302c75762c342c302c323231322e323232362c4e410d0a393236362c313937362c382c36342c332c75762c31312c302c313932342e3434382c4e410d0a393236362c313937382c31302c3130302c312c75762c31312c302c323035352e313833342c4e410d0a393236362c313937392c31312c3132312c302c75762c31312c302c313937362e363830382c323836342e363038320d0a383035392c313938392c332c392c312c75762c342c312c323437372e333437312c4e410d0a383035392c313939302c342c31362c302c75762c342c312c323333372e373033322c333131382e323632360d0a323736342c313938362c332c392c322c64762c352c302c323236332e353838372c333037372e303130350d0a333030382c313939302c332c392c312c64762c342c302c323834332e3034362c4e410d0a333030382c313939312c342c31362c302c64762c342c302c323838312e323933332c4e410d0a3337342c313938342c332c392c322c75762c352c302c313932342e353034342c4e410d0a3337342c313938352c342c31362c312c75762c352c312c323033312e332c323337332e383735310d0a3337342c313938362c352c32352c302c75762c352c312c323236382e372c333230362e313933330d0a373936322c313937392c342c31362c322c75762c362c302c323435382e353633332c333539392e313738370d0a373936322c313938302c352c32352c312c75762c362c302c323630302e323735392c4e410d0a333137322c313938342c332c392c302c75762c332c302c313933382e353038372c4e410d0a393639332c313938372c332c392c322c75762c352c302c323030332e323938332c333631342e303935350d0a393639332c313938382c342c31362c312c75762c352c312c323237332e323832362c333239392e323338360d0a3835392c313938322c352c32352c302c75762c352c302c323735372e383033392c343334342e303434330d0a373834372c313938342c332c392c322c75762c352c302c323034302e393636392c323837392e383035340d0a373834372c313938362c352c32352c302c75762c352c312c323337382e3735352c323935372e373531310d0a353438342c313937352c332c392c322c75762c352c302c323235392e343637322c4e410d0a353438342c313937362c342c31362c312c75762c352c302c323330372e323639382c333237352e373333350d0a353438342c313937372c352c32352c302c75762c352c302c323637312e303235352c4e410d0a3738332c313937392c332c392c332c75762c382c302c323235332e383736322c333238362e353232340d0a3738332c313938302c342c31362c332c75762c382c302c323233392e3634372c333434392e393433330d0a3738332c313938312c352c32352c332c75762c382c302c323734332e303930322c333630302e303033390d0a3738332c313938322c362c33362c322c75762c382c312c323538312e393233322c333539302e353638330d0a3738332c313938332c372c34392c312c75762c382c312c323231322e313132372c333131332e313331330d0a3738332c313938342c382c36342c302c75762c382c312c323331372e383936392c333137312e343733310d0a333634312c313937392c332c392c322c75762c352c312c4e412c323934352e313736350d0a333634312c313938302c342c31362c312c75762c352c302c323230322e3831332c333331322e353939330d0a333634312c313938312c352c32352c302c75762c352c302c323738362e3239342c333436372e383234370d0a393035312c313937392c332c392c312c75762c342c302c323233332e393832352c323539372e393334380d0a393035312c313938302c342c31362c302c75762c342c312c323236302e303138392c323933372e313938360d0a373534382c313939322c332c392c332c75762c31312c302c323736342e303736312c333630312e383037380d0a373534382c313939332c342c31362c332c75762c31312c312c323430362e343631372c333535322e363130390d0a373534382c313939352c362c33362c332c75762c31312c312c323334362e303430312c333034362e343034310d0a373534382c313939362c372c34392c332c75762c31312c312c4e412c333438332e343830380d0a373534382c313939372c382c36342c332c75762c31312c312c323730362e303931342c333638382e3231380d0a373534382c313939382c392c38312c322c75762c31312c312c323637392e333832332c333532332e323531350d0a373534382c313939392c31302c3130302c312c75762c31312c302c323734382e3039362c333631352e373030390d0a373534382c323030302c31312c3132312c302c75762c31312c302c323835302e323433322c333436392e353533380d0a313531372c313939322c332c392c332c75762c31342c312c323435322e3433342c323639322e323532350d0a313531372c313939332c342c31362c332c75762c31342c302c323235342e323338312c4e410d0a313531372c313939352c362c33362c332c75762c31342c302c323034332e363031372c323933302e393238360d0a313531372c313939372c382c36342c332c75762c31342c302c323531352e303134332c333437382e313338330d0a313531372c313939382c392c38312c332c75762c31342c302c323538362e343631372c333236302e353733330d0a313531372c313939392c31302c3130302c332c75762c31342c302c323538342e303330392c4e410d0a313531372c323030312c31322c3134342c322c75762c31342c302c323934332e393734372c4e410d0a313531372c323030322c31332c3136392c312c75762c31342c312c323735392e323536362c333138332e393538390d0a313531372c323030332c31342c3139362c302c75762c31342c302c323434322e383034332c4e410d0a373331312c313937372c382c36342c302c64762c382c302c323837362e323734362c4e410d0a323934312c313939322c332c392c322c75762c352c312c323432332e303238342c333131342e373738350d0a323934312c313939332c342c31362c312c75762c352c302c323232382e353238392c4e410d0a383536392c313938372c342c31362c332c64762c31312c302c323933302e303232312c343039392e313233340d0a383536392c313938382c352c32352c332c64762c31312c312c323738382e373433372c333636302e393635340d0a383536392c313938392c362c33362c332c64762c31312c312c323936382e39312c333931352e303233360d0a383536392c313939302c372c34392c332c64762c31312c312c323935362e363435352c333937342e373238340d0a383536392c313939312c382c36342c332c64762c31312c302c323936392e383035322c343537382e323231340d0a383536392c313939322c392c38312c322c64762c31312c302c333637382e323335322c343638302e373535310d0a383536392c313939332c31302c3130302c312c64762c31312c312c323937352e34322c333739322e303634380d0a383536392c313939342c31312c3132312c302c64762c31312c302c333234302e383335392c343437302e373730350d0a393935372c313938372c342c31362c332c64762c31332c312c323536392e323338312c333536312e393233340d0a393935372c313938382c352c32352c332c64762c31332c302c323435302e343138342c4e410d0a393935372c313938392c362c33362c332c64762c31332c302c323538362e343834332c333533362e313537330d0a393935372c313939302c372c34392c332c64762c31332c302c323532312e373736382c4e410d0a393935372c313939312c382c36342c332c64762c31332c302c323531352e303238312c4e410d0a393935372c313939332c31302c3130302c332c64762c31332c302c323438332e363232392c4e410d0a393935372c313939342c31312c3132312c322c64762c31332c302c323734372e353132362c4e410d0a323030392c313939322c332c392c332c64762c392c312c323732372e393337352c333539352e363539360d0a323030392c313939332c342c31362c332c64762c392c312c323533392e363537392c333534382e383836310d0a323030392c313939352c362c33362c332c64762c392c312c323634362e363939332c333930362e303530350d0a323030392c313939372c382c36342c312c64762c392c312c323934362e313938362c343032392e383731390d0a323030392c313939382c392c38312c302c64762c392c312c333135392e373331342c343035342e393834330d0a3233372c313939322c332c392c332c64762c392c302c323439372e313432352c333139322e3739380d0a3233372c313939332c342c31362c332c64762c392c312c323231322e393932362c333039382e3637380d0a3233372c313939352c362c33362c332c64762c392c302c323230302e353834342c333133312e313833320d0a3233372c313939362c372c34392c322c64762c392c312c4e412c333335362e323132360d0a3233372c313939382c392c38312c302c64762c392c302c323732332e383538332c4e410d0a363732342c323030352c332c392c332c75762c362c312c323130302e333534332c333030372e393439380d0a363732342c323030362c342c31362c322c75762c362c312c323430362e323838332c323831372e303038320d0a363732342c323030372c352c32352c312c75762c362c302c323436322e353230382c4e410d0a363732342c323030382c362c33362c302c75762c362c312c323235382e363231332c333037302e333731370d0a393334312c313939392c332c392c302c75762c332c302c4e412c333038302e373530310d0a363932392c313938302c332c392c312c75762c342c302c4e412c333434352e383037330d0a363932392c313938312c342c31362c302c75762c342c312c4e412c333439312e3232320d0a, 26444⟩

def pcs_c0 : Claim :=
  { column := some (b "age"),
    filter := [],
    stat := .min,
    naTokens := [b "", b "NA"],
    scale := ((1 : Rat) / 1),
    reported := b "3" }

theorem pcs_batch : runAll pcs_src [pcs_c0] =
    [.checked .consistent (.rat ((3 : Rat) / 1)) 617 0] := by decide +kernel

theorem pcs_claim_0 : run pcs_src pcs_c0 = .checked .consistent (.rat ((3 : Rat) / 1)) 617 0 :=
  run_of_runAll pcs_batch 0 rfl rfl
#print axioms pcs_claim_0

