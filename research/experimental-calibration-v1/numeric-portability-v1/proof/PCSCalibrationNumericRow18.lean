import PCSCalibrationNumericData
set_option autoImplicit false
set_option maxRecDepth 10000
namespace PCSExperimentalCalibration
theorem least_squares_row_18 : ∀ d, lsLoss ⟨18, by decide⟩ d = lsSSE ⟨18, by decide⟩ d := by decide +kernel
theorem minimax_row_18 : ∀ d, mmLoss ⟨18, by decide⟩ d = mmSSE ⟨18, by decide⟩ d := by decide +kernel
end PCSExperimentalCalibration
#print axioms PCSExperimentalCalibration.least_squares_row_18
#print axioms PCSExperimentalCalibration.minimax_row_18
