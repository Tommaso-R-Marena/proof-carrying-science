import PCS.V2.ProofGatedInference
import Lean

/- Research-only IO adapter over the unchanged formal codec/gate/inference.
   No theorem about host execution, isolation, or Python correspondence. -/
open Lean
open PCS.V2.ProofGatedArtifacts
open PCS.V2.ProofGatedSelfImprovement

def unhex (s : String) : Option ByteArray := do
  let chars := s.toList
  if chars.length % 2 != 0 then none else
    let rec loop : List Char → ByteArray → Option ByteArray
      | [], out => some out
      | a :: b :: rest, out => do
        let x ← "0123456789abcdef".toList.idxOf? a
        let y ← "0123456789abcdef".toList.idxOf? b
        loop rest (out.push (UInt8.ofNat (x*16+y)))
      | _, _ => none
    loop chars ByteArray.empty

def probe (j : Json) : Except String Json := do
  let rawHex ← (← j.getObjVal? "raw_hex").getStr?
  let xs ← (← j.getObjVal? "xs").getArr?
  let invalid := Json.mkObj [("valid", toJson false)]
  match unhex rawHex >>= String.fromUTF8? >>= decode with
  | none => pure invalid
  | some m =>
    let inputs ← xs.toList.mapM fun v => do
      let s ← v.getStr?
      match s.toInt? with
      | some n => pure n
      | none => throw "invalid integer"
    pure <| Json.mkObj [
      ("valid", toJson true), ("wire", toJson (encode m)),
      ("relu", toJson m.useReLU), ("weight", toJson (toString m.weight)),
      ("bias", toJson (toString m.bias)),
      ("predictions", toJson (inputs.map fun x => toString (predict m x))),
      ("finite_from_zero", toJson (accept ⟨true, 0, 0⟩ m))]

def transitionProbe (j : Json) : Except String Json := do
  let a ← (← j.getObjVal? "old_hex").getStr?
  let b ← (← j.getObjVal? "new_hex").getStr?
  let old := unhex a >>= String.fromUTF8?
  let proposed := unhex b >>= String.fromUTF8?
  let accepted := match old, proposed with
    | some x, some y => acceptWire x y
    | _, _ => false
  pure <| Json.mkObj [("accepted", toJson accepted),
    ("old_valid", toJson ((old >>= decode).isSome)),
    ("new_valid", toJson ((proposed >>= decode).isSome))]

@[export pgsi_research_main]
def pgsiResearchMain (args : List String) : IO UInt32 := do
  match args with
  | ["legacy", oldPath, newPath] => main [oldPath, newPath]
  | ["gate", oldPath, newPath] =>
    try
      let a ← IO.FS.readFile ⟨oldPath⟩
      let b ← IO.FS.readFile ⟨newPath⟩
      if acceptWire a b then
        IO.println "ACCEPT"
        return 0
      else
        IO.println "REJECT"
        return 1
    catch _ =>
      IO.println "REJECT"
      return 2
  | [mode] =>
    if mode != "probe" && mode != "transitions" then return 2
    let input ← IO.getStdin
    let output ← IO.getStdout
    repeat
      let line ← input.getLine
      if line.isEmpty then break
      match Json.parse line >>= (if mode == "probe" then probe else transitionProbe) with
      | .ok j => output.putStrLn j.compress
      | .error _ => output.putStrLn "{\"error\":\"invalid_request\"}"
    return 0
  | _ => return 2
