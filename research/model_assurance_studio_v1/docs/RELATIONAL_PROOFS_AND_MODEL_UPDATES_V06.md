# Proof-carrying neural relations and model updates (v0.6 research)

**Status:** working, narrowly scoped experimental research. **Not** a Lean-kernel proof, arbitrary ONNX verifier, secure sandbox, model-alignment assessment, or deployment authorization.

## The core idea

The developer proposes a model and optionally a proposed certificate; the reviewer chooses the actual **input region, desired output relation, update budget, and source-model identities**. Proof discovery may use numerical LP/MILP tools, but approval comes from an independent exact-rational checker running without those tools.

For a supported fixed-weight feedforward ONNX ReLU network `f` and a reviewer-owned input box `B`, the primary claim is:

`forall x in B, c dot f(x) <= u`.

The checker reconstructs `A z <= b`, a conservative polyhedral outer approximation of every exact-real execution from the actual screened ONNX bytes, and translates the requested output relation into a vector `d` over model variables. The untrusted prover supplies a sparse list of nonnegative rational multipliers `lambda` for individual rows. The standalone checker accepts only when:

- `lambda >= 0` exactly;
- `sum(lambda_i * A_i) = d` exactly;
- `sum(lambda_i * b_i) <= u` exactly;
- the certificate matches the exact SHA-256 of the submitted ONNX bytes and independently supplied reviewer box / relation / bound.

For every *real-arithmetic* model execution, `A z <= b` implies `d z <= lambda dot b <= u`. Thus the proof does **not** trust the LP optimizer's status, floating-point output, confidence score or stopping criterion. Exact rational calculations are recomputed from the serialized float32 weights interpreted as exact rational values; this alone does **not** bound floating-point rounding error when a runtime executes the graph.

### Complementary activation-cover proof

Global linear ReLU relaxations can be loose because they forget nonlinear correlations. `studio/activation_proof.py` proposes a complete binary ReLU phase tree. Every internal split covers **both** mathematical possibilities (`z <= 0`, `z >= 0`); every leaf verifies the goal or verifies exact infeasibility with a Farkas witness. The independent verifier checks full coverage, source binding, claim, and every leaf. Missing branches, fabricated multipliers, or unsupported operations fail closed. The approach is exponential in the worst case, so strict leaf/operation/resource budgets yield `OPEN`, not success.

Example: for `f(x) = ReLU(x) - ReLU(-x) - x`, the standalone checker establishes both `f(x) <= 0` and `-f(x) <= 0` over `[-1,1]`, hence `f(x)=0` **within the screened exact-real semantics**, even though global intervals and the tested global relaxation are inconclusive.

### Proof-gated model updates

For two models `f_old`, `f_new` on the **same mathematical input x**, the proposed model-update certificate proves:

`forall x in B: c dot (f_new(x) - f_old(x)) <= delta`.

`studio/update_kernel.py` reconstructs a joint polytope, explicitly equates the input vectors and matches only structurally identical exact-valued subexpressions between old and new models (including the exact rational interpretation of weights). It checks the update inequality using the same rational dual method. Both the old and new model's byte digests appear in the certificate and the separately pinned reviewer policy. No side-by-side independent input comparison, model-name substitution, or weakened domain is accepted.

**Composition rule:** if the baseline certificate establishes `c dot f_old(x) <= b` and the update certificate establishes `c dot (f_new(x)-f_old(x)) <= delta` on the same reviewer box, then `c dot f_new(x) <= b+delta`. Acceptance also requires `b+delta <= reviewer_required_limit`.

A guarantee about a single output relation on one small box is **not** proof of general safety or performance, even if all certificates check. If the baseline has no accepted guarantee, a small update delta does not imply a safe model.

## Run the independent reviewers, no numerical or ML dependencies

From the project root, assuming standard Python 3.10+:

