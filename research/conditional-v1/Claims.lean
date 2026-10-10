import Std
theorem conditional_target_0 (V00 V01 V02 V03 : Bool) (h : true = true) : (!((V00 || V01) || (V02 || V03))) = (((!V00) && (!V01)) && ((!V02) && (!V03))) := by
  simp only [Bool.not_or]
#print axioms conditional_target_0
theorem conditional_target_1 (V00 V01 V02 V03 : Bool) (h : (true && ((V00 && V01) && (V02 && V03))) = true) : ((V00 && V01) && (V02 && V03)) = ((V00 || V01) || (V02 || V03)) := by
  simp only [Bool.and_eq_true] at h
  simp_all
#print axioms conditional_target_1
theorem conditional_target_2 (V00 V01 V02 V03 V04 V05 V06 V07 : Bool) (h : true = true) : (!(((V00 || V01) || (V02 || V03)) || ((V04 || V05) || (V06 || V07)))) = ((((!V00) && (!V01)) && ((!V02) && (!V03))) && (((!V04) && (!V05)) && ((!V06) && (!V07)))) := by
  simp only [Bool.not_or]
#print axioms conditional_target_2
theorem conditional_target_3 (V00 V01 V02 V03 V04 V05 V06 V07 : Bool) (h : (true && (((V00 && V01) && (V02 && V03)) && ((V04 && V05) && (V06 && V07)))) = true) : (((V00 && V01) && (V02 && V03)) && ((V04 && V05) && (V06 && V07))) = (((V00 || V01) || (V02 || V03)) || ((V04 || V05) || (V06 || V07))) := by
  simp only [Bool.and_eq_true] at h
  simp_all
#print axioms conditional_target_3
theorem conditional_target_4 (V00 V01 V02 V03 V04 V05 V06 V07 V08 V09 V10 V11 : Bool) (h : true = true) : (!(((V00 || (V01 || V02)) || (V03 || (V04 || V05))) || ((V06 || (V07 || V08)) || (V09 || (V10 || V11))))) = ((((!V00) && ((!V01) && (!V02))) && ((!V03) && ((!V04) && (!V05)))) && (((!V06) && ((!V07) && (!V08))) && ((!V09) && ((!V10) && (!V11))))) := by
  simp only [Bool.not_or]
#print axioms conditional_target_4
theorem conditional_target_5 (V00 V01 V02 V03 V04 V05 V06 V07 V08 V09 V10 V11 : Bool) (h : (true && (((V00 && (V01 && V02)) && (V03 && (V04 && V05))) && ((V06 && (V07 && V08)) && (V09 && (V10 && V11))))) = true) : (((V00 && (V01 && V02)) && (V03 && (V04 && V05))) && ((V06 && (V07 && V08)) && (V09 && (V10 && V11)))) = (((V00 || (V01 || V02)) || (V03 || (V04 || V05))) || ((V06 || (V07 || V08)) || (V09 || (V10 || V11)))) := by
  simp only [Bool.and_eq_true] at h
  simp_all
#print axioms conditional_target_5
theorem conditional_target_6 (V00 V01 V02 V03 V04 V05 V06 V07 V08 V09 V10 V11 V12 V13 V14 V15 : Bool) (h : true = true) : (!((((V00 || V01) || (V02 || V03)) || ((V04 || V05) || (V06 || V07))) || (((V08 || V09) || (V10 || V11)) || ((V12 || V13) || (V14 || V15))))) = (((((!V00) && (!V01)) && ((!V02) && (!V03))) && (((!V04) && (!V05)) && ((!V06) && (!V07)))) && ((((!V08) && (!V09)) && ((!V10) && (!V11))) && (((!V12) && (!V13)) && ((!V14) && (!V15))))) := by
  simp only [Bool.not_or]
#print axioms conditional_target_6
theorem conditional_target_7 (V00 V01 V02 V03 V04 V05 V06 V07 V08 V09 V10 V11 V12 V13 V14 V15 : Bool) (h : (true && ((((V00 && V01) && (V02 && V03)) && ((V04 && V05) && (V06 && V07))) && (((V08 && V09) && (V10 && V11)) && ((V12 && V13) && (V14 && V15))))) = true) : ((((V00 && V01) && (V02 && V03)) && ((V04 && V05) && (V06 && V07))) && (((V08 && V09) && (V10 && V11)) && ((V12 && V13) && (V14 && V15)))) = ((((V00 || V01) || (V02 || V03)) || ((V04 || V05) || (V06 || V07))) || (((V08 || V09) || (V10 || V11)) || ((V12 || V13) || (V14 || V15)))) := by
  simp only [Bool.and_eq_true] at h
  simp_all
