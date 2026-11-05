import PCSCalibrationNumericData
set_option autoImplicit false
set_option maxRecDepth 10000
namespace PCSExperimentalCalibration
theorem least_squares_row_04 : ∀ d, lsLoss ⟨4, by decide⟩ d = lsSSE ⟨4, by decide⟩ d := by decide +kernel
theorem minimax_row_04 : ∀ d, mmLoss ⟨4, by decide⟩ d = mmSSE ⟨4, by decide⟩ d := by decide +kernel
end PCSExperimentalCalibration
#print axioms PCSExperimentalCalibration.least_squares_row_04
#print axioms PCSExperimentalCalibration.minimax_row_04
