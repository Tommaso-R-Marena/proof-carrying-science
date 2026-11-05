# Executed real-data regression and optimal-recovery experiment

PCS now independently certifies global regression optimality, sharp response sensitivity, and the exact uniform minimax recovery radius over arbitrary prediction functions under a declared polynomial/noise model. A separate numerical proof capsule verifies the held-out scores and aggregate comparisons on real Delft yacht resistance measurements. This is a new PCS assurance capability using established regression and minimax mathematics; no world-first physical or mathematical discovery is asserted.

## Observed result

The frozen protocol used all 308 observations, grouped by the five source hull variables, and fitted degrees 1, 2 and 3 separately within each hull. Seven alternating velocity positions trained each fit; the other seven were held out. The same split and all model degrees were retained throughout the complete run. The comparison is retrospective on public archival data, and one engineering pilot preceded the complete campaign. It is not blind external validation or validation on unseen hulls.

Pooled held-out squared errors over 154 observations (approximate decimal display; exact fractions and proofs are retained):

| Degree | Global least-squares SSE | Pointwise minimax SSE | SSE decrease | Hull-group improvements |
| --- | ---: | ---: | ---: | ---: |
| 1 | 19,357.898152 | 7,115.862829 | 63.24% | 22/22 |
| 2 | 4,524.393554 | 1,854.250749 | 59.02% | 22/22 |
| 3 | 467.264787 | 382.970462 | 18.04% | 22/22 |

The minimax estimator is pointwise and may use a different interpolation support at each query. Least squares fits one global polynomial per hull. Their empirical difference can therefore reflect interpolation locality and model misspecification as well as sensitivity optimization; this experiment does not isolate a causal mechanism or establish superiority over other predictive methods. Source groups `hull-03` and `hull-04` have identical 14-response curves, leaving **21 distinct response curves among 22 source hull groups**. Both were retained under the no-exclusion protocol; the groups are not asserted to be independent replications.

## Proved prediction limit

For the fixed training design, a reproducing weight vector and a matching dual polynomial certify

`optimal uniform radius = ε * sum(abs(weight_i))`.

The lower bound applies to every prediction function over that measurement vector, including nonlinear and learned predictors, uniformly over unrestricted real coefficients in the declared polynomial family and all coordinatewise response errors bounded by ε. The matching upper bound is attained by the certified linear estimator. Additional true prior constraints, new measurements, average-case criteria and pointwise guarantees at one observed response vector change that problem. They are not covered by this uniform impossibility statement.

At the unobserved extrapolation query Froude `0.6`, the certified gains are:

| Degree | Least-squares gain | Globally minimax gain | Gain decrease |
| --- | ---: | ---: | ---: |
| 1 | `41/14` | `13/6` | 26.02% |
| 2 | `277/28` | `151/18` | 15.20% |
| 3 | `4465/112` | `611/16` | 4.21% |

These gains depend on the common predictor design and repeat across hulls; they are not 22 independent discoveries. No physical target was observed at `0.6`, so this table is a proved sensitivity statement, not measured extrapolation accuracy. Exact sign-aligned perturbations at ε = 0, 0.001 and 0.01 attained the radii, with independent NumPy least-squares refits checked against their exact predicted shifts.

## Model adequacy result

**Every one of the 66 full-data polynomial classes fails the assumed absolute error budget `0.01` on the recorded responses.** The certified global SSE floor exceeds `14 * (0.01)^2`; `uniform_error_exclusion` then rules out every real coefficient vector fitting all 14 observations within that tolerance. The numerical capsule independently proves the 66 required inequalities. The joint polynomial-plus-error-budget hypotheses are incompatible with these encoded data. The actual measurement error and polynomial applicability were not established. This result prevents treating a correct optimizer or an optimal sensitivity certificate as physical validation.

## Exact qualification and retained evidence

The complete local run used clean source `42f53a634ab70ffa9994a496b1c3027d683874a3`. The original protocol was committed at `d57830e`; the minimax addendum at `60ac23f` precedes the successful pilot, and the all-estimator addendum explicitly records its later timing before the full campaign. No earlier protocol or experiment was overwritten.

