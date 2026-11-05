# Workstream C — Reproducibility & TCB

Independent evaluation of PCS reconstruction behavior and trusted computing base
boundaries. See `TECHNICAL_REPORT.md` for the full write-up.

```bash
PYTHONPATH=independent_eval/repro_tcb python -m python_harness run-all
python -m pytest independent_eval/repro_tcb/tests -q
```

| Doc | Purpose |
| --- | --- |
| `NONOVERLAP.md` | Writable scope vs forbidden trees / sibling PRs |
| `TEST_INVENTORY.md` | Tests and fixtures |
| `OPEN_TRUST_ASSUMPTIONS.md` | Residual trust inventory |
| `TECHNICAL_REPORT.md` | Tasks 12–14 findings |
