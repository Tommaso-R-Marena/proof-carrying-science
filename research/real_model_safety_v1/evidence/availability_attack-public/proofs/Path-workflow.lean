import Data
open PCSProgress PCSProgressData
namespace CapturedPath
theorem path : Path spec 3 0 4 := by
  apply Path.cons ⟨0,0,1⟩ rfl (by decide) (by decide)
  apply Path.cons ⟨1,1,3⟩ rfl (by decide) (by decide)
  apply Path.cons ⟨3,3,4⟩ rfl (by decide) (by decide)
  exact Path.nil 4
theorem bounded : rank spec 4 + 3 ≤ rank spec 0 :=
  (path_bound certificate_checked path (by decide)).2
theorem completed : 4 ∈ spec.goals ∧ 4 ∈ spec.base.safe := by decide
end CapturedPath
#print axioms CapturedPath.path
#print axioms CapturedPath.bounded
#print axioms CapturedPath.completed
