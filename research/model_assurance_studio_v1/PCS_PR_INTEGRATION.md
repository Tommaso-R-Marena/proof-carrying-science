# PCS Model Assurance Studio — additive incubation proposal (v0.8)

**Classification: experimental research. NOT a PCS v0.6 certified package.**

This folder is a separately runnable, local-first drag-and-drop inspection and proof-experiment prototype brought into PCS for review. It intentionally does **not** alter `pcs/`, `formal/`, CI authority scripts, signed receipts, deployment policy, or production package entrypoints. The existing PCS authority does not validate any of the certificates produced here.

## What is genuinely implemented

- Local browser intake: ONNX, safetensors, protein structures (PDB/mmCIF), SBML, FASTA and synthetic agent traces. Inspection is narrowly scoped and declines unsupported constructs.
- Experimental exact-rational Farkas/activation-case proofs over a screened dense ONNX subset, solver-guided candidate search, exact-real model-update drift proofs and independently rechecked witnesses.
- A conditional binary32 finite-rounding/error-budget lift for selected screened models; **not** official runtime execution equivalence.
- A local synthetic in-memory agent tool gate; not an isolation boundary against a malicious runtime.
- Ed25519 signed local publisher receipts with separately pinned keys. Signing does not establish scientific validity.
- NEW v0.8: `studio/reviewer_gate_v08.py` demands an *independently supplied* reviewer policy that pins BOTH model hashes, the full domain, the relational property, exact and float32 thresholds. It rejects rewritten claims or missing proofs and never returns a general safety verdict.

The v0.7 source export under `studio/lean_export_v07.py` is **not** a compiled Lean proof of the ONNX parser, LP relaxation, or float32 interpreter. It exports arithmetic consequences under explicit inequality hypotheses. Lean 4.28/Mathlib compilation and the semantic bridge remain outstanding. Official ONNX Runtime is not present in the original prototype's test environment and its optional native execution adapter must only be run with appropriate isolation.

## Focused reviewer gate (stdlib-only)

From this folder:

```sh
python -S -m unittest tests.test_reviewer_gate_v08 -v
python -S -m studio.reviewer_gate_v08 \
  samples/demo_trained_iris_mlp.onnx samples/demo_trained_iris_updated.onnx \
  validation/v06_iris_property_1_certificate.json \
  validation/v06_update_drift_certificate.json \
  validation/v08_iris_independent_reviewer_policy.json
```

The included policy is a **public demonstration fixture**. A real reviewer MUST obtain/approve the policy and model hashes independently of the submitter. Merely storing a policy in the same ZIP or accepting a browser-generated policy confers no independent authority.

## Full local UI

Set up a virtual environment and install this folder's `requirements.txt`. From this folder run `python -m uvicorn studio.server:app --host 127.0.0.1 --port 8765`, or use the provided Windows or macOS/Linux launcher. **Do not expose to the internet.** The parsers and optional native inference execution are not hardened against arbitrary malicious inputs. Avoid uploading sensitive/proprietary materials on an untrusted workstation.

## Release blockers before production promotion

1. Independent verification of parser/graph semantics and exact certificate checker in the pinned Lean kernel, without weakening PCS's current authoritative guard.
2. Test against official ONNX Runtime and an explicitly specified rounding/ordering contract; crosschecks over finite samples are not universal proofs.
3. Isolate untrusted files/native runtime execution at the OS/VM level and capture reproducible environmental evidence.
4. Full PCS integration gate and protected CI qualification on the exact proposed commit, plus independent code/security/rights review.
5. Real external-partner evaluation on legally cleared workflows; no biological validity or generalized AI safety claims.

**Merge posture:** draft until scoped source inspection, exact-commit CI, rights audit, and trust-boundary review are complete. This incubator is deliberately not promoted as `pcs verify-v06` authority.

## v0.9 addendum — proof-gated operating envelope

A new additive research control now checks **complete per-class update-margin evidence** for a reviewer-approved union of bounded regions and refuses to execute screened software-reference inference outside the verified region. See [full mathematical statement and limits](docs/OPERATING_ENVELOPE_V09.md).

The trained Iris demonstration comprises **three regions, six independent update proof pairs, and a conditional minimum float32 class margin of 1/4** under the documented arithmetic assumptions. Source data coverage is 27/150 points; the same data were used to choose the regions, so this is not a blind validation or accuracy metric. The exact three anchor inputs execute using the screened software reference after admission; all out-of-region requests abstain. The independent review path uses only the Python standard library:

```sh
python -S -m unittest tests.test_operating_envelope_v09 -q
PYTHONPATH=. python -S scripts/reproduce_v09_envelope.py
```

The browser exposes a **bundled demonstration only**, not authorization of arbitrary user-supplied models. The sample policy fingerprint is source-pinned for reproducibility; this is not proof of independently administered reviewer custody. The v0.9 checks are **experimental Python evidence**; Lean and official ONNX Runtime equivalence remain NOT_ESTABLISHED.

Optional non-authoritative second-backend observation: `PYTHONPATH=. python scripts/crosscheck_v09_torch_cpu.py` (requires PyTorch and scikit-learn). This separately executes all 150 Iris vectors in PyTorch CPU and the software sequential binary32 interpreter; the recorded run observed zero violations on the 27 conditionally admitted samples and maximum absolute numerical difference ~3.81e-6 across all 150. See `validation/v09_torch_cpu_observation.json`. These measurements are not a Lean proof, official ONNX Runtime equivalence, or held-out coverage evidence.


## v0.10 addendum — two-route binary32 envelope verification

[Direct binary32 and dual proof-gated assurance](docs/DIRECT_FP32_AND_DUAL_ASSURANCE_V10.md) adds a direct IEEE binary32 *value-semantics* partition certificate, a separate stdlib verifier, and a reviewer-pinned combined gate requiring both the existing v0.9 proof family and all six new direct binary32 margin proofs. The bundle holds 37 partition leaves, each independently reconstructed and checked against the reviewer-owned mathematical requirements; an absent or changed leaf makes the **entire** envelope OPEN. A 1-D ReLU identity that defeats one global numerical interval is provable with a complete eight-leaf binary32 cover.


```sh
PYTHONPATH=. python -S scripts/reproduce_v10_dual.py
PYTHONPATH=. python -S -m unittest tests.test_direct_fp32_v10 -q
```

The shared exact rational parser also rejects catastrophic decimal exponents *before* calling Fraction (e.g. `1e100000000`), instead of attempting enormous allocations before its bit-budget check. The local browser has a **Run dual-certified FP32 gate** demonstration using only bundled screened model bytes. This research-only result does not alter formal or production PCS authority, and is not yet Lean/ONNX Runtime verified. The two checking routes share Python and ONNX parser TCB rather than being independently implemented runtimes. Keep the PR in draft.
