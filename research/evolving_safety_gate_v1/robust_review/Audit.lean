import HardReview
import RobustObservation

/-! Emit executable decisions for differential checking by a second finite model. -/
namespace ReviewAudit

def word : (n : Nat) → Nat → RobustObservation.Word n
  | 0, _ => ()
  | n+1, mask => (mask % 2 == 1, word n (mask / 2))

def monitoring : IO Unit := do
  for n in [:5] do
    let size := 2 ^ n
    for x in [:size] do
      for y in [:size] do
        let encode := fun (e : Bool) => if e then word n y else word n x
        for a in [:n+1] do
          for b in [:n+1] do
            let radius := fun (e : Bool) => if e then b else a
            let compatible := RobustObservation.compatible encode radius
            let line := (List.range size).map fun z =>
              match RobustObservation.monitor [false, true] compatible id (word n z) with
              | some false => '0' | some true => '1' | none => '-'
            IO.println (String.ofList line)

def promotions : IO Unit := do
  let p := fun (mask packet : Nat) => mask.testBit packet
  for (hard, measured) in [
      ([(6,false), (4,true)], [(2,true), (3,true), (5,false)]),
      ([(7,true), (4,false), (5,true)], [(3,false), (3,true), (2,false), (6,true)])] do
    for old in [:256] do
      let line := (List.range 256).map fun newMask =>
        if HardReview.gate p 0 1 hard measured old newMask then '1' else '0'
      IO.println (String.ofList line)

end ReviewAudit

def main (args : List String) : IO UInt32 := do
  match args with
  | ["monitoring"] => ReviewAudit.monitoring
  | ["promotions"] => ReviewAudit.promotions
  | _ => return 2
  return 0
