import PCSCalibrationNumericData
set_option autoImplicit false
set_option maxRecDepth 10000
namespace PCSExperimentalCalibration
theorem least_squares_row_00 : ∀ d, lsLoss ⟨0, by decide⟩ d = lsSSE ⟨0, by decide⟩ d := by decide +kernel
theorem minimax_row_00 : ∀ d, mmLoss ⟨0, by decide⟩ d = mmSSE ⟨0, by decide⟩ d := by decide +kernel
end PCSExperimentalCalibration
#print axioms PCSExperimentalCalibration.least_squares_row_00
#print axioms PCSExperimentalCalibration.minimax_row_00
