import ClaimCheckAssurance.Authority

/-!
Prints `outward m f corM corD` (`ClaimCheckAssurance.Authority`) at every point of its finite input
domain: the five mathematical statuses × the 2^16 values of `Findings` × `corM` × `corD`, that is
5 × 2^18 = 1,310,720 points.  One line per status: its name, a space, then one character per point
(`U` unknown, `R` review, `C` confirmation, `D` discrepancy), point `i` at position `i`.  Bit `k` of
`i` is field `k` of `Findings` in declaration order (bit 0 `hasWindow` … bit 15 `sampleSizeOk`);
bit 16 is `corM`, bit 17 `corD`.  Evaluated by Lean from the definition the theorems are about, not
re-implemented; `check_conformance.py` (part E) compares every point with the Python policy.
Run: `LEAN_PATH=formal/.build lean --run conformance/ExportOutward.lean`.
-/

open PCS.ClaimCheck PCS.ClaimCheck.Assurance

def bit (i k : Nat) : Bool := (i >>> k) % 2 == 1

def findingsOf (i : Nat) : Findings :=
  { hasWindow := bit i 0, quoteOk := bit i 1, grounded := bit i 2, identOk := bit i 3, basicOk := bit i 4,
    boundedBound := bit i 5, noCompeting := bit i 6, lowRate := bit i 7, pinnedOk := bit i 8,
    notCount := bit i 9, boundedAll := bit i 10, noEligible := bit i 11, beyondRounding := bit i 12,
    dispersionNamed := bit i 13, inGrammar := bit i 14, sampleSizeOk := bit i 15 }

def code : PCS.ClaimCheck.Assurance.Verdict → Char
  | .unknown => 'U' | .review => 'R' | .confirmation => 'C' | .discrepancy => 'D'

def mathName : Math → String
  | .matchProved => "MATCH_PROVED" | .mismatchProved => "MISMATCH_PROVED"
  | .conditional => "CONDITIONAL_ON_CONVENTION" | .undefinedProved => "UNDEFINED_PROVED"
  | .notEstablished => "NOT_ESTABLISHED"

def line (m : Math) : String := Id.run do
  let mut s := mathName m ++ " "
  for i in [0:262144] do
    s := s.push (code (outward m (findingsOf i) (bit i 16) (bit i 17)))
  return s

def main : IO Unit := do
  for m in [Math.matchProved, .mismatchProved, .conditional, .undefinedProved, .notEstablished] do
    IO.println (line m)
