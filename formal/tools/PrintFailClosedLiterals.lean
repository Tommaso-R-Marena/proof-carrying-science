import PCS.V2.Witnesses.AISafetyCampaign

/-! Prints the hash literals and certificate sizes used by `PCS.V2.Golden.FailClosedFixtures`
    (generator only; every printed value is re-checked in the kernel by that file).
    Usage: `lake env lean --run tools/PrintFailClosedLiterals.lean`. -/

open PCS.V2.Witnesses.AISafetyGolden PCS.V2.Witnesses.AISafetyCampaign

def show1 (name : String) (s : FixtureSpec) : IO Unit := do
  IO.println s!"{name} sem={s.semHash} int={s.intHash} size={s.certBytes.size}"

def main : IO Unit := do
  show1 "m7" m7
  show1 "m7b" m7b
  show1 "m7c" m7c
  show1 "m15" m15
