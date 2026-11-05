import PCSCalibrationNumericData
set_option autoImplicit false
set_option maxRecDepth 10000
namespace PCSExperimentalCalibration
theorem least_squares_row_12 : ∀ d, lsLoss ⟨12, by decide⟩ d = lsSSE ⟨12, by decide⟩ d := by decide +kernel
theorem minimax_row_12 : ∀ d, mmLoss ⟨12, by decide⟩ d = mmSSE ⟨12, by decide⟩ d := by decide +kernel
end PCSExperimentalCalibration
#print axioms PCSExperimentalCalibration.least_squares_row_12
#print axioms PCSExperimentalCalibration.minimax_row_12
