import PCSCalibrationNumericData
set_option autoImplicit false
set_option maxRecDepth 10000
namespace PCSExperimentalCalibration
theorem least_squares_row_17 : ∀ d, lsLoss ⟨17, by decide⟩ d = lsSSE ⟨17, by decide⟩ d := by decide +kernel
theorem minimax_row_17 : ∀ d, mmLoss ⟨17, by decide⟩ d = mmSSE ⟨17, by decide⟩ d := by decide +kernel
end PCSExperimentalCalibration
#print axioms PCSExperimentalCalibration.least_squares_row_17
#print axioms PCSExperimentalCalibration.minimax_row_17
