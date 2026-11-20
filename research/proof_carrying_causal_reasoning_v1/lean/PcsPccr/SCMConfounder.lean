/-
Exact rational confounder SCM: equality of the backdoor functional with the
interventional law, plus correlation ≠ causation, for a fixed finite model.

Mechanisms:
  P(Z=1) = 1/2
  P(X=1 | Z=z) = (1 + ⟦z⟧) / 4
  P(Y=1 | X=x, Z=z) = (1 + ⟦x⟧ + 2⟦z⟧) / 8

Under these mechanisms the backdoor formula with adjustment set {Z} is
definitionally identical to P(Y | do(X)), and the observational conditional
P(Y=1 | X=1) is proved unequal to P(Y=1 | do(X=1)).
-/
namespace PcsPccr.SCMConfounder

abbrev Bit := Bool

def bitVal (b : Bit) : Rat := if b then 1 else 0

def pZ : Bit → Rat
  | true => 1/2
  | false => 1/2

def pX_given_Z (z : Bit) : Bit → Rat
  | true => (1 + bitVal z) / 4
  | false => 1 - (1 + bitVal z) / 4

def pY_given_XZ (x z : Bit) : Bit → Rat
  | true => (1 + bitVal x + 2 * bitVal z) / 8
  | false => 1 - (1 + bitVal x + 2 * bitVal z) / 8

/-- Observational joint. -/
def joint (z x y : Bit) : Rat :=
  pZ z * pX_given_Z z x * pY_given_XZ x z y

/-- Interventional law after do(X = xStar): Σ_z P(Z=z) P(Y=y | X=xStar, Z=z). -/
def pY_do (xStar y : Bit) : Rat :=
  pZ false * pY_given_XZ xStar false y + pZ true * pY_given_XZ xStar true y

/-- Backdoor functional with Z. -/
def backdoor (xStar y : Bit) : Rat :=
  pZ false * pY_given_XZ xStar false y + pZ true * pY_given_XZ xStar true y

/-- On this SCM the backdoor functional *is* the interventional law. -/
theorem backdoor_eq_intervention (xStar y : Bit) :
    backdoor xStar y = pY_do xStar y := rfl

def pY1_doX1 : Rat := pY_do true true
def backdoor_Y1_X1 : Rat := backdoor true true

theorem backdoor_matches_do_X1_Y1 : backdoor_Y1_X1 = pY1_doX1 := rfl

/-- Closed form: 1/8 + 1/4 = 3/8. -/
theorem pY1_doX1_value : pY1_doX1 = (3 : Rat) / 8 := by
  native_decide

theorem backdoor_Y1_X1_value : backdoor_Y1_X1 = (3 : Rat) / 8 := by
  native_decide

theorem pY1_doX0_value : pY_do false true = (1 : Rat) / 4 := by
  native_decide

def ate : Rat := pY_do true true - pY_do false true

theorem ate_value : ate = (1 : Rat) / 8 := by
  native_decide

def pX1 : Rat :=
  joint false true true + joint false true false +
    joint true true true + joint true true false

def pY1X1 : Rat := joint false true true + joint true true true

def pY1_given_X1 : Rat := pY1X1 / pX1

theorem pX1_pos : pX1 ≠ 0 := by native_decide

/-- Correlation ≠ causation on this exact SCM. -/
theorem association_ne_intervention : pY1_given_X1 ≠ pY1_doX1 := by
  native_decide

theorem pY1_given_X1_value : pY1_given_X1 = (5 : Rat) / 12 := by
  native_decide

/-- Marginal consistency: joints over Y sum to P(Z)P(X|Z). -/
theorem joint_sums_Y (z x : Bit) :
    joint z x false + joint z x true = pZ z * pX_given_Z z x := by
  cases z <;> cases x <;> native_decide

end PcsPccr.SCMConfounder
