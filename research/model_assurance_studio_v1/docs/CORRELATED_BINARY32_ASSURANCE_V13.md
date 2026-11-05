# v0.13: Correlation-preserving binary32 model assurance (experimental)

**Repository path:** `research/model_assurance_studio_v1/`  
**Integration:** additive, draft PR #196; production PCS authorities unchanged.  
**Status:** exact-rational Python experimental checker, **NOT** Lean-verified, **NOT** certified for official ONNX Runtime or any deployed inference engine. The entire local upload server remains a research tool, not a public model-execution sandbox.

## The problem addressed

Conventional interval propagation treats each output independently. Consider a
2-input model with `logit0 = x0` and `logit1 = x0 + 1`, constructed as a
screened `MatMul` followed by `Add` using embedded finite FLOAT32 weights. In
the nonfused, sequential binary32 software-value semantics, each operator
rounds separately. For inputs in `[-1000,1000]^2`, the old output-interval
method establishes only the useless bound

`logit0 - logit1 <= 1999`.

This v0.13 implementation retains **shared input dependencies**, explicitly
bounds per-operation binary32 rounding error, and establishes

`logit0 - logit1 <= -1/2`

on the **entire box**, with no splitting or random input sampling. A short
conservative rational witness is checked against an independently pinned claim
using `studio.affine_fp32_v13.verify`. This is a narrower statement than a
general-purpose soundness theorem for arbitrary programs.

## Mathematical derivation and soundness argument

An affine form is `A = c + sum_i a_i * epsilon_i`, where each independent
symbol `epsilon_i` ranges over `[-1,1]`. The same symbol IDs are retained on
fan-out paths and across output coordinates: this captures correlations.

Each real reviewer input `[l,u]` is represented by center `(l+u)/2` and an
independent radius `(u-l)/2`. This **over-approximates** the representable finite
binary32 input subset.

For a finite exact operand `z` rounded to binary32 RN-even, an absolute
conservative error is

`|RN32(z) - z| <= 2^(-24) * |z| + 2^(-150)`.

The first term is the usual conservative normal-rounding relative allowance,
while the second covers subnormal underflow. We calculate an exact rational
interval `[l,u]` of `z` from the current affine form and append a **fresh,
independent** error symbol whose radius is

`2^(-24) * max(|l|,|u|) + 2^(-150)`.

The checker also attempts exact rational RN-even rounding of both extremes and
**abstains** if either can overflow to a nonfinite result. No probabilistic
independence is assumed. MatMul/Gemm terms and additions are processed in the
specified nonfused order. Exact weights are read from screened embedded FLOAT32
initializers. With ReLU: if the affine input enclosure is wholly nonnegative,
retain the affine form; if nonpositive, return zero; otherwise for `l<0<u` use

`lambda = u/(u-l)`, `E = -l*u/(u-l)` and

`ReLU(z) = lambda*z + E/2 + (E/2)*epsilon_new`.

This follows because `0 <= ReLU(z)-lambda*z <= E` for all `z` in `[l,u]`.
The result is a sound over-approximation **assuming the specified finite
value semantics are correctly implemented**. There is no independence or
statistical approximation in these constructions.

For a linear reviewer claim `sum_j q_j * output_j <= L`, the checker adds the
coefficients of like symbols *before* interval evaluation. Its upper bound is
`sum_j(q_j*c_j) + sum_i |sum_j(q_j*a_ji)|`. If this is at most `L`, the
property is conditionally established for the screened semantics. Rounding
errors that arise from **different** operations keep distinct symbols.

> **TCB and proof status.** This is an argument for why the implementation's
> transformations should be conservative, plus exhaustive exact rederivation
> of each reported claim. It is **not** a kernel-checked Lean theorem. Python,
> `Fraction`, the ONNX wire grammar, the affine code, nonfused arithmetic order,
> host memory and input immutability remain explicitly trusted.

## Model-to-policy binding and operating gate

`studio.affine_envelope_v13.AffineEnvelopeGate` requires:

1. The reviewed SHA-256 digest of the entire externally supplied policy, **not** a digest supplied by the model developer or self-generated certificate.
2. Exact hashes of *both* original and updated model bytes; both must agree with a second Google protobuf model interpretation.
3. A complete previously checked v0.9 exact-real baseline/update plus rounding-error-lift bundle for **every competing class and every region**.
4. A complete v0.13 correlated binary32 certificate for each competing class and region, derived from reviewer-owned requirements rather than the candidate's claims.
5. Input membership as **exact finite binary32 hex words**, checked **before** screened software reference inference. Unknown, out-of-region, changed-model, missing-decoder, or inconsistent requests ABSTAIN.

