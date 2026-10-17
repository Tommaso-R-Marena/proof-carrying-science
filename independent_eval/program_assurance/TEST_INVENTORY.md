# TEST_INVENTORY — program_assurance

**Collected tests:** 20  
**Last pytest run:** 20 passed

## Exact commands

```bash
PYTHONPATH=independent_eval/program_assurance \
  python3 -m pytest -q independent_eval/program_assurance/tests

# Soft campaign summary
PYTHONPATH=independent_eval/program_assurance \
  python3 -m python_harness run-all

# Hard local gates (exit 1 on collisions/overlaps)
PYTHONPATH=independent_eval/program_assurance \
  python3 -m python_harness preflight
```

## Suites

| Module | Coverage |
| --- | --- |
| `test_collision_scanner.py` | Case-insensitive path collisions |
| `test_nonoverlap_auditor.py` | Sibling-branch changed-file overlaps |
| `test_inventory_aggregator.py` | PRESENT/MISSING report aggregation |
| `test_proposals_catalog.py` | Proposal catalog invariants |
| `test_preflight.py` | Hard-fail preflight gates |
| `test_residual_trust.py` | Residual-trust rollup (`tcb_closed=false`) |

Live preflight on this tip: collisions=0, pairwise overlaps=0, residual-trust sources_present=4, `tcb_closed=false`.
