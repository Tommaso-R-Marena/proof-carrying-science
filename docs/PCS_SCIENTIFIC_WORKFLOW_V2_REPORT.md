# Real-data scientific workflow v2

PCS now accepts an explicitly typed, previously unsupported finite measurement workflow: descriptive linear least squares on real Palmer Penguins field measurements. It binds original source/data/license bytes, makes measurement units and missing-data policy explicit, packages the result through existing signed PCS v0.6 authority, and independently recomputes every reported coefficient and residual statistic in a separate receiver process.

This is an operational extension from the authored synthetic mass-action workflow to an external empirical dataset. It is not evidence of autonomous scientific discovery, causal inference, learned domain generalization, or a new biological result. The numerical and empirical claims remain **OPEN** in PCS authority.

## Executed result

The final frozen experiment is in [`research/scientific-workflow-v2/final`](../research/scientific-workflow-v2/final). Its [`PROTOCOL.json`](../research/scientific-workflow-v2/final/PROTOCOL.json) was written before execution; [`SUMMARY.json`](../research/scientific-workflow-v2/final/SUMMARY.json) and four independently executed receiver receipts retain the outcomes.

| Observation | Executed result |
|---|---|
| Real input rows | 344 |
| Complete flipper-length/body-mass pairs | 342 |
| Excluded data-row indices (one-based, excluding header) | 4, 272 |
| Exact intercept, kg | `-5332210403/922395080` |
| Exact slope, kg/m | `1145743050/23059877` |
| Exact residual sum of squares, kg² | `24376501721/461197540` |
| Compiled PCS dimension claims | Both `COMPUTATIONALLY_SUPPORTED` |
| Numerical and empirical/causal/population claims | Both `OPEN` |
| Fresh independent receiver processes | Four |
| Identical key/input/archive-parameter reconstruction | Byte-identical ZIP |
| NumPy 2.2.6 independent `linalg.lstsq` baseline | Intercept absolute error `3.552713678800501e-15`; slope error `0`; predeclared tolerance `1e-10` |
| Final focused tests | 39 passed in 7.52 seconds |
| Experiment wall time | 9.001 seconds |
| Process self / child CPU | 4.553 / 5.194 seconds |
| Largest child RSS, Linux | 42,308 KiB |
| New human participation / training / spend | None / none / zero |

Resource values describe this small local execution; they are not scale forecasts. NumPy is an optional independently implemented numerical sanity baseline and grants no authority. The finite-data adapter uses exact fractions and validates normal-equation residual identities; it is not formally refined to Lean.

The positive bundle SHA-256 is `7f503d99a7069a2d3663883520e7c68663241b1f0eed66584bcb343756be8290`. The final unsigned byte-integrity manifest SHA-256 is `63d5bae1493098525085f69138c9a6bb44d7ea05ccf0dbf6f63b8928890e53e7`. The manifest is not an independent reviewer attestation.

## Source and rights

The dataset is real penguin field data collected by Dr. Kristen Gorman and Palmer Station LTER, distributed by `allisonhorst/palmerpenguins`. It was fetched at exact upstream revision `8957207b78d6ccd1b4654a9dd9c9041b657478ab`. Retained [`provenance.json`](../examples/scientific_workflow_v2/provenance.json), [`UPSTREAM_LICENSE.md`](../examples/scientific_workflow_v2/UPSTREAM_LICENSE.md) and [`UPSTREAM_README.md`](../examples/scientific_workflow_v2/UPSTREAM_README.md) record the original attribution, upstream CC0 1.0 dedication, exact URLs and byte hashes. No dataset measurements were invented or relabeled as synthetic.

| Original artifact | SHA-256 |
|---|---|
| `penguins.csv` | `f204db2c753b0937caac3cb35258562c14f073e4bbc76be24b4c51ce22767a93` |
| Upstream CC0 license | `8e2c443dd9aea6fcd6c293dbf66935bd5ef502fc0ca9b466c773cf9316d5e04c` |
| Upstream attribution README | `30248c3c8c97d7b2f3a4bc361f9209c64ad9c53f47169eb9fbb5c2d00fe5db92` |

The new workflow script and contract are authored CC0 artifacts. The receiver checks retained provenance bytes and digests; it does not perform online origin attestation or certify legal adequacy beyond the explicit source declaration. Measurement accuracy, original sampling design and missingness applicability remain assumptions.

## Operational interfaces

`pcs/scientific_workflow_v2.py` supplies a typed contract loader, bounded complete-case CSV evaluator, exact-rational unit conversions, independent centered least-squares calculation, source-derived obligation graph, existing PCS package builder and independently replaying package receiver. It reuses the v1 rational parser, path checks and obligation propagation. The original Claim IR, certificate format, trusted kernel and scientific acceptance rules remain the authorities.

