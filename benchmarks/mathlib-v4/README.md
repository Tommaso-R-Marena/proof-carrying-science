# Reproduce the source-only benchmark

Activate the pinned Lean4.28 environment and exact Mathlib8f9d9 dependencies, then:

```sh
python -m pcs.experimental.prover.benchmark_mathlib_v4 --root benchmarks/mathlib-v4 --mathlib .lake/packages/mathlib
```

`EXTRACT_SIGNATURES.lean` reads theorem types/universes only. `VALIDATE_RENDERING.lean` elaborates every rendered proposition and checks definitional equality against its authentic declaration. Run these with Lean and the existing Mathlib package paths for an independent regeneration; outputs must agree with the retained signature/round-trip receipts. They do not attempt proofs or disclose theorem bodies.

`protocol.json` freezes budgets and portfolio before fitting/evaluation. `tasks.json` is evaluation-only; do not feed it to training or retraining. Evaluation models may receive the current immutable goal and filtered eligible premises, but benchmark identities, target declaration names and solution bodies are evaluator metadata, not policy input. A proof must be independently reconstructed against that same proposition. `ARTIFACT_SHA256.json` records exact membership and byte hashes; supply its receiver-approved digest when verifying artifacts acquired from an untrusted source.
