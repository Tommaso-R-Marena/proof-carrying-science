# TEST_INVENTORY — program_assurance

**Collected tests:** 16
**Last pytest run:** 16 passed

## Exact commands

```bash
PYTHONPATH=independent_eval/program_assurance \
  python3 -m pytest -q independent_eval/program_assurance/tests

PYTHONPATH=independent_eval/program_assurance \
  python3 -m python_harness.run_all
```

## Collected test node ids

- `independent_eval/program_assurance/tests/test_collision_scanner.py::test_no_collision_on_distinct_names`
- `independent_eval/program_assurance/tests/test_collision_scanner.py::test_detects_checklist_case_collision`
- `independent_eval/program_assurance/tests/test_collision_scanner.py::test_detects_directory_component_case_collision`
- `independent_eval/program_assurance/tests/test_collision_scanner.py::test_write_collision_report_roundtrip`
- `independent_eval/program_assurance/tests/test_collision_scanner.py::test_skips_pycache`
- `independent_eval/program_assurance/tests/test_inventory_aggregator.py::test_missing_prefixes_recorded_as_missing`
- `independent_eval/program_assurance/tests/test_inventory_aggregator.py::test_present_inventory_extracts_collected_tests`
- `independent_eval/program_assurance/tests/test_inventory_aggregator.py::test_markdown_render_marks_missing`
- `independent_eval/program_assurance/tests/test_nonoverlap_auditor.py::test_pairwise_overlap_detected`
- `independent_eval/program_assurance/tests/test_nonoverlap_auditor.py::test_no_overlap_when_disjoint`
- `independent_eval/program_assurance/tests/test_nonoverlap_auditor.py::test_missing_branch_recorded`
- `independent_eval/program_assurance/tests/test_nonoverlap_auditor.py::test_diff_error_recorded`
- `independent_eval/program_assurance/tests/test_nonoverlap_auditor.py::test_write_nonoverlap_report`
- `independent_eval/program_assurance/tests/test_proposals_catalog.py::test_default_catalog_all_proposals`
- `independent_eval/program_assurance/tests/test_proposals_catalog.py::test_rejects_completion_claim`
- `independent_eval/program_assurance/tests/test_proposals_catalog.py::test_write_catalog_files`

## Counts by file

- `test_collision_scanner.py`: 5
- `test_nonoverlap_auditor.py`: 5
- `test_inventory_aggregator.py`: 3
- `test_proposals_catalog.py`: 3
