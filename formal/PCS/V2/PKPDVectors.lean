import PCS.V2.PKPDCheck

/-!
Executable vectors for the verified PK/PD checker (`PCS.V2.PKPDCheck`).  These are tests,
not proofs; the correctness theorems are `pkpdContractRun_sound`, `pkpdMatchRun_sound`,
`pkpdPeakRun_sound`, and (real-valued) `PCSReal.PKPD.expEncl_sound` /
`pcs_pkpd_reference_match_real`.
-/

namespace PCS.V2.PKPDVectors

open PCS.V2.PKPDCheck

-- strict decimals
#guard decimalQ "1.5e-3" == some (3 / 2000)
#guard decimalQ "-02.50" == some (-5 / 2)
#guard decimalQ "1e400" == some ((10 ^ 400 : Nat) : Rat)
#guard decimalQ "1e401" == none
#guard decimalQ ".5" == none
#guard decimalQ "5." == none
#guard decimalQ "+1" == none
#guard decimalQ " 1" == none
#guard decimalQ "NaN" == none
#guard decimalQ "1_0" == none

-- unit scales
#guard unitInfo "mg/L" == some (⟨1, -3, 0, 0⟩, 1 / 1000)
#guard unitInfo "L/h" == some (⟨0, 3, -1, 0⟩, 1 / 3600000)
#guard unitInfo "" == none

-- exp enclosure: exact at 0, tight around e^-1 = 0.3678794411714423215955...
#guard expEncl 0 == some (1, 1)
#guard match expEncl (-1) with
  | some (lo, hi) => decide (lo ≤ 367879441171442322 / 1000000000000000000 ∧
      367879441171442321 / 1000000000000000000 ≤ hi ∧ hi - lo ≤ 1 / 10 ^ 40)
  | none => false
#guard match expEncl (-50) with
  | some (lo, hi) => decide (0 < lo ∧ lo ≤ hi ∧ hi - lo ≤ hi / 10 ^ 30)
  | none => false

-- model contract
#guard (decodeModel "{\"model_type\":\"one_compartment_iv_bolus\",\"dose\":{\"value\":100.0,\"unit\":\"mg\"},\"volume\":{\"value\":10,\"unit\":\"L\"},\"clearance\":{\"value\":1,\"unit\":\"L/h\"},\"time_unit\":\"h\",\"concentration_unit\":\"mg/L\"}".toUTF8.data.toList).isSome
#guard (decodeModel "{\"model_type\":\"one_compartment_iv_bolus\",\"dose\":{\"value\":0,\"unit\":\"mg\"},\"volume\":{\"value\":10,\"unit\":\"L\"},\"clearance\":{\"value\":1,\"unit\":\"L/h\"},\"time_unit\":\"h\",\"concentration_unit\":\"mg/L\"}".toUTF8.data.toList).isNone
#guard (decodeModel "{\"model_type\":\"one_compartment_iv_bolus\",\"dose\":{\"value\":100,\"unit\":\"L\"},\"volume\":{\"value\":10,\"unit\":\"L\"},\"clearance\":{\"value\":1,\"unit\":\"L/h\"},\"time_unit\":\"h\",\"concentration_unit\":\"mg/L\"}".toUTF8.data.toList).isNone

-- committed-table concentration threshold
#guard modelConcentrationUnit "{\"model_type\":\"one_compartment_iv_bolus\",\"dose\":{\"value\":100,\"unit\":\"mg\"},\"volume\":{\"value\":10,\"unit\":\"L\"},\"clearance\":{\"value\":1,\"unit\":\"L/h\"},\"time_unit\":\"h\",\"concentration_unit\":\"mg/L\"}".toUTF8.data.toList == some "mg/L"
#guard peakRowB 12 0 ["10".toUTF8.data.toList] == true
#guard peakRowB 12 0 ["12".toUTF8.data.toList] == true
#guard peakRowB 12 0 ["12.0001".toUTF8.data.toList] == false
#guard peakRowB 12 0 ["-1".toUTF8.data.toList] == false

end PCS.V2.PKPDVectors
