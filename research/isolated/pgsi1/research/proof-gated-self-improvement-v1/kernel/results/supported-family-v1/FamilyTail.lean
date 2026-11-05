import PGSI1Bridge

namespace PCS.Research.SupportedCounterexampleFamily
open PCS.V2

def old (k : Int) : ProofGatedSelfImprovement.Neuron := ⟨true,k,4⟩
def candidate (k : Int) : ProofGatedSelfImprovement.Neuron := ⟨true,k+1,2-k⟩

theorem every_tail_input_worsens (k x : Int) (hk : 18 ≤ k) (hx : k+3 ≤ x) :
    (ProofGatedSelfImprovement.predict (old k) x - ProofGatedSelfImprovement.target x).natAbs <
    (ProofGatedSelfImprovement.predict (candidate k) x - ProofGatedSelfImprovement.target x).natAbs := by
  have hx0 : 0 ≤ x := by omega
  have hk0 : 0 ≤ k := by omega
  have hmul := Int.mul_le_mul_of_nonneg_right hk hx0
  have hmulk := Int.mul_le_mul_of_nonneg_left (by omega : 1 ≤ x) hk0
  have ha : 0 ≤ k*x+4 := by omega
  have hb : 0 ≤ (k+1)*x+(2-k) := by rw [Int.add_mul]; omega
  have ht : 0 ≤ 2*x+1 := by omega
  have ho : ProofGatedSelfImprovement.predict (old k) x - ProofGatedSelfImprovement.target x = (k-2)*x+3 := by
    simp only [old, ProofGatedSelfImprovement.predict, ↓reduceIte,
      ProofGatedSelfImprovement.target, ProofGatedSelfImprovement.relu, Int.max_def]
    simp [ha,ht]
    rw [Int.sub_mul]
    omega
  have hn : ProofGatedSelfImprovement.predict (candidate k) x - ProofGatedSelfImprovement.target x = (k-1)*(x-1) := by
    simp only [candidate, ProofGatedSelfImprovement.predict, ↓reduceIte,
      ProofGatedSelfImprovement.target, ProofGatedSelfImprovement.relu, Int.max_def]
    simp [hb,ht]
    simp only [Int.add_mul,Int.sub_mul,Int.mul_sub,Int.one_mul,Int.mul_one]
    omega
  have hnonnegative := Int.mul_nonneg (by omega : 0 ≤ k-1) (by omega : 0 ≤ x-1)
  have ho0 : 0 ≤ ProofGatedSelfImprovement.predict (old k) x - ProofGatedSelfImprovement.target x := by
    rw [ho,Int.sub_mul]
    omega
  have hn0 : 0 ≤ ProofGatedSelfImprovement.predict (candidate k) x - ProofGatedSelfImprovement.target x := by
    rw [hn]
    exact hnonnegative
  have hop := Int.natAbs_of_nonneg ho0
  have hnp := Int.natAbs_of_nonneg hn0
  simp only [Int.sub_mul,Int.mul_sub,Int.one_mul,Int.mul_one] at ho hn
  omega

#print axioms every_tail_input_worsens
end PCS.Research.SupportedCounterexampleFamily
