import ClaimCheckAssurance.Authority

/-!
Prints the Lean model's decision tables as JSON, for comparison with the Python implementation
(`check_conformance.py`).  Run by `conformance/run.sh`; evaluated by Lean, not hand-written.
-/

open PCS.ClaimCheck PCS.ClaimCheck.Assurance

def mathName : Math → String
  | .matchProved => "MATCH_PROVED" | .mismatchProved => "MISMATCH_PROVED"
  | .conditional => "CONDITIONAL_ON_CONVENTION" | .undefinedProved => "UNDEFINED_PROVED"
  | .notEstablished => "NOT_ESTABLISHED"

def verdictName : PCS.ClaimCheck.Assurance.Verdict → String
  | .unknown => "UNKNOWN" | .review => "REQUIRE_HUMAN_REVIEW"
  | .confirmation => "CONFIRMATION" | .discrepancy => "DISCREPANCY_FOR_REVIEW"

def maths : List Math := [.matchProved, .mismatchProved, .conditional, .undefinedProved, .notEstablished]
def bools : List Bool := [false, true]
def jb (b : Bool) : String := if b then "true" else "false"

/-- What the kernel accepted for one variant: a match, a mismatch, an undefined statistic, nothing. -/
def kinds : List (String × Option Outcome) :=
  [("match", some (run srcOne meanIsOne)), ("mismatch", some (run srcTwo meanIsOne)),
   ("undefined", some (.undefined .csvMalformed)), ("none", none)]

def lists : Nat → List (List (String × Option Outcome))
  | 0 => [[]]
  | n + 1 => (lists n).flatMap (fun l => kinds.map (fun k => k :: l))

def coreRows : List String :=
  maths.flatMap fun m => bools.flatMap fun a => bools.flatMap fun g => bools.flatMap fun s =>
    bools.flatMap fun w => bools.map fun c =>
      s!"[\"{mathName m}\",{jb a},{jb g},{jb s},{jb w},{jb c},\"{verdictName (core m a g s w c)}\"]"

def mathRows : List String :=
  ([1, 2, 3].flatMap lists).map fun l =>
    let names := ",".intercalate (l.map fun k => s!"\"{k.1}\"")
    s!"[[{names}],\"{mathName (mathStatus (l.map fun k => ⟨meanIsOne, k.2⟩))}\"]"

/-- Gate level, a proved mismatch that is attached, grounded and analysable. -/
def mismatchRows : List String :=
  bools.flatMap fun g1 => bools.flatMap fun g2 => bools.flatMap fun g3 => bools.flatMap fun g4 =>
    bools.flatMap fun g5 => bools.flatMap fun g6 => bools.flatMap fun g7 => bools.flatMap fun g8 =>
      bools.map fun cD =>
        let f : Findings := { allPass with notCount := g1, basicOk := g2, boundedAll := g3, noEligible := g4,
                                           beyondRounding := g5, dispersionNamed := g6, inGrammar := g7, sampleSizeOk := g8 }
        s!"[{jb g1},{jb g2},{jb g3},{jb g4},{jb g5},{jb g6},{jb g7},{jb g8},{jb cD},\"{verdictName (outward .mismatchProved f false cD)}\"]"

/-- Gate level, a proved match that is attached, grounded and analysable. -/
def matchRows : List String :=
  bools.flatMap fun g1 => bools.flatMap fun g2 => bools.flatMap fun g3 => bools.flatMap fun g4 =>
    bools.flatMap fun cM => bools.map fun pin =>
      let f : Findings := { allPass with basicOk := g1, boundedBound := g2, noCompeting := g3, lowRate := g4, pinnedOk := pin }
      s!"[{jb g1},{jb g2},{jb g3},{jb g4},{jb cM},{jb pin},\"{verdictName (outward .matchProved f cM false)}\"]"

#eval IO.println ("{\"core\":[" ++ ",".intercalate coreRows ++ "],\"math\":[" ++ ",".intercalate mathRows ++
  "],\"mismatch\":[" ++ ",".intercalate mismatchRows ++ "],\"match\":[" ++ ",".intercalate matchRows ++ "]}")
