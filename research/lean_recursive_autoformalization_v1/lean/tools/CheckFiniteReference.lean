import PCS.V2.NamedReference

/-! Independent receiver for two canonical JSON files. The first file belongs
to the reference reviewer and selects the free variable signature. -/
open Lean PCS.V2.FiniteReference

structure Document where
  format : String
  variables : List String
  contract : NamedContract
  deriving FromJson, ToJson

def readDocument (path : String) : IO Document := do
  let handle ← IO.FS.Handle.mk path .read
  let bytes ← handle.read 16385
  if bytes.size > 16384 then throw (IO.userError "document exceeds 16384 bytes")
  let some raw := String.fromUTF8? bytes | throw (IO.userError "invalid UTF-8")
  let parsed ← IO.ofExcept (Json.parse raw)
  let doc : Document ← IO.ofExcept (fromJson? parsed)
  if raw ≠ (toJson doc).compress ++ "\n" then
    throw (IO.userError "expected canonical compact JSON and one LF")
  if doc.format ≠ "pcs-bool-contract-v1" then throw (IO.userError "unknown format")
  if doc.variables.length > 10 then throw (IO.userError "more than 10 free variables")
  if doc.variables.eraseDups ≠ doc.variables then throw (IO.userError "duplicate free variable")
  return doc

def values : (names : List String) → Assignment names.length → List (String × Json)
  | [], _ => []
  | x :: xs, (b, rest) => (x, toJson b) :: values xs rest

def fields (c : Contract n) (ρ : Assignment n) : Json :=
  Json.mkObj [("premise", toJson (eval c.premise ρ)), ("conclusion", toJson (eval c.conclusion ρ))]

def compareDocuments (r c : Document) : Except String (UInt32 × Json) := do
  let names := r.variables
  if c.variables ≠ names then throw "ordered signatures differ"
  let perAssignment := r.contract.premise.cost + r.contract.conclusion.cost +
                       c.contract.premise.cost + c.contract.conclusion.cost
  if 2 ^ names.length * perAssignment > 1000000 then throw "exhaustive evaluation exceeds budget"
  let some reference := r.contract.resolve? names | throw "unbound reference variable"
  let some candidate := c.contract.resolve? names | throw "unbound candidate variable"
  match counterexample reference candidate with
  | some ρ => return (1, Json.mkObj [
      ("translation", "COUNTEREXAMPLE_FOUND"), ("assignment", Json.mkObj (values names ρ)),
      ("reference", fields reference ρ), ("candidate", fields candidate ρ),
      ("validity", "UNASSESSED")])
  | none =>
    match falsifier candidate with
    | some ρ => return (0, Json.mkObj [
        ("translation", "SEMANTICALLY_EQUIVALENT"), ("validity", "REFUTED"),
        ("assignment", Json.mkObj (values names ρ)), ("candidate", fields candidate ρ)])
    | none => return (0, Json.mkObj [
        ("translation", "SEMANTICALLY_EQUIVALENT"), ("validity", "VALID_FOR_ALL_ASSIGNMENTS")])

def main (args : List String) : IO UInt32 := do
  try
    let [refPath, candidatePath] := args | throw (IO.userError "expected REFERENCE.json CANDIDATE.json")
    let ref ← readDocument refPath
    let candidate ← readDocument candidatePath
    let (code, result) ← IO.ofExcept (compareDocuments ref candidate)
    IO.println result.compress
    return code
  catch e =>
    IO.println (Json.mkObj [("translation", "UNKNOWN"), ("reason", toJson e.toString)]).compress
    return 2
