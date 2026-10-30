import PCSEpistemic.Judgment

/-
Typed residual bridges.

A bridge may raise support from stratum `src` to stratum `dst` only when an
explicit residual obligation at `dst` is discharged by evidence that can
discharge `dst`. Silent inheritance from a lower ACCEPT is rejected.
-/

namespace PCSEpistemic

structure Bridge where
  id : String
  src : Stratum
  dst : Stratum
  residualId : String
  deriving DecidableEq, Repr

def Bridge.wellTypedB (b : Bridge) : Bool :=
  decide (b.src < b.dst)

structure ResidualDischarge where
  residual : Residual
  evidence : Evidence
  deriving DecidableEq, Repr

def ResidualDischarge.okB (d : ResidualDischarge) : Bool :=
  (d.evidence.outcome == Outcome.pass) &&
  (d.evidence.predicate == d.residual.reason) &&
  Stratum.canDischarge d.evidence.stratum d.residual.stratum

def applyBridge (b : Bridge) (d : ResidualDischarge) (c : Claim) : Bool :=
  b.wellTypedB &&
  (b.residualId == d.residual.id) &&
  (d.residual.stratum == b.dst) &&
  (c.stratum == b.dst) &&
  ResidualDischarge.okB d

theorem formal_continuum_bridge_requires_discharge
    (b : Bridge) (d : ResidualDischarge) (c : Claim)
    (hfail : ResidualDischarge.okB d = false) :
    applyBridge b d c = false := by
  simp [applyBridge, hfail]

def badFormalContinuumBridge : Bridge where
  id := "B_bad"
  src := .formal
  dst := .continuum
  residualId := "R_continuum"

def badContinuumResidual : Residual where
  id := "R_continuum"
  stratum := .continuum
  reason := "continuum-accuracy"

def badComputationalEvidence : Evidence where
  id := "E_comp"
  stratum := .computational
  outcome := .pass
  predicate := "continuum-accuracy"
  artifactIds := ["matrix.json"]

def badDischarge : ResidualDischarge where
  residual := badContinuumResidual
  evidence := badComputationalEvidence

def badClaim : Claim where
  id := "C_continuum"
  stratum := .continuum
  predicate := "amount-conserved"
  requiredEvidence := ["E_comp"]
  assumptions := ["A_model"]

theorem bad_computational_discharge_rejected :
    ResidualDischarge.okB badDischarge = false := by
  decide

theorem bad_bridge_rejected :
    applyBridge badFormalContinuumBridge badDischarge badClaim = false := by
  decide

/-- Mismatched residual stratum versus bridge destination is rejected. -/
def mismatchedBridge : Bridge where
  id := "B_mismatch"
  src := .continuum
  dst := .causal
  residualId := "R_continuum"

theorem mismatched_residual_bridge_rejected :
    applyBridge mismatchedBridge badDischarge badClaim = false := by
  decide

end PCSEpistemic
