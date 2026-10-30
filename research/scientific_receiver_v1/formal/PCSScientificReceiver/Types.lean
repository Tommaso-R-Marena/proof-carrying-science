import PCSIntegration

/-! Restricted data-only A→B scientific contracts. No producer proof flags. -/
namespace PCSScientificReceiver

structure Contract where
  referenceStep : Nat
  unitCode : Bool
  physical : Bool
  initialA : ℚ
  initialB : ℚ
  envValue : ℚ
  boxLo : ℚ
  boxHi : ℚ
  lower : ℚ
  upper : ℚ
  declaredTotal : ℚ
  firings : List ℚ
  deriving DecidableEq, Repr

def maxSteps : Nat := 64
def maxOperand : Nat := 1000000000000000000
def maxBytes : Nat := 8192
def maxFieldChars : Nat := 20

def rationalBounded (q : ℚ) : Bool :=
  decide (q.num.natAbs ≤ maxOperand ∧ q.den ≤ maxOperand)

def rationals (c : Contract) : List ℚ :=
  [c.initialA, c.initialB, c.envValue, c.boxLo, c.boxHi,
   c.lower, c.upper, c.declaredTotal] ++ c.firings

/-- Parsing/resource shape only; no scientific conclusion is assumed. -/
def bounded (c : Contract) : Bool :=
  decide (c.referenceStep ≤ maxSteps ∧ c.firings.length ≤ maxSteps) &&
  (rationals c).all rationalBounded

def initial (c : Contract) : Fin 2 → ℚ :=
  fun s => if s = 0 then c.initialA else c.initialB

def schedule (c : Contract) : Nat → Fin 1 → ℚ :=
  fun k _ => c.firings[k]?.getD 0

def state (c : Contract) (k : Nat) : Fin 2 → ℚ :=
  PCCA.Stoich.evolve PCSIntegration.transfer (schedule c) (initial c) k

def finalState (c : Contract) : Fin 2 → ℚ := state c c.firings.length

end PCSScientificReceiver
