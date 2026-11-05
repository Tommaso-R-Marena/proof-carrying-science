import Ledger
-- Batch framing: every five bytes is one independent request; incomplete tail refuses.
def frames : List UInt8 → List UInt8
 | [] => []
 | a::b::c::d::e::rest => PCSDisclosure.process [a,b,c,d,e] ++ frames rest
 | rest => PCSDisclosure.process rest
partial def readAll (h : IO.FS.Stream) (acc : ByteArray) : IO ByteArray := do
  let b ← h.read 65536
  if b.isEmpty then return acc
  if acc.size + b.size > 8388608 then throw (IO.userError "batch budget")
  readAll h (acc ++ b)
def main : IO Unit := do
  let i ← IO.getStdin; let o ← IO.getStdout
  let raw ← readAll i ByteArray.empty
  o.write ⟨(frames raw.data.toList).toArray⟩
  o.flush
