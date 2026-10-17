# Proof-carrying calibration on real experiments

The complete [executed experiment report](PCS_EXPERIMENTAL_CALIBRATION_V1_REPORT.md)
records all 22 hull groups, exact comparison proofs and scientific limits.

This extension checks finite regression and pointwise robust prediction proposals
with fresh Lean proofs. It is separate from PCS scientific acceptance and package
authority. Its empirical case uses the original 308 resistance observations from
22 hull forms in the Delft yacht hydrodynamics dataset, distributed by UCI under
CC BY 4.0. This is a retrospective computational experiment on archived physical
measurements. PCS did not collect new physical measurements or obtain independent
domain review.

## Mathematical contracts

The general library is `formal/real/PCSReal/Calibration.lean`. A finite design
matrix, responses, coefficient vector and query features have explicit types.
Theorems have namespace `PCSReal.Calibration`:

| Theorem | Exact mathematical content |
| --- | --- |
| `normal_orthogonal` | Normal equations imply residual orthogonality to every model displacement. |
| `loss_decomposition` | Every alternative coefficient vector has loss equal to the certified loss plus a sum of squared prediction differences. |
| `global_minimum` | The normal-equation solution minimizes finite squared loss over **all real coefficients**. |
| `model_exclusion` | Any threshold below that loss is unattainable by the entire declared model class. |
| `uniform_error_exclusion` | If the certified loss floor exceeds the sum-of-squares budget implied by a uniform error tolerance, no coefficient vector can fit every recorded response within that tolerance. |
| `reproduction_prediction` | Feature-reproducing weights evaluate any model in the declared linear span exactly. |
| `dual_prediction` | A row-span dual witness equates the weighted response with the fitted query. |
| `response_perturbation_bound` | Coordinatewise response changes bounded by ε change a weighted query by at most ε times the sum of absolute weights. |
| `sharp_perturbation_attained` | A sign-aligned admissible response change attains that bound. |
| `sharp_radius_iff` | A uniform perturbation radius works exactly when it is at least that sharp bound. |
| `physical_enclosure` | If the actual response errors obey the stated bound around a model in the declared span, feature reproduction gives a conditional enclosure of its query value. |
| `dual_gain_lower_bound` | A polynomial bounded by one on the training design lower-bounds the absolute-weight sum of **every** feature-reproducing linear estimator. |
| `minimax_weights_optimal` | A matching primal/dual witness proves global minimum sensitivity among that entire estimator class. |
| `minimax_radius_lower_bound` | Every reproducing estimator's valid uniform error radius is at least the certified minimax radius. |
| `any_estimator_radius_lower_bound` | Two indistinguishable admissible signals force a uniform lower bound for every prediction function, without assuming linearity. |
| `minimax_over_all_estimators_iff` | A prediction function with a uniform recovery radius exists exactly when that radius is at least the certified minimax value. |
| `fit_check_sound` | A finite exact-rational normal-equation check implies the real normal equations. |
| `cast_loss` | Exact rational squared loss embeds into the real squared loss. |
| `dual_check_sound` | A rational query-reproduction/row-span witness implies its real counterpart. |
| `minimax_check_sound` | Rational reproduction, bounded dual polynomial and matching objective witnesses imply the real minimax premises. |

Eleven static controls in `PCSReal.CalibrationControls` are `good_normal`,
`wrong_coefficient_rejected`, `exact_nonzero_residual`, `good_dual`,
`wrong_dual_rejected`, `sharp_gain`, `good_minimax`, `false_minimax_rejected`,
`smaller_uniform_radius_impossible`, `nonlinear_radius_two_impossible`, and
`uniform_noise_floor_impossible`. The complete static inventory has 31
names. Axiom audits permit only `propext`, `Classical.choice`, and `Quot.sound`,
or fewer. Every supported literal proposal has its own exact audited identities.

## Real-data protocol

The original protocol and the separately dated minimax addendum are preserved in
`research/experimental-calibration-v1/`. The addendum was frozen during engineering
development, before a successful pilot and before a complete 22-hull analysis.
This is not blind evaluation or an external preregistration.
The additional all-estimator theorem was recorded in a separate addendum after
that engineering pilot and before the complete campaign. The original protocols
were not rewritten.

All original rows are retained. Hull identity is the exact first five source
columns. Each hull has 14 distinct Froude values. Sorting those values determines
seven even-position training rows and seven odd-position held-out rows. The
predictor transformation is exactly `x = 40 * Froude`; source predictors and
responses are dimensionless. All degrees 1, 2 and 3 are evaluated for every hull.
Held-out observations do not enter those fits. Separate full-data fits certify
the best possible empirical loss of each class; they are labeled diagnostics.
Training Froude values run from `0.125` through `0.425`; the held-out `0.45`
measurement is also a small extrapolation beyond that training range.

At every held-out query and at extrapolation Froude `3/5`, the producer supplies
least-squares dual weights and a separate minimax primal/dual witness. The latter
is a **pointwise linear estimator**; different queries can use different weights.
It is not claimed to be one globally fitted polynomial curve. Gains depend on
the shared predictor design, so repeating a gain on 22 hulls is not 22 independent
discoveries of that gain. Response-sensitive prediction errors are reported for
all hulls and degrees.

