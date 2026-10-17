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
| `tests/test_canonical_seal.py` | `test_seal_stable_under_fixed_timestamp`, `test_tamper_breaks_seal`, `test_reseal_after_change_updates_digest`, `test_integrity_excludes_itself_from_payload` |
| `tests/test_program_context.py` | `test_attach_absent_is_not_pass`, `test_attach_results_dir_digests_summary`, `test_empty_attach_list_is_zero_requested` |
| `tests/test_json_schema_file.py` | `test_schema_file_exists_and_validates_card` |
| `tests/test_pkpd_real_path.py` | `test_pkpd_certify_verify_assurance_card` (skipped if pcs / example missing) |

**Collected:** 28 tests. **Last local run:** 28 passed.

Coverage includes lattice, hashing, JSON schema fields + schema file,
HTML disclaimer + skip-link/a11y + integrity/program-context sections,
CLI authority agree / disagree / inconclusive (monkeypatch), content-addressed
card seal (tamper detection), program_context ABSENT≠PASS, and optional
real-path pkpd certify→verify→card.
