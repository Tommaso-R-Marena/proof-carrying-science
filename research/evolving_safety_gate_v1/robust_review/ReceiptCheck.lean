import HardReview

/-! Numeric projection of authenticated inputs. The Python envelope parser
supplies only bounded table masks and case codes (2 * packet + label). -/
namespace ReceiptCheck

def parseCases (s : String) : Option (List (HardReview.Case Nat)) := do
  let cells ← (s.splitOn ",").mapM String.toNat?
  if cells.isEmpty || cells.length > 512 || cells.any (· ≥ 16) then none else
    some (cells.map fun c => (c / 2, c % 2 == 1))

def evaluate (older newer hard measured : String) : Option String := do
  let old ← older.toNat?
  let newMask ← newer.toNat?
  if old ≥ 256 || newMask ≥ 256 then none else
    let h ← parseCases hard
    let d ← parseCases measured
    let predict := fun (mask packet : Nat) => mask.testBit packet
    let ok := HardReview.gate predict 0 1 h d old newMask
    let a := HardReview.score predict old d
    let b := HardReview.score predict newMask d
    let x := HardReview.score predict old h
    let y := HardReview.score predict newMask h
    some s!"{ok} {a} {b} {x} {y}"

end ReceiptCheck

def main (args : List String) : IO UInt32 := do
  let [old, candidate, hard, measured] := args | return 2
  let some answer := ReceiptCheck.evaluate old candidate hard measured | return 2
  IO.println answer
  return 0
