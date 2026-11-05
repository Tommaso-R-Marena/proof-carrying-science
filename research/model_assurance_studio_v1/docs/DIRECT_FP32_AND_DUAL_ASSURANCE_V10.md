# PCS Model Assurance Studio v0.10: direct binary32 partition proofs and dual proof-gated admission

**Research status only.** The new numerical certificate is independently recomputable from the model bytes and a reviewer-owned policy, but **not** Lean-kernel checked, a general ONNX verifier, production authorization, or proof of deployed hardware/ONNX Runtime equivalence. The local HTTP UI remains a developer service, not a hostile-upload sandbox.

## Core result

For a screened ONNX model `f` with embedded finite FLOAT32 weights and a reviewer-owned box `B`, coefficient vector `c`, and required upper limit `L`, the direct binary32 verifier checks the conditional claim

> for every finite *binary32* input `x ∈ B`, `c·f_RN(x) ≤ L`,

where `f_RN` is **only** the selected software semantics: each multiplication and addition is separately correctly rounded to IEEE binary32, the dot-product terms are evaluated in increasing input-index order, Gemm bias is added afterwards, and Relu/Identity have exact numeric-value behavior. Signed zeros, exception flags, FMA, reassociation, FTZ/DAZ, mixed precision, dynamic shapes, and arbitrary kernels are outside this claim. A different runtime cannot inherit it without separate semantic correspondence evidence.

Instead of taking a numerical optimizer's safe/unsafe label, the verifier recursively replays a **binary partition tree**. The root equals the exact box from the pinned reviewer policy. Every internal node must split on one coordinate at a strictly interior rational point `t`, with **both** children covering `[lo,t]` and `[t,hi]`. Every leaf recomputes the model's rounded interval output through `studio.fp32_assurance.intervals` and verifies that the exact rational linear upper bound is **identical** to the candidate's recorded bound and is `≤ L`. Missing branches, forged bounds, malformed policy identity, byte-substituted models, unknown fields, non-finite inputs, or resource exhaustion lead to `OPEN`/`ABSTAIN`.

Mathematical argument (conditional on the Python interpreter's correctness): all real inputs in the root box are covered by the two closed children at each split; a finite input in the root falls in some leaf. Correctly rounded finite binary32 addition and multiplication are monotone on the numerical values. The exact interval transformer conservatively encloses each intermediate operation, so the leaf's linear upper bound encloses the output relation. The proof checker never invokes SciPy, numerical optimization, NumPy, PyTorch, or ONNX Runtime, and does not trust the leaf values without recomputing them.

### Comparison to prior versions

v0.9 independently replays exact-real ReLU/linear-relational certificates plus a conservative float32 rounding-error allowance. v0.10 can establish the **same mathematical input/output condition directly in the selected binary32 value semantics**, without using that real-to-float lift. These two mechanisms still share Python, the screened ONNX parser, and their mathematical assumptions; they are complementary mathematical proof routes, **not** independent software implementations.

A restricted 1-input nonlinear ReLU identity example (`ReLU(x) − ReLU(−x) − x`) is unproved by one unpartitioned numerical interval on `[-1,1]` at the tolerance `1/4`, yet an **8-leaf** checkable direct-binary32 partition establishes the conditional bound. This is a generated mathematical proof of an assumed numerical program, not a universal proof of real-world system safety.

## Trained model experiment: six direct binary32 properties

A trained 4-input / 3-output Iris MLP, already in v0.9, has three approved operating boxes. Each box has two necessary class-margin inequalities: `logit_other − logit_winner ≤ −1/4`. A local untrusted heuristic generated complete certificates of sizes **3, 1, 2, 16, 1, 14 leaves**, respectively. The exact-rational reviewer checked all **37 leaves**, all **six competing-output properties** and all three original v0.9 proof regions. The combined `DualAssuranceGate` **fails closed unless both complete proof families verify**; its screened binary32 reference executor only runs after this admission. Three original fixture anchor inputs were admitted and executed; the outside-domain control abstained before inference.

This does not add new independent evaluation data. The Iris dataset was used in selecting the operating boxes: the historical 27/150 measurement is not blind accuracy, generalization, or real deployment coverage.

## Files and reproducibility

- `studio/direct_fp32_v10.py`: small direct certificate checker and fail-closed, pinned-model admission gate.
- `studio/direct_fp32_proposer_v10.py`: **untrusted** adaptive partition generator; attempts heuristic splits but has no authority.
- `studio/dual_envelope_v10.py`: checks both mathematical evidence families before admitting any model input.
- `studio/relational_kernel.py`: reject giant decimal exponents **before** calling `Fraction`. Previous expressions such as `1e100000000` attempted catastrophic integer allocation before the 512-bit guard ran.
- `validation/v10_direct_fp32_partition_evidence.json`: exact model/policy-bound binary-tree witnesses for all six trained-model comparisons.
- `validation/v10_direct_fp32_review.json`: a reproducible local Python summary, **not** a third-party signature.
- `scripts/generate_direct_fp32_v10.py`: optional producer-side regenerate proof trees; third-party optimization is not needed for these examples.
- `scripts/reproduce_v10_dual.py`: deterministic proof replay with stdlib Python and admitted/abstained reference inference.
- `tests/test_direct_fp32_v10.py`: mutation controls, complete-cover rejection, resource limits, shared reviewer identity, exact-bit membership, all-competing-class proof enforcement, random numerical checks, and local HTTP demo.

From the root of this research directory:

```sh
PYTHONPATH=. python -S scripts/reproduce_v10_dual.py
PYTHONPATH=. python -S -m unittest tests.test_direct_fp32_v10 -q
# Optional producer rerun, not a trusted verification step:
PYTHONPATH=. python scripts/generate_direct_fp32_v10.py
```

**Critical reviewer-custody detail:** the sample v0.9 reviewer policy's SHA-256 is checked into the source for demo reproducibility. This is not an independent real-world trust anchor. A deployment must obtain policy approval and fingerprint out-of-band from an authorized reviewer, bind live model and input bytes at the execution boundary, and isolate any untrusted execution. A SHA hash of a producer-supplied policy alone cannot establish authorization.

## Open trust boundaries

The source parser, exact rational arithmetic and binary32 interval transformer remain part of the Python trusted computing base and are not Lean verified. The checker has not been validated against **official** ONNX Runtime. Correctness of numerical code in an unrelated hardware environment cannot be inferred from finite testing. The demonstration serves only the specified tiny ONNX subset and reviewer-defined classes/regions; it is not an AI alignment solution, biological verification, clinical safety claim, or safe public upload service. Keep PR #196 a **draft** until independent security review and exact-head CI and formal/runtime verification justify any further promotion.
