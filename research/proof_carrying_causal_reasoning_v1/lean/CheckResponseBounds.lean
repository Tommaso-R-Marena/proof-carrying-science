import PcsPccr.SharpResponseBounds

/-! A small stdin receiver for numerical trial subclaims. Each line contains
five space-separated, canonical unsigned decimals: N, control responders,
treated responders, claimed lower count, claimed upper count. Trusted margins
must be supplied by the caller. The receiver verifies a sharp interval in
the finite model and returns an explicit endpoint construction for each end.
No model code or formal command is accepted as input. -/
open PcsPccr.SharpResponseBounds

private def counts (t : Table) : String :=
  s!"{t.never} {t.helped} {t.harmed} {t.always}"

private def parseCount (s : String) : Option Nat := do
  guard (s.length ≤ 18)
  let n ← s.toNat?
  guard (toString n == s)
  return n

def checkLine (line : String) : String :=
  match (line.splitOn " ").mapM parseCount with
  | some [n, c, r, lo, hi] =>
    if checkInterval n c r lo hi then
      s!"ACCEPT {counts (complete n c r lo)} {counts (complete n c r hi)}"
    else "REJECT"
  | _ => "MALFORMED"

def main : IO Unit := do
  let input ← IO.getStdin
  let output ← IO.getStdout
  repeat
    let line ← input.getLine
    if line.isEmpty then break
    let bare := (line.dropSuffix "\n").toString
    output.putStrLn (checkLine bare)
