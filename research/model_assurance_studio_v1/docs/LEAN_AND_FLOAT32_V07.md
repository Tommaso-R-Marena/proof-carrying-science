# PCS Model Assurance Studio v0.7 — numerical and formal-verification boundary

**Release status: independently re-executable experimental analysis. Not production certification.**

This update adds a restricted binary32 value-level verifier, a conditional floating-point error lift for existing exact-real certificates, a source generator for Lean Farkas obligations, and an optional genuine ONNX Runtime CPU comparison command. The existing PCS verification authority is not changed.

## Result 1: exact binary32 *value* semantics

`studio/ieee754.py` represents every finite binary32 value as an exact `Fraction`; the rounder uses integer arithmetic to implement nearest-even including subnormal values. Its accepted semantics identify +0 and -0 **as numerical values**, not as IEEE bitwise equivalence. It rejects NaN, infinity and overflowing round results rather than making a claim about exceptional behavior.

`studio/fp32_assurance.py` screens a narrow fixed-shape ONNX subset and evaluates a conservative interval model where every elementary matrix multiply and add is independently rounded to binary32, in increasing dot-product index, with Gemm bias added at the end. ReLU and Identity are exact on finite numerical values. As an elementary consequence of interval arithmetic and monotone round-to-nearest-even, the output interval contains every result obtained under exactly these semantics from a binary32 input vector in the declared input box, so long as no checked operation overflows. No optimizer or neural-model code is executed during checking. Unknown models and overflow are OPEN.

**Not covered:** arbitrary ONNX runtimes, FMA, reassociation, flush-to-zero, reduced precision, NaN/Inf, signed-zero effects, tensor metadata outside the supported subset, GPUs, and host execution environment. `studio/fp32_assurance.py` is still a trusted Python program, not a kernel-checked proof.

### Verify a saved sequential-binary32 receipt

```bash
python -S -m studio.fp32_assurance samples/demo_dense_neural_violation.onnx validation/v07_dense_fp32_reviewer_policy.json --receipt validation/v07_dense_fp32_receipt.json
```

An independently chosen reviewer policy pins SHA-256, input box, output coefficients and upper limit. The browser's policy is **only a suggestion**, not independent authority.

## Result 2: lift existing exact-real proofs into a conditional binary32 error allowance

`studio/fp32_lift_v07.py` accepts an existing independently checked v0.6 exact-real Farkas / activation-case certificate or model-update certificate, computes conservative absolute binary32 rounding-error bounds, and checks whether the reviewer limit still holds after adding that rounding allowance.

Let `u = 2^-24` be binary32 unit roundoff and `η = 2^-150` half the smallest subnormal quantum. Assuming finite correctly rounded elementary operations (and *no* lower-precision or FTZ behavior):

`|RN(z) - z| ≤ u|z| + η`.

For a dot product whose exact absolute input-term sum is at most `S` and that contains no more than `K` primitive roundings, the error recurrence gives:

`E_K ≤ ((1+u)^K - 1) · (S + η/u)`.

The checker allows `K = 2n+1` for `n` multiplication terms, and `2n+2` when a bias is included. Previous-neuron rounding deviations are propagated with `Σ |weight_i| E_i`. Finite magnitude/overflow budgets are checked. This is conservative and can be loose, but it is not a sampled confidence interval. A ReLU is 1-Lipschitz, so it does not increase the absolute deviation.

If the existing exact-real certificate establishes `c·f_real(x) ≤ b` for all *real* `x` in the box, then every representable binary32 input x in that same box satisfies under the specified rounding contract:

`c·f_binary32(x) ≤ b + Σ |c_j| E_j`.

For an updated model, the checker first independently validates the exact-real baseline and same-input drift certificates, then uses:

`c·f_new,binary32(x) ≤ baseline_bound + drift_bound + Σ |c_j| E_new,j`.

The rounding recurrence and relation to real ONNX runtime implementations have **not** been formalized in Lean. Numerical tests of representative PyTorch and NumPy executions are evidence, not proof that all ONNX Runtime kernels honor the assumed contract.

### Re-run the trained-model demonstration

```bash
python -m studio.fp32_lift_v07 relation samples/demo_trained_iris_mlp.onnx validation/v06_iris_property_1_certificate.json validation/v06_iris_property_1_reviewer_policy.json --required-float-upper=-499/1000
python -m studio.fp32_lift_v07 update samples/demo_trained_iris_mlp.onnx samples/demo_trained_iris_updated.onnx validation/v06_iris_property_1_certificate.json validation/v06_iris_property_1_reviewer_policy.json validation/v06_update_drift_certificate.json validation/v06_update_reviewer_policy.json --required-float-upper=-37/100
```

