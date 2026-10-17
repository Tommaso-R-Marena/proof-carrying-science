# Test inventory — Workstream D

**Collected tests:** 10  
**Last pytest run:** 10 passed

```bash
PYTHONPATH=. python -m pytest -q independent_eval/reviewer_adoption/tests
```

| Suite | Coverage |
| --- | --- |
| `test_workbench.py` | Task 15 inspect + HTML; no ACCEPT authority |
| `test_blind_challenge.py` | Task 16 blinding + scorer; refuses unattested human study |
| `test_tabletop.py` | Task 17 offline scenarios; refuses live credential flags |
| `test_external_lab.py` | Task 18 checklist + burden tracker non-claims |

See `results/TEST_RUN.txt`.
