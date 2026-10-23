import PRISM.Examples.Families
import PRISM.Abstraction.Nuisance
import PRISM.Probabilistic.AnytimeValid
import PRISM.Examples.Generated.Biochem
import PRISM.Examples.Generated.BiochemRestricted
import PRISM.Examples.Generated.Causal
import PRISM.Examples.Generated.CausalObservationalOnly

/-!
# Axiom audit

`#print axioms` for every headline result.  The expected output for each is a
subset of `propext`, `Classical.choice`, `Quot.sound` (standard Lean/Mathlib
classical foundations).  No `sorryAx`, no custom axioms, no `native_decide`
(`Lean.ofReduceBool`) anywhere: concrete certificates are checked with
`decide +kernel`, i.e. by the Lean kernel's own reduction.
Run `lake env lean PRISM/AxiomAudit.lean` to reproduce; output recorded in
`results/axiom_audit.txt`.

This file is deliberately not a `module` (the module system forbids `#print axioms`).
-/

open PRISM PRISM.Problem

-- Version spaces, bounds, certification
#print axioms PRISM.Problem.mem_versionSpace
#print axioms PRISM.Problem.bounds_sound
#print axioms PRISM.Problem.bounds_sharp
#print axioms PRISM.Problem.bounds_optimal
#print axioms PRISM.Problem.classify_sound
#print axioms PRISM.Problem.inconsistencyCert_sound
#print axioms PRISM.Problem.inconsistencyCert_complete
#print axioms PRISM.Problem.certified_transfers_to_truth
#print axioms PRISM.Problem.certified_does_not_imply_truth
-- Policies and Bellman optimality
#print axioms PRISM.Problem.pathLength_lt_card
#print axioms PRISM.Problem.value_of_width_le
#print axioms PRISM.Problem.value_of_not_width_le
#print axioms PRISM.Problem.value_le_of_succeeds
#print axioms PRISM.Problem.exists_policy_of_value_le
#print axioms PRISM.Problem.value_le_iff
#print axioms PRISM.Problem.value_optimal
#print axioms PRISM.Problem.value_eq_top_iff
#print axioms PRISM.Problem.exists_policy_test_of_backup_le
#print axioms PRISM.Problem.exists_optimal_onlyInformative
#print axioms PRISM.Problem.value_mono
-- Impossibility and identifiability
#print axioms PRISM.Problem.obsEquiv_mem_terminal
#print axioms PRISM.Problem.impossibility
#print axioms PRISM.Problem.identifiable_iff
#print axioms PRISM.Problem.value_ne_top_iff
#print axioms PRISM.Problem.ImpossibilityCert.sound
#print axioms PRISM.Problem.impossibilityCert_complete
#print axioms PRISM.Problem.testAll_fails
-- Abstraction and the optimality sandwich
#print axioms PRISM.Problem.optimality_sandwich
#print axioms PRISM.Problem.value_eq_of_sandwich
#print axioms PRISM.Problem.value_sandwich
#print axioms PRISM.Problem.IsExactAbstraction.value_image
#print axioms PRISM.Problem.value_signatureQuotient
#print axioms PRISM.signature_only_quotient_unsound
-- Nuisance-factor elimination
#print axioms PRISM.Problem.terminal_liftZ
#print axioms PRISM.Problem.section_policy_lifts
#print axioms PRISM.Problem.value_prod_eq_section
#print axioms PRISM.Problem.nuisance_mixing_counterexample
-- Adversary certificates and checkers
#print axioms PRISM.Problem.adversary_sound
#print axioms PRISM.Problem.adversary_le_value
#print axioms PRISM.Problem.adversary_complete
#print axioms PRISM.Problem.le_value_iff_adversary
#print axioms PRISM.Problem.adversary_test_bound
#print axioms PRISM.Problem.checkPolicy_sound
#print axioms PRISM.Problem.checkAdversary_sound
#print axioms PRISM.Problem.checkSandwich_sound
#print axioms PRISM.Problem.checkOptimal_sound
#print axioms PRISM.Problem.optimal_certificate_exists
#print axioms PRISM.Problem.checkImpossible_sound
#print axioms PRISM.Problem.checkBounds_sound
#print axioms PRISM.Problem.checkCountermodel_sound
#print axioms PRISM.Problem.checkCertified_sound
#print axioms PRISM.Problem.checkInconsistent_sound
-- Families and negative results
#print axioms PRISM.Families.orLB_isAdversary
#print axioms PRISM.Families.or_value
#print axioms PRISM.Families.or_sizes
#print axioms PRISM.Families.ptr_adaptive
#print axioms PRISM.Families.ptr_nonadaptive
#print axioms PRISM.Families.trap_value
#print axioms PRISM.Families.trap_greedy_choice
#print axioms PRISM.Families.trap_greedy_suboptimal
-- Noisy / probabilistic extension
#print axioms PRISM.NoisyProblem.leafSum_histProb
#print axioms PRISM.NoisyProblem.reject_at_stop_le
#print axioms PRISM.NoisyProblem.reject_ever_le
#print axioms PRISM.NoisyProblem.false_certification_le
#print axioms PRISM.posthoc_alternative_invalid
-- Generated, kernel-checked demonstrations
#print axioms PRISM.Generated.Biochem.value_eq
#print axioms PRISM.Generated.Biochem.policy_optimal
#print axioms PRISM.Generated.Biochem.sharp_bounds
#print axioms PRISM.Generated.Biochem.countermodel_ok
#print axioms PRISM.Generated.BiochemRestricted.impossible
#print axioms PRISM.Generated.Causal.value_eq
#print axioms PRISM.Generated.Causal.sharp_bounds
#print axioms PRISM.Generated.CausalObservationalOnly.impossible
