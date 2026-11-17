# Performance report

Measurements from `scripts/run_benchmarks.py` on this agent host
(America/New_York session date 2026-11-17). Values are wall-clock milliseconds
from `time.perf_counter`; peak memory via `tracemalloc`.

Mode: `recheck_on_reuse=False` (ValidState trust — measures invalidation/reuse
bookkeeping). Agreement with independent `fresh_verify` required for every case.

## Results (recorded)

| Case | Nodes | Fresh ms | Incr ms | Reused | Rechecked | Speedup |
|---|---:|---:|---:|---:|---:|---:|
| chain_200_leaf | 200 | ~2.6 | ~5.0 | 199 | 1 | ~0.53× |
| chain_200_root | 200 | ~2.3 | ~4.5 | 0 | 200 | ~0.51× |
| wide_300_one_input | 600 | ~6.8 | ~14.8 | 590 | 10 | ~0.46× |
| branch_depth7_leaf | 127 | ~1.2 | ~2.6 | 120 | 7 | ~0.46× |
| shared_50_* | 53 | ~0.5–0.6 | ~1.1 | varies | varies | ~0.5× |
| sci_2000_sparse3 | 3999 | ~53 | ~110 | 3968 | 31 | ~0.48× |
| sci_2000_dense100 | 3999 | ~50 | ~112 | 3448 | 551 | ~0.45× |
| sci_10000_sparse5 | 19999 | ~279 | ~584 | 19937 | 62 | ~0.48× |

Exact numbers: `results/benchmark_report.json`.

## Interpretation

For these **cheap** exact Int ops, incremental verification is **slower** than
fresh recomputation. Bookkeeping (obligation keys, cache index, Affected closure,
assignment rebuild) dominates the tiny local checks.

This is an honest negative performance result for the synthetic micro-ops, not a
claim of universal slowdown. Expected benefit appears when local checks are
expensive (e.g. Lean kernel proof checks). With `recheck_on_reuse=True` (default
in the adversarial trust posture), cost rises further because every reuse repeats
`local_check_node`.

Root-heavy changes (entire graph affected) show no reuse benefit, as expected.
Sparse leaf changes maximize reuse counts but still lose on wall-clock for cheap ops.

## Bottlenecks

1. Whole-graph topo walk even when few nodes rechecked.
2. Obligation key construction for every node.
3. Optional defense-in-depth recheck on reuse.
4. Python interpreter overhead vs trivial arithmetic.

## Future optimization directions (not weakening assurance)

- Frontier-only scheduling of unaffected subgraphs.
- Persistent assignments when dep outputs unchanged (still prove eligibility).
- Native/Lean-extracted checkers for expensive obligations.
