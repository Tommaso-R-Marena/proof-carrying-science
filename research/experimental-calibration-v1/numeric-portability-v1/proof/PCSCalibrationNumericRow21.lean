import PCSCalibrationNumericData
set_option autoImplicit false
set_option maxRecDepth 10000
namespace PCSExperimentalCalibration
theorem least_squares_row_21 : ∀ d, lsLoss ⟨21, by decide⟩ d = lsSSE ⟨21, by decide⟩ d := by decide +kernel
theorem minimax_row_21 : ∀ d, mmLoss ⟨21, by decide⟩ d = mmSSE ⟨21, by decide⟩ d := by decide +kernel
end PCSExperimentalCalibration
#print axioms PCSExperimentalCalibration.least_squares_row_21
#print axioms PCSExperimentalCalibration.minimax_row_21
