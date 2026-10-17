import PCSCalibrationNumericData
set_option autoImplicit false
set_option maxRecDepth 10000
namespace PCSExperimentalCalibration
theorem least_squares_row_14 : ∀ d, lsLoss ⟨14, by decide⟩ d = lsSSE ⟨14, by decide⟩ d := by decide +kernel
theorem minimax_row_14 : ∀ d, mmLoss ⟨14, by decide⟩ d = mmSSE ⟨14, by decide⟩ d := by decide +kernel
end PCSExperimentalCalibration
#print axioms PCSExperimentalCalibration.least_squares_row_14
#print axioms PCSExperimentalCalibration.minimax_row_14
