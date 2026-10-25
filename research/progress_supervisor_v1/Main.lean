import Data
import Wire

def readBounded (stream : IO.FS.Stream) : Nat → ByteArray → IO ByteArray
  | 0, acc => pure acc
  | fuel+1, acc => do
    if acc.size ≥ 32769 then return acc
    let chunk ← stream.read (USize.ofNat (32769-acc.size))
    if chunk.isEmpty then return acc
    readBounded stream fuel (acc ++ chunk)

def main : IO Unit := do
  let raw ← readBounded (← IO.getStdin) 32769 ByteArray.empty
  let answer := if raw.size > 32768 then [1,3,0,0,0,0]
    else PCSProgressWire.batch PCSProgressData.spec (raw.data.toList.map UInt8.toNat)
  let output ← IO.getStdout
  output.write ⟨(answer.map UInt8.ofNat).toArray⟩
  output.flush