#print axioms conditional_target_7
theorem conditional_target_8 (V00 V01 V02 V03 V04 V05 V06 V07 V08 V09 V10 V11 V12 V13 V14 V15 V16 V17 V18 V19 : Bool) (h : true = true) : (!((((V00 || V01) || (V02 || (V03 || V04))) || ((V05 || V06) || (V07 || (V08 || V09)))) || (((V10 || V11) || (V12 || (V13 || V14))) || ((V15 || V16) || (V17 || (V18 || V19)))))) = (((((!V00) && (!V01)) && ((!V02) && ((!V03) && (!V04)))) && (((!V05) && (!V06)) && ((!V07) && ((!V08) && (!V09))))) && ((((!V10) && (!V11)) && ((!V12) && ((!V13) && (!V14)))) && (((!V15) && (!V16)) && ((!V17) && ((!V18) && (!V19)))))) := by
  simp only [Bool.not_or]
#print axioms conditional_target_8
theorem conditional_target_9 (V00 V01 V02 V03 V04 V05 V06 V07 V08 V09 V10 V11 V12 V13 V14 V15 V16 V17 V18 V19 : Bool) (h : (true && ((((V00 && V01) && (V02 && (V03 && V04))) && ((V05 && V06) && (V07 && (V08 && V09)))) && (((V10 && V11) && (V12 && (V13 && V14))) && ((V15 && V16) && (V17 && (V18 && V19)))))) = true) : ((((V00 && V01) && (V02 && (V03 && V04))) && ((V05 && V06) && (V07 && (V08 && V09)))) && (((V10 && V11) && (V12 && (V13 && V14))) && ((V15 && V16) && (V17 && (V18 && V19))))) = ((((V00 || V01) || (V02 || (V03 || V04))) || ((V05 || V06) || (V07 || (V08 || V09)))) || (((V10 || V11) || (V12 || (V13 || V14))) || ((V15 || V16) || (V17 || (V18 || V19))))) := by
  simp only [Bool.and_eq_true] at h
  simp_all
#print axioms conditional_target_9
theorem conditional_target_10 (V00 V01 V02 V03 V04 V05 V06 V07 V08 V09 V10 V11 V12 V13 V14 V15 V16 V17 V18 V19 V20 V21 V22 V23 : Bool) (h : true = true) : (!((((V00 || (V01 || V02)) || (V03 || (V04 || V05))) || ((V06 || (V07 || V08)) || (V09 || (V10 || V11)))) || (((V12 || (V13 || V14)) || (V15 || (V16 || V17))) || ((V18 || (V19 || V20)) || (V21 || (V22 || V23)))))) = (((((!V00) && ((!V01) && (!V02))) && ((!V03) && ((!V04) && (!V05)))) && (((!V06) && ((!V07) && (!V08))) && ((!V09) && ((!V10) && (!V11))))) && ((((!V12) && ((!V13) && (!V14))) && ((!V15) && ((!V16) && (!V17)))) && (((!V18) && ((!V19) && (!V20))) && ((!V21) && ((!V22) && (!V23)))))) := by
  simp only [Bool.not_or]
#print axioms conditional_target_10
theorem conditional_target_11 (V00 V01 V02 V03 V04 V05 V06 V07 V08 V09 V10 V11 V12 V13 V14 V15 V16 V17 V18 V19 V20 V21 V22 V23 : Bool) (h : (true && ((((V00 && (V01 && V02)) && (V03 && (V04 && V05))) && ((V06 && (V07 && V08)) && (V09 && (V10 && V11)))) && (((V12 && (V13 && V14)) && (V15 && (V16 && V17))) && ((V18 && (V19 && V20)) && (V21 && (V22 && V23)))))) = true) : ((((V00 && (V01 && V02)) && (V03 && (V04 && V05))) && ((V06 && (V07 && V08)) && (V09 && (V10 && V11)))) && (((V12 && (V13 && V14)) && (V15 && (V16 && V17))) && ((V18 && (V19 && V20)) && (V21 && (V22 && V23))))) = ((((V00 || (V01 || V02)) || (V03 || (V04 || V05))) || ((V06 || (V07 || V08)) || (V09 || (V10 || V11)))) || (((V12 || (V13 || V14)) || (V15 || (V16 || V17))) || ((V18 || (V19 || V20)) || (V21 || (V22 || V23))))) := by
  simp only [Bool.and_eq_true] at h
  simp_all
#print axioms conditional_target_11
