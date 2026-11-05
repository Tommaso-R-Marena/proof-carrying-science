import PCSCalibrationNumericRow00
import PCSCalibrationNumericRow01
import PCSCalibrationNumericRow02
import PCSCalibrationNumericRow03
import PCSCalibrationNumericRow04
import PCSCalibrationNumericRow05
import PCSCalibrationNumericRow06
import PCSCalibrationNumericRow07
import PCSCalibrationNumericRow08
import PCSCalibrationNumericRow09
import PCSCalibrationNumericRow10
import PCSCalibrationNumericRow11
import PCSCalibrationNumericRow12
import PCSCalibrationNumericRow13
import PCSCalibrationNumericRow14
import PCSCalibrationNumericRow15
import PCSCalibrationNumericRow16
import PCSCalibrationNumericRow17
import PCSCalibrationNumericRow18
import PCSCalibrationNumericRow19
import PCSCalibrationNumericRow20
import PCSCalibrationNumericRow21
import Mathlib.Tactic.FinCases
set_option autoImplicit false
set_option maxRecDepth 10000
set_option maxHeartbeats 1000000
open Finset
namespace PCSExperimentalCalibration
theorem all_heldout_least_squares_scores_exact : ∀ h d, lsLoss h d = lsSSE h d := by
  intro h d
  fin_cases h
  · exact least_squares_row_00 d
  · exact least_squares_row_01 d
  · exact least_squares_row_02 d
  · exact least_squares_row_03 d
  · exact least_squares_row_04 d
  · exact least_squares_row_05 d
  · exact least_squares_row_06 d
  · exact least_squares_row_07 d
  · exact least_squares_row_08 d
  · exact least_squares_row_09 d
  · exact least_squares_row_10 d
  · exact least_squares_row_11 d
  · exact least_squares_row_12 d
  · exact least_squares_row_13 d
  · exact least_squares_row_14 d
  · exact least_squares_row_15 d
  · exact least_squares_row_16 d
  · exact least_squares_row_17 d
  · exact least_squares_row_18 d
  · exact least_squares_row_19 d
  · exact least_squares_row_20 d
  · exact least_squares_row_21 d
theorem all_heldout_minimax_scores_exact : ∀ h d, mmLoss h d = mmSSE h d := by
  intro h d
  fin_cases h
  · exact minimax_row_00 d
  · exact minimax_row_01 d
  · exact minimax_row_02 d
  · exact minimax_row_03 d
  · exact minimax_row_04 d
  · exact minimax_row_05 d
  · exact minimax_row_06 d
  · exact minimax_row_07 d
  · exact minimax_row_08 d
  · exact minimax_row_09 d
  · exact minimax_row_10 d
  · exact minimax_row_11 d
  · exact minimax_row_12 d
  · exact minimax_row_13 d
  · exact minimax_row_14 d
  · exact minimax_row_15 d
  · exact minimax_row_16 d
  · exact minimax_row_17 d
  · exact minimax_row_18 d
  · exact minimax_row_19 d
  · exact minimax_row_20 d
  · exact minimax_row_21 d
theorem pooled_least_squares_scores_exact : ∀ d, (∑ h, lsSSE h d) = lsPooled d := by decide +kernel
theorem pooled_minimax_scores_exact : ∀ d, (∑ h, mmSSE h d) = mmPooled d := by decide +kernel
theorem all_minimax_gains_bounded_by_least_squares : ∀ d i, mmGain d i ≤ lsGain d i := by decide +kernel
theorem every_minimax_heldout_score_below_least_squares : ∀ h d, mmSSE h d < lsSSE h d := by decide +kernel
theorem degree_2_heldout_win_count_exact : (∑ h : Fin 22, if lsSSE h ⟨1, by decide⟩ < lsSSE h ⟨0, by decide⟩ then (1 : Nat) else 0) = 22 := by decide +kernel
theorem degree_3_heldout_win_count_exact : (∑ h : Fin 22, if lsSSE h ⟨2, by decide⟩ < lsSSE h ⟨1, by decide⟩ then (1 : Nat) else 0) = 22 := by decide +kernel
theorem every_full_data_class_exceeds_epsilon_0_01_budget : ∀ h d, (14 : ℚ) * (1/100)^2 < fullFloor h d := by decide +kernel
end PCSExperimentalCalibration
#print axioms PCSExperimentalCalibration.all_heldout_least_squares_scores_exact
#print axioms PCSExperimentalCalibration.all_heldout_minimax_scores_exact
#print axioms PCSExperimentalCalibration.pooled_least_squares_scores_exact
#print axioms PCSExperimentalCalibration.pooled_minimax_scores_exact
#print axioms PCSExperimentalCalibration.all_minimax_gains_bounded_by_least_squares
#print axioms PCSExperimentalCalibration.every_minimax_heldout_score_below_least_squares
#print axioms PCSExperimentalCalibration.degree_2_heldout_win_count_exact
#print axioms PCSExperimentalCalibration.degree_3_heldout_win_count_exact
#print axioms PCSExperimentalCalibration.every_full_data_class_exceeds_epsilon_0_01_budget
