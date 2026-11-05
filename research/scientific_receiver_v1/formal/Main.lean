import PCSScientificReceiver.Receiver
import Lean.Data.Json

/-! Bounded binary framing and JSON rendering are trusted host IO, outside the
pure receiving theorem. Each request is a big-endian u32 length and raw bytes.
The process accepts no authority path, expression, or executable from requests.
-/
open PCSScientificReceiver
open Lean (toJson)

def qString (q : Rat) : String :=
  String.ofList (PCS.V2.ProofGatedCodec.renderInt q.num) ++ "/" ++
  String.ofList (PCS.V2.ProofGatedCodec.renderNat q.den)

def hexBytes (raw : ByteArray) : String :=
  String.ofList (raw.data.toList.flatMap fun b =>
    let digits := "0123456789abcdef".toList
    [digits[b.toNat / 16]!, digits[b.toNat % 16]!])

def resultJson (r : Result) : Lean.Json := Lean.Json.mkObj [
  ("stepCount", toJson r.stepCount), ("unitCode", toJson r.unitCode),
  ("physical", toJson r.physical), ("finalA", toJson (qString r.finalA)),
  ("finalB", toJson (qString r.finalB)), ("total", toJson (qString r.total)),
  ("lowerA", toJson (qString r.lowerA)), ("upperA", toJson (qString r.upperA)),
  ("lowerB", toJson (qString r.lowerB)), ("upperB", toJson (qString r.upperB))]

def response (raw : ByteArray) (result : Option Result) (error : String) : Lean.Json :=
  Lean.Json.mkObj [("accepted", toJson result.isSome),
    ("protocol", toJson "PCS-SCI-BOUND-V1"), ("policy", toJson (1 : Nat)),
    ("raw_hex", toJson (hexBytes raw)), ("scientific_acceptance", toJson false),
    ("production_authority", toJson false),
    ("result", result.map resultJson |>.getD Lean.Json.null),
    ("error", toJson error)]

def readExactly (stream : IO.FS.Stream) (n : Nat) : IO ByteArray := do
  let rec go : Nat → ByteArray → IO ByteArray
    | 0, acc => pure acc
    | fuel + 1, acc => do
      if acc.size ≥ n then return acc
      let part ← stream.read (n - acc.size).toUSize
      if part.isEmpty then return acc
      go fuel (acc ++ part)
  go (n + 1) ByteArray.empty

def emit (out : IO.FS.Stream) (raw : ByteArray) (r : Option Result) (error : String) : IO Unit := do
  out.putStr ((response raw r error).compress ++ "\n")
  out.flush

partial def requests (input out : IO.FS.Stream) : IO Unit := do
  let header ← readExactly input 4
  if header.isEmpty then return
  if header.size != 4 then
    emit out ByteArray.empty none "truncated_header"
    return
  let n := header.data.foldl (fun acc b => acc * 256 + b.toNat) 0
  if n > maxBytes then
    emit out ByteArray.empty none "oversize_frame"
    return
  let raw ← readExactly input n
  if raw.size != n then
    emit out raw none "truncated_body"
    return
  let r := receive raw.data.toList
  emit out raw r (if r.isSome then "" else "decode_or_contract_rejection")
  requests input out

def main : IO Unit := do
  requests (← IO.getStdin) (← IO.getStdout)
