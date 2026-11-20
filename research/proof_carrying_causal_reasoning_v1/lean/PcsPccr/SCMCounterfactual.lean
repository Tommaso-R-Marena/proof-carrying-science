/-
Exact twin-network counterfactuals on the confounder SCM (same mechanisms as
SCMConfounder). Shared Unif[0,1] exogenous noise yields Pearl abduction →
action → prediction with rational closed forms.

Mechanisms:
  P(Z=1) = 1/2
  P(X=1 | Z=z) = (1 + ⟦z⟧) / 4
  P(Y=1 | X=x, Z=z) = (1 + ⟦x⟧ + 2⟦z⟧) / 8

Results (native_decide on finite enumeration):
  P(Y_1 = 1 | X = 1) = P(Y = 1 | X = 1) = 5/12   (consistency)
  P(Y_1 = 1 | X = 0) = 7/20 ≠ P(Y = 1 | do(X = 1)) = 3/8
-/
namespace PcsPccr.SCMCounterfactual

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

def joint (z x y : Bit) : Rat :=
  pZ z * pX_given_Z z x * pY_given_XZ x z y

def pX (x : Bit) : Rat :=
  joint false x false + joint false x true + joint true x false + joint true x true

def pY1_given_X (x : Bit) : Rat :=
  (joint false x true + joint true x true) / pX x

/-- Interventional P(Y=1 | do(X=xStar)). -/
def pY1_do (xStar : Bit) : Rat :=
  pZ false * pY_given_XZ xStar false true + pZ true * pY_given_XZ xStar true true

/-- Bridge: P(C=1 | F=f, p_f, p_c) for shared U~Unif[0,1]. -/
def bridge (factual : Bit) (pF pC : Rat) : Rat :=
  if factual then
    (if pF ≤ pC then pF else pC) / pF
  else
    if pC ≤ pF then 0 else (pC - pF) / (1 - pF)

/-- Weight of a counterfactual (z,y) given factual (zF,xF,yF) under do(X=xStar).
Z is root so it is pinned to zF; Y bridges from factual parents (xF,zF) to (xStar,zF). -/
def cfWeight (zF xF yF z y : Bit) (xStar : Bit) : Rat :=
  let wZ : Rat := if z = zF then 1 else 0
  let pF := pY_given_XZ xF zF true
  let pC := pY_given_XZ xStar zF true
  let q := bridge yF pF pC
  let wY : Rat := if y then q else 1 - q
  wZ * wY

/-- P(Y_{xStar}=1 | X=xEv) by enumerating factual worlds with X=xEv. -/
def cfY1_given_X (xStar xEv : Bit) : Rat :=
  let mass := pX xEv
  let numer :=
    (List.foldl (fun acc zF =>
      List.foldl (fun acc2 yF =>
        let wF := joint zF xEv yF
        let pY := cfWeight zF xEv yF zF true xStar
        acc2 + wF * pY) acc [false, true]) 0 [false, true])
  numer / mass

def cf_Y1_given_X0 : Rat := cfY1_given_X true false
def cf_Y1_given_X1 : Rat := cfY1_given_X true true

theorem pX0_pos : pX false ≠ 0 := by native_decide
theorem pX1_pos : pX true ≠ 0 := by native_decide

/-- Consistency: Y_1 | X=1 equals observational P(Y=1|X=1). -/
theorem consistency_Y1_given_X1 : cf_Y1_given_X1 = pY1_given_X true := by
  native_decide

theorem consistency_value : cf_Y1_given_X1 = (5 : Rat) / 12 := by
  native_decide

/-- Breakthrough separation: counterfactual ≠ interventional under confounding. -/
theorem cf_ne_interventional_given_X0 : cf_Y1_given_X0 ≠ pY1_do true := by
  native_decide

theorem cf_Y1_given_X0_value : cf_Y1_given_X0 = (7 : Rat) / 20 := by
  native_decide

theorem interventional_Y1_doX1 : pY1_do true = (3 : Rat) / 8 := by
  native_decide

end PcsPccr.SCMCounterfactual