Perturbation sizes `0`, `1/1000` and `1/100` are declared sensitivity scenarios,
not measured instrument precision or confidence levels. Actual sign-aligned
perturbation runs and independent NumPy refits accompany the algebraic bounds.
Finite held-out errors do not imply population coverage, causal effects, or
accuracy at the extrapolated point, which has no observed target.

The all-estimator lower bound is **uniform** over unrestricted real polynomial
coefficients and all allowed response errors at the fixed design. It covers
nonlinear and learned prediction functions under that same guarantee. It does
not assert pointwise optimality at each observed response vector, average-case
optimality, or impossibility for methods with additional truthful prior
constraints or measurements. The matching upper bound is attained by the
certified reproducing linear estimator. The synthetic indistinguishable-signal
argument is a mathematical limitation, not another physical experiment.

## Receiver and replay

`pcs/calibration_kernel_v1.py` is the experimental receiver. It accepts bounded
`x,y` CSV, a contract fixing current data hashes, degrees, fit rows and query
points, and a separate untrusted numerical certificate. Duplicate keys,
noncanonical certificate rationals, inconsistent hashes, extra fields, ambiguous
row selection and executable text are rejected. It never executes supplied Lean,
optimizer code or model checkpoints. Fixed proof text contains only bounded
validated rational literals and numeric indices.

The candidate producer in `pcs/experimental/calibration_proposer_v1.py` uses exact
Gaussian elimination and finite interpolation-support enumeration. Its algorithm
and search completeness are not trusted for support. The receiver freshly
compiles its own general library, checks each literal normal equation, exact SSE,
dual relation and minimax inequality, and audits the entire generated inventory.
Each declared model runs in a separate fresh Lean process. The exported
`proof-units/ReplayModel*.lean` files contain the exact original model namespace
from `Replay.lean`, with its complete axiom-audit targets. The receiver binds
each unit's bytes and requires the union of all audited identities before
granting support. All processes share one request deadline and the existing
2,048 MiB per-process cap. `Replay.lean` remains the complete readable proof;
the smaller exported units are the sources actually compiled under that cap.
False coefficients, residuals, dual weights or sensitivity gains grant no support.
Compiler failure, timeout and missing dependencies never count as a refutation
or a positive proof.
For a mathematically invalid finite witness, a separate generated theorem
`PCSCalibrationRejected.certificate_rejected` must compile and pass its own
axiom audit before the receiver reports `CERTIFICATE_FALSIFIED`. Ordinary compiler
errors alone retain an unsupported status. This refutes the submitted numerical
certificate, not the physical experiment or the whole polynomial model class.

The aggregate numerical comparisons use a separate portable proof package:
22 row modules supply 44 supporting calculation lemmas, and a final module
assembles the same nine primary theorem types. Data definitions and primary
statements are compared byte-for-byte with the retained original capsule.
Fresh compilation audits all 53 primary/supporting identities within a 180-second
total kernel budget and the same 2,048 MiB cap per process. Supporting lemmas
are proof-engineering certificates rather than additional experimental findings.
The original capsule and its first hosted-run memory failure are retained in
the [portability record](../research/experimental-calibration-v1/numeric-portability-v1/README.md).

Each receiving request has a total kernel budget of at most 300 seconds (default 180),
sequential elaboration and a 2,048 MiB memory limit per Lean process. Input limits
are 2 MiB per raw artifact, 2–64 rows, 1–6 declared models, polynomial degrees
1–3, and at most eight queries per model. Not every maximum-size request is
guaranteed to finish within those limits. Pinned Lean 4.28.0 and Mathlib at
`8f9d9cff6bd728b17a24e163c9402775d9e6a365` remain trusted installed dependencies.

For the real-data experiment, with pinned Lean/Mathlib and NumPy available:

```sh
python scripts/run_experimental_calibration_v1.py --output /tmp/pcs-yacht-new
```

Each hull directory includes its exact CSV, contract, proposed certificate,
metrics and fresh receiving receipt. A single request can be independently replayed:

```sh
python -m pcs.cli calibration-kernel-v1 \
  --data /path/hull-00/data.csv \
  --contract /path/hull-00/contract.json \
  --certificate /path/hull-00/certificate.json \
  --output /tmp/pcs-calibration-receipt-new
```

Completed mathematical replay receipts use a new directory and retain byte
inventories, exact proof text and receiving-source snapshots. Malformed-intake
errors retain diagnostics; the attack campaign also inventories their attempted
inputs. These are source-bound research receipts, not signed
PCS package acceptance or independent reviewer attestations.

## Remaining scientific assumptions

The mathematics establishes properties of exact arrays reconstructed by the
receiver. CSV/source parsing, data selection and Python/Lean implementation
correspondence are not universally refined. The optimizer is untrusted, while
installed compiler/dependency artifacts and the native environment remain trusted
infrastructure. Data origin is retained provenance, not online origin attestation.
Dataset licensing and attribution are preserved in the example directory.

Unknown predictor errors, true measurement error bounds, applicability of the
polynomial model, physical extrapolation validity, population generalization and
external domain review remain open. Mathematical support cannot close these
obligations. `scientific_acceptance` and `pcs_authority` remain false. This is a
new PCS verification capability using established regression and minimax
mathematics, not a claim of a world-first mathematical or physical discovery.

Sources: [UCI dataset and license](https://archive.ics.uci.edu/dataset/243/yacht+hydrodynamics),
[dataset DOI](https://doi.org/10.24432/C5XG7R).
