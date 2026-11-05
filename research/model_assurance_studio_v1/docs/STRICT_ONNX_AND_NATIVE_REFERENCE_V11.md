# v0.11 — Strict screened ONNX intake and native CPU differential evidence

**Status:** Research only, proposed as an additive update to draft PR #196. Not PCS authority. No Lean kernel proof, official ONNX Runtime equivalence, secure sandbox, or broad model-safety claim.

## 1. Confirmed parser ambiguity and its repair

The previous `studio/dense_nn.py` manually interpreted selected ONNX protobuf fields (see the upstream [ONNX protobuf schema](https://github.com/onnx/onnx/blob/main/onnx/onnx.proto)). It retained **only the last `ModelProto.graph` occurrence** even though duplicate *singular embedded-message* protobuf fields are merged by standard protobuf parsing. It also accepted `TypeProto` objects containing `tensor_type` followed by a conflicting `sequence_type`, ignoring the latter even though they occupy a protobuf **oneof**. Thus the checker could claim a conditional property about bytes whose standard ONNX meaning was different or invalid. This is a model-to-math binding flaw; it is **not a demonstrated attack that executed unsafe ONNX Runtime inference**.

v0.11 restricts the reviewed semantic grammar: one top-level graph, one model IR version, one standard opset import, explicit unique tensor-only input/output types, bounded dimensions and inline `FLOAT32` initializers, no ambiguous data encoding, no local function definitions or training information, no node overloads or semantic field duplication, and no model over 8 MiB for the proof path. Unsupported inputs explicitly abstain. Metadata that does not change mathematical semantics may also be rejected; this is intentionally a restricted subset and **not** a complete ONNX conformance parser.

The negative suite synthesizes eleven malformed/ambiguous protobuf variants and tests both the bare parser and the full direct-proof verifier after an attacker has recomputed the proposed policy/model SHA-256 fields. All must be refused. Eight previously supported neural-network fixtures remain accepted. `python -S -m unittest tests.test_strict_onnx_v11 -v` requires only the Python standard library.

## 2. Independent numeric evaluator in fixed C (optional)

`studio/native_fp32_reference_v11.c` is a fixed, inspectable, bounded native CPU implementation of `[1,n]` MatMul, default Gemm, elementwise Add, ReLU and Identity. It consumes only a numeric instruction stream *constructed by the screened Python parser*. It **does not compile model-provided source**, deserialize Python pickles, import arbitrary native model libraries, or run the input `.onnx` as a program. Its compiler flags suppress fast math and fused operations, and the runner checks binary32 layout, round-to-nearest mode and preservation of the minimum subnormal. The Python driver independently executes the exact-rational software reference and compares returned numerical values (signed-zero bit semantics intentionally excluded).

```sh
# Run the fixed-C differential and fail-closed parser tests
PYTHONPATH=. python -S -m unittest tests.test_native_fp32_v11 tests.test_strict_onnx_v11 -v

# Optional: 150 Iris inputs, using saved standardization profile
PYTHONPATH=. python scripts/reproduce_v11_native.py

# Replay the separate operating-envelope mathematical evidence
PYTHONPATH=. python -S scripts/reproduce_v10_dual.py
```

In the recorded local **GCC** (C evaluator) run, all 150 standardized Iris inputs agreed with the exact-rational Python binary32 reference at the numeric-value level, with no observed discrepancies; see `validation/v11_native_cpu_observation.json`. The `gcc` and `clang` compiler paths also agreed locally on a small input set. An additional 18 randomized, bounded ONNX graphs exercising default Gemm, dynamic Add and ReLU agreed with the rational interpreter on 22 inputs each, including subnormal/negative-value controls. This is *finite empirical evidence*, from the same public Iris dataset used to select v0.9 operating regions: **not held-out/generalization evidence**.

Crucial exclusions: compilation and execution of fixed C is still native execution with host compiler/CPU/OS trust assumptions. The compiler flags do not prove IEEE compliance or ONNX Runtime behavior. An untrusted third-party model must **not** be executed in a native on-device library by analogy to this program. This feature is a CLI-only optional local research crosscheck and is **not** an authoritative checker or a public upload endpoint.

## 3. Local HTTP metadata boundary

The local FastAPI intake now refuses duplicate Host/Origin headers, policy headers longer than 8192 characters, duplicate JSON keys, and non-finite JSON constants. Existing host and same-origin allowlists remain. These are local development protections and **do not make this service safe to expose on a public network**. The browser continues to show OPEN rather than SAFE for unsupported models.

## 4. Remaining assurance gap

The scientifically decisive next task is a **kernel-checked proof of the normalized model/certificate correspondence** and the direct rational/IEEE interval transformer, accompanied by a genuinely independent official ONNX Runtime conformance campaign with execution-environment capture. The present Python verifier, ONNX wire decoder, fractional arithmetic and native compiler/runtime remain part of the trust boundary. Neither the v0.10 dual routes nor the new C evaluator constitutes a second formal proof kernel. No merge/production authority should be inferred until independent code/security/rights review and CI on the exact source commit are complete.
