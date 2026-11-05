> **v0.13 correlation-preserving binary32 research (draft PR #196):** Added a reviewer-pinned affine abstract interpreter retaining shared input/output correlations and explicit per-operation RN-even error allowances. On a serialized ONNX correlation example, the older interval bound is **1999** while the new checker proves the scoped output-difference limit **≤ −1/2** over the same domain. Six trained-Iris update comparisons also recheck without partition trees; the enhanced gate still requires separate baseline/update evidence and independent protobuf agreement. Includes drag-and-drop use, adversarial tests, and a separate fixed-C numerical comparison. This is **experimental Python value-semantics assurance**, not Lean-verified or official ONNX Runtime conformance. [Reproduce the v0.13 result and inspect the trust boundary](docs/CORRELATED_BINARY32_ASSURANCE_V13.md).

> **v0.11 trust-boundary hardening (draft PR #196):** Fixed two confirmed protobuf interpretation ambiguities in the screened ONNX proof path (a repeated singular graph and a conflicting tensor/sequence type), now rejecting models whose bytes can have a different or invalid meaning under standard ONNX parsing. Added fail-closed strict semantic field checks and negative proof tests; an optional fixed-C binary32 evaluator now independently crosschecks the exact rational software evaluator. A recorded 150-point Iris C/float32 differential campaign observed no numerical disagreements; this is finite, non-held-out evidence, **not** Lean-checked, official ONNX Runtime conformance, or an isolation boundary. Local upload policy and duplicate Host/Origin header validation are also hardened. [Reproduce the v0.11 evidence and inspect the limitations](docs/STRICT_ONNX_AND_NATIVE_REFERENCE_V11.md).

> **v0.10 research advance (draft PR #196):** Added a **direct binary32 partition-certificate checker** and a fail-closed **dual-proof input gate**. In the trained Iris fixture, all six class-margin properties over the original three reviewer-approved regions now have both (1) v0.9 exact-real/update + rounding-lift evidence and (2) newly independently recomputed binary32 partition evidence (37 leaves total). The new verifier requires *both* proof families before screened reference inference. A significant resource-exhaustion defect in rational exponent parsing was also fixed. [Exact mathematical statement, tests, and limitations](docs/DIRECT_FP32_AND_DUAL_ASSURANCE_V10.md). These checks share Python/ONNX parsing and are **not** Lean-verified, production OS isolation, or universal ONNX Runtime safety assurance.

> **v0.9 research advance:** Proof-gated selective inference over reviewer-pinned operating regions. The local demo verifies six baseline/update certificate pairs across three trained Iris classifier regions and refuses computation outside the conditionally proven domain. [Technical definition, reproducibility and limits](docs/OPERATING_ENVELOPE_V09.md). Not Lean-verified, official ONNX Runtime, or a deployment safety certificate.

# PCS Model Assurance Studio — v0.7 research update

**New:** exact-rational binary32 rounding, conservative numerical error lifting for proof-gated model updates, Lean 4/Mathlib certificate *source* export, and an optional genuine ONNX Runtime CPU comparison. These mechanisms are deliberately separated from the existing v0.6 PCS authority.

To get started, extract this ZIP and run `launch_windows.bat` (Windows) or `sh launch_mac_linux.sh` (macOS/Linux). In the drag-and-drop interface select **Check binary32 rounding** or **Check selected model in float32**. Use the CLI to reproduce the model-update lifting results.

Read **[v0.7 numerical and formal boundaries](docs/LEAN_AND_FLOAT32_V07.md)** before interpreting a conditional verdict. In particular, the included Lean source is **not compiled** and the official ONNX Runtime adapter has **not executed here**, because neither toolchain was available in the environment. NumPy/PyTorch comparisons do not establish general runtime equivalence. The browser generates suggested reviewer policies; independent acceptance requires a separately pinned policy and model identity.

---

# PCS Model Assurance Studio v0.6 — proof-gated model update research prototype

**Project:** [Proof-Carrying Science (PCS)](https://github.com/Tommaso-R-Marena/proof-carrying-science) · **Status:** standalone incubator. **Nothing in this package has been merged into the original PCS repository.** No clinical, biological, generalized AI safety, Lean, or ONNX Runtime certificates are issued.

## NEW in v0.6: independently checkable neural-network relations and model changes

v0.6 includes three complementary, carefully scoped exact-rational proof mechanisms: **(1) relational output/decision-margin Farkas certificates**, **(2) exhaustive ReLU activation-case covers when a global relaxation is inconclusive**, and **(3) same-input two-model behavioral-drift certificates with proof-gated update composition**. A separate, standard-library-only reviewer (`python -S`) recomputes the entire restricted ONNX abstraction, checks every rational proof, and rejects changes to an independently pinned policy or either source model's hash. The numerical optimizer is never a proof authority.

The drag-and-drop interface now offers **Prove a neural invariant**, **Prove a nonlinear identity**, **Prove a trained Iris classifier margin**, **Prove a trained-model update**, and **Compare selected ONNX model pair**. A real trained 4→8→3 ReLU classifier (scikit-learn Iris data, 91.1% held-out accuracy) has two independently checked local margin properties. A changed learned model has a proof-checked `1/8` relative drift bound and a composition guaranteeing its selected margin stays `>= 3/8` over the stated four-dimensional local box. This is a **mathematical statement under the screened real-arithmetic model**, not runtime or deployment safety. Official ONNX Runtime is absent and was not tested.

Start with **[Proof-carrying neural relations & model updates](docs/RELATIONAL_PROOFS_AND_MODEL_UPDATES_V06.md)** for exact equations, trust boundaries, step-by-step standalone verification and reproducible trained-model evidence. Existing v0.5 inspectors and demos are retained below.

Quick independent check from project root (stdlib only):

```sh
python -S -m studio.verify_update compose samples/demo_trained_iris_mlp.onnx samples/demo_trained_iris_updated.onnx validation/v06_iris_property_1_certificate.json validation/v06_iris_property_1_reviewer_policy.json validation/v06_update_drift_certificate.json validation/v06_update_reviewer_policy.json --required-new-upper=-3/8
```

The live HTTP endpoint `/api/compare-update` accepts two length-prefixed screened ONNX models, while the reviewer checks independent externally pinned source hashes and requirements. The new workflow does not perform external tool execution or deploy an updated model.

## 1. Getting started

- **Windows:** Extract ZIP and double-click `launch_windows.bat`. Python 3.10+ and network access for initial dependency installation are needed.
- **macOS / Linux:** Extract ZIP, run `sh launch_mac_linux.sh`.
- **Manual:** `python -m pip install -r requirements.txt`, then `python -m uvicorn studio.server:app --host 127.0.0.1 --port 8765` and open `http://127.0.0.1:8765`.

The server binds **only to localhost**; no model upload is deliberately written to disk by `/api/analyze`. Uploads are held in memory (limit 128 MiB). Analysis of third-party data still requires appropriate permission. The Python/native parsers and worker subprocesses are not security-audited or OS-sandboxed. **Do not expose the development server publicly or upload executable, sensitive, or untrusted proprietary artifacts without a secure deployment design.**

Supported inspectors: `.onnx`, `.safetensors`, `.pdb`, `.cif`, `.sbml`, FASTA, and synthetic `.agenttrace.json`. The app detects and declines several dangerous serialization disguises rather than loading pickles, ZIP model code, or executable checkpoints.

### Original v0.5 demo buttons (still available)

1. **Prove a nonlinear bound.** Loads `demo_partition_abs.onnx`, a tiny real-arithmetic network calculating `|x|`. On `[-1,1]`, ordinary interval bounds are inconclusive (`[0,2]`), but finite subdivision at `x=0` gives two independently recomputed enclosure leaves `[0,1]`. This is a **conditional real-arithmetic certificate**, not an IEEE float32 / official ONNX Runtime / Lean certificate.
2. **Find a hidden failure.** Loads `demo_hidden_spike.onnx`, with a thin activation peak near `x=0.317`. The deterministic corner/random probe search found no violation. An optional SciPy HiGHS MILP solver found a candidate, checked it with exact rational evaluation, and NumPy float32 replay produced `1.199960708618164` against the chosen upper bound `0.5`. Optional PyTorch CPU independently reproduced the same output. This is a scoped violation of **screened reference semantics**, not live deployment equivalence.
3. **Run neural-network demo.** The existing weighted dense ONNX model reproduces a first output of `1.25` against a policy max of `1.0` with NumPy float32. Enable **PyTorch CPU crosscheck** for an independent implementation; PyTorch must be installed separately.
4. **Challenge the agent guard.** A deterministic 64-case metamorphic campaign mutates authorized publication and public-dataset requests, including forbidden tools, altered messages, injected authority fields, and deceptive Unicode. All 64 are denied against the toy in-memory backend. These are **fixed synthetic test cases only**, not evidence of broad prompt-injection immunity.
5. **Run guarded tool demo.** Only the tiny host-owned in-memory backend runs, never external commands or network actions. Unauthorized proposals are rejected **before** the synthetic effect; decisions are HMAC chained using the temporary host key.

The interface is interactive, local-first, and makes per-finding PASS / FAIL / OPEN distinctions. The overall decision can be `FAIL` or `OPEN`—**never an unconditional SAFE** verdict. A scoped PASS never certifies a model safe to deploy.

## 2. Important new verification boundaries

### Finite subdivision proof (bounded exact rational checker)

`studio/partition_proof.py` constructs a binary split tree covering the assumed input hyperrectangle. Each leaf stores a bounded exact rational interval enclosure. `verify_certificate` verifies the screened model's semantic digest, input assumptions, output limits, exact split coverage, node budget, leaf count, and recomputed leaf enclosures. If the tree is incomplete, contains a malformed branch, or runs out of its 1–128 leaf budget, the conclusion remains **OPEN**.

The mathematical property being checked is specifically a supported small dense network under **exact real-number operator semantics**, with all input coordinates in the stated common box. The implementation itself is **not proved correct in Lean**. No float32-rounding soundness, arbitrary ONNX semantics, or biological validity is inferred.

The standalone rechecker accepts the matching receipt and model bytes:

```bash
python -m studio.verify_partition validation/v05_partition_abs_receipt.json samples/demo_partition_abs.onnx
```

### Solver-guided adversarial model search

`studio/milp_challenge.py` encodes screened `MatMul`, default-attribute `Gemm`, `Add`, `Identity` and `Relu` as a bounded mixed-integer linear program. It uses bounded real interval enclosures to derive safe Big-M parameters. SciPy/HiGHS is a **numerical challenger**, not a theorem prover. All returned points must be in the claimed box **after float32 conversion** and must violate the target under a fresh exact rational interpreter; otherwise they are discarded. A `FAIL` finding requires opt-in separate NumPy replay to reproduce an observed numerical violation. For stronger reference agreement, opt into the PyTorch CPU worker as well. A solver that fails, times out, or finds nothing yields only **OPEN**.

The graph subset is intentionally tiny: explicit FLOAT32 `[1,n]` inputs/outputs, embedded 1-D/2-D float32 weights, 64 nodes and up to 1,024 initializer values. The exact supported operator grammar is in `studio/dense_nn.py`. Solver variable/constraint/big-M budgets are separate and may cause an explicit abstention. All subprocesses execute only screened operations, not original uploaded Python or ONNX bytecode. **They are not OS security sandboxes.**

### Publisher signatures with independently pinned trust

Unsigned artifact/receipt SHA-256 digests detect casual tampering, but can be recomputed by anyone. v0.5 adds **optional Ed25519 signatures** using a publisher-owned private key that is **generated and retained on the user's own machine**. The reviewer must obtain and pin the public-key SHA-256 fingerprint **out of band**. Signatures require a fresh successful replay of the report first.

```bash
# Run from the extracted project directory; use a PRIVATE location outside the project for keys.
python -m studio.signature init --private-key /secure/location/pcs-signing.pem --public-key /secure/location/pcs-signing.pub
python -m studio.signature sign validation/v05_partition_abs_receipt.json samples/demo_partition_abs.onnx --private-key /secure/location/pcs-signing.pem --output /secure/location/partition-signature.json
python -m studio.signature verify /secure/location/partition-signature.json validation/v05_partition_abs_receipt.json samples/demo_partition_abs.onnx --expected-fingerprint YOUR_INDEPENDENTLY_TRUSTED_SHA256_FINGERPRINT
```

These are **publisher authenticity signatures**, not Lean-authoritative PCS certificates, proof of completeness, immutable log anchors, or scientific acceptance. Do not share the private key. The source archive intentionally contains **no signing keys**.

### Review an unsigned receipt with full reanalysis

```bash
python -m studio.verify_receipt validation/v05_hidden_spike_receipt.json samples/demo_hidden_spike.onnx --replay
python -m studio.adversarial_campaign
```

`--replay` checks generated findings under the exact installed engine and dependencies. Numerical replays and version strings are intentionally environment-dependent; when reproducing an existing receipt, use a matching Python/dependency environment. To verify original v0.4 receipts with full replay, use the v0.4 engine; newer engines may digest-verify legacy receipts but refuse exact reanalysis under changed code.

## 3. Testing

```bash
python -m unittest discover -q
python -m tests.live_http_v05
python -m tests.browser_smoke_v05  # Playwright + Chromium required; mocks ONLY browser transport
node --check studio/app.js
```

The reference environment ran **166/166 automated tests**, a live local HTTP API smoke including hostile header rejection, and a Chromium UI workflow smoke rendering actual backend-generated results with mocked transport. Direct Chromium-to-localhost navigation is restricted by the execution environment and is not claimed. See `validation/TEST_REPORT_V05.md` for actual commands, environment and adversarial results.

`studio/agent_gate.py` and `studio/guard_runtime.py` remain synthetic. The real PCS v0.6 Lean authority is **not called**. The exported PCS-shaped Claim IR is **candidate data** and carries no trusted acceptance status.

## 4. Development priorities

1. Validate v0.5 behavior on a clean machine with official, version-pinned `onnx` and `onnxruntime` **inside a properly isolated model runtime**, and compare decoded model execution against screened reference interpreters. Actual ONNX Runtime is absent in the reference testing environment.
2. Give supported properties a typed, reviewer-owned property DSL for per-output limits, classification invariants, agent resource restrictions and domain-appropriate biological assumptions. Current input/output boxes are scalar ranges applied to each coordinate.
3. Prove the supported exact-real interval/subdivision checker and its model/receipt serialization bridge in Lean; carefully state what remains outside that proof, including IEEE rounding and scientific assumptions.
4. Replace demo-only tools with a non-bypassable permissioned real execution boundary and independent audit custody, under a carefully reviewed security threat model.
5. Carry out independent evaluation on legally cleared, genuine AI and computational biology models before any scientific/commercial assurance claims.

Full threat boundary: `docs/THREAT_MODEL_V05.md`. Neither PCS's original repository nor its verification roots have been modified by this standalone research package.

### v0.12 — Dual decoding and model-to-proof binding (research only)

The enhanced local demonstration cross-checks the mathematical ONNX graph decoded by
PCS's screened parser against an independently constructed Google protobuf decoder,
then requires **both** complete prior mathematical proof families before software
reference inference. If protobuf is missing or the decoders disagree, this enhanced
gate refuses to execute. The separate stdlib-only mathematical replay remains
available without protobuf. The parser now rejects previously ignored ONNX sparse
initializer graph fields. See [the v0.12 threat-boundary report](docs/DUAL_PROTOBUF_SEMANTICS_V12.md)
for reproducibility, tests and limitations.

```sh
PYTHONPATH=. python scripts/reproduce_v12_dual_decoder.py
```

No official ONNX Runtime semantics, Lean kernel proof, secure host, independent
policy custody or generalized AI safety verdict is established.
