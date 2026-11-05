import RequestProject.AION.Checker
import RequestProject.AION.PathSemantics
import RequestProject.AION.NegativeResults
import RequestProject.AION.Examples.BirthDeath
import RequestProject.AION.Examples.BDcert
import RequestProject.AION.Examples.GeneCert
import RequestProject.AION.Examples.XYsmall
import RequestProject.AION.Examples.XYmain

/-! Axiom audit of every headline theorem.  Expected output: only `propext`,
`Classical.choice`, `Quot.sound`; the four concrete certificate theorems
additionally use `Lean.ofReduceBool` / `Lean.trustCompiler` (from `native_decide`,
i.e. they trust the Lean compiler to evaluate the verified checker). -/

-- generic theory (no computation trusted)
#print axioms AION.JumpModel.hitProb_le_of_supersolution
#print axioms AION.JumpModel.le_hitProb_of_subsolution
#print axioms AION.JumpModel.sandwich
#print axioms AION.JumpModel.relative_error_of_sandwich
#print axioms AION.JumpModel.expectedJumps_le
#print axioms AION.JumpModel.expectedTime_le
#print axioms AION.JumpModel.hitProb_harmonic
#print axioms AION.JumpModel.max_principle
#print axioms AION.JumpModel.relative_error_transfer_upper
#print axioms AION.JumpModel.relative_error_transfer_lower
#print axioms AION.JumpModel.gen_le_of_le_on_jumps
#print axioms AION.JumpModel.gen_min_nonpos
#print axioms AION.JumpModel.union_barrier
#print axioms AION.JumpModel.compositional_union_bound
#print axioms AION.AffineFamily.robust_supersolution
#print axioms AION.JumpModel.hitN_eq_path_sum
#print axioms AION.JumpModel.sum_pathWeight
-- reaction networks, exponential tails, verified checker
#print axioms AION.MACRN.next_add_inp
#print axioms AION.MACRN.genQ_expBar
#print axioms AION.descFactorial_add_vandermonde
#print axioms AION.MACRN.cellCheck_sound
#print axioms AION.MACRN.checkUpper_sound
#print axioms AION.MACRN.checkLower_sound
-- examples and negative results
#print axioms AION.Examples.BirthDeath.bd_exact
#print axioms AION.NegativeResults.escape_certificate_necessary
#print axioms AION.NegativeResults.gen_mul
#print axioms AION.NegativeResults.leibniz_fails
#print axioms AION.NegativeResults.mm1_hits_surely
-- concrete certificates (native_decide)
#print axioms AION.Examples.BDcert.sandwich
#print axioms AION.Examples.GeneCert.sandwich
#print axioms AION.Examples.XYsmall.sandwich
#print axioms AION.Examples.XYmain.sandwich
