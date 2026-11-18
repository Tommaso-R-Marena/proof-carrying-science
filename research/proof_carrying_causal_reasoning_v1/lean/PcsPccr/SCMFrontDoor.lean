/-
Exact rational front-door SCM: front-door functional equals the interventional
law, and observational association ≠ causation, for a fixed finite model.

Graph: U → X, U → Y, X → M, M → Y (classic front-door with latent confounder).

Mechanisms:
  P(U=1) = 1/2
  P(X=1 | U=u) = (1 + ⟦u⟧) / 4
  P(M=1 | X=x) = (1 + ⟦x⟧) / 4
  P(Y=1 | M=m, U=u) = (1 + ⟦m⟧ + 2⟦u⟧) / 8

Closed forms (verified against Python BinarySCM):
  P(Y=1 | do(X=1)) = 5/16
  P(Y=1 | do(X=0)) = 9/32
  ATE = 1/32
  P(Y=1 | X=1) = 17/48 ≠ 5/16
-/
namespace PcsPccr.SCMFrontDoor

abbrev Bit := Bool

def bitVal (b : Bit) : Rat := if b then 1 else 0

def pU : Bit → Rat
  | true => 1/2
  | false => 1/2

def pX_given_U (u : Bit) : Bit → Rat
  | true => (1 + bitVal u) / 4
  | false => 1 - (1 + bitVal u) / 4

def pM_given_X (x : Bit) : Bit → Rat
  | true => (1 + bitVal x) / 4
  | false => 1 - (1 + bitVal x) / 4

def pY_given_MU (m u : Bit) : Bit → Rat
  | true => (1 + bitVal m + 2 * bitVal u) / 8
  | false => 1 - (1 + bitVal m + 2 * bitVal u) / 8

/-- Observational joint P(U,X,M,Y). -/
def joint (u x m y : Bit) : Rat :=
  pU u * pX_given_U u x * pM_given_X x m * pY_given_MU m u y

/-- Interventional law after do(X = xStar): Σ_{u,m} P(U) P(M|X=xStar) P(Y|M,U). -/
def pY_do (xStar y : Bit) : Rat :=
  pU false * pM_given_X xStar false *
      pY_given_MU false false y +
    pU false * pM_given_X xStar true *
      pY_given_MU true false y +
    pU true * pM_given_X xStar false *
      pY_given_MU false true y +
    pU true * pM_given_X xStar true *
      pY_given_MU true true y

/-- Marginal P(X=x). -/
def pX (x : Bit) : Rat :=
  pU false * pX_given_U false x + pU true * pX_given_U true x

/-- Observational P(M=m | X=x) (= structural, since M ⟂ U | X). -/
def pM_given_X_obs (x m : Bit) : Rat := pM_given_X x m

/-- Observational P(Y=y | X=x, M=m) = Σ_u P(Y|M,U) P(U|X,M).
    Under this SCM: P(U|X,M) = P(U|X) because M ⟂ U | X. -/
def pU_given_X (x u : Bit) : Rat :=
  (pU u * pX_given_U u x) / pX x

def pY_given_XM (x m y : Bit) : Rat :=
  pU_given_X x false * pY_given_MU m false y +
    pU_given_X x true * pY_given_MU m true y

/-- Front-door functional:
    Σ_m P(M=m|X=xStar) Σ_{x'} P(Y=y|X=x',M=m) P(X=x'). -/
def frontdoor (xStar y : Bit) : Rat :=
  let inner (m : Bit) : Rat :=
    pY_given_XM false m y * pX false + pY_given_XM true m y * pX true
  pM_given_X_obs xStar false * inner false +
    pM_given_X_obs xStar true * inner true

def pY1_doX1 : Rat := pY_do true true
def frontdoor_Y1_X1 : Rat := frontdoor true true

theorem frontdoor_matches_do_X1_Y1 : frontdoor_Y1_X1 = pY1_doX1 := by
  native_decide

theorem pY1_doX1_value : pY1_doX1 = (5 : Rat) / 16 := by
  native_decide

theorem frontdoor_Y1_X1_value : frontdoor_Y1_X1 = (5 : Rat) / 16 := by
  native_decide

theorem pY1_doX0_value : pY_do false true = (9 : Rat) / 32 := by
  native_decide

def ate : Rat := pY_do true true - pY_do false true

theorem ate_value : ate = (1 : Rat) / 32 := by
  native_decide

def pX1 : Rat := pX true

def pY1X1 : Rat :=
  joint false true false true + joint false true true true +
    joint true true false true + joint true true true true

def pY1_given_X1 : Rat := pY1X1 / pX1

theorem pX1_pos : pX1 ≠ 0 := by native_decide

theorem association_ne_intervention : pY1_given_X1 ≠ pY1_doX1 := by
  native_decide

theorem pY1_given_X1_value : pY1_given_X1 = (17 : Rat) / 48 := by
  native_decide

theorem frontdoor_eq_intervention (xStar y : Bit) :
    frontdoor xStar y = pY_do xStar y := by
  cases xStar <;> cases y <;> native_decide

end PcsPccr.SCMFrontDoor
