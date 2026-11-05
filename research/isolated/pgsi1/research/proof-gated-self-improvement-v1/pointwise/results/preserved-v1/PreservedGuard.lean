import Pointwise
import Controls

/-! Add the new invariant without deleting any guarantee of the prior guard. -/
namespace PCS.Research.PreservedPointwiseGuard
open IntegerAffine PGSI1Bridge

structure Case where
  prior : GuardCase
  dominance : List Row

def accepts (c : Case) : Bool :=
  checkGuardCase c.prior && Pointwise.accept (embed c.prior.old) (embed c.prior.new)
    targetNet c.dominance

theorem accepts_sound (c : Case) (h : accepts c = true) :
    GuardMeaning c.prior ∧ Pointwise.Dominates (embed c.prior.old) (embed c.prior.new) targetNet := by
  have hp : checkGuardCase c.prior = true ∧
      Pointwise.accept (embed c.prior.old) (embed c.prior.new) targetNet c.dominance = true := by
    simpa only [accepts, Bool.and_eq_true] using h
  exact ⟨checkGuardCase_sound c.prior hp.1, Pointwise.accept_sound _ _ _ _ hp.2⟩

open KernelControls
def first : Case := ⟨⟨zero,middle,firstRows,zeroRows,middleRows,-20,20,41,20,20,20,-1⟩, firstRows⟩
def second : Case := ⟨⟨middle,final,secondRows,middleRows,finalRows,-20,20,20,0,20,-20,-1⟩, secondRows⟩

theorem first_update : accepts first = true := by decide
theorem second_update : accepts second = true := by decide

#print axioms accepts_sound
#print axioms first_update
#print axioms second_update
end PCS.Research.PreservedPointwiseGuard
