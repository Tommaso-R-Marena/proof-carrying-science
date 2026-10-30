import PCSCalibrationNumericData
set_option autoImplicit false
set_option maxRecDepth 10000
namespace PCSExperimentalCalibration
theorem least_squares_row_02 : ∀ d, lsLoss ⟨2, by decide⟩ d = lsSSE ⟨2, by decide⟩ d := by decide +kernel
theorem minimax_row_02 : ∀ d, mmLoss ⟨2, by decide⟩ d = mmSSE ⟨2, by decide⟩ d := by decide +kernel
end PCSExperimentalCalibration
#print axioms PCSExperimentalCalibration.least_squares_row_02
#print axioms PCSExperimentalCalibration.minimax_row_02
