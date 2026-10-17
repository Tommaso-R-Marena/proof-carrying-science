import PCSCalibrationNumericData
set_option autoImplicit false
set_option maxRecDepth 10000
namespace PCSExperimentalCalibration
theorem least_squares_row_05 : ∀ d, lsLoss ⟨5, by decide⟩ d = lsSSE ⟨5, by decide⟩ d := by decide +kernel
theorem minimax_row_05 : ∀ d, mmLoss ⟨5, by decide⟩ d = mmSSE ⟨5, by decide⟩ d := by decide +kernel
end PCSExperimentalCalibration
#print axioms PCSExperimentalCalibration.least_squares_row_05
#print axioms PCSExperimentalCalibration.minimax_row_05
