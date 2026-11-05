import PGSI1Bridge
set_option maxRecDepth 10000
set_option maxHeartbeats 20000000
open PCS.Research.IntegerAffine PCS.Research.PGSI1Bridge
namespace PCS.Research.GuardReplay
def cases : List GuardCase := [
(⟨⟨true,(31 : Int),(4 : Int)⟩,⟨true,(32 : Int),(-29 : Int)⟩,[⟨⟨none,(some (-1 : Int))⟩,⟨(0 : Int),(0 : Int)⟩,⟨(0 : Int),(0 : Int)⟩,⟨(0 : Int),(0 : Int)⟩⟩,⟨⟨(some (0 : Int)),(some (0 : Int))⟩,⟨(31 : Int),(4 : Int)⟩,⟨(0 : Int),(0 : Int)⟩,⟨(2 : Int),(1 : Int)⟩⟩,⟨⟨(some (1 : Int)),none⟩,⟨(31 : Int),(4 : Int)⟩,⟨(32 : Int),(-29 : Int)⟩,⟨(2 : Int),(1 : Int)⟩⟩],[⟨⟨none,(some (-1 : Int))⟩,⟨(0 : Int),(0 : Int)⟩,⟨(0 : Int),(0 : Int)⟩,⟨0,0⟩⟩,⟨⟨(some (0 : Int)),none⟩,⟨(31 : Int),(4 : Int)⟩,⟨(2 : Int),(1 : Int)⟩,⟨0,0⟩⟩],[⟨⟨none,(some (-1 : Int))⟩,⟨(0 : Int),(0 : Int)⟩,⟨(0 : Int),(0 : Int)⟩,⟨0,0⟩⟩,⟨⟨(some (0 : Int)),(some (0 : Int))⟩,⟨(0 : Int),(0 : Int)⟩,⟨(2 : Int),(1 : Int)⟩,⟨0,0⟩⟩,⟨⟨(some (1 : Int)),none⟩,⟨(32 : Int),(-29 : Int)⟩,⟨(2 : Int),(1 : Int)⟩,⟨0,0⟩⟩],(-20 : Int),(20 : Int),583,570,(20 : Int),(20 : Int),(-1 : Int)⟩ : GuardCase)]
theorem checked : cases.all checkGuardCase = true := by decide
theorem cases_sound : ∀ c ∈ cases, GuardMeaning c := checkGuardBatch_sound cases checked
#print axioms cases_sound
end PCS.Research.GuardReplay