The producer example calculates uncentered normal equations using only the Python standard library. The receiver calculates centered sufficient statistics separately. No submitted scientific project code is executed by discovery, bundle building or receiving. The experiment runner executes only the explicitly authored example producer.

Supported input is a bounded CSV with named positive length/mass columns, exact declared `mm→m`, `g→kg`, or supported identity conversions, and a fixed exclusion rule for missing predictor/response pairs. Data is limited to 4,096 rows and 2 MiB per artifact; intermediate rational sums are checked against 4,096-bit bounds. Malformed, singular, undersized or unsupported inputs fail explicitly. Different scientific algorithms, units, implicit missing-data rules and arbitrary executable submissions require additional adapters.

Reproduce the experiment with a **new** output directory:

```bash
source /workspace/.onboarding/activate.sh
python scripts/run_scientific_workflow_v2.py --output /tmp/pcs-workflow-v2-new
python -m pytest tests/test_scientific_workflow_v2.py -q
```

A researcher can submit a separately prepared eligible workflow, including its contract, original data, source license/provenance and reported result:

```bash
python scripts/run_scientific_workflow_v2.py \
  --project /path/to/project --work-directory /tmp/pcs-workflow-work \
  --output /tmp/workflow.pcs.zip --private-key /secure/producer.pem \
  --public-key /path/to/producer-public.pem --fingerprint PINNED_FINGERPRINT \
  --confirm-reviewed-draft
```

That flag records the caller's explicit bounded-draft confirmation; it is not authenticated independent scientific review. Receive in a fresh process:

```bash
python scripts/run_scientific_workflow_v2.py \
  --replay /tmp/workflow.pcs.zip --public-key /path/to/producer-public.pem \
  --fingerprint PINNED_FINGERPRINT --output /tmp/fresh-receiver.json
```

`pcs_package_valid`, `independent_replay_consistent`, `bounded_contract_satisfied` and `scientific_acceptance` are distinct outputs. A valid signed package can contain falsified or OPEN claims. Bounded success additionally requires matching source/report/obligation replay and both actual compiled dimension decisions being `COMPUTATIONALLY_SUPPORTED`. Scientific acceptance remains false.

## Negative evidence and authority regression

The final signed controls and receiver outputs demonstrate:

- A reported zero slope is a valid signed PCS package but fails the bounded numerical contract.
- An incorrect millimetre-to-metre scale is rejected before calculation.
- A changed applicability premise invalidates transitive cached results.
- A changed measurement byte creates a changed data-binding obligation and invalidates dependent complete-case, numerical and workflow results.
- A false numerical report re-signed with the legitimate ephemeral producer key passes ordinary package integrity and is rejected by fresh algorithm replay.
- A deliberately re-signed `kg/m*m` dimension claim is `FALSIFIED_OR_CHECK_FAILED` under the compiled authority and cannot produce bounded success.
- Focused tests additionally cover float/bool confusion in counts, duplicate/sorted exclusions, missing/nonfinite/negative measurements, singular fits, duplicate columns, ragged rows, path traversal, rational aggregation limits, hash mismatch, altered bundles, wrong producer pins, missing confirmation and a generic external-workflow CLI with dangerous source retained but never executed.

The first execution discovered a meaningful integration bug: PCS's unit grammar parses `kg/m*m` as `kg/(m*m)`. The initial code treated package-level `accepted` as sufficient even though the compiled slope claim was FALSIFIED. That exact initial evidence is preserved unchanged under [`initial-invalid-dimension-expression`](../research/scientific-workflow-v2/initial-invalid-dimension-expression) and is **not a valid positive scientific result**. The renderer now uses `kg*m/m`, Python independently evaluates the dimensional checks, and the receiver explicitly requires the compiled claim decisions. The intermediate green run before dataset invalidation was added is retained under `preceding-no-data-invalidation`; the final acceptance evidence is only `final/`.

## Remaining obligations

There is no source-bound theorem for this Python least-squares adapter, no proof of empirical accuracy or causal/population validity, no authenticated external scientific reviewer, and no learned research-planning or model improvement claim. Exact finite replay is stronger than trusting a producer's signed assertion but is still a computational check under the pinned Python environment. The source-bound formalization of parsing, row selection, rational arithmetic and adapter/kernel correspondence remains OPEN.

The external-domain transfer is one legally cleared observed dataset and one explicit scientific algorithm. It does not establish broad scientific competence. Further progress should add independently reviewed unfamiliar workflows, robust statistical uncertainty and confounding obligations, additional algorithm adapters, and a formally checked least-squares specification with executable refinement.
