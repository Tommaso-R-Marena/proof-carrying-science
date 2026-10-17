# Test inventory — Workstream F

Run:

```bash
PYTHONPATH=independent_eval/assurance_card python3 -m pytest -q \
  independent_eval/assurance_card/tests
```

## Node ids (collected)

| File | Tests |
| --- | --- |
| `tests/test_claim_lattice.py` | `test_inspection_classes_match_product_lattice`, `test_classify_computationally_supported`, `test_classify_cryptographic_validity`, `test_classify_scientific_adequacy_open`, `test_classify_rejected_or_failed`, `test_classify_unknown_or_ambiguous`, `test_summarize_classes_counts` |
| `tests/test_hashing_paths.py` | `test_sha256_known_vector`, `test_sha256_file_and_paths`, `test_paths_resolve_dir_and_certificate` |
| `tests/test_card_schema.py` | `test_inspect_fixture_claims_and_flags`, `test_card_json_schema_fields`, `test_build_assurance_card_provenance_hashes` |
| `tests/test_html_a11y.py` | `test_html_contains_disclaimer_skip_link_and_banner`, `test_cli_main_writes_both` |
| `tests/test_authority_lane.py` | `test_authority_agree_when_cli_ok`, `test_authority_disagree_when_cli_fails_and_classes_supported`, `test_authority_inconclusive_when_cli_unavailable`, `test_authority_agree_when_cli_fails_and_rejected_class` |
| `tests/test_pkpd_real_path.py` | `test_pkpd_certify_verify_assurance_card` (skipped if pcs / example missing) |

**Minimum target:** ≥10 tests. This suite exceeds that with lattice, hashing,
schema, HTML/a11y, and CLI agree / disagree / inconclusive coverage.
