import PCSCalibrationNumericData
set_option autoImplicit false
set_option maxRecDepth 10000
namespace PCSExperimentalCalibration
theorem least_squares_row_19 : ∀ d, lsLoss ⟨19, by decide⟩ d = lsSSE ⟨19, by decide⟩ d := by decide +kernel
theorem minimax_row_19 : ∀ d, mmLoss ⟨19, by decide⟩ d = mmSSE ⟨19, by decide⟩ d := by decide +kernel
end PCSExperimentalCalibration
#print axioms PCSExperimentalCalibration.least_squares_row_19
#print axioms PCSExperimentalCalibration.minimax_row_19
