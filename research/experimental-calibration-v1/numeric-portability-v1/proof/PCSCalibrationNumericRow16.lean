import PCSCalibrationNumericData
set_option autoImplicit false
set_option maxRecDepth 10000
namespace PCSExperimentalCalibration
theorem least_squares_row_16 : ∀ d, lsLoss ⟨16, by decide⟩ d = lsSSE ⟨16, by decide⟩ d := by decide +kernel
theorem minimax_row_16 : ∀ d, mmLoss ⟨16, by decide⟩ d = mmSSE ⟨16, by decide⟩ d := by decide +kernel
end PCSExperimentalCalibration
#print axioms PCSExperimentalCalibration.least_squares_row_16
#print axioms PCSExperimentalCalibration.minimax_row_16
