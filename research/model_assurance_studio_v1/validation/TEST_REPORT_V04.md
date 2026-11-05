# PCS Model Assurance Studio v0.4 — verification and boundaries

Date: 2026-11-04. Environment: Python 3.13, NumPy 2.3.5, Torch 2.10 CPU available for optional independent numerical test. Neither `onnx` nor `onnxruntime` was installed.

## Executed testing

- **112/112** automated tests passed via `python -m unittest discover -q` (unit, integration, adversarial, randomized and receipt tests). No skipped tests in the reference run.
- **11 dense-network tests** checked serialized ONNX with actual weight tensors, exact-rational box checks, float32 reference replay, Gemm, unsupported operators, malformed and nonfinite initializers, tampering, deterministic results, and the HTTP analysis API.
- **5 additional dense hardening tests** checked float32 input-box membership, abstention on an unrepresentable box, subprocess failures, 80 random byte-level mutations, and 24 seeded independent PyTorch-vs-NumPy result comparisons.
- **18 guarded-tool tests** checked allowed/denied synthetic effects, count budgets, concurrent tool proposals, repeated IDs, malformed/counterfeit policies, deny-before-dispatch, HMAC tamper/reorder checks and the guard demo HTTP API.
- The previous **78 v0.3** tests continue to pass, including SBML chemistry, scalar ONNX, safetensors, agent trace and local server checks.
- `node --check studio/app.js` passed.
- A Chromium browser smoke test clicked the **Run neural-network demo** and **Run guarded tool demo** controls, displayed actual FastAPI-generated assessment/guard responses through a stubbed `fetch` transport, produced both preview PNGs and reported **zero JavaScript exceptions**. This is NOT an actual browser TCP-to-server test; administrative restrictions block the latter.

## Concrete neural violation and separately scoped PASS

Artifact: `samples/demo_dense_neural_violation.onnx`. Embedded FLOAT32 identity weight matrix of shape 2x2; biases `[0.25,-0.25]`; `MatMul -> Add -> Relu`, input `[1,2]`, output `[1,2]`.

Requested input box: each input coordinate in `[-1,1]`. Requested output bounds `[0,1]`.

- Exact rational interval propagation is **inconclusive** as a safety guarantee: upper bound for output 0 is `5/4`; the results are correctly `OPEN` at the conditional box checker.
- Bounded exact-rational candidate search found a violating input `[1,1]` after three probes. The candidate is hash-bound to the exact artifact and policy.
- Separate-process NumPy float32 replay produced output `[1.25,0.75]`; output 0 violated the specified upper limit `1.0`. The scoped `ONNX_DENSE_F32_REPLAY` check is `FAIL`, and overall assessment is `FAIL`.
- When the reviewer instead requires output in `[0,1.25]`, exact interval propagation returns `PASS` **for the conditional mathematical real-arithmetic claim only**, while overall report remains `OPEN` and no numerical candidate was required.
- Both emitted receipts passed `--replay`, recomputing the analysis under their embedded policies. The checker is not a separate formal implementation and the receipts are unsigned.

**Not demonstrated:** actual ONNX Runtime execution, float32 universally sound intervals, robustness to all adversarial examples, arbitrary neural model support or a formal Lean theorem.

## Concrete guarded execution

Artifact: `samples/demo_agent_attack_blocked.agenttrace.json`. A fixed host policy controlled the `GuardedDemoRuntime` in-memory tool executor. Of **three proposals**, **one allowed** demo action executed in memory and **two were denied before effect**. The host's HMAC chain self-verification succeeded. Uploaded `executed` entries were ignored as untrusted.

**Not demonstrated:** independent third-party audit of log completeness, external sink deployment, true execution sandboxing, immunity to guard bypass, secure retention/custody, or an authenticated production root of trust.

## Receipt and integration scope

- `validation/v04_dense_violation_receipt.json` — hash-bound local evaluation, replayable with exact source + code.
- `validation/v04_dense_conditional_pass_receipt.json` — separate reviewer thresholds, conditional box PASS and overall OPEN.
- `validation/v04_guarded_synthetic_execution_example.json` — synthetic in-memory execution audit with host-only ephemeral HMAC key. The exported audit can NOT be authenticated by a reviewer without custody of that key, and the recorder itself is not independently trusted.
- The original PCS production v0.6 Lean verification authority has **not** been used or changed. These are untrusted research candidates.

## Overall assessment

The narrow v0.4 workflows perform real mathematical, numerical and in-memory policy tests with scoped findings. This is an improvement in reproducible experiments, **not** evidence of a new general AI safety breakthrough or a deployable certified security appliance. The correct next independently reproducible step is an isolated, pinned ONNX Runtime execution and a real non-bypassable host tool adapter with independently controlled provenance.
