# Scientific evaluation report

Synthetic PK/PD pilot and falsification suite executed via
`scripts/run_synthetic_pilot.py` and `scripts/run_benchmarks.py`.

## Results (this environment)

- Independent reconstruction: `INDEPENDENTLY_REPRODUCED`
- External laboratory validation: `OPEN` (no outside lab participated)
- Benchmark metrics: see `results/benchmark_report.json` (6/6 correct; 0 false accepts)

## Negative controls

- Wrong PK predictions → `REFUTED`
- Bad clearance units → `REFUTED`
- Train/test leakage → `REFUTED`
- Causal language with associational evidence → `REFUTED`

## Datasets

All fixtures are synthetic; license: Apache-2.0 with the repository.


## Journal-backed demos

See `JOURNAL_DEMOS_REPORT.md`. Theophylline oral fits computationally supported; IV misspecification refuted; Indometh monoexponential negative control refuted; external validation OPEN.
