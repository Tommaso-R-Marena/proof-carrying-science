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

def pcs_src : Source := ⟨0x736f696c536f7572636553702c736f696c5472742c7265702c6e6f335f6e5f70706d2c6f6c73656e5f705f70706d2c4b5f70706d2c4b5f6d65715f313030672c4e615f70706d2c4e615f6d65715f313030672c43615f6d65715f313030672c4d675f6d65715f313030672c4345432c4f4d2c70480d434f2c492c312c352e36322c362e322c34312c302e312c31362c302e30372c312e33332c302e382c322e332c312e39312c352e36340d434f2c492c322c322e37322c342e342c33342c302e30392c31382c302e30382c322e38392c312e31352c342e32312c312e38312c352e38370d434f2c492c332c31382e38372c32352e322c38312c302e32312c33322c302e31342c372e30322c322e34362c392e38332c372e36392c352e36370d434f2c492c342c352e33372c31302e372c33342c302e30392c31392c302e30382c332e31352c312e38312c352e31332c322e30352c362e31320d434f2c492c352c352e31322c31302e392c3130392c302e32382c32312c302e30392c352e37312c322e37372c382e38342c342c362e33360d434f2c492c362c322e37332c372e312c32392c302e30372c32312c302e30392c332e31352c322e30372c352e33382c322e36342c362e32350d434f2c572c312c362e36322c332e322c32372c302e30372c31352c302e30372c312e34352c302e39312c322e352c322e31382c352e34310d434f2c572c322c352e31372c332e332c33302c302e30382c31362c302e30372c332e35352c312e33322c352e30312c322e37372c352e38370d434f2c572c332c32322e36322c31352e342c35342c302e31342c32332c302e312c362e30352c322e32322c382e35312c372e34352c352e34340d434f2c572c342c382e32322c362e392c38362c302e32322c32302c302e30392c342e36362c322e33352c372e33312c322e39382c362e31380d434f2c572c352c362e37372c372e382c33332c302e30382c31392c302e30382c332e362c322e30332c352e37392c322e33332c362e31330d434f2c572c362c372e31372c342e372c32352c302e30362c32302c302e30392c332e31392c322e30392c352e34332c322e34322c352e39310d43512c492c312c392e35322c31382e342c3338332c302e39382c3234372c312e30372c362e35392c362e352c31352e31342c392e32342c362e33320d43512c492c322c382e33372c31342e362c3430322c312e30332c3135382c302e36392c352e31332c352e31312c31312e39352c372e33392c362e32330d43512c492c332c332e37332c31312c3136352c302e34322c35382c302e32352c322e30362c312e36392c342e34322c342e37332c352e35390d43512c492c342c342e37332c31302c3138342c302e34372c35312c302e32322c322e332c312e382c342e37392c342e332c352e37310d43512c492c352c382e35372c31352e392c3333362c302e38362c3139382c302e38362c362e32362c352e32312c31332e31392c31302e35382c362e30320d43512c492c362c332e30382c31322e362c3138392c302e34382c3135352c302e36372c332e34322c332e36332c382e32312c392e31342c352e35380d43512c572c312c32382e38322c31302e322c3332352c302e38332c3234362c312e30372c362e34332c362e34332c31342e37362c392e39322c362e30320d43512c572c322c32332e39322c382e352c3335312c302e392c3135392c302e36392c352e32372c352e33332c31322e31392c372e34332c352e38350d43512c572c332c31322e35372c372e322c3136372c302e34332c36312c302e32362c322e332c312e392c342e38392c342e33352c352e33350d43512c572c342c32332e34322c372e362c3138372c302e34382c35392c302e32352c322e37332c322e30392c352e35342c342e34392c352e33350d43512c572c352c34332e32372c362e362c3237332c302e372c3137302c302e37342c352e37322c342e36362c31312e38322c382e39382c352e35370d43512c572c362c31392e34322c362e332c3136322c302e34312c3133342c302e35382c332e31332c332e32332c372e33362c372e32362c352e33310d46432c492c312c332e32342c352c34372c302e31322c31352c302e30372c312e35312c302e39312c322e36312c312e30352c352e37390d46432c492c322c332e36372c372e312c34332c302e31312c31382c302e30382c322e38322c312e33352c342e33362c322e38322c352e39380d46432c492c332c332e30332c342e352c33352c302e30392c31332c302e30362c312e38312c302e39352c322e39312c312e30332c352e39330d46432c492c342c322e372c352e342c35342c302e31342c31352c302e30372c312e38342c302e39322c322e39362c312e31372c362e30310d46432c492c352c302e34342c352e362c32322c302e30362c31332c302e30362c312e34362c312e30382c322e36352c312e30372c352e36370d46432c492c362c302e38312c332e392c32312c302e30352c31322c302e30352c312e34362c302e38392c322e34352c302e36362c362e30390d46432c572c312c342e34322c332e382c34342c302e31312c31362c302e30372c312e35322c302e392c322e36312c312e30332c352e37350d46432c572c322c362e34372c352e312c33342c302e30392c31372c302e30382c322e38342c312e33362c342e33372c322e33312c352e37380d46432c572c332c322e332c342c33322c302e30382c31342c302e30362c312e37372c302e39322c322e38332c312e30342c352e39360d46432c572c342c342e35352c342e372c35312c302e31332c31392c302e30382c312e39332c302e39362c332e312c312e32312c352e38370d46432c572c352c322e34382c342e392c32312c302e30352c31342c302e30362c312e362c312e31352c322e38372c302e39392c352e36340d46432c572c362c322e37372c332e362c32302c302e30352c31322c302e30352c312e33372c302e38372c322e33342c302e36332c352e39360d46562c492c312c302e362c31352e362c3130362c302e32372c34382c302e32312c362e31342c322e322c382e38322c342e31352c362e35360d46562c492c322c302e31392c342e322c38362c302e32322c33332c302e31342c352e32352c312e362c372e32312c312e37382c372e32310d46562c492c332c302e352c342e392c39322c302e32342c34312c302e31382c382c322e33322c31302e37332c322e35352c362e390d46562c492c342c312e35362c382e352c3131302c302e32382c34322c302e31382c31302e38372c322e39372c31342e33312c332e38382c362e37390d46562c492c352c312e34372c31352e332c3133332c302e33342c34382c302e32312c372e38392c322e36352c31312e30382c342e31332c362e38320d46562c492c362c302e33342c32332e322c3139302c302e34392c3130372c302e34372c372e32332c332e31342c31312e33322c342e31352c362e35320d46562c572c312c382e32322c31332e382c39382c302e32352c34372c302e32312c362e392c322e31392c392e35352c342e30312c362e33370d46562c572c322c322e38362c322e382c38352c302e32322c33332c302e31342c342e37362c312e36322c362e37342c312e38312c362e39310d46562c572c332c312e39392c322e342c38352c302e32322c34312c302e31382c372e38372c322e31372c31302e34342c322e30372c362e38360d46562c572c342c392e35372c342e312c3132302c302e33312c34302c302e31372c31312e32362c332e30362c31342e382c342e31362c362e370d46562c572c352c372e32322c382e372c3131392c302e33312c34342c302e31392c372e342c322e34322c31302e33312c342e30332c362e37320d46562c572c362c392e34322c31322e372c3136362c302e34332c3130342c302e34352c362e37322c322e39362c31302e35362c332e38352c362e340d47432c492c312c342e32382c332e332c34312c302e31312c31322c302e30352c312e31372c302e36332c312e39362c312e31332c352e39310d47432c492c322c322c382c35342c302e31342c32332c302e312c312e38392c312e33362c332e34392c312e39352c352e39390d47432c492c332c312e39342c392e392c33342c302e30392c32312c302e30392c332e30362c312e39322c352e31362c322e34392c352e36310d47432c492c342c312e39392c31342c34352c302e31312c32312c302e30392c322e34322c312e39382c342e362c322e312c352e34320d47432c492c352c312e38392c382e392c33362c302e30392c32312c302e30392c332e30362c312e39332c352e31372c322e362c352e35360d47432c492c362c332e33332c31322c33392c302e312c32312c302e30392c332e392c322e312c362e31382c332e36352c362e31310d47432c572c312c382e35322c322e372c34312c302e312c31322c302e30352c312e32322c302e36382c322e30362c312e31352c352e34310d47432c572c322c352e38322c362e372c35362c302e31342c32332c302e312c322e31352c312e34332c332e38332c312e39322c352e38310d47432c572c332c31302e32322c352e332c35322c302e31332c32312c302e30392c332e37332c312e35362c352e35322c322e39372c352e37390d47432c572c342c372e37372c31322e342c35302c302e31332c32312c302e30392c322e36332c322e30362c342e39312c322e33352c352e34310d47432c572c352c31302e36322c372e332c33352c302e30392c32342c302e312c332e31352c322e30372c352e34312c322e37352c352e34360d47432c572c362c31312e32372c382e392c33352c302e30392c32332c302e312c332e38382c322e31322c362e31392c332e322c352e37330d474d2c492c312c322e312c372e372c34332c302e31312c31382c302e30382c322e32342c312e33392c332e38322c322e30372c352e36390d474d2c492c322c322e34362c392e332c35352c302e31342c31372c302e30372c322e36322c312e33352c342e31392c322e37312c352e37350d474d2c492c332c342e30352c392e352c35342c302e31342c31372c302e30372c322e38342c312e30392c342e31332c332e32372c352e35360d474d2c492c342c352e36322c31372e322c34322c302e31312c32332c302e312c362e32362c322c382e34372c382e30382c352e33310d474d2c492c352c342e33352c362e322c38342c302e32322c31392c302e30382c322e30342c312e31352c332e34392c322e31332c352e37390d474d2c492c362c352e35372c372e372c35302c302e31332c31382c302e30382c322e33342c312e31392c332e37332c322e33332c352e360d474d2c572c312c31312e36322c352c34322c302e31312c31382c302e30382c322e33372c312e34352c342c322e33312c352e34380d474d2c572c322c31312e33372c362c34392c302e31322c31372c302e30382c322e36362c312e33352c342e32312c322e362c352e33390d474d2c572c332c31302e36372c382c34362c302e31322c31372c302e30382c332e32382c312e31382c342e36362c332e32322c352e330d474d2c572c342c32392e36322c31302e362c33302c302e30382c32312c302e30392c362e30332c312e392c382e30392c382e312c352e30310d474d2c572c352c352e32372c342e392c37382c302e322c31382c302e30382c322e30352c312e31382c332e35312c322e32332c352e38330d474d2c572c362c31302e37372c362e352c34332c302e31312c31342c302e30362c322e33312c312e31382c332e36362c322e35392c352e33330d50452c492c312c312e39312c392e382c3138382c302e34382c35362c302e32342c312e39372c322e32312c342e392c342e30332c362e30330d50452c492c322c322e35342c31302e392c3233302c302e35392c37362c302e33332c322e33322c322e35372c352e38312c342e38332c362e30350d50452c492c332c322e342c372c3133302c302e33332c37362c302e33332c322e34322c322e30332c352e31312c332e32342c352e39360d50452c492c342c322e37382c362e372c3133372c302e33352c37332c302e33322c322e31332c322e30332c342e38322c332e34342c362e30350d50452c492c352c312e33312c372e362c3132302c302e33312c35392c302e32362c312e312c312e33332c322e39392c322e30382c362e30340d50452c492c362c322e30392c362e382c3130392c302e32382c35312c302e32322c312e34372c312e33322c332e32392c322e36352c352e38330d50452c572c312c31302e32372c362e362c3136392c302e34332c35352c302e32342c312e38362c322e31312c342e36352c342e31332c352e37390d50452c572c322c31312e37372c362e322c3230392c302e35332c37322c302e33312c322e32312c322e34342c352e34392c342e36322c352e37340d50452c572c332c31302e39322c342e342c3132322c302e33312c36372c302e32392c322e33332c312e39392c342e39322c332e31382c352e380d50452c572c342c382e34322c332e362c3131342c302e32392c36392c302e332c312e38362c312e37392c342e32352c322e39382c352e36370d50452c572c352c392e37372c362e352c3131392c302e332c36322c302e32372c312e31372c312e34312c332e31362c322e30332c352e38340d50452c572c362c382e38372c352e382c39372c302e32352c35322c302e32332c312e342c312e32362c332e31342c322e382c352e360d50532c492c312c332e31372c342e342c3130322c302e32362c3237392c312e32312c342e35322c332e32312c392e32312c322e38312c382e30330d50532c492c322c312e30372c342e382c38372c302e32322c3130342c302e34352c322e35392c312e33342c342e36312c312e34322c372e34320d50532c492c332c312e31332c392e322c3233382c302e36312c3134312c302e36312c352c332e34332c392e36352c342e34352c362e31370d50532c492c342c352e35372c31352e372c3238362c302e37332c3132392c302e35362c31312e38362c332e32382c31362e34332c332e39382c372e31390d50532c492c352c302e35392c31302e392c3137352c302e34352c39342c302e34312c392e38322c322e37332c31332e342c342e30322c362e39340d50532c492c362c302e37372c31302c3232322c302e35372c3230352c302e38392c342e33382c332e37342c392e35382c332e36382c362e35380d50532c572c312c31392e39322c322e392c37392c302e322c3236352c312e31352c342e33332c322e38332c382e35312c312e39342c372e38380d50532c572c322c31312e34322c322e362c38322c302e32312c3131382c302e35312c332e35362c312e39322c362e322c312e35342c372e32320d50532c572c332c352e32372c362e352c3231332c302e35342c3134382c302e36342c352e32352c332e35362c31302c342e36312c362e30390d50532c572c342c31342e34322c31332e352c3235332c302e36352c3132332c302e35342c392e30322c332e31332c31332e33332c342e30332c372e30310d50532c572c352c342e33372c382e312c3134332c302e33372c39362c302e34322c372e35352c322e38332c31312e31362c342e332c362e36380d50532c572c362c382e38372c362e372c3138382c302e34382c3139362c302e38352c342e30362c332e37362c392e31362c332e33382c362e34360d52532c492c312c302e31312c342e332c33342c302e30392c33322c302e31342c312e36352c312e32332c332e31312c312e37322c362e31320d52532c492c322c312e30332c322e342c34392c302e31332c32352c302e31312c312e36322c302e37322c322e35382c302e36382c372e30370d52532c492c332c312e39332c332e352c33392c302e312c33302c302e31332c312e36362c302e37342c322e36332c302e36372c372e30390d52532c492c342c312e37342c332e352c35302c302e31332c33302c302e31332c312e37312c302e37322c322e372c302e35392c372e34350d52532c492c352c302e32342c322e372c33322c302e30382c32382c302e31322c322e35382c322e342c352e31382c312e36352c362e35340d52532c492c362c302e312c342e362c34312c302e312c34352c302e31392c342e39352c322e38312c382e30352c322e36352c362e37380d52532c572c312c322e38322c332e312c33342c302e30392c33312c302e31342c312e35332c312e31372c322e39322c312e34382c362e30390d52532c572c322c322e352c322e342c34372c302e31322c32382c302e31322c312e34382c302e37342c322e34362c302e382c362e39360d52532c572c332c332e37342c312e392c33382c302e312c33312c302e31332c312e35342c302e37342c322e35312c302e35392c362e37310d52532c572c342c332e35362c322e372c34362c302e31322c32372c302e31322c312e36362c302e37352c322e36352c302e36312c372e31330d52532c572c352c382e36372c322e392c34332c302e31312c33312c302e31332c332e33332c322e38352c362e34322c322e38322c362e31370d52532c572c362c322e34392c332e382c34322c302e31312c34322c302e31382c352e30342c322e38322c382e31352c322e37382c362e36340d524f2c492c312c302e312c32342e352c3134322c302e33362c37392c302e33342c392e32342c322e32332c31322e31372c352e34392c362e35310d524f2c492c322c302e39362c32322e352c37302c302e31382c34342c302e31392c362e35322c322e30392c382e39382c352e37312c352e34370d524f2c492c332c362e31322c33312e352c38312c302e32312c3131342c302e352c362e38322c312e37332c392e32362c322e37392c372e30390d524f2c492c342c332e36342c32322e372c3130362c302e32372c35332c302e32332c392e352c312e34392c31312e352c322e37382c372e35340d524f2c492c352c302e312c332c32342c302e30362c33342c302e31352c322e32342c332e30372c352e35322c312e35372c372e35380d524f2c492c362c302e312c342e322c33392c302e312c34382c302e32312c332e392c342e38322c392e30332c322e31362c362e39380d524f2c572c312c302e36382c31382e372c3131322c302e32392c38342c302e33372c31322e312c322e382c31352e35352c352e37322c362e34320d524f2c572c322c392e32322c31322e382c36362c302e31372c34332c302e31392c362e33372c322e30322c382e37352c352e32352c352e33350d524f2c572c332c392e38372c32352e372c37312c302e31382c3130392c302e34372c372e39322c312e382c31302e33382c322e35362c372e310d524f2c572c342c31312e36372c31382e372c39362c302e32342c35392c302e32362c392e35332c312e36312c31312e36342c322e34332c372e34360d524f2c572c352c302e35362c332e312c32382c302e30372c33332c302e31342c322e37322c332e35322c362e34352c312e382c372e37310d524f2c572c362c302e32312c332e372c34362c302e31322c34362c302e322c332e37392c342e36362c382e37372c322e32362c362e37370d53412c492c312c31312e30322c31322c3138392c302e34382c3331372c312e33382c322e35392c332e352c372e39352c392e34382c352e330d53412c492c322c31362e38372c31352c3139392c302e35312c3239362c312e32392c332e372c342e352c392e39392c31312c352e35310d53412c492c332c31302e36372c31342e342c3234302c302e36312c3339302c312e372c332e382c342e35322c31302e36322c392e35312c352e36310d53412c492c342c362e33322c31362e352c3232342c302e35372c3138372c302e38312c342e39372c352e34332c31312e37382c392e35342c352e37370d53412c492c352c34302e39322c32332e332c3436332c312e31392c3234352c312e30372c372e35362c362e37342c31362e35362c31302e362c352e39320d53412c492c362c31302e36322c32342e392c3332372c302e38342c3237382c312e32312c342e39362c352e33332c31322e33332c31332e37342c352e36330d53412c572c312c31392e36322c362e392c3137392c302e34362c3238342c312e32332c322e36362c332e342c372e37352c392e35372c352e31330d53412c572c322c33332e31372c362e382c3138372c302e34382c3237322c312e31382c332e35372c342e34322c392e36352c392e38352c352e32330d53412c572c332c31362e38372c372e322c3230342c302e35322c3337332c312e36322c332e37332c342e362c31302e34382c392e34342c352e35330d53412c572c342c32342e37322c392e342c3236312c302e36372c3233312c312c362c362e35372c31342e32352c31312e39332c352e35340d53412c572c352c31362e34322c31312c3436392c312e322c3234362c312e30372c372e36342c362e38332c31362e37352c31302e39342c352e39330d53412c572c362c33362e37322c31382e312c3338382c302e39392c3334302c312e34382c362e32312c362e36392c31352e33372c31352e35332c352e34390d53432c492c312c312e37352c31332e322c3131352c302e32392c3130362c302e34362c352e32332c322e34322c382e34312c342e33342c362e34310d53432c492c322c332e33342c392e382c36332c302e31362c3130302c302e34332c352e33372c322e32322c382e31392c332e39392c362e320d53432c492c332c302e34342c31302e392c3132382c302e33332c3134332c302e36322c362e30382c322e33322c392e33352c332e39382c362e34350d53432c492c342c372e37322c362e382c34372c302e31322c33312c302e31332c332e33352c312e38362c352e34362c312e30382c362e33390d53432c492c352c382e30372c31392e332c37382c302e322c39312c302e342c372e30392c322e35382c31302e32372c342e39322c352e38380d53432c492c362c322e30372c382e322c34382c302e31322c33392c302e31372c332c312e39382c352e32372c322e34312c352e34340d53432c572c312c392e31372c392e392c39312c302e32332c3130342c302e34352c352e36382c322e34332c382e37392c332e33372c362e34360d53432c572c322c31302e32322c362e312c35342c302e31342c39342c302e34312c352e332c322e31352c382c332e37312c362e30370d53432c572c332c322e38372c352e342c39392c302e32352c3133362c302e35392c352e35352c322e312c382e352c332e36312c362e36340d53432c572c342c31322e34372c362e332c34322c302e31312c33302c302e31332c332e30372c312e38312c352e31322c302e39342c362e33340d53432c572c352c34322e32322c31342e332c38312c302e32312c3130362c302e34362c372e37392c332e31342c31312e362c372e31352c352e34320d53432c572c362c31302e33372c362e342c34342c302e31312c34332c302e31382c332e31312c322e30342c352e34352c322e34362c352e32380d54462c492c312c312e31372c31312e362c3136362c302e34322c3137392c302e37382c322e38322c332e38392c372e39312c352e37322c352e38390d54462c492c322c312e30332c31302e312c3136342c302e34322c3134382c302e36342c322e33332c332e30392c362e34382c352e33322c352e38370d54462c492c332c302e35312c31342e332c3231302c302e35342c3137392c302e37382c322e37312c332e36342c372e36372c352e34342c360d54462c492c342c302e31352c31322e312c3136332c302e34322c3135372c302e36382c352e31392c332e32392c392e35372c362e30332c362e30320d54462c492c352c302e312c31382e372c3330302c302e37372c3236302c312e31332c342e33392c352e31342c31312e34322c31302e34312c352e37330d54462c492c362c302e312c31342e362c3333332c302e38352c3137362c302e37362c342e38322c342e37342c31312e31382c372e31362c362e30320d54462c572c312c31302e39372c362e352c3134382c302e33382c3136392c302e37332c322e34372c332e352c372e30372c352e37382c352e370d54462c572c322c32322e39372c382e362c3136382c302e34332c3136302c302e372c322e37312c332e35352c372e33382c342e392c352e35390d54462c572c332c31332e34372c392e362c3139332c302e34392c3136362c302e37322c322e36372c332e35382c372e34372c352e34322c352e38340d54462c572c342c31342e33322c382e322c3135342c302e33392c3136322c302e372c352e33372c332e34352c392e39322c352e36342c352e37370d54462c572c352c32322e30372c382e312c3235322c302e36352c3233332c312e30312c342e30342c342e37332c31302e34332c392e33372c352e34360d54462c572c362c31342e32372c372c3239352c302e37352c3136332c302e37312c342e362c342e35312c31302e35382c372e31392c352e38370d54472c492c312c302e33332c31302c3137372c302e34352c35322c302e32332c312e36352c312e37372c342e312c332e34352c352e38370d54472c492c322c302e34362c31312c3137302c302e34332c3137322c302e37352c322e39372c332e37372c372e39322c352e37322c362e30310d54472c492c332c322e33362c372c3131322c302e32392c37352c302e33332c312e39332c312e39362c342e352c332e30382c352e38370d54472c492c342c302e32322c31332e372c3234332c302e36322c3131312c302e34382c332e342c332e32372c372e37382c372e32372c352e36390d54472c492c352c302e33362c31352e342c3237392c302e37312c3233312c312c332e38322c342e30342c392e35382c372e31342c352e38360d54472c492c362c322e30352c31302e372c3136322c302e34312c3135392c302e36392c322e33362c332e31312c362e35382c352e34392c352e37390d54472c572c312c33392e39372c382e372c3137322c302e34342c3231382c302e39352c332e34342c342e32362c392e30382c352e39372c352e36370d54472c572c322c34312e33322c382e332c3136322c302e34312c3230342c302e38392c332e31322c332e39362c382e33372c352e37392c352e34310d54472c572c332c31352e32372c352e332c3130362c302e32372c37382c302e33342c322e31322c322e31342c342e38372c332e32382c352e36340d54472c572c342c32372e33322c382c3139332c302e34392c3130362c302e34362c332e31392c332e30352c372e322c362e35362c352e32330d54472c572c352c34362e35322c392e332c3233342c302e362c3232362c302e39382c332e37382c342e31322c392e34382c362e39312c352e33380d54472c572c362c32372e33372c362e362c3135312c302e33392c3136322c302e372c322e34362c332e32342c362e37392c352e34372c352e3337, 9792⟩

def pcs_c0 : Claim :=
  { column := none,
    filter := [],
    stat := .count,
    naTokens := [b "", b "NA"],
    scale := ((1 : Rat) / 1),
    reported := b "14" }

def pcs_c1 : Claim :=
  { column := none,
    filter := [.textEq (b "soilSourceSp") (b "CO")],
    stat := .count,
    naTokens := [b "", b "NA"],
    scale := ((1 : Rat) / 1),
    reported := b "6" }

theorem pcs_batch : runAll pcs_src [pcs_c0, pcs_c1] =
    [.checked .inconsistent (.rat ((168 : Rat) / 1)) 168 0,
    .checked .inconsistent (.rat ((12 : Rat) / 1)) 12 0] := by decide +kernel

theorem pcs_claim_0 : run pcs_src pcs_c0 = .checked .inconsistent (.rat ((168 : Rat) / 1)) 168 0 :=
  run_of_runAll pcs_batch 0 rfl rfl
#print axioms pcs_claim_0

theorem pcs_claim_1 : run pcs_src pcs_c1 = .checked .inconsistent (.rat ((12 : Rat) / 1)) 12 0 :=
  run_of_runAll pcs_batch 1 rfl rfl
#print axioms pcs_claim_1

