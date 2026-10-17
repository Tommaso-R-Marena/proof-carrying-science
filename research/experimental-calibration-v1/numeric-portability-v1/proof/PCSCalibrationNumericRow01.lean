import PCSCalibrationNumericData
set_option autoImplicit false
set_option maxRecDepth 10000
namespace PCSExperimentalCalibration
theorem least_squares_row_01 : ∀ d, lsLoss ⟨1, by decide⟩ d = lsSSE ⟨1, by decide⟩ d := by decide +kernel
theorem minimax_row_01 : ∀ d, mmLoss ⟨1, by decide⟩ d = mmSSE ⟨1, by decide⟩ d := by decide +kernel
end PCSExperimentalCalibration
#print axioms PCSExperimentalCalibration.least_squares_row_01
#print axioms PCSExperimentalCalibration.minimax_row_01
