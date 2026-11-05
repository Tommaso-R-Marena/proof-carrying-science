import PCSCalibrationNumericData
set_option autoImplicit false
set_option maxRecDepth 10000
namespace PCSExperimentalCalibration
theorem least_squares_row_07 : ∀ d, lsLoss ⟨7, by decide⟩ d = lsSSE ⟨7, by decide⟩ d := by decide +kernel
theorem minimax_row_07 : ∀ d, mmLoss ⟨7, by decide⟩ d = mmSSE ⟨7, by decide⟩ d := by decide +kernel
end PCSExperimentalCalibration
#print axioms PCSExperimentalCalibration.least_squares_row_07
#print axioms PCSExperimentalCalibration.minimax_row_07
