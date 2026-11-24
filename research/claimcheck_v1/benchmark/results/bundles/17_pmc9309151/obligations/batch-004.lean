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

def pcs_src : Source := ⟨0x74616e6b2c6167652c414c432c534c5f6d6d2c426f64795f64657074682c4d7573636c655f617265612c6470682c67726f7774685f73706565642c7265706561745f6e6f2c696e646976696475616c5f6e6f2c696e646976696475616c5f69642c73706565642c67726f75700d0a616765315f312c312c6d61726b65642c32312e35312c342e3331352c32382e3732382c32302c302e393235352c312c322c312c34332e37393435363930362c726f7574696e650d0a616765315f312c312c6d61726b65642c32312e35312c342e3331352c32382e3732382c32302c302e393235352c322c322c312c34382e35343738323036362c726f7574696e650d0a616765315f312c312c6d61726b65642c32312e35312c342e3331352c32382e3732382c32302c302e393235352c332c322c312c33362e363138363232322c726f7574696e650d0a616765315f312c312c6d61726b65642c32322e36392c342e3531372c32342e3831312c32302c302e393834352c312c332c322c35392e39393930373031332c726f7574696e650d0a616765315f312c312c6d61726b65642c32322e36392c342e3531372c32342e3831312c32302c302e393834352c322c332c322c36362e30373339392c726f7574696e650d0a616765315f312c312c6d61726b65642c32322e36392c342e3531372c32342e3831312c32302c302e393834352c332c332c322c36322e36303238363233372c726f7574696e650d0a616765315f312c332c6e6f6e652c31372e31332c332e3430342c31372e3232322c32302c302e373036352c312c342c332c34352e38373932393332342c726f7574696e650d0a616765315f312c332c6e6f6e652c31372e31332c332e3430342c31372e3232322c32302c302e373036352c322c342c332c33302e32363633353938392c726f7574696e650d0a616765315f312c332c6e6f6e652c31372e31332c332e3430342c31372e3232322c32302c302e373036352c332c342c332c34392e39333337383633342c726f7574696e650d0a616765335f312c312c6e6f6e652c32352e32352c352e3736382c34332e3232322c32302c312e313132352c312c312c342c33322e34313639363337382c726f7574696e650d0a616765335f312c312c6e6f6e652c32352e32352c352e3736382c34332e3232322c32302c312e313132352c322c312c342c33392e31353939363734362c726f7574696e650d0a616765335f312c312c6e6f6e652c32352e32352c352e3736382c34332e3232322c32302c312e313132352c332c312c342c33372e31313138343230392c726f7574696e650d0a616765335f312c312c6e6f6e652c32332e30372c342e3831362c33312e3136372c32302c312e303033352c312c322c352c34332e35353031363537382c726f7574696e650d0a616765335f312c312c6e6f6e652c32332e30372c342e3831362c33312e3136372c32302c312e303033352c322c322c352c33392e31353837333537392c726f7574696e650d0a616765335f312c312c6e6f6e652c32332e30372c342e3831362c33312e3136372c32302c312e303033352c332c322c352c33332e34323038373737322c726f7574696e650d0a616765335f312c332c6d61726b65642c31382e34342c332e36322c31372e3336332c32302c302e3737322c312c332c362c34322e363438313636382c726f7574696e650d0a616765335f312c332c6d61726b65642c31382e34342c332e36322c31372e3336332c32302c302e3737322c322c332c362c34372e35323839343834392c726f7574696e650d0a616765335f312c332c6d61726b65642c31382e34342c332e36322c31372e3336332c32302c302e3737322c332c332c362c34362e36353938303935372c726f7574696e650d0a616765335f312c312c6e6f6e652c31352e39352c332e3436342c31342e3633332c32302c302e363437352c312c342c372c33382e30353639383331342c726f7574696e650d0a616765335f312c312c6e6f6e652c31352e39352c332e3436342c31342e3633332c32302c302e363437352c322c342c372c37312e32303835383936372c726f7574696e650d0a616765335f312c312c6e6f6e652c31352e39352c332e3436342c31342e3633332c32302c302e363437352c332c342c372c36312e35313438323938352c726f7574696e650d0a616765315f322c312c6d61726b65642c32342e37362c352e3533342c34302e3333362c32302c312e3038382c312c312c382c37372e34353436383930392c726f7574696e650d0a616765315f322c312c6d61726b65642c32342e37362c352e3533342c34302e3333362c32302c312e3038382c322c312c382c38322e35323332313539382c726f7574696e650d0a616765315f322c312c6d61726b65642c32342e37362c352e3533342c34302e3333362c32302c312e3038382c332c312c382c38392e35333133393738352c726f7574696e650d0a616765315f322c312c6d61726b65642c32312e36362c352e3136382c32392e3539382c32302c302e3933332c312c322c392c39362e36313537333938342c726f7574696e650d0a616765315f322c312c6d61726b65642c32312e36362c352e3136382c32392e3539382c32302c302e3933332c322c322c392c39312e35393933353837342c726f7574696e650d0a616765315f322c312c6d61726b65642c32312e36362c352e3136382c32392e3539382c32302c302e3933332c332c322c392c38352e33303030353333352c726f7574696e650d0a616765315f322c312c6d61726b65642c31342e34392c322e3930352c31302e3935342c32302c302e353734352c312c332c31302c35372e36343930343332372c726f7574696e650d0a616765315f322c312c6d61726b65642c31342e34392c322e3930352c31302e3935342c32302c302e353734352c322c332c31302c35362e30323633343438332c726f7574696e650d0a616765315f322c312c6d61726b65642c31342e34392c322e3930352c31302e3935342c32302c302e353734352c332c332c31302c35392e30303037333739392c726f7574696e650d0a616765315f322c312c6d61726b65642c31352e32312c332e3036382c31332e3330342c32302c302e363130352c312c342c31312c34352e32383832303937362c726f7574696e650d0a616765315f322c312c6d61726b65642c31352e32312c332e3036382c31332e3330342c32302c302e363130352c322c342c31312c34362e31383233303931392c726f7574696e650d0a616765315f322c312c6d61726b65642c31352e32312c332e3036382c31332e3330342c32302c302e363130352c332c342c31312c35362e30313330343132372c726f7574696e650d0a616765335f322c312c6e6f6e652c32312e32392c342e3330342c32362e3937372c32302c302e393134352c312c312c31322c35312e33383932303837372c726f7574696e650d0a616765335f322c312c6e6f6e652c32312e32392c342e3330342c32362e3937372c32302c302e393134352c322c312c31322c36322e38303636323931332c726f7574696e650d0a616765335f322c312c6e6f6e652c32312e32392c342e3330342c32362e3937372c32302c302e393134352c332c312c31322c36382e37313735393736392c726f7574696e650d0a616765335f322c312c6e6f6e652c32302e37332c342e3337342c32342e3233392c32302c302e383836352c312c322c31332c33342e33333537353836332c726f7574696e650d0a616765335f322c312c6e6f6e652c32302e37332c342e3337342c32342e3233392c32302c302e383836352c322c322c31332c33332e38383735323432382c726f7574696e650d0a616765335f322c312c6e6f6e652c32302e37332c342e3337342c32342e3233392c32302c302e383836352c332c322c31332c32382e34383839353339362c726f7574696e650d0a616765335f322c312c6e6f6e652c31372e39332c332e3137372c31362e3937362c32302c302e373436352c312c332c31342c34372e38353438353236372c726f7574696e650d0a616765335f322c312c6e6f6e652c31372e39332c332e3137372c31362e3937362c32302c302e373436352c322c332c31342c34362e34363733353038312c726f7574696e650d0a616765335f322c312c6e6f6e652c31372e39332c332e3137372c31362e3937362c32302c302e373436352c332c332c31342c34372e36343138313131372c726f7574696e650d0a616765335f322c332c6d61726b65642c31372e332c332e35342c31342e32332c32302c302e3731352c312c342c31352c34352e39353533353636372c726f7574696e650d0a616765335f322c332c6d61726b65642c31372e332c332e35342c31342e32332c32302c302e3731352c322c342c31352c34302e32313438303031372c726f7574696e650d0a616765335f322c332c6d61726b65642c31372e332c332e35342c31342e32332c32302c302e3731352c332c342c31352c34312e39373538333238312c726f7574696e650d0a616765315f312c312c6d61726b65642c32332e33362c342e3635382c33322e3734362c32342c302e3834383333333333332c312c312c31372c38382e34303030313039332c726f7574696e650d0a616765315f312c312c6d61726b65642c32332e33362c342e3635382c33322e3734362c32342c302e3834383333333333332c322c312c31372c37352e37333530353135322c726f7574696e650d0a616765315f312c312c6d61726b65642c32332e33362c342e3635382c33322e3734362c32342c302e3834383333333333332c332c312c31372c35362e36383435393236342c726f7574696e650d0a616765315f312c312c6d61726b65642c31392e32352c342e34322c31382e3438332c32342c302e3637373038333333332c312c322c31382c34372e30343838343533322c726f7574696e650d0a616765315f312c312c6d61726b65642c31392e32352c342e34322c31382e3438332c32342c302e3637373038333333332c322c322c31382c35372e33313337313436312c726f7574696e650d0a616765315f312c312c6d61726b65642c31392e32352c342e34322c31382e3438332c32342c302e3637373038333333332c332c322c31382c36342e36343537363939372c726f7574696e650d0a616765315f312c312c6d61726b65642c31392e37312c342e3031322c32312e3335312c32342c302e36393632352c312c332c31392c36342e35343532343633342c726f7574696e650d0a616765315f312c312c6d61726b65642c31392e37312c342e3031322c32312e3335312c32342c302e36393632352c322c332c31392c37362e32363330323631342c726f7574696e650d0a616765315f312c312c6d61726b65642c31392e37312c342e3031322c32312e3335312c32342c302e36393632352c332c332c31392c37302e39373238313633332c726f7574696e650d0a616765315f312c332c6e6f6e652c32312e31322c342e3339332c32352e3339312c32342c302e3735352c312c342c32302c35332e36393933303336362c726f7574696e650d0a616765315f312c332c6e6f6e652c32312e31322c342e3339332c32352e3339312c32342c302e3735352c322c342c32302c35382e39373532353032382c726f7574696e650d0a616765315f312c332c6e6f6e652c32312e31322c342e3339332c32352e3339312c32342c302e3735352c332c342c32302c34382e30353331323533312c726f7574696e650d0a616765335f312c312c6e6f6e652c31382e32372c332e3638322c31372e372c32342c302e36333632352c312c312c32312c35352e31353233303532312c726f7574696e650d0a616765335f312c312c6e6f6e652c31382e32372c332e3638322c31372e372c32342c302e36333632352c322c312c32312c36372e39343732383831382c726f7574696e650d0a616765335f312c312c6e6f6e652c31382e32372c332e3638322c31372e372c32342c302e36333632352c332c312c32312c36392e32303633343939312c726f7574696e650d0a616765335f312c332c6d61726b65642c31382e37332c332e3137392c31372e32352c32342c302e3635353431363636372c312c322c32322c35362e36323337353434312c726f7574696e650d0a616765335f312c332c6d61726b65642c31382e37332c332e3137392c31372e32352c32342c302e3635353431363636372c322c322c32322c33302e353131323333342c726f7574696e650d0a616765335f312c332c6d61726b65642c31382e37332c332e3137392c31372e32352c32342c302e3635353431363636372c332c322c32322c33342e35353335313035362c726f7574696e650d0a616765335f312c332c6d61726b65642c31382e38362c332e3732322c31392e3330392c32342c302e3636303833333333332c312c332c32332c33342e31323834313034352c726f7574696e650d0a616765335f312c332c6d61726b65642c31382e38362c332e3732322c31392e3330392c32342c302e3636303833333333332c322c332c32332c34342e33313832383937382c726f7574696e650d0a616765335f312c332c6d61726b65642c31382e38362c332e3732322c31392e3330392c32342c302e3636303833333333332c332c332c32332c33342e36383936353232362c726f7574696e650d0a616765335f312c312c6e6f6e652c31372e37382c332e3430372c31372e3134312c32342c302e3631353833333333332c312c342c32342c35332e32323538333534362c726f7574696e650d0a616765335f312c312c6e6f6e652c31372e37382c332e3430372c31372e3134312c32342c302e3631353833333333332c322c342c32342c33322e35393738303235332c726f7574696e650d0a616765335f312c312c6e6f6e652c31372e37382c332e3430372c31372e3134312c32342c302e3631353833333333332c332c342c32342c35312e39343732383532342c726f7574696e650d0a616765335f312c312c6e6f6e652c31392e31362c332e3735322c32312e3132352c32342c302e3637333333333333332c312c352c32352c34302e30393533383734372c726f7574696e650d0a616765335f312c312c6e6f6e652c31392e31362c332e3735322c32312e3132352c32342c302e3637333333333333332c322c352c32352c34382e37393237363836352c726f7574696e650d0a616765335f312c312c6e6f6e652c31392e31362c332e3735322c32312e3132352c32342c302e3637333333333333332c332c352c32352c32362e32333430383638322c726f7574696e650d0a616765315f312c312c6d61726b65642c32312e37332c342e3138342c32362e3331312c32372c302e3639333730333730342c312c312c32362c34362e373134343432352c726f7574696e650d0a616765315f312c312c6d61726b65642c32312e37332c342e3138342c32362e3331312c32372c302e3639333730333730342c322c312c32362c34342e39343531313331312c726f7574696e650d0a616765315f312c312c6d61726b65642c32312e37332c342e3138342c32362e3331312c32372c302e3639333730333730342c332c312c32362c33352e37353434333637342c726f7574696e650d0a616765315f312c312c6d61726b65642c32302e34362c342e3434362c32372e3231372c32372c302e3634363636363636372c312c322c32372c36312e37333839343536332c726f7574696e650d0a616765315f312c312c6d61726b65642c32302e34362c342e3434362c32372e3231372c32372c302e3634363636363636372c322c322c32372c37392e38313238323937342c726f7574696e650d0a616765315f312c312c6d61726b65642c32302e34362c342e3434362c32372e3231372c32372c302e3634363636363636372c332c322c32372c36372e37363034393232352c726f7574696e650d0a616765315f312c332c6e6f6e652c32312e39372c342e3338382c32332e3230352c32372c302e3730323539323539332c312c332c32382c34332e33363332393430382c726f7574696e650d0a616765315f312c332c6e6f6e652c32312e39372c342e3338382c32332e3230352c32372c302e3730323539323539332c322c332c32382c33372e35373635353533362c726f7574696e650d0a616765315f312c332c6e6f6e652c32312e39372c342e3338382c32332e3230352c32372c302e3730323539323539332c332c332c32382c33362e37323235373730352c726f7574696e650d0a616765315f312c312c6d61726b65642c31392e35312c342e3230352c31382e3836332c32372c302e3631313438313438312c312c342c32392c35342e31313234363432342c726f7574696e650d0a616765315f312c312c6d61726b65642c31392e35312c342e3230352c31382e3836332c32372c302e3631313438313438312c322c342c32392c34392e30303131313937342c726f7574696e650d0a616765315f312c312c6d61726b65642c31392e35312c342e3230352c31382e3836332c32372c302e3631313438313438312c332c342c32392c36302e37303138373636382c726f7574696e650d0a616765335f312c332c6d61726b65642c32302e36342c342e3435372c32302e3131332c32372c302e3635333333333333332c312c312c33302c36332e35333132323134312c726f7574696e650d0a616765335f312c332c6d61726b65642c32302e36342c342e3435372c32302e3131332c32372c302e3635333333333333332c322c312c33302c33322e32333339393932322c726f7574696e650d0a616765335f312c332c6d61726b65642c32302e36342c342e3435372c32302e3131332c32372c302e3635333333333333332c332c312c33302c33382e323632333034392c726f7574696e650d0a616765335f312c312c6e6f6e652c32342e31352c342e3437362c33312e36332c32372c302e3738333333333333332c312c322c33312c39342e303235373035392c726f7574696e650d0a616765335f312c312c6e6f6e652c32342e31352c342e3437362c33312e36332c32372c302e3738333333333333332c322c322c33312c3130332e323838393731342c726f7574696e650d0a616765335f312c312c6e6f6e652c32342e31352c342e3437362c33312e36332c32372c302e3738333333333333332c332c322c33312c35312e343130313138332c726f7574696e650d0a616765335f312c312c6e6f6e652c32332e312c352e32392c33322e3433372c32372c302e3734343434343434342c312c332c33322c34342e343232393637392c726f7574696e650d0a616765335f312c312c6e6f6e652c32332e312c352e32392c33322e3433372c32372c302e3734343434343434342c322c332c33322c37352e393335313631332c726f7574696e650d0a616765335f312c312c6e6f6e652c32332e312c352e32392c33322e3433372c32372c302e3734343434343434342c332c332c33322c34372e31303038333033362c726f7574696e650d0a616765335f312c312c6e6f6e652c32312e31372c342e3330322c32352e3332342c32372c302e3637323936323936332c312c342c33332c36332e30303936353437322c726f7574696e650d0a616765335f312c312c6e6f6e652c32312e31372c342e3330322c32352e3332342c32372c302e3637323936323936332c322c342c33332c35342e32363634343733392c726f7574696e650d0a616765335f312c312c6e6f6e652c32312e31372c342e3330322c32352e3332342c32372c302e3637323936323936332c332c342c33332c35392e35313035393033322c726f7574696e650d0a616765315f322c312c6d61726b65642c31392e362c332e3833332c31382e3430322c32372c302e3631343831343831352c312c312c33342c3132372e323830393833322c726f7574696e650d0a616765315f322c312c6d61726b65642c31392e362c332e3833332c31382e3430322c32372c302e3631343831343831352c322c312c33342c37372e31363333383130332c726f7574696e650d0a616765315f322c312c6d61726b65642c31392e362c332e3833332c31382e3430322c32372c302e3631343831343831352c332c312c33342c34372e31373436323132322c726f7574696e650d0a616765315f322c332c6e6f6e652c32302e312c342e30322c32332e3933312c32372c302e3633333333333333332c312c322c33352c39322e36383538343235312c726f7574696e650d0a616765315f322c332c6e6f6e652c32302e312c342e30322c32332e3933312c32372c302e3633333333333333332c322c322c33352c38382e32383931383539372c726f7574696e650d0a616765315f322c332c6e6f6e652c32302e312c342e30322c32332e3933312c32372c302e3633333333333333332c332c322c33352c38382e30363433303032322c726f7574696e650d0a616765315f322c312c6d61726b65642c31342e352c332e3139372c31332e3538352c32372c302e3432353932353932362c312c332c33362c33372e33333537363538372c726f7574696e650d0a616765315f322c312c6d61726b65642c31342e352c332e3139372c31332e3538352c32372c302e3432353932353932362c322c332c33362c33312e363336373031392c726f7574696e650d0a616765315f322c312c6d61726b65642c31342e352c332e3139372c31332e3538352c32372c302e3432353932353932362c332c332c33362c32362e35363633353833332c726f7574696e650d0a616765315f322c332c6e6f6e652c32302e32392c342e3337312c32332e3038322c32372c302e36343033373033372c312c342c33372c34352e30313536373136342c726f7574696e650d0a616765315f322c332c6e6f6e652c32302e32392c342e3337312c32332e3038322c32372c302e36343033373033372c322c342c33372c34312e32313831363132342c726f7574696e650d0a616765315f322c332c6e6f6e652c32302e32392c342e3337312c32332e3038322c32372c302e36343033373033372c332c342c33372c34342e34343332303539392c726f7574696e650d0a616765335f322c312c6e6f6e652c31382e32392c332e3539352c31352e3930372c32372c302e3536363239363239362c312c312c33382c33392e35303038343130352c726f7574696e650d0a616765335f322c312c6e6f6e652c31382e32392c332e3539352c31352e3930372c32372c302e3536363239363239362c322c312c33382c34312e313833333439372c726f7574696e650d0a616765335f322c312c6e6f6e652c31382e32392c332e3539352c31352e3930372c32372c302e3536363239363239362c332c312c33382c34332e37393535363738332c726f7574696e650d0a616765335f322c312c6e6f6e652c31392e36362c332e3837362c31392e3235312c32372c302e3631373033373033372c312c332c34302c34392e37313434352c726f7574696e650d0a616765335f322c312c6e6f6e652c31392e36362c332e3837362c31392e3235312c32372c302e3631373033373033372c322c332c34302c35352e3333373635312c726f7574696e650d0a616765335f322c312c6e6f6e652c31392e36362c332e3837362c31392e3235312c32372c302e3631373033373033372c332c332c34302c35362e30373533373533362c726f7574696e650d0a616765335f322c312c6e6f6e652c31392e31382c342e3032322c31382e3335342c32372c302e3539393235393235392c312c342c34312c38302e36353834323536392c726f7574696e650d0a616765335f322c312c6e6f6e652c31392e31382c342e3032322c31382e3335342c32372c302e3539393235393235392c322c342c34312c38322e34343631363438382c726f7574696e650d0a616765335f322c312c6e6f6e652c31392e31382c342e3032322c31382e3335342c32372c302e3539393235393235392c332c342c34312c39312e35363631303038342c726f7574696e650d0a616765335f322c332c6d61726b65642c31362e34362c332e3435362c31342e3037372c32372c302e3439383531383531392c312c352c34322c34342e34373232333633312c726f7574696e650d0a616765335f322c332c6d61726b65642c31362e34362c332e3435362c31342e3037372c32372c302e3439383531383531392c322c352c34322c32342e39313135323332332c726f7574696e650d0a616765335f322c332c6d61726b65642c31362e34362c332e3435362c31342e3037372c32372c302e3439383531383531392c332c352c34322c36302e36393437323534352c726f7574696e650d0a616765315f312c312c6d61726b65642c31372e37362c332e3738352c31352e3438382c33302c302e3439322c312c312c34332c33322e38363733363738342c726f7574696e650d0a616765315f312c312c6d61726b65642c31372e37362c332e3738352c31352e3438382c33302c302e3439322c322c312c34332c35322e32323539383131332c726f7574696e650d0a616765315f312c312c6d61726b65642c31372e37362c332e3738352c31352e3438382c33302c302e3439322c332c312c34332c36342e36353638353339352c726f7574696e650d0a616765315f312c312c6d61726b65642c31362e39372c332e3630382c31372e3730392c33302c302e3436353636363636372c312c322c34342c34362e37323730373234332c726f7574696e650d0a616765315f312c312c6d61726b65642c31362e39372c332e3630382c31372e3730392c33302c302e3436353636363636372c322c322c34342c35302e34373434343137332c726f7574696e650d0a616765315f312c312c6d61726b65642c31362e39372c332e3630382c31372e3730392c33302c302e3436353636363636372c332c322c34342c34302e37303230353538382c726f7574696e650d0a616765315f312c312c6d61726b65642c32332e31392c342e3630362c32372e3639382c33302c302e3637332c312c332c34352c34372e38373133373535322c726f7574696e650d0a616765315f312c312c6d61726b65642c32332e31392c342e3630362c32372e3639382c33302c302e3637332c322c332c34352c34392e34393632323834392c726f7574696e650d0a616765315f312c312c6d61726b65642c32332e31392c342e3630362c32372e3639382c33302c302e3637332c332c332c34352c36302e38313130333530332c726f7574696e650d0a616765315f312c312c6d61726b65642c32302e31342c332e3639332c32302e39332c33302c302e3537313333333333332c312c342c34362c35372e39303531373431372c726f7574696e650d0a616765315f312c312c6d61726b65642c32302e31342c332e3639332c32302e39332c33302c302e3537313333333333332c322c342c34362c36352e34373034353033382c726f7574696e650d0a616765315f312c312c6d61726b65642c32302e31342c332e3639332c32302e39332c33302c302e3537313333333333332c332c342c34362c36312e37393036303235372c726f7574696e650d0a616765315f312c312c6d61726b65642c32322e34382c342e3338392c32352e3231312c33302c302e3634393333333333332c312c352c34372c33382e37333031333639362c726f7574696e650d0a616765315f312c312c6d61726b65642c32322e34382c342e3338392c32352e3231312c33302c302e3634393333333333332c322c352c34372c35312e31353339323931312c726f7574696e650d0a616765315f312c312c6d61726b65642c32322e34382c342e3338392c32352e3231312c33302c302e3634393333333333332c332c352c34372c34392e32313631313935332c726f7574696e650d0a616765335f312c312c6e6f6e652c32332e32372c342e3836382c32382e3937352c33302c302e3637353636363636372c312c312c34382c38342e36343832383334352c726f7574696e650d0a616765335f312c312c6e6f6e652c32332e32372c342e3836382c32382e3937352c33302c302e3637353636363636372c322c312c34382c36392e34373033373330362c726f7574696e650d0a616765335f312c312c6e6f6e652c32332e32372c342e3836382c32382e3937352c33302c302e3637353636363636372c332c312c34382c34382e32303233382c726f7574696e650d0a616765335f312c332c6d61726b65642c32332e33342c342e3530372c32382e3833372c33302c302e3637382c312c322c34392c35372e34393734343439322c726f7574696e650d0a616765335f312c332c6d61726b65642c32332e33342c342e3530372c32382e3833372c33302c302e3637382c322c322c34392c35342e32333436333930362c726f7574696e650d0a616765335f312c332c6d61726b65642c32332e33342c342e3530372c32382e3833372c33302c302e3637382c332c322c34392c33322e33303939303030332c726f7574696e650d0a616765335f312c332c6d61726b65642c32312e38332c342e32312c32382e37312c33302c302e3632373636363636372c312c332c35302c35322e31323638363435322c726f7574696e650d0a616765335f312c332c6d61726b65642c32312e38332c342e32312c32382e37312c33302c302e3632373636363636372c322c332c35302c35332e383130333037352c726f7574696e650d0a616765335f312c332c6d61726b65642c32312e38332c342e32312c32382e37312c33302c302e3632373636363636372c332c332c35302c35302e38313932383837312c726f7574696e650d0a616765335f312c312c6e6f6e652c32332e37322c342e3735322c33302e3136382c33302c302e3639303636363636372c312c342c35312c35312e36393730373635382c726f7574696e650d0a616765335f312c312c6e6f6e652c32332e37322c342e3735322c33302e3136382c33302c302e3639303636363636372c322c342c35312c35352e36393431373138352c726f7574696e650d0a616765335f312c312c6e6f6e652c32332e37322c342e3735322c33302e3136382c33302c302e3639303636363636372c332c342c35312c34362e33323938393438322c726f7574696e650d0a616765335f312c312c6e6f6e652c32312e36372c332e3933312c32332e3039312c33302c302e3632323333333333332c312c352c35322c34342e39383439303630312c726f7574696e650d0a616765335f312c312c6e6f6e652c32312e36372c332e3933312c32332e3039312c33302c302e3632323333333333332c322c352c35322c35342e32363932333632392c726f7574696e650d0a616765335f312c312c6e6f6e652c32312e36372c332e3933312c32332e3039312c33302c302e3632323333333333332c332c352c35322c35372e39303031363738382c726f7574696e650d0a616765315f322c332c6e6f6e652c31382e37342c332e3730332c31372e3835382c33302c302e3532343636363636372c312c312c35332c32392e37303334383635342c726f7574696e650d0a616765315f322c332c6e6f6e652c31382e37342c332e3730332c31372e3835382c33302c302e3532343636363636372c322c312c35332c33322e30323733313539342c726f7574696e650d0a616765315f322c332c6e6f6e652c31382e37342c332e3730332c31372e3835382c33302c302e3532343636363636372c332c312c35332c33372e35353338313930362c726f7574696e650d0a616765315f322c332c6e6f6e652c31362e35332c332e3538322c31332e3931332c33302c302e3435312c312c322c35342c34372e30393730303930352c726f7574696e650d0a616765315f322c332c6e6f6e652c31362e35332c332e3538322c31332e3931332c33302c302e3435312c322c322c35342c34392e34353732313036352c726f7574696e650d0a616765315f322c332c6e6f6e652c31362e35332c332e3538322c31332e3931332c33302c302e3435312c332c322c35342c34322e333632333435392c726f7574696e650d0a616765315f322c312c6d61726b65642c32332e37342c342e3838372c32392e3030352c33302c302e3639313333333333332c312c332c35352c37302e373834363434332c726f7574696e650d0a616765315f322c312c6d61726b65642c32332e37342c342e3838372c32392e3030352c33302c302e3639313333333333332c322c332c35352c35382e34353437303230392c726f7574696e650d0a616765315f322c312c6d61726b65642c32332e37342c342e3838372c32392e3030352c33302c302e3639313333333333332c332c332c35352c34392e33393433383334332c726f7574696e650d0a616765315f322c312c6d61726b65642c31382e33352c342e3232362c31392e3838372c33302c302e3531313636363636372c312c342c35362c34372e33303534383236362c726f7574696e650d0a616765315f322c312c6d61726b65642c31382e33352c342e3232362c31392e3838372c33302c302e3531313636363636372c322c342c35362c34392e31373934373334372c726f7574696e650d0a616765315f322c312c6d61726b65642c31382e33352c342e3232362c31392e3838372c33302c302e3531313636363636372c332c342c35362c36312e37323439303735392c726f7574696e650d0a616765335f322c312c6e6f6e652c31392e32382c342e3131342c32312e3036332c33302c302e3534323636363636372c312c312c35372c38362e37393838343831362c726f7574696e650d0a616765335f322c312c6e6f6e652c31392e32382c342e3131342c32312e3036332c33302c302e3534323636363636372c322c312c35372c38362e393131323632312c726f7574696e650d0a616765335f322c312c6e6f6e652c31392e32382c342e3131342c32312e3036332c33302c302e3534323636363636372c332c312c35372c37322e393533373238372c726f7574696e650d0a616765335f322c312c6e6f6e652c32302e34312c342e3234312c31372e39342c33302c302e3538303333333333332c312c322c35382c35342e37303232353739362c726f7574696e650d0a616765335f322c312c6e6f6e652c32302e34312c342e3234312c31372e39342c33302c302e3538303333333333332c322c322c35382c35392e31373636323931372c726f7574696e650d0a616765335f322c312c6e6f6e652c32302e34312c342e3234312c31372e39342c33302c302e3538303333333333332c332c322c35382c35352e31353339363431322c726f7574696e650d0a616765335f322c332c6d61726b65642c31382e31312c332e3936312c31382e3135322c33302c302e3530333636363636372c312c332c35392c34352e38383533343730392c726f7574696e650d0a616765335f322c332c6d61726b65642c31382e31312c332e3936312c31382e3135322c33302c302e3530333636363636372c322c332c35392c35312e30373234383837352c726f7574696e650d0a616765335f322c332c6d61726b65642c31382e31312c332e3936312c31382e3135322c33302c302e3530333636363636372c332c332c35392c35332e37313035323737392c726f7574696e650d0a616765315f312c312c6d61726b65642c32312e35312c342e3331352c32382e3732382c32302c302e393235352c312c322c312c3535372e353337353236322c62757273740d0a616765315f312c312c6d61726b65642c32312e35312c342e3331352c32382e3732382c32302c302e393235352c322c322c312c3439392e373037363033332c62757273740d0a616765315f312c312c6d61726b65642c32312e35312c342e3331352c32382e3732382c32302c302e393235352c332c322c312c3338392e353835313131372c62757273740d0a616765315f312c312c6d61726b65642c32322e36392c342e3531372c32342e3831312c32302c302e393834352c312c332c322c3630302e333834333737322c62757273740d0a616765315f312c312c6d61726b65642c32322e36392c342e3531372c32342e3831312c32302c302e393834352c322c332c322c3530372e3737393038322c62757273740d0a616765315f312c332c6e6f6e652c31372e31332c332e3430342c31372e3232322c32302c302e373036352c312c342c332c3339322e373134383731342c62757273740d0a616765315f312c332c6e6f6e652c31372e31332c332e3430342c31372e3232322c32302c302e373036352c322c342c332c3537302e323731353835372c62757273740d0a616765315f312c332c6e6f6e652c31372e31332c332e3430342c31372e3232322c32302c302e373036352c332c342c332c3433342e373336303936352c62757273740d0a616765335f312c312c6e6f6e652c32352e32352c352e3736382c34332e3232322c32302c312e313132352c312c312c342c3437382e393639393035322c62757273740d0a616765335f312c312c6e6f6e652c32352e32352c352e3736382c34332e3232322c32302c312e313132352c322c312c342c3231382e373233363731342c62757273740d0a616765335f312c312c6e6f6e652c32352e32352c352e3736382c34332e3232322c32302c312e313132352c332c312c342c3633302e343732373434342c62757273740d0a616765335f312c312c6e6f6e652c32332e30372c342e3831362c33312e3136372c32302c312e303033352c312c322c352c3730352e363539313939352c62757273740d0a616765335f312c312c6e6f6e652c32332e30372c342e3831362c33312e3136372c32302c312e303033352c322c322c352c3633382e303232313933332c62757273740d0a616765335f312c312c6e6f6e652c32332e30372c342e3831362c33312e3136372c32302c312e303033352c332c322c352c3531392e303535353330392c62757273740d0a616765335f312c332c6d61726b65642c31382e34342c332e36322c31372e3336332c32302c302e3737322c312c332c362c3236322e303834363032362c62757273740d0a616765335f312c332c6d61726b65642c31382e34342c332e36322c31372e3336332c32302c302e3737322c332c332c362c3337342e303636373931332c62757273740d0a616765335f312c312c6e6f6e652c31352e39352c332e3436342c31342e3633332c32302c302e363437352c312c342c372c3430362e343534393333352c62757273740d0a616765335f312c312c6e6f6e652c31352e39352c332e3436342c31342e3633332c32302c302e363437352c322c342c372c3336392e3535303935392c62757273740d0a616765315f322c312c6d61726b65642c32342e37362c352e3533342c34302e3333362c32302c312e3038382c312c312c382c3335322e383135333431322c62757273740d0a616765315f322c312c6d61726b65642c32342e37362c352e3533342c34302e3333362c32302c312e3038382c322c312c382c3233302e363432373337352c62757273740d0a616765315f322c312c6d61726b65642c32342e37362c352e3533342c34302e3333362c32302c312e3038382c332c312c382c3239322e373539343032312c62757273740d0a616765315f322c312c6d61726b65642c32312e36362c352e3136382c32392e3539382c32302c302e3933332c312c322c392c3332382e393132363033362c62757273740d0a616765315f322c312c6d61726b65642c32312e36362c352e3136382c32392e3539382c32302c302e3933332c322c322c392c3333332e313530303932392c62757273740d0a616765315f322c312c6d61726b65642c32312e36362c352e3136382c32392e3539382c32302c302e3933332c332c322c392c3232382e353832303336362c62757273740d0a616765315f322c312c6d61726b65642c31342e34392c322e3930352c31302e3935342c32302c302e353734352c312c332c31302c3138342e34393937382c62757273740d0a616765315f322c312c6d61726b65642c31342e34392c322e3930352c31302e3935342c32302c302e353734352c322c332c31302c3335312e353831333137362c62757273740d0a616765315f322c312c6d61726b65642c31342e34392c322e3930352c31302e3935342c32302c302e353734352c332c332c31302c3434302e363930383634352c62757273740d0a616765315f322c312c6d61726b65642c31352e32312c332e3036382c31332e3330342c32302c302e363130352c312c342c31312c3435372e313439363638312c62757273740d0a616765315f322c312c6d61726b65642c31352e32312c332e3036382c31332e3330342c32302c302e363130352c322c342c31312c3332322e373730363332312c62757273740d0a616765315f322c312c6d61726b65642c31352e32312c332e3036382c31332e3330342c32302c302e363130352c332c342c31312c3338322e383233343033372c62757273740d0a616765335f322c312c6e6f6e652c32312e32392c342e3330342c32362e3937372c32302c302e393134352c312c312c31322c3332362e393638393733352c62757273740d0a616765335f322c312c6e6f6e652c32312e32392c342e3330342c32362e3937372c32302c302e393134352c322c312c31322c3239392e393130343030352c62757273740d0a616765335f322c312c6e6f6e652c32312e32392c342e3330342c32362e3937372c32302c302e393134352c332c312c31322c3438372e393837383937312c62757273740d0a616765335f322c312c6e6f6e652c32302e37332c342e3337342c32342e3233392c32302c302e383836352c312c322c31332c3535382e333730323037322c62757273740d0a616765335f322c312c6e6f6e652c32302e37332c342e3337342c32342e3233392c32302c302e383836352c322c322c31332c3438362e333730343935332c62757273740d0a616765335f322c312c6e6f6e652c32302e37332c342e3337342c32342e3233392c32302c302e383836352c332c322c31332c3435312e313233373738312c62757273740d0a616765335f322c312c6e6f6e652c31372e39332c332e3137372c31362e3937362c32302c302e373436352c312c332c31342c3338302e313836333836392c62757273740d0a616765335f322c312c6e6f6e652c31372e39332c332e3137372c31362e3937362c32302c302e373436352c322c332c31342c3333332e373634313938352c62757273740d0a616765335f322c332c6d61726b65642c31372e332c332e35342c31342e32332c32302c302e3731352c312c342c31352c3536352e3033303938392c62757273740d0a616765335f322c332c6d61726b65642c31372e332c332e35342c31342e32332c32302c302e3731352c322c342c31352c3237312e343233323639372c62757273740d0a616765335f322c332c6d61726b65642c31372e332c332e35342c31342e32332c32302c302e3731352c332c342c31352c3237382e363034303331352c62757273740d0a616765315f312c312c6d61726b65642c32332e33362c342e3635382c33322e3734362c32342c302e3834383333333333332c312c312c31372c3432382e363239303333332c62757273740d0a616765315f312c312c6d61726b65642c32332e33362c342e3635382c33322e3734362c32342c302e3834383333333333332c322c312c31372c3439312e333934383033342c62757273740d0a616765315f312c312c6d61726b65642c32332e33362c342e3635382c33322e3734362c32342c302e3834383333333333332c332c312c31372c3337362e373834353538342c62757273740d0a616765315f312c312c6d61726b65642c31392e32352c342e34322c31382e3438332c32342c302e3637373038333333332c312c322c31382c3435362e363836333438332c62757273740d0a616765315f312c312c6d61726b65642c31392e32352c342e34322c31382e3438332c32342c302e3637373038333333332c322c322c31382c3537382e343830383337352c62757273740d0a616765315f312c312c6d61726b65642c31392e32352c342e34322c31382e3438332c32342c302e3637373038333333332c332c322c31382c3431382e333637303631382c62757273740d0a616765315f312c312c6d61726b65642c31392e37312c342e3031322c32312e3335312c32342c302e36393632352c312c332c31392c3531382e393336343237342c62757273740d0a616765315f312c312c6d61726b65642c31392e37312c342e3031322c32312e3335312c32342c302e36393632352c322c332c31392c3439302e333533353431362c62757273740d0a616765315f312c312c6d61726b65642c31392e37312c342e3031322c32312e3335312c32342c302e36393632352c332c332c31392c3335302e3630323830392c62757273740d0a616765315f312c332c6e6f6e652c32312e31322c342e3339332c32352e3339312c32342c302e3735352c312c342c32302c3431382e383537323530372c62757273740d0a616765315f312c332c6e6f6e652c32312e31322c342e3339332c32352e3339312c32342c302e3735352c322c342c32302c3332342e363836353332312c62757273740d0a616765315f312c332c6e6f6e652c32312e31322c342e3339332c32352e3339312c32342c302e3735352c332c342c32302c3337332e3439333933382c62757273740d0a616765335f312c312c6e6f6e652c31382e32372c332e3638322c31372e372c32342c302e36333632352c312c312c32312c3432332e393134333239382c62757273740d0a616765335f312c312c6e6f6e652c31382e32372c332e3638322c31372e372c32342c302e36333632352c322c312c32312c3537352e353536313132342c62757273740d0a616765335f312c312c6e6f6e652c31382e32372c332e3638322c31372e372c32342c302e36333632352c332c312c32312c3433382e373031313032372c62757273740d0a616765335f312c332c6d61726b65642c31382e37332c332e3137392c31372e32352c32342c302e3635353431363636372c312c322c32322c3331312e383331333337342c62757273740d0a616765335f312c332c6d61726b65642c31382e37332c332e3137392c31372e32352c32342c302e3635353431363636372c322c322c32322c3437382e333039343432322c62757273740d0a616765335f312c332c6d61726b65642c31382e37332c332e3137392c31372e32352c32342c302e3635353431363636372c332c322c32322c3534332e343838373334362c62757273740d0a616765335f312c332c6d61726b65642c31382e38362c332e3732322c31392e3330392c32342c302e3636303833333333332c312c332c32332c3332332e383338333230342c62757273740d0a616765335f312c332c6d61726b65642c31382e38362c332e3732322c31392e3330392c32342c302e3636303833333333332c322c332c32332c3436382e363231383233322c62757273740d0a616765335f312c332c6d61726b65642c31382e38362c332e3732322c31392e3330392c32342c302e3636303833333333332c332c332c32332c3234392e343434383237362c62757273740d0a616765335f312c312c6e6f6e652c31372e37382c332e3430372c31372e3134312c32342c302e3631353833333333332c312c342c32342c3437392e323939323136352c62757273740d0a616765335f312c312c6e6f6e652c31372e37382c332e3430372c31372e3134312c32342c302e3631353833333333332c322c342c32342c3234352e303033343633352c62757273740d0a616765335f312c312c6e6f6e652c31372e37382c332e3430372c31372e3134312c32342c302e3631353833333333332c332c342c32342c3438332e35373733392c62757273740d0a616765335f312c312c6e6f6e652c31392e31362c332e3735322c32312e3132352c32342c302e3637333333333333332c312c352c32352c3237372e383136383730342c62757273740d0a616765335f312c312c6e6f6e652c31392e31362c332e3735322c32312e3132352c32342c302e3637333333333333332c322c352c32352c3437372e323431303236362c62757273740d0a616765335f312c312c6e6f6e652c31392e31362c332e3735322c32312e3132352c32342c302e3637333333333333332c332c352c32352c3335332e323330343034392c62757273740d0a616765315f312c312c6d61726b65642c32312e37332c342e3138342c32362e3331312c32372c302e3639333730333730342c312c312c32362c3435332e363833393437312c62757273740d0a616765315f312c312c6d61726b65642c32312e37332c342e3138342c32362e3331312c32372c302e3639333730333730342c332c312c32362c3239372e363634353533382c62757273740d0a616765315f312c312c6d61726b65642c32302e34362c342e3434362c32372e3231372c32372c302e3634363636363636372c312c322c32372c3638382e363236333632372c62757273740d0a616765315f312c312c6d61726b65642c32302e34362c342e3434362c32372e3231372c32372c302e3634363636363636372c322c322c32372c3337382e383332363035362c62757273740d0a616765315f312c312c6d61726b65642c32302e34362c342e3434362c32372e3231372c32372c302e3634363636363636372c332c322c32372c3532392e3531393732312c62757273740d0a616765315f312c332c6e6f6e652c32312e39372c342e3338382c32332e3230352c32372c302e3730323539323539332c312c332c32382c3530392e333434353838342c62757273740d0a616765315f312c332c6e6f6e652c32312e39372c342e3338382c32332e3230352c32372c302e3730323539323539332c322c332c32382c3437312e3134363039312c62757273740d0a616765315f312c332c6e6f6e652c32312e39372c342e3338382c32332e3230352c32372c302e3730323539323539332c332c332c32382c3633332e393339303436382c62757273740d0a616765315f312c312c6d61726b65642c31392e35312c342e3230352c31382e3836332c32372c302e3631313438313438312c312c342c32392c3530352e343730323237362c62757273740d0a616765315f312c312c6d61726b65642c31392e35312c342e3230352c31382e3836332c32372c302e3631313438313438312c322c342c32392c3530322e313336373230312c62757273740d0a616765315f312c312c6d61726b65642c31392e35312c342e3230352c31382e3836332c32372c302e3631313438313438312c332c342c32392c3233372e393931393433322c62757273740d0a616765335f312c332c6d61726b65642c32302e36342c342e3435372c32302e3131332c32372c302e3635333333333333332c312c312c33302c3331322e363333373838392c62757273740d0a616765335f312c332c6d61726b65642c32302e36342c342e3435372c32302e3131332c32372c302e3635333333333333332c322c312c33302c3238372e363630313834372c62757273740d0a616765335f312c332c6d61726b65642c32302e36342c342e3435372c32302e3131332c32372c302e3635333333333333332c332c312c33302c3231372e333030373532372c62757273740d0a616765335f312c312c6e6f6e652c32342e31352c342e3437362c33312e36332c32372c302e3738333333333333332c312c322c33312c3234362e323235353631342c62757273740d0a616765335f312c312c6e6f6e652c32342e31352c342e3437362c33312e36332c32372c302e3738333333333333332c322c322c33312c3434312e3534363936332c62757273740d0a616765335f312c312c6e6f6e652c32342e31352c342e3437362c33312e36332c32372c302e3738333333333333332c332c322c33312c3438322e373432313838382c62757273740d0a616765335f312c312c6e6f6e652c32332e312c352e32392c33322e3433372c32372c302e3734343434343434342c312c332c33322c3231312e373035393136342c62757273740d0a616765335f312c312c6e6f6e652c32332e312c352e32392c33322e3433372c32372c302e3734343434343434342c322c332c33322c3531392e393835343036312c62757273740d0a616765335f312c312c6e6f6e652c32332e312c352e32392c33322e3433372c32372c302e3734343434343434342c332c332c33322c3336322e303337333430372c62757273740d0a616765335f312c312c6e6f6e652c32312e31372c342e3330322c32352e3332342c32372c302e3637323936323936332c312c342c33332c3333362e353933373234332c62757273740d0a616765335f312c312c6e6f6e652c32312e31372c342e3330322c32352e3332342c32372c302e3637323936323936332c322c342c33332c3137322e353236393134392c62757273740d0a616765335f312c312c6e6f6e652c32312e31372c342e3330322c32352e3332342c32372c302e3637323936323936332c332c342c33332c3332382e393233343031382c62757273740d0a616765315f322c312c6d61726b65642c31392e362c332e3833332c31382e3430322c32372c302e3631343831343831352c312c312c33342c3234322e353236343532332c62757273740d0a616765315f322c312c6d61726b65642c31392e362c332e3833332c31382e3430322c32372c302e3631343831343831352c322c312c33342c3439352e343633393038322c62757273740d0a616765315f322c312c6d61726b65642c31392e362c332e3833332c31382e3430322c32372c302e3631343831343831352c332c312c33342c3239382e353630363634382c62757273740d0a616765315f322c332c6e6f6e652c32302e312c342e30322c32332e3933312c32372c302e3633333333333333332c312c322c33352c3331362e303832343235382c62757273740d0a616765315f322c332c6e6f6e652c32302e312c342e30322c32332e3933312c32372c302e3633333333333333332c322c322c33352c3235322e373234363833372c62757273740d0a616765315f322c312c6d61726b65642c31342e352c332e3139372c31332e3538352c32372c302e3432353932353932362c312c332c33362c3232392e363431343631332c62757273740d0a616765315f322c312c6d61726b65642c31342e352c332e3139372c31332e3538352c32372c302e3432353932353932362c322c332c33362c3137302e353932373832342c62757273740d0a616765315f322c312c6d61726b65642c31342e352c332e3139372c31332e3538352c32372c302e3432353932353932362c332c332c33362c3137312e373034373138332c62757273740d0a616765315f322c332c6e6f6e652c32302e32392c342e3337312c32332e3038322c32372c302e36343033373033372c312c342c33372c3430332e313538323831352c62757273740d0a616765315f322c332c6e6f6e652c32302e32392c342e3337312c32332e3038322c32372c302e36343033373033372c322c342c33372c3434322e313533313331372c62757273740d0a616765315f322c332c6e6f6e652c32302e32392c342e3337312c32332e3038322c32372c302e36343033373033372c332c342c33372c3436312e313939363532382c62757273740d0a616765335f322c312c6e6f6e652c31382e32392c332e3539352c31352e3930372c32372c302e3536363239363239362c312c312c33382c3339322e323336313836342c62757273740d0a616765335f322c312c6e6f6e652c31382e32392c332e3539352c31352e3930372c32372c302e3536363239363239362c322c312c33382c3334362e313337363131362c62757273740d0a616765335f322c312c6e6f6e652c31392e36362c332e3837362c31392e3235312c32372c302e3631373033373033372c312c332c34302c3735352e313333373236392c62757273740d0a616765335f322c312c6e6f6e652c31392e36362c332e3837362c31392e3235312c32372c302e3631373033373033372c322c332c34302c3337362e333730313630372c62757273740d0a616765335f322c312c6e6f6e652c31392e36362c332e3837362c31392e3235312c32372c302e3631373033373033372c332c332c34302c3434322e383232373330372c62757273740d0a616765335f322c312c6e6f6e652c31392e31382c342e3032322c31382e3335342c32372c302e3539393235393235392c312c342c34312c3237322e343538383433382c62757273740d0a616765335f322c312c6e6f6e652c31392e31382c342e3032322c31382e3335342c32372c302e3539393235393235392c322c342c34312c3230362e3334303435352c62757273740d0a616765335f322c312c6e6f6e652c31392e31382c342e3032322c31382e3335342c32372c302e3539393235393235392c332c342c34312c3330332e3832303237362c62757273740d0a616765335f322c332c6d61726b65642c31362e34362c332e3435362c31342e3037372c32372c302e3439383531383531392c312c352c34322c3434312e393130323237342c62757273740d0a616765335f322c332c6d61726b65642c31362e34362c332e3435362c31342e3037372c32372c302e3439383531383531392c322c352c34322c3233392e353033373230322c62757273740d0a616765335f322c332c6d61726b65642c31362e34362c332e3435362c31342e3037372c32372c302e3439383531383531392c332c352c34322c3233362e313039363232352c62757273740d0a616765315f312c312c6d61726b65642c31372e37362c332e3738352c31352e3438382c33302c302e3439322c312c312c34332c3433342e3830393535372c62757273740d0a616765315f312c312c6d61726b65642c31372e37362c332e3738352c31352e3438382c33302c302e3439322c322c312c34332c3137362e393039323539352c62757273740d0a616765315f312c312c6d61726b65642c31372e37362c332e3738352c31352e3438382c33302c302e3439322c332c312c34332c3334372e393134303537382c62757273740d0a616765315f312c312c6d61726b65642c31362e39372c332e3630382c31372e3730392c33302c302e3436353636363636372c312c322c34342c39302e31353233333433342c62757273740d0a616765315f312c312c6d61726b65642c31362e39372c332e3630382c31372e3730392c33302c302e3436353636363636372c322c322c34342c3135322e333037303736362c62757273740d0a616765315f312c312c6d61726b65642c31362e39372c332e3630382c31372e3730392c33302c302e3436353636363636372c332c322c34342c3439322e373437333037382c62757273740d0a616765315f312c312c6d61726b65642c32332e31392c342e3630362c32372e3639382c33302c302e3637332c312c332c34352c3533352e353734353730312c62757273740d0a616765315f312c312c6d61726b65642c32332e31392c342e3630362c32372e3639382c33302c302e3637332c322c332c34352c3333312e373934313332372c62757273740d0a616765315f312c312c6d61726b65642c32332e31392c342e3630362c32372e3639382c33302c302e3637332c332c332c34352c3230362e303338303133362c62757273740d0a616765315f312c312c6d61726b65642c32302e31342c332e3639332c32302e39332c33302c302e3537313333333333332c312c342c34362c3333312e383935313232382c62757273740d0a616765315f312c312c6d61726b65642c32302e31342c332e3639332c32302e39332c33302c302e3537313333333333332c322c342c34362c3536302e343432393838332c62757273740d0a616765315f312c312c6d61726b65642c32302e31342c332e3639332c32302e39332c33302c302e3537313333333333332c332c342c34362c3236362e373132393037382c62757273740d0a616765315f312c312c6d61726b65642c32322e34382c342e3338392c32352e3231312c33302c302e3634393333333333332c322c352c34372c3439392e373930393333322c62757273740d0a616765335f312c312c6e6f6e652c32332e32372c342e3836382c32382e3937352c33302c302e3637353636363636372c312c312c34382c3139392e323735333630342c62757273740d0a616765335f312c312c6e6f6e652c32332e32372c342e3836382c32382e3937352c33302c302e3637353636363636372c322c312c34382c3334372e363132313330392c62757273740d0a616765335f312c312c6e6f6e652c32332e32372c342e3836382c32382e3937352c33302c302e3637353636363636372c332c312c34382c3333342e353530353032362c62757273740d0a616765335f312c332c6d61726b65642c32332e33342c342e3530372c32382e3833372c33302c302e3637382c312c322c34392c3335382e323932373331332c62757273740d0a616765335f312c332c6d61726b65642c32332e33342c342e3530372c32382e3833372c33302c302e3637382c322c322c34392c3235362e373830393733362c62757273740d0a616765335f312c332c6d61726b65642c32332e33342c342e3530372c32382e3833372c33302c302e3637382c332c322c34392c3138362e393838343835322c62757273740d0a616765335f312c332c6d61726b65642c32312e38332c342e32312c32382e37312c33302c302e3632373636363636372c312c332c35302c3339342e323937363337352c62757273740d0a616765335f312c332c6d61726b65642c32312e38332c342e32312c32382e37312c33302c302e3632373636363636372c322c332c35302c3430332e343330353637342c62757273740d0a616765335f312c312c6e6f6e652c32332e37322c342e3735322c33302e3136382c33302c302e3639303636363636372c312c342c35312c3337352e3536373838382c62757273740d0a616765335f312c312c6e6f6e652c32332e37322c342e3735322c33302e3136382c33302c302e3639303636363636372c322c342c35312c3333322e393136363932372c62757273740d0a616765335f312c312c6e6f6e652c32332e37322c342e3735322c33302e3136382c33302c302e3639303636363636372c332c342c35312c3431332e303439323330322c62757273740d0a616765335f312c312c6e6f6e652c32312e36372c332e3933312c32332e3039312c33302c302e3632323333333333332c312c352c35322c3431312e313236313238362c62757273740d0a616765335f312c312c6e6f6e652c32312e36372c332e3933312c32332e3039312c33302c302e3632323333333333332c322c352c35322c3331302e323530313239312c62757273740d0a616765335f312c312c6e6f6e652c32312e36372c332e3933312c32332e3039312c33302c302e3632323333333333332c332c352c35322c3436382e353333363735342c62757273740d0a616765315f322c332c6e6f6e652c31382e37342c332e3730332c31372e3835382c33302c302e3532343636363636372c312c312c35332c3232332e313734383431312c62757273740d0a616765315f322c332c6e6f6e652c31382e37342c332e3730332c31372e3835382c33302c302e3532343636363636372c322c312c35332c3339372e353138353934372c62757273740d0a616765315f322c332c6e6f6e652c31382e37342c332e3730332c31372e3835382c33302c302e3532343636363636372c332c312c35332c3234372e383333373439322c62757273740d0a616765315f322c332c6e6f6e652c31362e35332c332e3538322c31332e3931332c33302c302e3435312c312c322c35342c3335372e343839363833312c62757273740d0a616765315f322c332c6e6f6e652c31362e35332c332e3538322c31332e3931332c33302c302e3435312c322c322c35342c3231362e393330383433352c62757273740d0a616765315f322c332c6e6f6e652c31362e35332c332e3538322c31332e3931332c33302c302e3435312c332c322c35342c3338322e333339373137362c62757273740d0a616765315f322c312c6d61726b65642c32332e37342c342e3838372c32392e3030352c33302c302e3639313333333333332c312c332c35352c3331332e383134353739332c62757273740d0a616765315f322c312c6d61726b65642c32332e37342c342e3838372c32392e3030352c33302c302e3639313333333333332c322c332c35352c3530342e323035363730352c62757273740d0a616765315f322c312c6d61726b65642c32332e37342c342e3838372c32392e3030352c33302c302e3639313333333333332c332c332c35352c3235362e333339353433312c62757273740d0a616765315f322c312c6d61726b65642c31382e33352c342e3232362c31392e3838372c33302c302e3531313636363636372c312c342c35362c3436342e363235323230392c62757273740d0a616765315f322c312c6d61726b65642c31382e33352c342e3232362c31392e3838372c33302c302e3531313636363636372c322c342c35362c3434382e383739303635352c62757273740d0a616765315f322c312c6d61726b65642c31382e33352c342e3232362c31392e3838372c33302c302e3531313636363636372c332c342c35362c3237302e353534343132312c62757273740d0a616765335f322c312c6e6f6e652c31392e32382c342e3131342c32312e3036332c33302c302e3534323636363636372c312c312c35372c3335362e323736343339372c62757273740d0a616765335f322c312c6e6f6e652c31392e32382c342e3131342c32312e3036332c33302c302e3534323636363636372c322c312c35372c3334342e343332343736322c62757273740d0a616765335f322c312c6e6f6e652c31392e32382c342e3131342c32312e3036332c33302c302e3534323636363636372c332c312c35372c3435392e363632363434332c62757273740d0a616765335f322c312c6e6f6e652c32302e34312c342e3234312c31372e39342c33302c302e3538303333333333332c312c322c35382c3238352e393334373330312c62757273740d0a616765335f322c312c6e6f6e652c32302e34312c342e3234312c31372e39342c33302c302e3538303333333333332c322c322c35382c3236352e333939383839342c62757273740d0a616765335f322c312c6e6f6e652c32302e34312c342e3234312c31372e39342c33302c302e3538303333333333332c332c322c35382c3334382e383430363436312c62757273740d0a616765335f322c332c6d61726b65642c31382e31312c332e3936312c31382e3135322c33302c302e3530333636363636372c312c332c35392c3234382e333633373531312c62757273740d0a616765335f322c332c6d61726b65642c31382e31312c332e3936312c31382e3135322c33302c302e3530333636363636372c322c332c35392c3234352e323239323136342c62757273740d0a616765335f322c332c6d61726b65642c31382e31312c332e3936312c31382e3135322c33302c302e3530333636363636372c332c332c35392c3133372e303130323038372c62757273740d0a, 24478⟩

def pcs_c0 : Claim :=
  { column := none,
    filter := [],
    stat := .count,
    naTokens := [b "", b "NA"],
    scale := ((1 : Rat) / 1),
    reported := b "2000.5" }

def pcs_c1 : Claim :=
  { column := none,
    filter := [],
    stat := .count,
    naTokens := [b "", b "NA"],
    scale := ((1 : Rat) / 1),
    reported := b "1996.9" }

theorem pcs_batch : runAll pcs_src [pcs_c0, pcs_c1] =
    [.checked .inconsistent (.rat ((332 : Rat) / 1)) 332 0,
    .checked .inconsistent (.rat ((332 : Rat) / 1)) 332 0] := by decide +kernel

theorem pcs_claim_0 : run pcs_src pcs_c0 = .checked .inconsistent (.rat ((332 : Rat) / 1)) 332 0 :=
  run_of_runAll pcs_batch 0 rfl rfl
#print axioms pcs_claim_0

theorem pcs_claim_1 : run pcs_src pcs_c1 = .checked .inconsistent (.rat ((332 : Rat) / 1)) 332 0 :=
  run_of_runAll pcs_batch 1 rfl rfl
#print axioms pcs_claim_1

