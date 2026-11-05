# TEST_INVENTORY — scientific_falsification

**Collected tests:** 28
**Last pytest run:** 28 passed

## Exact commands

```bash
PYTHONPATH=independent_eval/scientific_falsification \
  python3 -m pytest -q independent_eval/scientific_falsification/tests

# Efficient selective campaign (SKIPPED ≠ PASS)
PYTHONPATH=independent_eval/scientific_falsification \
  python3 -m python_harness.run_all --skip-build --only aristotle --only inadequacy
```

## Collected test node ids

- `independent_eval/scientific_falsification/tests/test_casebook.py::test_casebook_has_at_least_six_cases`
- `independent_eval/scientific_falsification/tests/test_casebook.py::test_case_certify_and_verify[01_pkpd_one_compartment]`
- `independent_eval/scientific_falsification/tests/test_casebook.py::test_case_certify_and_verify[02_pkpd_with_peak_threshold_note]`
- `independent_eval/scientific_falsification/tests/test_casebook.py::test_case_certify_and_verify[03_mass_action_reaction_balance]`
- `independent_eval/scientific_falsification/tests/test_casebook.py::test_case_certify_and_verify[04_unit_compatible_concentration]`
- `independent_eval/scientific_falsification/tests/test_casebook.py::test_case_certify_and_verify[05_csv_disjoint_cohorts]`
- `independent_eval/scientific_falsification/tests/test_casebook.py::test_case_certify_and_verify[06_scientific_workflow_composite]`
- `independent_eval/scientific_falsification/tests/test_casebook.py::test_case_certify_and_verify[07_pkpd_alt_parameters]`
- `independent_eval/scientific_falsification/tests/test_casebook.py::test_pkpd_negative_control_fails_reference_match`
- `independent_eval/scientific_falsification/tests/test_casebook.py::test_fixture_hashes_immutable`
- `independent_eval/scientific_falsification/tests/test_discovery_benchmark.py::test_discovery_benchmark_precision_recall_abstention`
- `independent_eval/scientific_falsification/tests/test_external_validity.py::test_templates_exist_without_participant_results`
- `independent_eval/scientific_falsification/tests/test_external_validity.py::test_score_blank_protocol_completeness`
- `independent_eval/scientific_falsification/tests/test_external_validity.py::test_score_does_not_invent_results`
- `independent_eval/scientific_falsification/tests/test_inadequacy.py::test_inadequacy_index_lists_four_examples`
- `independent_eval/scientific_falsification/tests/test_inadequacy.py::test_correct_but_inadequate_pkpd_still_verifies`
- `independent_eval/scientific_falsification/tests/test_inadequacy.py::test_balanced_but_biologically_inadequate_verifies`
- `independent_eval/scientific_falsification/tests/test_inadequacy.py::test_units_ok_quantity_inadequate_verifies`
- `independent_eval/scientific_falsification/tests/test_inadequacy.py::test_aristotle_candidates_are_proposals_only`
- `independent_eval/scientific_falsification/tests/test_inadequacy.py::test_disjoint_but_biased_cohorts_verifies_without_adequacy`
- `independent_eval/scientific_falsification/tests/test_metamorphic.py::test_metamorphic_suite_on_pkpd_case`
- `independent_eval/scientific_falsification/tests/test_metamorphic.py::test_metamorphic_suite_on_reaction_case`
- `independent_eval/scientific_falsification/tests/test_metamorphic.py::test_metamorphic_suite_on_units_case`
- `independent_eval/scientific_falsification/tests/test_metamorphic.py::test_metamorphic_suite_on_composite_case`
- `independent_eval/scientific_falsification/tests/test_metamorphic.py::test_metamorphic_campaign_covers_extended_cases`
- `independent_eval/scientific_falsification/tests/test_scorecard_and_only.py::test_scorecard_marks_inadequacy_open_and_never_accepts`
- `independent_eval/scientific_falsification/tests/test_scorecard_and_only.py::test_seal_detects_tamper`
- `independent_eval/scientific_falsification/tests/test_scorecard_and_only.py::test_run_all_only_aristotle_skips_heavy_surfaces`

Coverage includes casebook controls, inadequacy (PASS≠adequacy), Aristotle
proposal candidates with obligation sketches + seals, metamorphic oracles,
discovery metrics, external-validity completeness, falsification scorecard
(lattice-aligned, non-authority), and `--only` selective runs.
