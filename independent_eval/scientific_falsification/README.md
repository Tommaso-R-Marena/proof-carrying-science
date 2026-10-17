# Workstream B — Scientific Falsification and Casebook

Black-box scientific evaluation of PCS. **Does not modify** production `pcs/`,
`formal/`, `research/`, `site/`, or `.github/`.

## Layout

| Path | Purpose |
| --- | --- |
| `casebook/cases/` | ≥6 computational workflows (Task 7) |
| `inadequacy/examples/` | Computational PASS without empirical adequacy (Task 8) |
| `metamorphic/` | Valid/invalid transforms vs `pcs certify`/`verify` (Task 9) |
| `discovery_benchmark/` | Read-only `pcs discover-v06` metrics (Task 10) |
| `external_validity/` | Protocol templates + completeness scorer (Task 11) |
| `python_harness/` | Fixture builders and evaluation runners |
| `fixtures/FIXTURE_HASHES.json` | SHA-256 manifest for immutable inputs |
| `tests/` | Pytest suite |
| `results/` | Campaign outputs (generated) |

## Exact commands

```bash
# From repository root
python3 -m pip install -e '.[dev]'
export PATH="$HOME/.local/bin:$PATH"

PYTHONPATH=. python3 independent_eval/scientific_falsification/python_harness/build_fixtures.py

PYTHONPATH=independent_eval/scientific_falsification \
  python3 -m pytest -q independent_eval/scientific_falsification/tests

PYTHONPATH=independent_eval/scientific_falsification \
  python3 -m python_harness.run_all --skip-build
```

## Non-claims

This workstream does not claim biological adequacy, clinical validity,
completed external-lab validation, or that PCS verification equals scientific
truth. No participants or study results were invented.
