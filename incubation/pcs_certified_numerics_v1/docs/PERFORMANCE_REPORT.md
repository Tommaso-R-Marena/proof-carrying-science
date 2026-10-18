# Performance report

From `scripts/run_benchmarks.py` on the development host (exact re-run may vary slightly):

| Benchmark | Result |
|---|---|
| `x*(1-x)` on `[0,1]` natural width | `1` |
| same, mean-value width | `1` (not strictly tighter on this instance with current gradient enclosure) |
| root `x²−2` on `[0,2]` to width `1/1000` | `UNIQUE` in ~1 ms |
| 2D quadratic BnB `tol=1/20` | 53 subdivisions, gap `9/8192`, ~7 ms |

Lean cold build is dominated by Mathlib; with oleans cache, CertNum modules build in seconds.