The policy in this repository is a public fixture, **not an independently
administered trust root**. This is an optional *alternative research proof
route* to the v0.10 partition checker, not a silent replacement of the
existing v0.12 gate. A correlation-aware method may prove some claims with fewer
partitions, but both methods share a Python and screened-ONNX trust boundary.

## Reproduce

From this folder, with Python 3.12+:

```bash
# Independent mathematical replay, no external libraries, no optimizer:
PYTHONPATH=. python -S scripts/reproduce_v13_affine.py
PYTHONPATH=. python -S -m unittest tests.test_affine_random_v13 -v

# Full v0.13 verifier/integration tests require Google protobuf:
PYTHONPATH=. python -m unittest tests.test_affine_fp32_v13 tests.test_affine_http_v13 tests.test_affine_random_v13 -v

# Pinned-policy + two-decoder + screened inference demonstration:
PYTHONPATH=. python scripts/reproduce_v13_affine.py

# Optional untrusted candidate producer (does NOT establish reviewer authority):
PYTHONPATH=. python scripts/generate_v13_affine.py

# Review the correlated model's exact claim using a SHA-256 independently
# obtained from the policy; do NOT copy a hash out of an untrusted certificate:
PYTHONPATH=. python -S -m studio.affine_fp32_v13 \
  samples/demo_correlated_fp32_margin_v13.onnx \
  validation/v13_correlated_reviewer_policy.json \
  validation/v13_correlated_margin_candidate.json \
  --trusted-policy-sha256 POLICY_DIGEST_FROM_SEPARATE_REVIEWER_CHANNEL
```


**Dependency boundary:** `-S` disables third-party site packages, including
Google protobuf. The `test_all_six_trained_iris_margin_certificates` and
`test_caller_mutation_after_gate_creation_does_not_change_admission` tests
intentionally require the independent decoder and will *not* pass if the
entire `tests.test_affine_fp32_v13` suite is run with `-S`. That is a
missing-dependency/abstention outcome, not an invalid mathematical
certificate. The standard-library mathematical replay still checks all six
Iris claims plus the correlation challenge, and reports the combined gate
as `NOT_ESTABLISHED`. Never interpret successful math-only replay as
full model admission or two-decoder verification.

The local drag-and-drop interface adds **Prove a correlated float32 margin**
and **Check selected model correlation**. The upload API returns a *suggested*
reviewer policy and untrusted candidate; it never claims that the browser has
established independent policy custody, Lean proof, or deployed runtime safety.

## Actual evaluations (bounded and deliberately scoped)

- **Synthetic correlation challenge:** old binary32 interval upper `1999`;
  new affine bound `< -1/2`. The exact witness is
  `validation/v13_correlated_margin_candidate.json`.
- **Trained Iris 4→8→3 successor:** six class-margin claims over three
  previously chosen regions rechecked without any partition tree; the
  complete affine proof set is in `validation/v13_affine_iris_candidate.json`.
  The same 27/150 demo coverage as before is retained; the Iris data were
  used in choosing these regions. This is **not held-out coverage evidence**.
- **Randomized soundness checks:** 80 weighted ReLU neural graphs × 24
  binary32 inputs and 40 Gemm graphs × 16 inputs were cross-checked against
  an independent exact sequential binary32 evaluator. Existing trained-model
  and correlation samples received additional enclosures; passing finite
  samples does not constitute a universal proof.
- **C numerical reference:** 50 test inputs for the correlation model agreed
  with the separately compiled, fixed C CPU evaluator. The compiler/CPU/OS
  remain outside the proved mathematical boundary. This is not ONNX Runtime.
- **Adversarial controls:** forged upper bounds, altered model bytes, changed
  policy, removed/reordered competitor proofs, malformed independent decoder,
  model rehashing and out-of-region admissions are rejected.

The entire existing PCS production/Lean authority is unchanged. No model
safety certification, biological/clinical validity, official ONNX conformance,
hardware floating-point correspondence, secure remote ingestion, or general AI
alignment is asserted. A formal semantic bridge and runtime validation remain
research blockers before promotion.
