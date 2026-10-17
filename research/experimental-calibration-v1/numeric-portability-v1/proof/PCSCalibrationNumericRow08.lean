import PCSCalibrationNumericData
set_option autoImplicit false
set_option maxRecDepth 10000
namespace PCSExperimentalCalibration
theorem least_squares_row_08 : ∀ d, lsLoss ⟨8, by decide⟩ d = lsSSE ⟨8, by decide⟩ d := by decide +kernel
theorem minimax_row_08 : ∀ d, mmLoss ⟨8, by decide⟩ d = mmSSE ⟨8, by decide⟩ d := by decide +kernel
end PCSExperimentalCalibration
#print axioms PCSExperimentalCalibration.least_squares_row_08
#print axioms PCSExperimentalCalibration.minimax_row_08
