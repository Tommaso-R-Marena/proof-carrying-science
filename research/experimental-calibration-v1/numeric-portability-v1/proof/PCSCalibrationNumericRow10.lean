import PCSCalibrationNumericData
set_option autoImplicit false
set_option maxRecDepth 10000
namespace PCSExperimentalCalibration
theorem least_squares_row_10 : ∀ d, lsLoss ⟨10, by decide⟩ d = lsSSE ⟨10, by decide⟩ d := by decide +kernel
theorem minimax_row_10 : ∀ d, mmLoss ⟨10, by decide⟩ d = mmSSE ⟨10, by decide⟩ d := by decide +kernel
end PCSExperimentalCalibration
#print axioms PCSExperimentalCalibration.least_squares_row_10
#print axioms PCSExperimentalCalibration.minimax_row_10
