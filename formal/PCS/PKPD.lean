import PCS.Core

namespace PCS.PKPD

inductive Dimension
  | dimensionless
  | mass
  | volume
  | time
  | concentration
  | volumePerTime
  deriving DecidableEq, Repr

inductive Unit
  | one
  | mg | g
  | mL | L
  | min | h
  | mgPerL | gPerL
  | mLPerMin | LPerH
  deriving DecidableEq, Repr

def dimension : Unit → Dimension
  | Unit.one => Dimension.dimensionless
  | Unit.mg | Unit.g => Dimension.mass
  | Unit.mL | Unit.L => Dimension.volume
  | Unit.min | Unit.h => Dimension.time
  | Unit.mgPerL | Unit.gPerL => Dimension.concentration
  | Unit.mLPerMin | Unit.LPerH => Dimension.volumePerTime

def Compatible (u v : Unit) : Prop := dimension u = dimension v

structure OneCompartmentIVContract where
  doseUnit : Unit
  volumeUnit : Unit
  clearanceUnit : Unit
  timeUnit : Unit
  concentrationUnit : Unit
  doseIsMass : dimension doseUnit = Dimension.mass
  volumeIsVolume : dimension volumeUnit = Dimension.volume
  clearanceIsVolumePerTime : dimension clearanceUnit = Dimension.volumePerTime
  timeIsTime : dimension timeUnit = Dimension.time
  concentrationIsMassPerVolume : dimension concentrationUnit = Dimension.concentration

structure DirectEmaxContract where
  concentrationUnit : Unit
  ec50Unit : Unit
  effectUnit : Unit
  e0Unit : Unit
  emaxUnit : Unit
  ec50MatchesConcentration : Compatible ec50Unit concentrationUnit
  e0MatchesEffect : Compatible e0Unit effectUnit
  emaxMatchesEffect : Compatible emaxUnit effectUnit

example : Compatible Unit.mgPerL Unit.gPerL := by rfl
example : Compatible Unit.h Unit.min := by rfl

def canonicalPK : OneCompartmentIVContract where
  doseUnit := Unit.mg
  volumeUnit := Unit.L
  clearanceUnit := Unit.LPerH
  timeUnit := Unit.h
  concentrationUnit := Unit.mgPerL
  doseIsMass := rfl
  volumeIsVolume := rfl
  clearanceIsVolumePerTime := rfl
  timeIsTime := rfl
  concentrationIsMassPerVolume := rfl

def canonicalPD : DirectEmaxContract where
  concentrationUnit := Unit.mgPerL
  ec50Unit := Unit.mgPerL
  effectUnit := Unit.one
  e0Unit := Unit.one
  emaxUnit := Unit.one
  ec50MatchesConcentration := rfl
  e0MatchesEffect := rfl
  emaxMatchesEffect := rfl

theorem canonical_pk_units_valid :
    dimension canonicalPK.doseUnit = Dimension.mass ∧
    dimension canonicalPK.volumeUnit = Dimension.volume ∧
    dimension canonicalPK.clearanceUnit = Dimension.volumePerTime ∧
    dimension canonicalPK.timeUnit = Dimension.time ∧
    dimension canonicalPK.concentrationUnit = Dimension.concentration := by
  exact ⟨canonicalPK.doseIsMass,
    canonicalPK.volumeIsVolume,
    canonicalPK.clearanceIsVolumePerTime,
    canonicalPK.timeIsTime,
    canonicalPK.concentrationIsMassPerVolume⟩

theorem canonical_pd_units_valid :
    Compatible canonicalPD.ec50Unit canonicalPD.concentrationUnit ∧
    Compatible canonicalPD.e0Unit canonicalPD.effectUnit ∧
    Compatible canonicalPD.emaxUnit canonicalPD.effectUnit := by
  exact ⟨canonicalPD.ec50MatchesConcentration,
    canonicalPD.e0MatchesEffect,
    canonicalPD.emaxMatchesEffect⟩

end PCS.PKPD
