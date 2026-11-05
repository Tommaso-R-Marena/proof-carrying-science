# PCS Model Assurance Studio v0.5 — independently reproducible local validation

**Date:** 2026-11-04. **Platform:** Linux x86_64, Python 3.13; see `V05_ENVIRONMENT.json` for package versions. This is a self-run developer evaluation, not an external security audit or a Lean proof.

## Overall result

- `python -m unittest discover -q` — **166 tests passed**. No failures or skips in the reference environment.
- `node --check studio/app.js` — passed syntax validation.
- `python -m tests.live_http_v05` — **passed on a real Uvicorn server bound to 127.0.0.1:8765**, including model upload / MILP-replay receipt, synthetic guard campaign, and hostile Host/Origin header rejection.
- `python -m tests.browser_smoke_v05` — **passed**, using Chromium and **real analysis results with stubbed browser HTTP transport**. Direct Chromium navigation to localhost was blocked by the test environment; full live browser-to-server navigation **has not been demonstrated**.
- `python -m studio.verify_partition validation/v05_partition_abs_receipt.json samples/demo_partition_abs.onnx` — valid conditional finite-cover real-number certificate.
- `python -m studio.verify_receipt validation/v05_hidden_spike_receipt.json samples/demo_hidden_spike.onnx --replay` — local exact receipt reanalysis passed.
- `python -m studio.verify_receipt validation/v05_dense_two_reference_receipt.json samples/demo_dense_neural_violation.onnx --replay` — local exact receipt reanalysis passed.

### Demonstration results

| Scenario | Earlier approach | v0.5 result | Correct interpretation |
|---|---|---|---|
| `demo_partition_abs.onnx`, input box `[-1,1]`, required output `[0,1]` | A single interval pass gives an inconclusive `[0,2]` | Two finite partition leaves cover full input range, each enclosed in `[0,1]`, verifier reconstructs all regions | Conditional mathematical real-arithmetic enclosure for a screened model only |
| `demo_hidden_spike.onnx`, input `[-1,1]`, output max `0.5` | Up to 256 deterministic probes found no candidate | SciPy MILP finds float32 input approximately `0.31700000166893005`; exact rational evaluator sees `629125/524288`, NumPy and PyTorch CPU both return `1.199960708618164` | A concrete reference numerical violation, **not execution in official ONNX Runtime** |
| `demo_dense_neural_violation.onnx`, output max `1.0` | NumPy first output 1.25 | PyTorch CPU also reproduced 1.25, and local exact receipts were re-analyzed | Independent implementations agree within stated tolerance on this witness |
| 64 mutated synthetic agent actions | v0.4 toy pre-dispatch policy | All 64 proposals denied, zero synthetic publications; local host HMAC chain validated | Only the fixed in-memory policy against the explicit generated challenge set |
| Publisher signature | Prior unsigned artifact hash could be recomputed | Ed25519 signature verification requires an externally pinned fingerprint; forged content and attacker keys rejected | Source authentication conditional on independent trust pin, not proof of model correctness |

### Negative and robustness tests

- For the finite proof verifier: malformed split axis, split at endpoint, omitted branches, altered split point, changed leaf enclosure, forged leaf counts, altered proof scope, mismatched policy, changed model, missing full cover, rehashed false certificate, and randomized exact rational property checks.
- For solver-guided search: out-of-box float32 candidate abstention, numerical MILP timeout/dependency failure, unsupported operator, enlarged numerical range, absence of witness remains OPEN, candidate must survive exact point recomputation, and independent NumPy/PyTorch replay.
- For publisher signatures: tampered receipt findings, modified source artifact, incorrect fingerprint, new attacker-controlled signing key, modified signature, absent envelope fields, key overwrite refusal, signing refusal on a forged-rehashed receipt, and Unix private key permissions.
- For the synthetic agent guard: prohibited tool names, altered destination/body, argument-schema smuggling, unknown dataset IDs, unicode confusables, invalid shapes, fake policy authority, duplicate action IDs, budget exhaustion, HMAC tampering, and concurrency.

## Tests not performed / remaining trust boundaries

Official ONNX Runtime and the `onnx` package were **not installed** and cannot be retrieved from this environment; no claim of actual ONNX Runtime model execution or structural checker success is made. NumPy and PyTorch are independent references for screened operations only. The finite partition proof is checked by Python rational code with shared arithmetic semantics; **there is no Lean kernel proof** of its source-code correctness. The receipt signer establishes **publisher authenticity when pinned**, not scientific adequacy or production safety. The production PCS v0.6 authority is not called. No hostile operating-system attack, third-party security audit, public deployment, real agent tool integration, or biological validation was carried out.

The browser UI is not an external website, and this testing does not claim production browser support or cloud deployment. Reproducibility depends on the toolchain versions in `V05_ENVIRONMENT.json`. Example models are small controlled fixtures, not external production evaluations.
