import PGSI1Bridge

namespace PCS.Research.SupportedTailCounterexample
open PCS.V2

def old : ProofGatedSelfImprovement.Neuron := ⟨true,31,4⟩
def candidate : ProofGatedSelfImprovement.Neuron := ⟨true,32,-29⟩

theorem concrete_errors :
    (ProofGatedSelfImprovement.predict old 34 - ProofGatedSelfImprovement.target 34).natAbs = 989 ∧
    (ProofGatedSelfImprovement.predict candidate 34 - ProofGatedSelfImprovement.target 34).natAbs = 990 := by decide

theorem every_tail_input_worsens (x : Int) (hx : 34 ≤ x) :
    (ProofGatedSelfImprovement.predict old x - ProofGatedSelfImprovement.target x).natAbs <
    (ProofGatedSelfImprovement.predict candidate x - ProofGatedSelfImprovement.target x).natAbs := by
  have ha : 0 ≤ 31*x+4 := by omega
  have ht : 0 ≤ 2*x+1 := by omega
  have ho : ProofGatedSelfImprovement.predict old x - ProofGatedSelfImprovement.target x = 29*x+3 := by
    simp only [old, ProofGatedSelfImprovement.predict, ↓reduceIte,
      ProofGatedSelfImprovement.target, ProofGatedSelfImprovement.relu, Int.max_def]
    simp [ha, ht]
    omega
  have hn : ProofGatedSelfImprovement.predict candidate x - ProofGatedSelfImprovement.target x = 30*x-30 := by
    simp only [candidate, ProofGatedSelfImprovement.predict, ↓reduceIte,
      ProofGatedSelfImprovement.target, ProofGatedSelfImprovement.relu, Int.max_def]
    have hb' : 0 ≤ 32*x + (-29) := by omega
    simp [hb', ht]
    omega
  have hp := Int.natAbs_of_nonneg (by omega : 0 ≤ ProofGatedSelfImprovement.predict old x - ProofGatedSelfImprovement.target x)
  have hq := Int.natAbs_of_nonneg (by omega : 0 ≤ ProofGatedSelfImprovement.predict candidate x - ProofGatedSelfImprovement.target x)
  omega

#print axioms concrete_errors
#print axioms every_tail_input_worsens
end PCS.Research.SupportedTailCounterexample
