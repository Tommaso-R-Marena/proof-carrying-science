import PCSIntegration

open PCSIntegration CertNum CertNum.Expr CertNum.Certificate

def rationalText (q : ℚ) : String :=
  if q.den = 1 then toString q.num else s!"{q.num}/{q.den}"

def bounds : Interval → Option (ℚ × ℚ)
  | .empty => none
  | .nonempty lo hi _ => some (lo, hi)

/-- Fixed diagnostic fixture only: no general JSON decoding or promotion authority. -/
def main : IO Unit := do
  let initial : Fin 2 → ℚ := fun s => if s = 0 then 1 else 0
  let firing : ℚ := 1 / 3
  let state := PCCA.Stoich.evolve transfer (fun _ _ => firing) initial 1
  let some (aLo, aHi) := bounds sampleCertificate.claimed
    | throw (IO.userError "empty numerical fixture enclosure")
  let some (bLo, bHi) := bounds (Interval.sub (Interval.singleton 1) sampleCertificate.claimed)
    | throw (IO.userError "empty complement fixture enclosure")
  let some value := sampleCertificate.expr.eval (fun _ => none)
    | throw (IO.userError "undefined numerical fixture expression")
  let accepted := checkIntervalEnclosure sampleCertificate
  unless accepted do throw (IO.userError "actual numerical checker rejected fixture")
  let fields := ["PCSAB1", rationalText (transfer 0 0), rationalText (transfer 1 0),
    rationalText (initial 0), rationalText (initial 1), rationalText firing, "1",
    rationalText (state 0), rationalText (state 1), rationalText value,
    rationalText aLo, rationalText aHi, rationalText bLo, rationalText bHi,
    toString accepted]
  IO.println (String.intercalate "|" fields)
