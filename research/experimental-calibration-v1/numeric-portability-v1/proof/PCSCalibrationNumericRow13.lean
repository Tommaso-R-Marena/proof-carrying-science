import PCSCalibrationNumericData
set_option autoImplicit false
set_option maxRecDepth 10000
namespace PCSExperimentalCalibration
theorem least_squares_row_13 : ∀ d, lsLoss ⟨13, by decide⟩ d = lsSSE ⟨13, by decide⟩ d := by decide +kernel
theorem minimax_row_13 : ∀ d, mmLoss ⟨13, by decide⟩ d = mmSSE ⟨13, by decide⟩ d := by decide +kernel
end PCSExperimentalCalibration
#print axioms PCSExperimentalCalibration.least_squares_row_13
#print axioms PCSExperimentalCalibration.minimax_row_13
