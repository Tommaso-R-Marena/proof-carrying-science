import Progress
namespace PCSProgressData
def spec : PCSProgress.Spec := ⟨⟨[0],[0,1,2,3,4],[⟨0,0,0⟩,⟨0,0,1⟩,⟨0,1,5⟩,⟨0,5,0⟩,⟨1,1,2⟩,⟨1,5,5⟩,⟨2,2,3⟩,⟨2,3,4⟩,⟨2,3,5⟩,⟨2,5,5⟩,⟨3,3,4⟩,⟨3,5,5⟩,⟨4,4,4⟩,⟨4,5,5⟩,⟨5,4,5⟩],[(1,1),(2,2),(3,3)],[5]⟩,[4],[(1,3),(2,2),(3,1),(4,0)]⟩
theorem certificate_checked : PCSProgress.check spec = true := by decide
theorem winning : ∀ s ∈ PCSProgress.region spec, PCSProgress.CanForce spec.base spec.goals (PCSProgress.rank spec s) s := PCSProgress.winning_can_force certificate_checked
theorem losing {s : Nat} (h : s ∉ PCSProgress.region spec) : ∀ n, ¬ PCSProgress.CanForce spec.base spec.goals n s := PCSProgress.losing_no_finite_bound certificate_checked h
end PCSProgressData

#print axioms PCSProgressData.certificate_checked
#print axioms PCSProgressData.winning
#print axioms PCSProgressData.losing
