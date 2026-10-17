import PCSCalibrationNumericData
set_option autoImplicit false
set_option maxRecDepth 10000
namespace PCSExperimentalCalibration
theorem least_squares_row_06 : ∀ d, lsLoss ⟨6, by decide⟩ d = lsSSE ⟨6, by decide⟩ d := by decide +kernel
theorem minimax_row_06 : ∀ d, mmLoss ⟨6, by decide⟩ d = mmSSE ⟨6, by decide⟩ d := by decide +kernel
end PCSExperimentalCalibration
#print axioms PCSExperimentalCalibration.least_squares_row_06
#print axioms PCSExperimentalCalibration.minimax_row_06
