import PCSCalibrationNumericData
set_option autoImplicit false
set_option maxRecDepth 10000
namespace PCSExperimentalCalibration
theorem least_squares_row_03 : ∀ d, lsLoss ⟨3, by decide⟩ d = lsSSE ⟨3, by decide⟩ d := by decide +kernel
theorem minimax_row_03 : ∀ d, mmLoss ⟨3, by decide⟩ d = mmSSE ⟨3, by decide⟩ d := by decide +kernel
end PCSExperimentalCalibration
#print axioms PCSExperimentalCalibration.least_squares_row_03
#print axioms PCSExperimentalCalibration.minimax_row_03
