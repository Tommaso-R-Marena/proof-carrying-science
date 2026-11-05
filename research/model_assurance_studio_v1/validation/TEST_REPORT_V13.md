# PCS Model Assurance Studio v0.13 — local research qualification

**Status:** the five separately run regression groups all completed with code 0. These local results are not hosted PCS full-repository CI, an independent security audit, official ONNX Runtime conformance, or Lean kernel verification. Earlier single-process attempts exceeded the test runner limit without yielding a verdict; those attempts were not counted as passes.

| Group | Tests passed | Nested subtests (reported separately) | Runtime |
|---|---:|---:|---:|
| Intake / v0.3 / scientific inspectors / agent guard / dense networks | 112 | 29 | 17.94 s |
| Adversarial/legacy / strict ONNX / independent protobuf decoder | 55 | 120 | 11.40 s |
| Float32 / relational proofs / update proofs / reviewer pinning | 62 | 37 | 3.27 s |
| Direct FP32 / operating envelope / native C / HTTP hardening / nonlinear identity / new affine proofs + HTTP + random models | 75 | 205 | 15.77 s |
| MILP challenger | 14 | 6 | 10.98 s |
| **Total** | **318** | **397** | — |

**Additional new research checks:**

- The serialized correlation challenge has plain binary32 interval upper bound `1999`; the independently recomputed affine certificate proves the reviewer limit `-1/2` on the same full `[-1000,1000]^2` domain.
- Six conditional class-margin checks on the genuinely trained Iris successor over three preselected, non-held-out model regions pass without any partition-tree leaf certificate.
- `python -S scripts/reproduce_v13_affine.py` reruns all seven mathematical claims with no third-party dependency. Without Google protobuf, the *full* two-decoder gate reports `NOT_ESTABLISHED`, not acceptance.
- With Google protobuf available, the reviewer-controlled gate verifies both original/updated model decoders and all six earlier exact-real-update and affine binary32 claims, conditionally executes three approved screened software inputs, and **abstains** for the out-of-region input.
- Seeded randomized enclosures covered 80 weighted ReLU graphs × 24 binary32 inputs and 40 Gemm graphs × 16 binary32 inputs. Finite sample coverage does not prove universal transformer soundness.
- The compiled, fixed C evaluator matched the exact software-reference *numeric values* on all 50 preselected/deterministic correlation-example inputs. C/CPU/build environment remain unverified and this is not official ONNX Runtime.
- Fake certificates, tightened upper limits, changed source bytes, altered reviewer requirements and model hashes, removed or reordered proofs, mismatched decoders and out-of-region model execution were rejected.
- Updated JavaScript passes `node --check`. `python -m compileall` passes. The local `/api/affine-demo` and `/api/affine-fp32` endpoints pass integration tests including hostile origin and malformed-claim controls.

**Trust limits:** Python rational arithmetic, fixed model grammar, rounding model and host policy custody remain trusted. The result is conditional assurance in an explicit screened software-value semantics, **not** Lean-kernel safety certification, official ONNX Runtime equivalence, generic AI alignment or a safe public upload service. Existing PCS production verification code and authoritative proof gates were not modified.
