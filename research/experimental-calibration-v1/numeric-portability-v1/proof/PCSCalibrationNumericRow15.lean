import PCSCalibrationNumericData
set_option autoImplicit false
set_option maxRecDepth 10000
namespace PCSExperimentalCalibration
theorem least_squares_row_15 : ∀ d, lsLoss ⟨15, by decide⟩ d = lsSSE ⟨15, by decide⟩ d := by decide +kernel
theorem minimax_row_15 : ∀ d, mmLoss ⟨15, by decide⟩ d = mmSSE ⟨15, by decide⟩ d := by decide +kernel
end PCSExperimentalCalibration
#print axioms PCSExperimentalCalibration.least_squares_row_15
#print axioms PCSExperimentalCalibration.minimax_row_15
