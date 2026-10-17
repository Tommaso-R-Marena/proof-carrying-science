# Test inventory — Workstream C

Run from repository root (or the `ws-c` worktree):

```bash
python -m pytest independent_eval/repro_tcb/tests -q
```

Or exercise the harness end-to-end:

```bash
PYTHONPATH=independent_eval/repro_tcb python -m python_harness run-all
```

| Test module | Task | What it covers |
| --- | --- | --- |
| `tests/test_reconstruction.py` | 12 | Identical-archive replay vs regenerated (canonical / noncanonical); clean-dir isolation; cross-Python SHA-256; environment provenance fields |
| `tests/test_tcb_atlas.py` | 13 | Machine-readable graph chain; trust-class taxonomy; read-only probes of `formal/` + `pcs/`; open gaps |
| `tests/test_traceability.py` | 14 | Claim parsing; supported / unsupported / stale / ambiguous classification; JSON audit output |
| `tests/test_fixtures_hashes.py` | 12–14 | Deterministic fixture materialization; SHA-256 manifest round-trip |

## Fixtures

| Path | Role |
| --- | --- |
| `fixtures/evidence_bundle/*` | Synthetic certificate / policy / transcript members |
| `fixtures/evidence_canonical.zip` | Canonical ZIP_STORED archive of those members |
| `fixtures/claims/sample_claims_report.md` | Mixed supported/unsupported/stale/ambiguous claims |
| `fixtures/hashes.json` | Pinned SHA-256 digests for the above |

## Results (generated)

| Path | Producer |
| --- | --- |
| `results/reconstruction_*.json` | Task 12 |
| `results/reconstruction_campaign.json` | Task 12 campaign summary |
| `results/tcb_atlas.json` | Task 13 |
| `results/traceability_audit.json` | Task 14 |
