# Test inventory — Workstream B

| Suite | Result |
| --- | --- |
| `pytest independent_eval/scientific_falsification/tests` | **20 passed** |
| Casebook fixtures | **7** cases; all positive certify+verify PASS |
| Inadequacy examples | **3** computational PASS; **0** empirical adequacy established |
| Metamorphic (PK/PD) | **3/3** valid oracles; **2/2** invalid oracles |
| Discovery benchmark | **4** projects; macro precision/recall **1.0**; abstention accuracy **1.0** |
| External-validity scorer | blank template completeness **0.7143**; `empirical_adequacy_established=false` |
| Fixture hash manifest | **76** hashed files |

Exact commands (repository root):

```bash
PYTHONPATH=. python3 independent_eval/scientific_falsification/python_harness/build_fixtures.py
PYTHONPATH=independent_eval/scientific_falsification python3 -m pytest -q independent_eval/scientific_falsification/tests
PYTHONPATH=independent_eval/scientific_falsification python3 -m python_harness.run_all --skip-build
```

See `results/SUMMARY.json` and `results/TEST_RUN.txt`.
