import PGSI1Bridge

namespace PCS.Research.KernelControls
open IntegerAffine PGSI1Bridge
open PCS.V2

def zero : ProofGatedSelfImprovement.Neuron := ⟨true,0,0⟩
def middle : ProofGatedSelfImprovement.Neuron := ⟨true,1,1⟩
def final : ProofGatedSelfImprovement.Neuron := ⟨true,2,1⟩
def firstRows : List Row := [⟨⟨none,(some (-1 : Int))⟩,⟨(0 : Int),(0 : Int)⟩,⟨(0 : Int),(0 : Int)⟩,⟨(0 : Int),(0 : Int)⟩⟩,⟨⟨(some (0 : Int)),none⟩,⟨(0 : Int),(0 : Int)⟩,⟨(1 : Int),(1 : Int)⟩,⟨(2 : Int),(1 : Int)⟩⟩]
def secondRows : List Row := [⟨⟨none,(some (-1 : Int))⟩,⟨(0 : Int),(0 : Int)⟩,⟨(0 : Int),(0 : Int)⟩,⟨(0 : Int),(0 : Int)⟩⟩,⟨⟨(some (0 : Int)),none⟩,⟨(1 : Int),(1 : Int)⟩,⟨(2 : Int),(1 : Int)⟩,⟨(2 : Int),(1 : Int)⟩⟩]
def zeroRows : List Row := [⟨⟨none,(some (-1 : Int))⟩,⟨(0 : Int),(0 : Int)⟩,⟨(0 : Int),(0 : Int)⟩,⟨0,0⟩⟩,⟨⟨(some (0 : Int)),none⟩,⟨(0 : Int),(0 : Int)⟩,⟨(2 : Int),(1 : Int)⟩,⟨0,0⟩⟩]
def middleRows : List Row := [⟨⟨none,(some (-1 : Int))⟩,⟨(0 : Int),(0 : Int)⟩,⟨(0 : Int),(0 : Int)⟩,⟨0,0⟩⟩,⟨⟨(some (0 : Int)),none⟩,⟨(1 : Int),(1 : Int)⟩,⟨(2 : Int),(1 : Int)⟩,⟨0,0⟩⟩]
def finalRows : List Row := [⟨⟨none,(some (-1 : Int))⟩,⟨(0 : Int),(0 : Int)⟩,⟨(0 : Int),(0 : Int)⟩,⟨0,0⟩⟩,⟨⟨(some (0 : Int)),none⟩,⟨(2 : Int),(1 : Int)⟩,⟨(2 : Int),(1 : Int)⟩,⟨0,0⟩⟩]

theorem first_guard : guardAccept zero middle firstRows zeroRows middleRows
    (-20) 20 41 20 20 20 (-1) = true := by decide

theorem second_guard : guardAccept middle final secondRows middleRows finalRows
    (-20) 20 20 0 20 (-20) (-1) = true := by decide

theorem first_universal_preservation : ∀ x : Int,
    ProofGatedSelfImprovement.correct zero x → ProofGatedSelfImprovement.correct middle x :=
  (guardAccept_sound zero middle firstRows zeroRows middleRows
    (-20) 20 41 20 20 20 (-1) first_guard).2.1

theorem second_universal_preservation : ∀ x : Int,
    ProofGatedSelfImprovement.correct middle x → ProofGatedSelfImprovement.correct final x :=
  (guardAccept_sound middle final secondRows middleRows finalRows
    (-20) 20 20 0 20 (-20) (-1) second_guard).2.1

-- A nonvacuous universal-preservation + perfect-window certificate still
-- permits deterioration beyond the chosen window. This is a proved negative
-- result about the stated conditions, not authorization of this wider model.
def oldNet : Net := ⟨[],0⟩
def farNet : Net := ⟨[⟨1,2,1⟩,⟨10,1,-21⟩],0⟩
def farPreservesRows : List Row := [⟨⟨none,(some (-1 : Int))⟩,⟨(0 : Int),(0 : Int)⟩,⟨(0 : Int),(0 : Int)⟩,⟨(0 : Int),(0 : Int)⟩⟩,⟨⟨(some (0 : Int)),(some (21 : Int))⟩,⟨(0 : Int),(0 : Int)⟩,⟨(2 : Int),(1 : Int)⟩,⟨(2 : Int),(1 : Int)⟩⟩,⟨⟨(some (22 : Int)),none⟩,⟨(0 : Int),(0 : Int)⟩,⟨(12 : Int),(-209 : Int)⟩,⟨(2 : Int),(1 : Int)⟩⟩]
def farMaxRows : List Row := [⟨⟨none,(some (-1 : Int))⟩,⟨(0 : Int),(0 : Int)⟩,⟨(0 : Int),(0 : Int)⟩,⟨0,0⟩⟩,⟨⟨(some (0 : Int)),(some (21 : Int))⟩,⟨(2 : Int),(1 : Int)⟩,⟨(2 : Int),(1 : Int)⟩,⟨0,0⟩⟩,⟨⟨(some (22 : Int)),none⟩,⟨(12 : Int),(-209 : Int)⟩,⟨(2 : Int),(1 : Int)⟩,⟨0,0⟩⟩]

theorem far_nonvacuous : acceptNonvacuous oldNet farNet targetNet farPreservesRows (-1) = true := by decide
theorem far_perfect_window : acceptMaximum farNet targetNet farMaxRows (-20) 20 0 (-20) = true := by decide

theorem far_preserves_all_integers : ∀ x : Int,
    predict oldNet x = predict targetNet x → predict farNet x = predict targetNet x :=
  (acceptNonvacuous_sound oldNet farNet targetNet farPreservesRows (-1) far_nonvacuous).1

theorem far_correct_witness : predict oldNet (-1) = predict targetNet (-1) :=
  (acceptNonvacuous_sound oldNet farNet targetNet farPreservesRows (-1) far_nonvacuous).2

theorem far_error_worsens :
    (predict oldNet 32 - predict targetNet 32).natAbs = 65 ∧
    (predict farNet 32 - predict targetNet 32).natAbs = 110 := by decide

end PCS.Research.KernelControls
