# Test inventory — Workstream C

| Suite | Result |
| --- | --- |
| `pytest independent_eval/repro_tcb/tests` | **10 passed** |
| Reconstruction campaign | identical-archive replay + regenerated canonical + noncanonical recorded |
| TCB atlas | machine-readable graph (see `results/tcb_atlas.json`) |
| Traceability audit | supported / unsupported / stale / ambiguous classifications |

```bash
PYTHONPATH=independent_eval/repro_tcb python3 -m python_harness run-all
PYTHONPATH=independent_eval/repro_tcb python3 -m pytest -q independent_eval/repro_tcb/tests
```

See `results/workstream_c_summary.json`.
