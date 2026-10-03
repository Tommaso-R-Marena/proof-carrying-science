import PCS.V2.Checkers
import PCS.V2.Vectors

/-!
# Executable checks for the verified built-in executor (tests, not proofs)

These `#guard`s exercise the Lean `unit_compatible` and `csv_disjoint` checkers on the
counterexamples found against the former Python implementations, and check that the golden
package is accepted when every built-in evidence kind is replayed by the verified
dispatcher (`Checkers.builtinExecWith`) rather than taken from a transcript.
-/

namespace PCS.V2.BuiltinVectors

open PCS PCS.V2.Json PCS.V2.Replay PCS.V2.EndToEnd PCS.V2.Vectors PCS.V2.Checkers PCS.V2.Chemistry

/-! ## Units -/

open PCS.V2.Units in
section
#guard unitCompatibleB "mg/L" "ug/mL"
#guard unitCompatibleB "L/h" "mL/min"
#guard unitCompatibleB "mol/L" "mM"
#guard !unitCompatibleB "mg" "L"
#guard !unitCompatibleB "mg/L" "mg"
-- counterexample 5: a trailing newline is not part of the unit grammar
#guard !unitCompatibleB "m\n" "m"
-- counterexample 6: U+0662 is not an ASCII exponent digit
#guard !unitCompatibleB "m^\u0662" "m^2"
-- counterexample 7: huge exponents are compared dimensionally (no float overflow)
#guard unitCompatibleB "M^200" "M^200"
-- counterexample 8: no float underflow
#guard unitCompatibleB "1/ug^40" "1/ug^40"
-- the empty expression is dimensionless (as in production)
#guard unitCompatibleB "" ""
#guard !unitCompatibleB "" "m"
#guard !unitCompatibleB "furlong" "furlong"
end

/-! ## Strict CSV -/

open PCS.V2.Csv in
section
def b (s : String) : List UInt8 := s.toUTF8.data.toList

#guard parseCsv (b "id,x\n1,a\n2,b\n") == some ([b "id", b "x"], [[b "1", b "a"], [b "2", b "b"]])
#guard parseCsv (b "id,x\r\n1,a\r\n") == some ([b "id", b "x"], [[b "1", b "a"]])
-- blank lines are skipped
#guard parseCsv (b "id\n\n1\n\n") == some ([b "id"], [[b "1"]])
-- counterexample 9: duplicate header names are rejected
#guard parseCsv (b "id,id\n1,2\n") == none
-- counterexample 10: short rows are rejected (DictReader would fill `None`)
#guard parseCsv (b "id,x\n1\n") == none
-- counterexample 11: quoting is outside the strict subset
#guard parseCsv (b "id\n\"1\"\n") == none
-- counterexample 12: a lone CR is rejected
#guard parseCsv (b "id\r1\n") == none
#guard parseCsv (b "") == none
#guard parseCsv [0xff, 10] == none

#guard csvDisjointB (b "id,x\n1,a\n2,b\n") (b "x,id\nc,3\n") (b "id")
#guard !csvDisjointB (b "id,x\n1,a\n2,b\n") (b "x,id\nc,2\n") (b "id")
#guard !csvDisjointB (b "id\n1\n") (b "ID\n2\n") (b "id")
-- keys are compared byte-exactly (no Unicode normalisation)
#guard csvDisjointB (b "id\n\u00e9\n") (b "id\ne\u0301\n") (b "id")
-- whitespace is significant
#guard csvDisjointB (b "id\n1\n") (b "id\n 1\n") (b "id")
end

/-! ## Dispatcher -/

def ev (s : String) : JVal := (parse s.toList).getD .null

def req (s : String) (arts : List (String × ByteArray) := []) : ReplayRequest :=
  { certificateSemanticHash := [], checkerVersion := "", evidence := ev s, artifacts := arts }

/-- A fallback that claims PASS for everything: built-in kinds must ignore it. -/
def lyingPass : Executor := fun _ => ⟨.computationalTest, .pass⟩

#guard (builtinExecWith lyingPass (req "{\"check_spec\":{\"type\":\"unit_compatible\",\"left_unit\":\"mg\",\"right_unit\":\"L\"}}")).outcome == .fail
#guard (builtinExecWith lyingPass (req "{\"check_spec\":{\"type\":\"unit_compatible\",\"left_unit\":\"mg/L\",\"right_unit\":\"ug/mL\"}}")).outcome == .pass
#guard (builtinExecWith lyingPass (req "{\"check_spec\":{\"type\":\"unit_compatible\",\"left_unit\":1,\"right_unit\":\"L\"}}")).outcome == .fail
#guard (builtinExecWith lyingPass (req "{\"check_spec\":{\"type\":\"csv_disjoint\",\"left_artifact\":\"A\",\"right_artifact\":\"B\",\"key\":\"id\"}}")).outcome == .fail
#guard (builtinExecWith lyingPass (req "{\"check_spec\":{\"type\":\"csv_disjoint\",\"left_artifact\":\"A\",\"right_artifact\":\"B\",\"key\":\"id\"}}"
    [("A", "id\n1\n".toUTF8), ("B", "id\n1\n".toUTF8)])).outcome == .fail
#guard (builtinExecWith lyingPass (req "{\"check_spec\":{\"type\":\"csv_disjoint\",\"left_artifact\":\"A\",\"right_artifact\":\"B\",\"key\":\"id\"}}"
    [("A", "id\n1\n".toUTF8), ("B", "id\n2\n".toUTF8)])).outcome == .pass
#guard (builtinExecWith lyingPass (req "{\"check_spec\":{\"type\":\"reaction_balance\",\"reactants\":[{\"coefficient\":1,\"formula\":\"H2\"}],\"products\":[{\"coefficient\":1,\"formula\":\"H\"}]}}")).outcome == .fail

/-- The golden package with all built-in evidence replayed by the verified dispatcher. -/
def builtinOracles : Oracles := { goldenOracles with exec := builtinExecWith unverifiedExec }

#guard accepts builtinOracles goldenAnchor goldenInput

end PCS.V2.BuiltinVectors
