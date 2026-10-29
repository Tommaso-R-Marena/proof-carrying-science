# Bounded-wire / large-intermediate-rational resource probe

Actual Lean launches: 13; cases: 13; cases with issues: 0; timeout: False.

Each row includes a fresh actual Lean `--run` process and its startup/Main elaboration/IO/receiving. These are descriptive end-to-end measurements, not isolated receiver timing or asymptotic results.

| Case | Wire bytes | Largest intermediate denominator digits | Actual accepted | Cold process seconds | Status |
|---|---:|---:|---|---:|---|
| n00-physical-0 | 79 | 1 | True | 2.462697 | evaluated |
| n00-physical-1 | 79 | 1 | True | 2.333228 | evaluated |
| n08-physical-0 | 317 | 72 | True | 2.615642 | evaluated |
| n08-physical-1 | 317 | 72 | True | 2.528922 | evaluated |
| n16-physical-0 | 555 | 144 | True | 2.486830 | evaluated |
| n16-physical-1 | 555 | 144 | True | 2.522741 | evaluated |
| n32-physical-0 | 1029 | 288 | True | 2.502708 | evaluated |
| n32-physical-1 | 1029 | 288 | True | 2.622862 | evaluated |
| n64-physical-0 | 1973 | 576 | True | 2.570507 | evaluated |
| n64-physical-1 | 1973 | 576 | True | 2.701773 | evaluated |
| n64-wrong-bound-environment | 1973 | 576 | False | 2.474450 | evaluated |
| temporary-negative-physical-0 | 88 | 1 | True | 2.699465 | evaluated |
| temporary-negative-physical-1 | 88 | 1 | False | 2.520478 | evaluated |

Total observed wall time: 33.060454 seconds; global budget 120.0 seconds.

All submitted rational operands remain within the unchanged 10^18 bound. Pairwise coprimality was checked by gcd, without claiming primality. The two schedule halves cancel to a bounded final value; the transient-negative controls distinguish physical from algebraic scope. Every actual response, raw input and process output is preserved. No source generation or training occurred.

Finite targeted resource falsification attempt, not an asymptotic bound, hard worst-case guarantee, standalone-native benchmark, protected execution root, empirical model validation or production authority. Successful cold-start timings do not isolate receiving cost.
