import PCSCalibrationNumericData
set_option autoImplicit false
set_option maxRecDepth 10000
namespace PCSExperimentalCalibration
theorem least_squares_row_11 : ∀ d, lsLoss ⟨11, by decide⟩ d = lsSSE ⟨11, by decide⟩ d := by decide +kernel
theorem minimax_row_11 : ∀ d, mmLoss ⟨11, by decide⟩ d = mmSSE ⟨11, by decide⟩ d := by decide +kernel
end PCSExperimentalCalibration
#print axioms PCSExperimentalCalibration.least_squares_row_11
#print axioms PCSExperimentalCalibration.minimax_row_11
