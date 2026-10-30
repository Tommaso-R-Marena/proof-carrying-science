import PCSScientific.Bridge
import RequestProject.AION.Examples.BirthDeath

/-! A synthetic, model-conditional safety experiment. The infinite-state chain
is mathematical; the assay outcomes are stipulated model predictions, not data. -/
set_option autoImplicit false
namespace PCSScientific.RiskDemo
open PRISM PRISM.Problem AION AION.Examples.BirthDeath

noncomputable def mu (m : Fin 2) : ℝ := if m = 0 then 2 else 3/2
lemma mu_gt_one (m : Fin 2) : (1 : ℝ) < mu m := by fin_cases m <;> norm_num [mu]
noncomputable def net (m : Fin 2) : AION.JumpModel Nat (Fin 2) :=
  bd 1 (mu m) (by norm_num) (le_trans (by norm_num : (0:ℝ) ≤ 1) (mu_gt_one m).le)
noncomputable def risk (m : Fin 2) : ℝ := net m |>.hitProb {0} {y | 20 ≤ y} 1

theorem risk_closed (m : Fin 2) :
    risk m = if m = 0 then (1 : ℝ)/1048575 else 524288/3485735825 := by
  have h := bd_exact (lam := (1:ℝ)) (mu := mu m) (by norm_num) (mu_gt_one m)
    (N := 20) (by norm_num) (x := 1) (by norm_num)
  change (bd 1 (mu m) _ _).hitProb {0} {y | 20 ≤ y} 1 = _
  rw [h]
  fin_cases m <;> norm_num [mu]

def P : PRISM.Problem (Fin 2) (Fin 2) (Fin 2) where
  obs m _ := m
  q m := if m = 0 then 0 else 1
  cost e := if e = 0 then 1 else 7

def cert : PRISM.Problem.OptCert (Fin 2) (Fin 2) (Fin 2) where
  policy := .test 0 (fun _ => .stop)
  bound := 1
  core := Finset.univ
  adversary := [(Finset.univ,1)]

theorem cert_ok : P.checkOptimal 0 Finset.univ cert = true := by decide +kernel

theorem classifier_correct (m : Fin 2) : P.q m = 0 ↔ risk m ≤ (1:ℝ)/100000 := by
  rw [risk_closed]
  fin_cases m <;> norm_num [P]

theorem optimal_safe_experiment (m : Fin 2) :
    (∀ a ∈ P.terminal cert.policy m Finset.univ, P.q a = 0 ↔ risk m ≤ (1:ℝ)/100000) ∧
    (∀ p : PRISM.Policy (Fin 2) (Fin 2), P.Succeeds 0 p Finset.univ →
      cert.bound ≤ P.worstCost p Finset.univ) := by
  exact PCSScientific.optimal_identified_risk P Finset.univ cert risk ((1:ℝ)/100000)
    (fun a _ => classifier_correct a) cert_ok m (Finset.mem_univ m)

theorem exact_optimal_cost : P.value 0 Finset.univ = 1 := by
  exact (PRISM.Problem.checkOptimal_sound (by norm_num) cert_ok).2.2.2

theorem initial_risk_ambiguous : risk 0 ≤ (1:ℝ)/100000 ∧ (1:ℝ)/100000 < risk 1 := by
  rw [risk_closed,risk_closed]
  norm_num

def noAssay : PRISM.Problem (Fin 2) (Fin 1) (Fin 1) where
  obs _ _ := 0
  q m := if m = 0 then 0 else 1
  cost _ := 1

theorem no_assay_cert : noAssay.checkImpossible 0 Finset.univ 1 0 = true := by decide +kernel

theorem no_assay_impossible :
    (∀ p : PRISM.Policy (Fin 1) (Fin 1), ¬ noAssay.Succeeds 0 p Finset.univ) ∧
      noAssay.value 0 Finset.univ = ⊤ :=
  PRISM.Problem.checkImpossible_sound (by norm_num) no_assay_cert
end PCSScientific.RiskDemo