- Twenty general Lean theorems and eleven static controls: complete 31-name axiom audit.
- Twenty-two independent real-data receiving processes; 132 fitting certificates and 528 paired least-squares/minimax prediction certificates; 386 exact theorem identities audited per receiver.
- Twelve fresh attack receivers: one valid control, eleven intended rejections, eight separately compiled kernel proofs of certificate falsity. Compiler errors alone never count as refutations.
- Nine additional Lean theorems check all held-out SSEs, both pooled totals, minimax-versus-least-squares inequalities, degree-comparison counts, and the full-data error-budget inequalities.
- Forty focused tests passed without skips. Full real-analysis bridge build completed 8,088 targets and retained the existing audits. The native-authority target passed using retained cache; protected CI must independently qualify the final integration tree.
- Independent arithmetic replay verified all original-row selections, every normal equation, all dual constraints, exact reported errors and 832 byte-inventory checks.

The complete local campaign took 959.933622 seconds on the existing two-core, 8 GiB environment using two isolated receiving workers. These are execution observations, not scale forecasts. Final-head full Python and protected CI qualification are separate from this earlier-source snapshot and are recorded on the integration PR and completion record; no earlier run is relabeled as final-head CI.

Immutable source-qualified evidence: [`local-qualification-42f53a6`](../research/experimental-calibration-v1/local-qualification-42f53a6/README.md). Failed and preceding engineering evidence remains under [`engineering-history`](../research/experimental-calibration-v1/engineering-history/README.md). The complete theorem catalogue, replay commands and trust boundaries are in [the capability document](PCS_EXPERIMENTAL_CALIBRATION_V1.md).

## Adoption boundary

The first protected candidate `32a752c` passed all 1,909 local Python tests with
no skips, but its monolithic numerical capsule exceeded the hosted runner's
2,048 MiB Lean interpreter cap. The static 31-name audit passed; the new CI
real-data campaign had not yet run. The [portability repair](../research/experimental-calibration-v1/numeric-portability-v1/README.md)
retains the identical numeric definitions and nine primary theorem types,
checks 44 supporting row lemmas in separate fresh processes, and preserves both
the 2,048 MiB per-process cap and 180-second total budget. Eight source/data/
metadata substitution controls reject before launching Lean. The failed job,
original capsule and earlier source-qualified results remain unchanged. Later
final-head qualification is recorded separately on the integration PR.

Candidate `aec859b` subsequently passed 1,917 local Python tests without skips
and a clean 53-name numerical replay. Its hosted run also passed that replay
and all 48 calibration tests, then certified hulls 0–13 before the combined
receiving proof reached the same interpreter cap on later hulls. No false
certificate proof was obtained for those resource failures. The receiver now
compiles the identical model namespaces in separate fresh processes, checks
their complete combined inventory and exports their exact source hashes.
The request deadline, memory cap, theorem types, source data, held-out split
and scientific conclusions remain unchanged. The second failed artifact is
retained under `research/experimental-calibration-v1/receiving-portability-v1/`;
qualification of the repaired candidate is separate from these historical runs.

This is an experimental exact-rational regression and optimal-recovery fragment. CSV/source translation, native arithmetic execution correspondence, unknown predictor errors, actual measurement precision, physical model adequacy, generalization and external domain review remain OPEN. The receipts grant mathematical support for the declared finite arrays. `scientific_acceptance` and `pcs_authority` remain false. No learned model was promoted and no external proof-development trace was used for training.

Data: Gerritsma, J., Onnink, R., & Versluis, A. (1981), [Yacht Hydrodynamics](https://doi.org/10.24432/C5XG7R), UCI Machine Learning Repository, [CC BY 4.0](https://archive.ics.uci.edu/dataset/243/yacht+hydrodynamics). Original bytes, full license, citation, retained upstream metadata and exact source hashes accompany the evidence. No new physical measurements, independent outside review, causal finding or population confidence statement is claimed.
