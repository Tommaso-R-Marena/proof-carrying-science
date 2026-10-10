import PCSReferenceCertificates.Plan
namespace PCSDD
theorem counterexample_from_pipeline {t : CTask n} {lim : Limits} {ctx s c d : Nat} {m : Mgr}
  (h : pipeline t lim = .ok (.decided ctx s c d,m)) (hn : d ≠ 0) :
  (check t lim).decision = .counterexample := by
  unfold check
  rw [h]
  simp only [if_neg hn]
#print axioms counterexample_from_pipeline
end PCSDD
