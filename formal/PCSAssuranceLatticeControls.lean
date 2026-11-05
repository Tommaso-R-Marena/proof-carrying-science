import PCSAssuranceLattice

/-!
Executable positive/negative controls for the assurance lattice kernel.
These are ordinary-kernel `decide` certificates over finite literal packages.
-/
set_option autoImplicit false

namespace PCSAssuranceLatticeControls

open PCSAssuranceLattice

def goodPackage : Package :=
  { claims := [
      { id := 0, required := .provenance, artifactDeps := [10], premiseClaims := [] },
      { id := 1, required := .computational, artifactDeps := [11], premiseClaims := [0] },
      { id := 2, required := .formal, artifactDeps := [12], premiseClaims := [1] }],
    evidence := [
      { claimId := 0, stratum := .provenance, accepted := true },
      { claimId := 1, stratum := .computational, accepted := true },
      { claimId := 2, stratum := .formal, accepted := true }],
    bridges := [],
    changedArtifacts := [] }

theorem good_package_checks : check goodPackage = true := by decide

def silentFormalForgery : Package :=
  { claims := [
      { id := 0, required := .formal, artifactDeps := [1], premiseClaims := [] }],
    evidence := [
      { claimId := 0, stratum := .computational, accepted := true }],
    bridges := [],
    changedArtifacts := [] }

theorem silent_formal_forgery_rejected : check silentFormalForgery = false := by decide

def empiricalAsFormal : Package :=
  { claims := [
      { id := 0, required := .formal, artifactDeps := [1], premiseClaims := [] }],
    evidence := [
      { claimId := 0, stratum := .empirical, accepted := true }],
    bridges := [],
    changedArtifacts := [] }

theorem empirical_cannot_forge_formal : check empiricalAsFormal = false := by decide

def bridgedUpgrade : Package :=
  { claims := [
      { id := 0, required := .formal, artifactDeps := [1], premiseClaims := [] }],
    evidence := [
      { claimId := 0, stratum := .computational, accepted := true }],
    bridges := [
      { claimId := 0, fromStratum := .computational, toStratum := .formal, accepted := true }],
    changedArtifacts := [] }

theorem bridged_upgrade_accepted : check bridgedUpgrade = true := by decide

def invalidatedByChange : Package :=
  { claims := [
      { id := 0, required := .computational, artifactDeps := [7], premiseClaims := [] }],
    evidence := [
      { claimId := 0, stratum := .computational, accepted := true }],
    bridges := [],
    changedArtifacts := [7] }

theorem changed_artifact_invalidates : check invalidatedByChange = false := by decide

def missingPremise : Package :=
  { claims := [
      { id := 0, required := .computational, artifactDeps := [1], premiseClaims := [] },
      { id := 1, required := .formal, artifactDeps := [2], premiseClaims := [0] }],
    evidence := [
      -- Premise claim 0 has no accepted evidence.
      { claimId := 1, stratum := .formal, accepted := true }],
    bridges := [],
    changedArtifacts := [] }

theorem missing_premise_rejected : check missingPremise = false := by decide

def composedChain : Package :=
  { claims := [
      { id := 0, required := .provenance, artifactDeps := [1], premiseClaims := [] },
      { id := 1, required := .computational, artifactDeps := [2], premiseClaims := [0] }],
    evidence := [
      { claimId := 0, stratum := .provenance, accepted := true },
      { claimId := 1, stratum := .computational, accepted := true }],
    bridges := [],
    changedArtifacts := [] }

theorem composed_chain_accepted : check composedChain = true := by decide

end PCSAssuranceLatticeControls

#print axioms PCSAssuranceLatticeControls.good_package_checks
#print axioms PCSAssuranceLatticeControls.silent_formal_forgery_rejected
#print axioms PCSAssuranceLatticeControls.empirical_cannot_forge_formal
#print axioms PCSAssuranceLatticeControls.bridged_upgrade_accepted
#print axioms PCSAssuranceLatticeControls.changed_artifact_invalidates
#print axioms PCSAssuranceLatticeControls.missing_premise_rejected
#print axioms PCSAssuranceLatticeControls.composed_chain_accepted
