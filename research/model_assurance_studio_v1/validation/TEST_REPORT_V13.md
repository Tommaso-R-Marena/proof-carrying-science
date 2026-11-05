# PCS Model Assurance Studio v0.13 — local research qualification

**Status:** a follow-up on November 5 reran **every discovered test module**
from the exact amended source in five disjoint, successful unittest groups.
The independently enumerated test count is **305**, not the 318 originally
reported below. The earlier 318/397 figures were not reproducible from the
archived source and are **superseded**, not counted as successful additional
checks. A single-process run previously timed out without a result.

| Group | Distinct tests passed | Runtime |
|---|---:|---:|
| Intake / v0.3 / scientific inspectors / agent guard / dense networks | 112 | 19.06 s |
| Adversarial/legacy / strict ONNX / independent protobuf decoder | 55 | 10.98 s |
| Float32 / relational proofs / update proofs / reviewer pinning | 48 | 1.03 s |
| Direct FP32 / operating envelope / native C / HTTP hardening / activation and new affine proofs + random models | 76 | 14.79 s |
| MILP challenger | 14 | 9.77 s |
| **Total** | **305** | — |

Count verified by `unittest.defaultTestLoader.discover('tests', pattern='test_*.py')`
(305 discovered) and by exit code 0 of each of the five disjoint runs.
Nested subtests are *not* added to the test count and were not independently
recounted for this amendment. The earlier claim of 397 nested subtests is
withdrawn pending a reproducible census.

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

## v0.13.1 reproducibility follow-up (November 5, 2026)

One v0.13 documentation command incorrectly combined `python -S` with the
integration tests that require the optional Google protobuf decoder. Running
that exact command reproduces **two failures** (`test_all_six_trained_iris_margin_certificates`
and `test_caller_mutation_after_gate_creation_does_not_change_admission`): the
two-decoder gate correctly abstains without protobuf, while those tests require
positive admission. This is a **test invocation error**, not a certificate
soundness result. The documented commands now separate stdlib-only mathematical
replay (`python -S scripts/reproduce_v13_affine.py`), stdlib randomized tests,
and full integration tests with protobuf installed.

A new subprocess regression exercises the real `-S` path (rather than mocking
an unavailable decoder): it checks that all six Iris mathematical claims replay,
that the correlation claim replays, and that complete gate admission is
`NOT_ESTABLISHED`. The focused suite (affine, HTTP, randomized tests) passed
**19/19** with installed protobuf; stdlib randomized tests passed **2/2**.
The complete 23-module test suite passed **305/305** when run in five disjoint
groups. Earlier v0.13 report counts (318 tests and 397 reported subtests)
were not reproducible by discovery of the exact release files, so they have
been superseded rather than silently carried forward.
The full replay with protobuf returned conditional acceptance for three test
anchors and ABSTAIN outside the approved envelope; the stdlib-only replay
reported `NOT_ESTABLISHED` for full admission, as required. No changes were made
to the numerical verifier, model grammar, trusted authority, or certificates.
These are local research tests, not Lean/official ONNX Runtime qualification.
