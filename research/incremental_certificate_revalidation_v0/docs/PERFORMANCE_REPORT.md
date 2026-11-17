# Performance report

Measurements on this agent host (America/New_York session date 2026-11-17).
Wall-clock via `time.perf_counter`; peak memory via `tracemalloc` where recorded.

## Cheap ops — negative result (preserved)

Mode: `recheck_on_reuse=False` (ValidState trust). Source: `scripts/run_benchmarks.py`
→ `results/benchmark_report.json`.

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

For **cheap** exact Int ops, incremental verification is **slower** than fresh
recomputation. Bookkeeping dominates the tiny local checks. This negative finding
is retained intentionally.

## Expensive local checks — positive result

Modeled expensive proof-checking via `DelayedRegistry` (`delay_ms` sleep per
`local_check_node`). Source: `benchmarks/expensive_suite.py` →
`results/expensive_benchmark_report.json`.

Cost axes distinguished:

| Axis | What it measures |
|---|---|
| Fresh full recompute | Every node runs local_check (certificate recompute + check) |
| Trusted incremental | `recheck_on_reuse=False`: cache validation / eligibility only on reuse; Affected nodes rechecked |
| Defense incremental | `recheck_on_reuse=True`: every reuse repeats local_check |

| Case | Nodes | Delay/check | Fresh ms | Trusted incr ms | Defense incr ms | Trusted speedup |
|---|---:|---:|---:|---:|---:|---:|
| chain_80_leaf | 80 | 2 ms | ~171 | ~2.7 | ~173 | **~64×** |
| chain_80_root | 80 | 2 ms | ~171 | ~173 | ~172 | ~0.99× (no reuse) |
| chain_200_leaf | 200 | 2 ms | ~426 | ~3.4 | ~430 | **~123×** |
| chain_200_mid | 200 | 2 ms | ~428 | ~214 | ~429 | **~2×** |

### Interpretation

1. When local checks are expensive and changes are sparse, **trusted reuse** yields
   large wall-clock speedups (cache validation ≪ certificate rechecking ≪ full
   mathematical recomputation of every node).
2. Root-heavy / full-affected changes show **no** incremental benefit — expected
   performance failure mode when reuse is empty.
3. Defense-in-depth recheck-on-reuse erases the speedup (every node still pays the
   expensive check). Useful as an adversarial posture, not as a performance path.
4. These timings are synthetic delays, not Lean kernel measurements; they isolate
   cost structure, not production proof-checker throughput.

## Bottlenecks (unchanged)

1. Whole-graph topo walk even when few nodes rechecked.
2. Obligation key construction for every node.
3. Optional defense-in-depth recheck on reuse.
4. Python interpreter overhead vs trivial arithmetic (cheap-ops regime).

## Future optimization directions (not weakening assurance)

- Frontier-only scheduling of unaffected subgraphs.
- Persistent assignments when dep outputs unchanged (still prove eligibility).
- Native/Lean-extracted checkers for expensive obligations.
