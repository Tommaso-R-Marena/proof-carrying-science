# Workstream B — Scientific Falsification and Casebook

Black-box scientific evaluation of PCS. **Does not modify** production `pcs/`, `formal/`, or CI.

## Components

| Path | Purpose |
| --- | --- |
| `casebook/` | ≥6 computational workflows with assumptions, negatives, licenses |
| `inadequacy/` | Computational PASS without empirical adequacy |
| `metamorphic/` | Valid/invalid transforms vs `pcs certify`/`verify` |
| `discovery_benchmark/` | Read-only `pcs discover-v06` precision/recall/abstention |
| `external_validity/` | Preregisterable protocol templates + completeness scorer |
| `python_harness/` | Fixture builders and evaluation runners |
| `fixtures/FIXTURE_HASHES.json` | SHA-256 manifest for immutable inputs |
| `tests/` | Pytest suite |
| `results/` | Machine-readable campaign outputs (generated) |

## Commands

```bash
# From repository root
python3 -m pip install -e '.[dev]'
PYTHONPATH=. python3 independent_eval/scientific_falsification/python_harness/build_fixtures.py
PYTHONPATH=independent_eval/scientific_falsification python3 -m pytest -q independent_eval/scientific_falsification/tests
PYTHONPATH=independent_eval/scientific_falsification python3 -m python_harness.run_all --skip-build
```

## Non-claims

This workstream does not claim biological adequacy, clinical validity, completed external-lab validation, or that PCS verification equals scientific truth.
