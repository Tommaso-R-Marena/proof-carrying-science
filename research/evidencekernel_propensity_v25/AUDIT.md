# V25 adversarial and assurance audit

## Verified executable checks

1. Confirmed exact agreement with V24 when **every upper ceiling equals the original exact reference propensity** and the registered strategy and alpha budgets are unchanged. The V24 reference bound is reproduced byte-for-byte as an exact rational.
2. Exact one-sided propensity bias identity checked over five reference values, four ceilings, three actual probabilities below each ceiling, and all four binary potential-outcome pairs.
3. Exact K=1 interval-failure correction checked against all compatible two-unit binary outcome/label/assignment combinations.
4. Exhaustive four-unit binary potential-outcome schedules with adaptive stop and two differently state-dependent actual treatment probability laws bounded by stated ceilings. The conditional false-exclusion probability never exceeds the chosen nominal alpha (`1/2`) in these bounded test spaces.
5. Exact 64-unit binomial propensity mismatch attack: `p_actual=9/10` but `q=cap=1/2` rejects in `k=43,...,64` treated-count cases, producing false discovery probability > 0.999999. With a valid `cap=9/10`, reference `q=1/2` or `q=9/10`, no treated-count case rejects under the same registered tuning.
6. Altered protocol/evidence pins, bad upper rational representation, impossible strategy weights, overspent alpha, impossible stopping and unsupported calibration budget are rejected.
7. Differential agreement between independent Python `Fraction` and Node.js `BigInt` calculations for the complete signed-*locally* example, 80 independently generated bounded test protocols, the exact piecewise-linear sensitivity frontier and tampered pin variants.
8. Exact sensitivity-frontier boundary tested by replay with ceilings increased by half the computed frontier, exactly to the frontier and just beyond it. The strict rejection disappears exactly at the rational threshold in this demonstration.

## What was NOT verified

- No original theorem is claimed; the martingale and sensitivity ingredients have established prior art.
- No Lean kernel theorem for the implemented combination was built.
- No prospective real-world scientific study, independent entropy beacon, physical assignment log, laboratory validation, externally timestamped registration or trusted upper-propensity calibration was used.
- The calibration `delta` parameter is accepted as a stated premise, not inferred from real reference measurements.
- Marginal randomization frequencies, recorded probabilities, JSON hashes or forged signatures do **not** establish a true sequential conditional upper bound.
- Finite-model enumeration and randomized differential tests are implementation evidence, **not** proofs for all unbounded physical experiments.
- The current code's limits (cohort ≤100,000, states ≤16, strategies ≤16) and rational-size budget may restrict computational usability on extremely long prefixes. No cross-platform performance certification is claimed.

## Review-required proof obligations

A reviewer should independently formalize `E_p HT(q) - tau = (p-q)*(Y1/q+Y0/(1-q))`, conditional Hoeffding supermartingale composition, pathwise top-K outcome-interval correction, Bonferroni spending over preregistered references and optional stopping, and the exact piecewise-affine frontier crossing. Additional external review should challenge whether any proposed propensity ceiling is physically defensible after conditioning on participant characteristics, enrollment order and the recorded history.
