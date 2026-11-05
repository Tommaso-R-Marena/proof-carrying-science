# v0.12 — Independently decoded model semantics before proof-gated execution

**Status: experimental and conditional; not PCS trusted authority, Lean verification, official ONNX checker, or deployed runtime conformance.** This contribution is isolated to draft PR #196's `research/model_assurance_studio_v1/` tree.

## New threat-boundary finding

The hand-written screened ONNX parser accepted a `GraphProto.sparse_initializer` (field 16), silently ignoring its contents. We reproduced this with an otherwise well-formed screened dense ONNX model: adding field 16 did not change the Python screen's mathematical graph, despite introducing an ONNX graph component outside the modeled grammar. The original checker did not establish whether that additional field would be legal or affect a deployed runtime. **It must not claim model-byte semantic correspondence while ignoring unsupported graph structures.** The screen now rejects GraphProto field 16 unequivocally. The positive sparse-initializer parsing feature is intentionally not added.

## Two-decoder comparison

`studio/protobuf_dual_decoder_v12.py` creates a **fixed** protobuf descriptor with Google protobuf's descriptor machinery, mirroring the fields in the narrow ONNX subset. No model-provided Python code, external files, generated source, or imported ONNX operator kernels are run. The fixed schema's field numbers and oneofs were checked against ONNX's published `onnx.proto` / `onnx.proto3` (source snapshot retrieved 2026-11-04; this demo does not pin a complete external ONNX specification artifact).

The comparison reconstructs independently from the Google protobuf decoder: (1) the model's IR version and standard opset; (2) names and explicit `[1,n]` input/output types; (3) the ordered node operator names, arguments and output names; and (4) exact binary32 weight **bits**, preserving negative zero. It compares that to the hand-written screen's numerical semantic representation. A mismatch or invalid encoding returns `DISAGREEMENT`; absence of Google protobuf returns `NOT_RUN`, **never** a pass. Metadata that does not affect the screened mathematical grammar may be omitted from the comparison, but the hand-written parser continues to reject unknown semantic fields. This is not a general ONNX implementation or conformance checker.

`DualDecoderAssuranceGate` requires agreement for **both original and updated model files** *before* it invokes the v0.10 dual mathematical proof gate. Missing dependencies, false/missing proof branches, model substitution, and wrong policy fingerprints lead to `OPEN` and refusal to execute. Only after all checks pass can the host-side screened reference interpreter process exact binary32 words in an approved operating region. No public-facing upload endpoint executes arbitrary model code.

The code intentionally retains the v0.10 standard-library-only proof verification path for environments without Google protobuf; the **new enhanced admission route**, however, requires it. The reviewer still must independently obtain the policy hash: the fixture's checked-in hash is a reproducibility convenience, **not an independently administered authority**.

## Reproduce

From this directory:

```sh
# Optional Python package for the new independent wire decoder:
python -m pip install 'protobuf>=5,<7'

# New detailed tests; the base proof replay does not require protobuf:
PYTHONPATH=. python -m unittest tests.test_protobuf_dual_decoder_v12 -v
PYTHONPATH=. python scripts/reproduce_v12_dual_decoder.py

# Verify the fail-closed missing-dependency state:
PYTHONPATH=. python -S scripts/reproduce_v12_dual_decoder.py

# Original independent proof replay still works in stdlib-only mode:
PYTHONPATH=. python -S scripts/reproduce_v10_dual.py
```

The new regression suite includes malformed sparse initializer, duplicate graphs, oneof alternatives, a forgery that recomputes policy/model hashes, deliberate internal screen corruption, packed FLOAT32 tensors with signed-zero values, an actual host-side refusal-before-execution assertion, and 384 reproducible wire-format mutations. The local Iris demonstration rechecks six exact-real/update proofs, six direct binary32 partition certificates (37 leaves), and three conditional admissions. It checks the same *training-derived* Iris regions used in prior releases; it is **not** independent held-out generalization evidence.

## What this does *not* prove

- Two decoders do not create a trusted formal authority. Both still share the **chosen restricted ONNX semantics**, Python host, model byte custody and unverified mathematical checkers. Bugs may remain in common assumptions.
- Google's protobuf library decodes the wire format; this fixed descriptor is not the **official** ONNX model checker or an official ONNX Runtime execution.
- Binary32 output guarantees concern a particular nonfused, finite, round-to-nearest-even software interpretation, not arbitrary accelerated inference kernels.
- No Lean kernel has checked this decoder, floating-point interpreter, model-to-proof correspondence, or policy custody.
- The local server still is not a hardened public upload service or an OS process sandbox.

**Next prerequisite:** under pinned Lean 4.28, formalize semantic equivalence for the accepted normalized grammar and the small certificate checker; run official ONNX checker/runtime conformance in a sealed test environment; retain independent reviewer-owned trust anchors. Do not merge or promote production authority on the basis of this result alone.
