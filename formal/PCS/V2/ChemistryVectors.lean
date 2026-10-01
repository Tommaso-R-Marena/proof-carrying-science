import PCS.V2.Chemistry
import PCS.V2.Vectors

/-!
# Executable checks for the Lean `reaction_balance` executor (tests, not proofs)

Most importantly, the golden package is accepted when the Lean checker **replays its
chemistry evidence itself** (`chemExecWith unverifiedExec`) instead of using a
recorded or constant-PASS executor.
-/

namespace PCS.V2.ChemistryVectors

open PCS PCS.V2.Json PCS.V2.Replay PCS.V2.EndToEnd PCS.V2.Chemistry PCS.V2.Vectors

#guard tokenize "H2O".toList == some [("H", 2), ("O", 1)]
#guard tokenize "Co".toList == some [("Co", 1)]
#guard tokenize "CO".toList == some [("C", 1), ("O", 1)]
#guard tokenize "C12H22O11".toList == some [("C", 12), ("H", 22), ("O", 11)]
#guard tokenize "h2".toList == none
#guard tokenize "H2 O".toList == none
-- U+0662 ARABIC-INDIC DIGIT TWO is not an ASCII digit (counterexample 3).
#guard tokenize "H\u0662".toList == none

def ev (s : String) : JVal := (parse s.toList).getD .null

def req (s : String) : ReplayRequest :=
  { certificateSemanticHash := [], checkerVersion := "", evidence := ev s, artifacts := [] }

def water : String :=
  "{\"check_spec\":{\"products\":[{\"coefficient\":2,\"formula\":\"H2O\"}],\"reactants\":[{\"coefficient\":2,\"formula\":\"H2\"},{\"coefficient\":1,\"formula\":\"O2\"}],\"type\":\"reaction_balance\"}}"
def waterUnbalanced : String :=
  "{\"check_spec\":{\"products\":[{\"coefficient\":1,\"formula\":\"H2O\"}],\"reactants\":[{\"coefficient\":2,\"formula\":\"H2\"},{\"coefficient\":1,\"formula\":\"O2\"}],\"type\":\"reaction_balance\"}}"
def waterBoolCoeff : String :=
  "{\"check_spec\":{\"products\":[{\"coefficient\":2,\"formula\":\"H2O\"}],\"reactants\":[{\"coefficient\":2,\"formula\":\"H2\"},{\"coefficient\":true,\"formula\":\"O2\"}],\"type\":\"reaction_balance\"}}"
def waterZeroCoeff : String :=
  "{\"check_spec\":{\"products\":[{\"coefficient\":0,\"formula\":\"H2O\"}],\"reactants\":[{\"coefficient\":0,\"formula\":\"H2\"}],\"type\":\"reaction_balance\"}}"

#guard (chemExecWith unverifiedExec (req water)) == ⟨.computationalTest, .pass⟩
#guard (chemExecWith unverifiedExec (req waterUnbalanced)) == ⟨.computationalTest, .fail⟩
-- `true` is not a coefficient (counterexample 4: Python's `isinstance(True, int)`).
#guard (chemExecWith unverifiedExec (req waterBoolCoeff)) == ⟨.computationalTest, .fail⟩
#guard (chemExecWith unverifiedExec (req waterZeroCoeff)) == ⟨.computationalTest, .fail⟩

/-- The golden package with the chemistry evidence genuinely replayed in Lean. -/
def chemOracles : Oracles := { goldenOracles with exec := chemExecWith unverifiedExec }

#guard accepts chemOracles goldenAnchor goldenInput

end PCS.V2.ChemistryVectors