A deliberately substituted model or a changed policy makes the update fail closed. `-37/100` is an *illustrative reviewer requirement*, not a general biological or alignment assurance statement.

## Result 3: Lean 4 source generation, **not yet a kernel proof**

`studio/lean_export_v07.py` refuses to export from an invalid exact-rational certificate and emits a Lean 4 / Mathlib theorem expressing its *pure linear-inequality consequence*, with rational coefficients and a proof script using `ring`, `norm_num` and `linarith`. It also emits the elementary proof-gated-update composition lemma. The file intentionally has **explicit inequality hypotheses** instead of claiming to have Lean-parsed ONNX bytes. It therefore has a **trusted Python translation boundary**, even if compilation succeeds later.

Example commands:

```bash
python -m studio.lean_export_v07 relation samples/demo_trained_iris_mlp.onnx validation/v06_iris_property_1_certificate.json validation/v06_iris_property_1_reviewer_policy.json validation/iris_margin_generated.lean
python -m studio.lean_export_v07 update samples/demo_trained_iris_mlp.onnx samples/demo_trained_iris_updated.onnx validation/v06_update_drift_certificate.json validation/v06_update_reviewer_policy.json validation/iris_drift_generated.lean
```

The actual check must happen under the pinned Lean 4.28.0 / Mathlib toolchain. From the PCS formal Lake environment, for example:

```bash
lake env lean /absolute/path/to/iris_margin_generated.lean
lake env lean /absolute/path/to/iris_drift_generated.lean
```

Or run `python -m studio.lean_status_v07 /absolute/path/to/proof.lean --project-dir /path/to/pcs/formal` and inspect `kernel_checked`. A source file's existence, a Python checker success, a tactic name, or a syntactically plausible proof does **not** establish kernel verification. At release time, Lean/Lake were unavailable here, so generated modules **remain uncompiled**. Even successful compilation would prove only consequences of the generated numerical hypotheses, not the soundness of ONNX parsing or the IEEE error model. A full Lean-certified system still requires those bridges to be formalized and checked.

## Result 4: optional *actual* ONNX Runtime, not a simulated result

`studio/onnxruntime_crosscheck_v07.py` executes the submitted ONNX bytes in a real `onnxruntime.InferenceSession` with CPUExecutionProvider, a single thread and graph optimizations disabled, and compares finitely many output vectors to an independent, exact-rational sequential binary32 software interpreter. It reports the official package version, maximum ULP difference, disagreements and example mismatches. If official ONNX Runtime is absent, it reports `NOT_RUN` and exits nonzero; there is **no fake fallback**.

On your own trusted local machine, optionally install `onnx` and `onnxruntime` as supported by your Python platform, then run:

```bash
python -m studio.onnxruntime_crosscheck_v07 samples/demo_trained_iris_mlp.onnx --count 96 --timeout 50 --output validation/your_real_onnxruntime_comparison.json
```

**Security warning:** The ONNX Runtime adapter loads model data into a native C++ runtime. Its subprocess and timeout are *not* a security sandbox. Do not run the optional adapter on untrusted third-party files without a separate hardened process/container/VM and resource policy. The drag-and-drop web server does not expose this execution route.

Even a successful CPU crosscheck establishes agreement for a finite test set, not a universal equivalence theorem, not float32-runtime soundness, and not AI alignment safety. An observed difference is evidence that the model of numerical behavior or the exact rollout order needs refinement.

## What it still takes to complete the original ambitious objective

1. **Actually compile** the Lean proof code under a pinned toolchain and fix any resulting errors; the current environment had no Lean binary or downloadable packages.
2. Extend the Lean semantics beyond pure inequality consequences to prove the restricted ONNX graph decoder, polytope construction, interval abstract interpreter, finite roundoff budget and source-to-certificate binding.
3. Install and run the **official** ONNX Runtime in hardened local isolation, compare the screened graph to its actual kernel behavior, and develop operator-level conformance proofs or enforce runtime-specific numerical contracts.
4. Extend from screened dense feedforward FLOAT32 ReLU networks to meaningful safety properties for production models; independently validate assumptions and negative results with real partners.

**No generalized AI safety, deployment authorization, clinical validity, standard-level IEEE verification, or universal ONNX Runtime correspondence is claimed.**
