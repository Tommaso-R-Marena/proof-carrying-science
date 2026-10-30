# Performance and comparisons

Raw data: `results/benchmarks.json`, table: `results/summary.md`. These were measured on a single CPU core in the build
sandbox, with Python 3.11 (standard-library `Fraction`) and Lean 4.28.0. Times are wall-clock times.

## Certified sandwiches (all bounds hold for the infinite chain)

| case | core (box) states | P (≈) | certified U/L − 1 | synth (s) | Python check (s) | cert size |
|---|---|---|---|---|---|---|
| A birth–death N=10 | 10 | 9.78e-4 | 4.2e-8 | 0.06 | 0.001 | 1.6 KB |
| A birth–death N=40 | 40 | 9.09e-13 | 2.2e-7 | 0.51 | 0.002 | 6 KB |
| A birth–death N=80 | 80 | 8.27e-25 | 4.6e-7 | 1.39 | 0.004 | 13 KB |
| B gene expression N=40 | 600 | 6.13e-6 | 2.7e-7 | 2.4 | 0.06 | 81 KB |
| B gene expression N=60 | 900 | 1.65e-9 | 3.8e-7 | 3.7 | 0.09 | 124 KB |
| B gene expression N=80 | 1200 | 2.32e-13 | 1.4e-5 | 5.3 | 0.12 | 171 KB |
| C modulated growth N=20 | 800 | 5.06e-6 | 2.2e-7 | 22.5 | 0.10 | 109 KB |
| C modulated growth N=30 | 1200 | 3.91e-8 | 3.1e-7 | 38.8 | 0.14 | 168 KB |
| C modulated growth N=40 | 1600 | 5.19e-10 | 4.0e-7 | 55.0 | 0.20 | 230 KB |
| C modulated growth N=60 | 2400 | 2.80e-13 | 5.7e-7 | 100.9 | 0.30 | 354 KB |

In Example A the exact gambler's-ruin value lies inside every certified interval (`exact_in_sandwich` in the JSON).
Lean also proves the closed form symbolically (`bd_exact`).

## Lean (verified checker) validation via `native_decide`

| file | certificate | time |
|---|---|---|
| `Examples/BDcert.lean` | A, N=20 | 8.4 s |
| `Examples/GeneCert.lean` | B, N=40 | 10.1 s |
| `Examples/XYsmall.lean` | C, N=20, box 20×25 | 11.2 s |
| `Examples/XYmain.lean` | C, N=30, box 30×40 | 13.2 s |

A full `lake build` of the library takes about 25 s when the Mathlib cache is present.

## Comparison with finite-state projection (same core box)

FSP on the box gives the rigorous bracket `[L_FSP, L_FSP + P_exit]`, where `P_exit` is the probability of leaving the box
before absorption. This uses the same core states as our certificate, so the comparison is like for like.

| case | true P (≈) | FSP upper | our upper |
|---|---|---|---|
| C, N=60, box 60×40 | 2.803e-13 | 5.15e-13 (84% over) | 2.803343e-13 (5.7e-7 over L) |
| C, N=30, box 30×22 | 3.906e-8 | 7.15e-4 (uninformative) | 3.9087e-8 (6.4e-4 over L) |

*Interpretation.* FSP charges every unit of probability that leaves the box as "target reached". Our upper
certificate charges it at the value of the certified tail function, which is tiny where the exit happens
(at large enzyme counts `Y`, X is unlikely to grow). This is the weighted interface effect. FSP with a much
larger box also becomes tight, so this is a constant-factor and box-size advantage, **not a proven asymptotic separation**.

## Comparison with stochastic simulation (SSA)

With 20,000 Gillespie trajectories per case (0.2–1.8 s per case), we observed 0 hits for every event with
`P ≤ 1e-6`. Hence naive Monte Carlo at this budget yields only the trivial 95% upper bound of about `1.5e-4`, and
no relative accuracy. Importance sampling and splitting would do far better, but they give statistical, not
certified, answers. We did not implement them.

## Robust parameters (Example C, N=30, all five rate constants independently uncertain)

| uncertainty | robust U | robust L | constant-vertex U (growth-favouring) | constant-vertex L |
|---|---|---|---|---|
| ±1% | 7.575e-8 | 2.008e-8 | 7.575e-8 | 2.008e-8 |
| ±5% | 1.032e-6 | 1.358e-9 | 1.032e-6 | 1.358e-9 |

The single robust certificate (about 10 s) matches the extreme constant-parameter certificates to 5 digits. This
indicates that the per-state worst case over the interval introduces almost no conservatism here. Sensitivity is large,
however: ±5% in the rates moves P over three orders of magnitude.

## Complexity (informal, not proved in Lean)

Let the box have `n = ∏ box_i` states, with `R` reactions of maximal order `k` in `d` species.
* Checking the core is `O(nR)` exact rational operations.
* The interface layer has `O(R·n/min box_i)` comparisons.
* The cell checks for each face require `O(R·(k+1)^d)` falling-factorial coefficients.
* The escape certificate check is `O(nR)`.

So the verifier is linear in the certificate size. The certificate size is the box size, which must contain the
region that carries most of the probability flux toward the target. For Example C it grows as `O(N·M)`. Synthesis
is dominated by an iterative linear solve in floating point, followed by exact repair.
