# Real-world mutation campaign

- Mutations: 37
- Expected-detection probes: 34
- Caught: 34
- Missed: 0
- False alarms: 0
- Benign OK (boundary controls): 3
- Catch rate (among expected): 1.0

## Missed (honest gaps)

- (none)

## All mutation outcomes

- **CAUGHT** `pcs_pkpd_one_compartment` / `scale_one_concentration_1.5x` / pkpd_verify: REFUTED — predictions deviate from one-compartment IV bolus model
- **CAUGHT** `pcs_pkpd_one_compartment` / `clearance_unit_nonsense` / unit_error: REFUTED — unit_errors: OBSERVED_FAILURE
- **CAUGHT** `pcs_pkpd_one_compartment` / `causal_overclaim_text` / causal_check: REFUTED — unsupported_causal_interpretation: OBSERVED_FAILURE
- **CAUGHT** `pcs_mass_action` / `break_cleavage_stoichiometry` / atom_balance: REFUTED — atom balance failure
- **CAUGHT** `pcs_mass_action` / `inject_exec` / python_static_flags: CONDITIONAL — ['dynamic_execution:exec']
- **CAUGHT** `pcs_biopharma_demo` / `leak_S001_into_test` / data_leakage: REFUTED — data_leakage: OBSERVED_FAILURE
- **CAUGHT** `pcs_biopharma_demo` / `drop_concentration_column` / csv_schema: REFUTED — missing columns ['concentration_mg_L']
- **CAUGHT** `pcs_pkpd_translation_benchmark` / `halve_effect_keep_conc` / emax_consistency: CAUGHT — e=41.66666666666665 e_hat=83.33333333333333
- **CAUGHT** `pcs_pkpd_translation_benchmark` / `clearance_unit_label_only_mL_min` / unit_aware_consistency: CAUGHT — clearance/volume unit label inconsistent with numeric fields under prediction check
- **CAUGHT** `pcs_scientific_workflow_v3` / `double_CellA_last_step` / amount_conservation: CAUGHT — spread=0.25812155469914866
- **CAUGHT** `pcs_scientific_workflow_v3` / `inject_eval` / python_static_flags: CAUGHT — ['dynamic_execution:eval', 'filesystem:open']
- **CAUGHT** `journal_theoph` / `10x_one_concentration` / oral_fit_degradation: DEGRADED — rmse=25.5197
- **CAUGHT** `journal_puromycin` / `10x_one_rate_treated` / mm_fit_degradation: CAUGHT — rmse=192.758 med_rel=0.291
- **CAUGHT** `journal_puromycin` / `swap_treated_untreated_labels` / registered_group_params: CAUGHT — group labels appear swapped relative to registered parameters
- **CAUGHT** `journal_indometh` / `zero_one_concentration` / nonnegative_concentration_integrity: CAUGHT — integrity=REFUTED rmse=0.2832
- **CAUGHT** `edrug3d` / `synthetic_inconsistent_half_life` / half_life_consistency: INCONSISTENT — rel_err=0.993
- **CAUGHT** `osp_ddi` / `blank_first_reference` / missing_reference: DETECTED — missing=1
- **CAUGHT** `osp_pediatrics` / `blank_reference` / missing_reference: CAUGHT — missing=1
- **CAUGHT** `osp_pediatrics` / `negative_cl_avg` / neg_cl_count: CAUGHT — neg_cl=1
- **CAUGHT** `nlmixr2data_theo_sd` / `negative_concentration` / nca_rejects_negative: CAUGHT — negative concentration unsupported in this fragment
- **CAUGHT** `nlmixr2data_theo_sd` / `negative_concentration_count` / neg_count: OK — neg=1
- **CAUGHT** `nlmixr2data_warfarin` / `negative_dv_obs` / nonnegative_concentration_integrity: CAUGHT — neg=1 integrity=REFUTED
- **CAUGHT** `nlmixr2data_warfarin` / `1e-12_time_jitter` / longitudinal_time_integrity: CAUGHT — longitudinal time integrity failures: 220
- **CAUGHT** `nlmixr2data_bolus_1cpt` / `negative_dv_subject1` / nonnegative_concentration_integrity: CAUGHT — non-positive/NaN concentrations: 1
- **CAUGHT** `nlmixr2data_bolus_1cpt` / `time_jitter_subject1` / longitudinal_time_integrity: CAUGHT — longitudinal time integrity failures: 1
- **CAUGHT** `package_real_pkpd` / `policy_version_swap` / review_rejects: CAUGHT — PCS_NEXT_POLICY_SUBSTITUTION: package policy differs from receiver pin
- **CAUGHT** `package_real_pkpd` / `post_freeze_prediction_append` / stale_substitution: CAUGHT — [{"kind": "stale_or_substituted_artifact", "path": "predictions.csv", "frozen_sha256": "47a616e774f42e851f2e6ef07d8d1a80bb17a00d3267def5e07ba331f83c20f9", "curr
- **CAUGHT** `package_real_pkpd` / `duplicate_json_keys` / canonical_loader: CAUGHT — 
- **BENIGN_OK** `pcs_pkpd_one_compartment` / `1e-9_relative_perturbation` / pkpd_verify_within_tol: COMPUTATIONALLY_TESTED — boundary: should remain accepted under stated tol
- **BENIGN_OK** `pcs_pkpd_one_compartment` / `noncausal_correct_claim_text` / causal_check_should_pass: COMPUTATIONALLY_TESTED — correct non-causal claim must not be refuted
- **CAUGHT** `pcs_pkpd_one_compartment` / `swap_csv_value_order` / pkpd_or_parse: CAUGHT — predictions deviate from one-compartment IV bolus model
- **BENIGN_OK** `pcs_pkpd_one_compartment` / `5e-7_all_rows_within_rel_tol` / pkpd_verify_within_tol: COMPUTATIONALLY_TESTED — just below rel_tol=1e-6
- **CAUGHT** `pcs_pkpd_one_compartment` / `2e-6_all_rows_over_rel_tol` / pkpd_verify: CAUGHT — predictions deviate from one-compartment IV bolus model
- **CAUGHT** `metamorphic_pk` / `partial_dose_scale_table` / dose_homogeneity_table: CAUGHT — scaled prediction table violates dose homogeneity
- **CAUGHT** `evidence_store` / `tamper_event_payload` / verify_chain: CAUGHT — PCS_NEXT_HASH_MISMATCH: event hash mismatch at 1
- **CAUGHT** `osp_synthetic` / `cl_auc_dose_inconsistent` / osp_consistency: CAUGHT — CL vs Dose/AUC inconsistent rel_err=0.980
- **CAUGHT** `pcs_pkpd_translation_benchmark` / `halve_all_effects_adapter` / emax_adapter: CAUGHT — effect rows deviate from direct Emax model
