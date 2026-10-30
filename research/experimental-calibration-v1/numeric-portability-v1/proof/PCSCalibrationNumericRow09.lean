import PCSCalibrationNumericData
set_option autoImplicit false
set_option maxRecDepth 10000
namespace PCSExperimentalCalibration
theorem least_squares_row_09 : ∀ d, lsLoss ⟨9, by decide⟩ d = lsSSE ⟨9, by decide⟩ d := by decide +kernel
theorem minimax_row_09 : ∀ d, mmLoss ⟨9, by decide⟩ d = mmSSE ⟨9, by decide⟩ d := by decide +kernel
end PCSExperimentalCalibration
#print axioms PCSExperimentalCalibration.least_squares_row_09
#print axioms PCSExperimentalCalibration.minimax_row_09