```bash
python -S -m studio.verify_relational samples/demo_relational_margin.onnx validation/v06_relational_margin_certificate.json validation/v06_relational_reviewer_policy.json
python -S -m studio.verify_relational samples/demo_activation_identity.onnx validation/v06_activation_identity_certificate.json validation/v06_activation_reviewer_policy.json
python -S -m studio.verify_relational samples/demo_trained_iris_mlp.onnx validation/v06_iris_property_1_certificate.json validation/v06_iris_property_1_reviewer_policy.json
python -S -m studio.verify_update drift samples/demo_trained_iris_mlp.onnx samples/demo_trained_iris_updated.onnx validation/v06_update_drift_certificate.json validation/v06_update_reviewer_policy.json
python -S -m studio.verify_update compose samples/demo_trained_iris_mlp.onnx samples/demo_trained_iris_updated.onnx validation/v06_iris_property_1_certificate.json validation/v06_iris_property_1_reviewer_policy.json validation/v06_update_drift_certificate.json validation/v06_update_reviewer_policy.json --required-new-upper=-3/8
```

**Negative control** (must exit nonzero): replace `demo_trained_iris_updated.onnx` with `demo_trained_iris_bad_update.onnx` in the final command.

## Trained-network experiment (not a frontier-AI study)

`tests/make_iris_trained_model.py` trained a small 4-input, 8-hidden-ReLU, 3-logit PyTorch classifier on 105 **real Iris measurements** with deterministic seed 1991, then evaluated on 45 held-out measurements (41/45 = **91.1%** accuracy). Its learned float32 matrices were serialized into the restricted ONNX protobuf format (official ONNX/ONNX Runtime were unavailable). A distinct screened NumPy interpreter compared outputs against fresh PyTorch computation across all 150 Iris records; max abs output difference `3.814697265625e-6`, mean `3.931919733683268e-7`. This is numerical cross-check evidence, **not** proof of official ONNX Runtime equivalence.

Two class-margin relations were independently certified over one **four-dimensional local box** around a correctly classified held-out sample, not over all possible Iris features. The example update changes one output-layer bias by `1/8`; the independent checker accepts an exact drift bound `1/8` and composes it with a baseline `1/2` margin guarantee to infer updated margin `>= 3/8` over that same local box. A malicious altered-bias model is rejected under the same reviewer policy. Those thresholds are illustrative, not claims of biological or clinical fitness.

## Trust and operational boundaries

- **Trusted computational base:** local Python interpreter, Python `fractions.Fraction`, the restricted ONNX protobuf/screening code and the exact checker itself; the machine and input source must be trusted. No Lean proof has been produced for this verifier.
- **Untrusted proposal:** SciPy/HiGHS numerical LP and MILP, any heuristic discovery, the developer-proposed model, and certificates before independent checking.
- **Input trust:** a reviewer must **independently** pin the two model SHA-256 digests, input box, coefficient vector, and acceptance bound. An assessment-produced *suggested reviewer policy* is not trusted merely because PCS generated it. Unsigned hashes protect against accidental alteration, not a malicious party able to replace the whole package.
- **Numerical semantics:** the guarantees describe mathematical real arithmetic with IEEE-754 float32 weights interpreted as exact rationals. Real hardware introduces rounding, reduced precision, fused kernels and platform dependencies not covered here.
- **Supported grammar:** screened dense, fixed-weight, feedforward 1xN float32 ONNX subset: restricted `MatMul`, default `Gemm`, `Add`, `Identity`, `Relu`, constrained shapes/initializers and budgets. No custom operators, stateful agent tools, training behavior, generative sequence models, dynamic shapes, official runtime equivalence, general tensor operators or stochastic semantics.
- **Safety, science and security:** No proof of absence of prompt injection, jailbreaks, privacy leakage, systemic bias, clinical validity, scientific inference adequacy or a production non-bypassable enforcement boundary. The localhost drag/drop app is **not** an adversarial multi-tenant upload service.
- **Failure behavior:** unsupported models, numerical optimization failures, missing certificates or policy mismatches yield `OPEN` or rejection; never a universal safe label.

## Path to genuinely stronger assurance

1. Prove the restricted graph interpreter, outer-polytope reconstruction, activation cover and exact checker in Lean with exact serialization bridges.
2. Specify a precise IEEE-754 semantics and obtain conservative error bounds or execution-trace proof checking; independently reproduce behavior in pinned **official ONNX Runtime**.
3. Add typed reviewer-owned real-world properties and model lineage governance, not arbitrary user-input trust promotion.
4. Run independent external validation, publish negative tests, and review the security/deployment boundary with experts.

This work is based on standard Farkas/LP duality, convex relaxations and activation splitting. We do **not** claim a novel mathematical theorem or a new general AI-safety guarantee. Its contribution is a coherent working proof-gated model-update workflow with an independently executable exact checker.
