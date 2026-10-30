import PCSCalibrationNumericData
set_option autoImplicit false
set_option maxRecDepth 10000
namespace PCSExperimentalCalibration
theorem least_squares_row_20 : ∀ d, lsLoss ⟨20, by decide⟩ d = lsSSE ⟨20, by decide⟩ d := by decide +kernel
theorem minimax_row_20 : ∀ d, mmLoss ⟨20, by decide⟩ d = mmSSE ⟨20, by decide⟩ d := by decide +kernel
end PCSExperimentalCalibration
#print axioms PCSExperimentalCalibration.least_squares_row_20
#print axioms PCSExperimentalCalibration.minimax_row_20
