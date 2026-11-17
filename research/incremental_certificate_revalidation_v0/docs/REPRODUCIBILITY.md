# Reproducibility

## Identities

| Item | Value |
|---|---|
| Base main commit | `bc78660b5fac857fce3873eb6cda0445d1903da1` (see `BASE_COMMIT.txt`) |
| Branch | `research/pcs-incremental-revalidation-v0` |
| Lean | 4.28.0 (`formal/lean-toolchain`) |
| Python | 3.12+ stdlib + pytest |

## Commands

```bash
export PATH="$HOME/.local/lean-4.28.0/bin:$PATH"
export PYTHONPATH=research/incremental_certificate_revalidation_v0
bash research/incremental_certificate_revalidation_v0/scripts/check_lean.sh
python -m pytest -q research/incremental_certificate_revalidation_v0/tests
python research/incremental_certificate_revalidation_v0/scripts/run_demo.py
python research/incremental_certificate_revalidation_v0/scripts/run_adversarial.py
python research/incremental_certificate_revalidation_v0/scripts/run_benchmarks.py
```

## Outputs

| File | Content |
|---|---|
| `results/lean_build.log` | Lake build + axiom printouts |
| `results/demo_report.json` | E2E demo |
| `results/adversarial_report.json` | Attack outcomes |
| `results/benchmark_report.json` | Timings |

## Assumptions

- Exact equality of obligation keys (no hash-as-proof).
- Local ValidState trust for `prior_accepted` bits when `recheck_on_reuse=False`.
- Synthetic ops only; no claim about scientific measurement truth.
- Differential agreement ≠ Lean refinement of Python.
