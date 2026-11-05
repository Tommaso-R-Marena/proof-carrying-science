import PCSEpistemic.Evaluate

/-!
# Positive and negative controls for the epistemic lattice

Full topological package evaluation is covered by the Python receiving campaign.
These Lean controls pin the local evaluator laws that the package loop invokes.
-/
set_option autoImplicit false

namespace PCSEpistemic.Controls

open PCSEpistemic

def atomPeak : Atom := 1
def atomN : Atom := 2
def falsifierPeak : Literal := ⟨atomPeak, true⟩
def supportN : Literal := ⟨atomN, true⟩

def claimEmpirical : Claim :=
  ⟨0, .empirical, [], [falsifierPeak], [supportN]⟩

def claimFormalDep : Claim :=
  ⟨1, .formal, [0], [], []⟩

def obsOk : Observations := ⟨[(atomPeak, false), (atomN, true)]⟩
def obsFalsified : Observations := ⟨[(atomPeak, true), (atomN, true)]⟩
def obsIncomplete : Observations := ⟨[(atomPeak, false)]⟩

def evidenceEmpiricalPass : Evidence := ⟨0, .empirical, true⟩
def evidenceWrongClass : Evidence := ⟨0, .formal, true⟩
def evidenceFormalPass : Evidence := ⟨1, .formal, true⟩

theorem claim_empirical_wellFormed :
    claimEmpirical.wellFormed = true := by
  simp [claimEmpirical, Claim.wellFormed, requiresFalsifier, falsifierPeak]

theorem good_claim_supported :
    evalClaim claimEmpirical [] [evidenceEmpiricalPass] obsOk = .supported := by
  simp [evalClaim, claimEmpirical, Claim.wellFormed, requiresFalsifier, depJoin,
        anyFalsifier, Literal.matches, Observations.lookup, allSupport,
        Literal.satisfied, evidenceFor, classCompatible, falsifierPeak, supportN,
        obsOk, evidenceEmpiricalPass, atomPeak, atomN]

theorem falsified_claim_refuted :
    evalClaim claimEmpirical [] [evidenceEmpiricalPass] obsFalsified = .refuted := by
  simp [evalClaim, claimEmpirical, Claim.wellFormed, requiresFalsifier, depJoin,
        anyFalsifier, Literal.matches, Observations.lookup, allSupport,
        Literal.satisfied, evidenceFor, classCompatible, falsifierPeak, supportN,
        obsFalsified, evidenceEmpiricalPass, atomPeak, atomN]

theorem promotion_claim_open :
    evalClaim claimEmpirical [] [evidenceWrongClass] obsOk = .open_ := by
  simp [evalClaim, claimEmpirical, Claim.wellFormed, requiresFalsifier, depJoin,
        anyFalsifier, Literal.matches, Observations.lookup, allSupport,
        Literal.satisfied, evidenceFor, classCompatible, falsifierPeak, supportN,
        obsOk, evidenceWrongClass, atomPeak, atomN]

theorem incomplete_claim_open :
    evalClaim claimEmpirical [] [evidenceEmpiricalPass] obsIncomplete = .open_ := by
  simp [evalClaim, claimEmpirical, Claim.wellFormed, requiresFalsifier, depJoin,
        anyFalsifier, Literal.matches, Observations.lookup, allSupport,
        Literal.satisfied, evidenceFor, classCompatible, falsifierPeak, supportN,
        obsIncomplete, evidenceEmpiricalPass, atomPeak, atomN]

theorem dependent_reopens_when_premise_refuted :
    evalClaim claimFormalDep [.refuted] [evidenceFormalPass] obsOk = .open_ := by
  simp [evalClaim, claimFormalDep, Claim.wellFormed, requiresFalsifier, depJoin,
        anyFalsifier, evidenceFor, classCompatible, evidenceFormalPass, obsOk]

theorem dependent_supported_when_premise_supported :
    evalClaim claimFormalDep [.supported] [evidenceFormalPass] obsOk = .supported := by
  simp [evalClaim, claimFormalDep, Claim.wellFormed, requiresFalsifier, depJoin,
        anyFalsifier, evidenceFor, classCompatible, evidenceFormalPass, obsOk,
        allSupport]

theorem unfalsifiable_not_wellFormed :
    Claim.wellFormed ⟨2, .empirical, [], [], [supportN]⟩ = false := by
  simp [Claim.wellFormed, requiresFalsifier]

theorem empty_empirical_package_unsound_control :
    Package.structurallySound
      { claims := [⟨2, .empirical, [], [], [supportN]⟩]
        evidence := [evidenceEmpiricalPass]
        observations := obsOk } = false := by
  simp [Package.structurallySound, Package.idsUnique, Package.depsResolved, hasDup,
        Claim.wellFormed, requiresFalsifier, supportN]

theorem good_package_structurally_sound :
    Package.structurallySound
      { claims := [claimEmpirical]
        evidence := [evidenceEmpiricalPass]
        observations := obsOk } = true := by
  simp [Package.structurallySound, Package.idsUnique, Package.depsResolved, hasDup,
        Claim.wellFormed, requiresFalsifier, claimEmpirical, falsifierPeak]

end PCSEpistemic.Controls
