# Scientific engines: experimental PCS integration

This isolated library integrates two uploaded Aristotle artifacts: PRISM finite-model experiment design and AION infinite-state rare-event bounds. Neither the upload's instructions nor its reported results confer verification authority. Original archives and intake hashes are retained in `provenance/`. Upstream READMEs and papers in `vendor/` document their authors' claims; this README and the admission report describe what PCS actually checks.

The new executable capability connects rare-event mathematics to experiment selection. `PCSScientific.RiskDemo` proves exact hitting probabilities for two linear birth-death models, proves that their risks lie on opposite sides of a threshold, and proves a cheapest distinguishing experiment. A negative control proves that no adaptive policy can identify the risk class when every assay is uninformative. This is a synthetic, model-conditional scientific result. It is not evidence about a biological system or a neural model.

## Run and replay

Use the repository's pinned Lean 4.28.0 and Mathlib dependency cache (`source scripts/activate_lean_428.sh; lake exe cache get`), and install the hashed development requirements. From the repository root:

```bash
python -m research.scientific_engines_v1 risk-demo \
  research/scientific_engines_v1/examples/risk-demo.json /tmp/pcs-risk-demo
python -m research.scientific_engines_v1 replay \
  /tmp/pcs-risk-demo/evidence.json /tmp/pcs-risk-replay
```

Both output directories must be fresh. Each invocation builds the admitted libraries and audits theorem assumptions. Replay rederives the claims from the original input bytes and runs actual Lean proofs again. PRISM evidence contains its exact generated policy certificate, so replay does not need to trust the search result or find the same policy again.

The `prism` command accepts the finite-model problem format in `vendor/prism/examples/*/problem.json`. It returns sharp bounds and, when certified, a globally minimax optimal experiment policy or an impossibility witness. Empty version spaces produce `INCONSISTENT`, never vacuous certification. Search resource exhaustion produces unresolved planning, never an optimality claim.

The `aion` command accepts supported `AION-sandwich-1` certificates. It checks exact rational inequalities in Python, emits a sanitized mathematical instance, and requires ordinary Lean kernel evaluation plus a theorem assumption audit. Python approval alone cannot produce an accepted evidence package. Large certificates may exceed the resource budget and fail closed.

## Trust contract

* Mathematical soundness relies on Lean and the audited standard assumptions `propext`, `Classical.choice`, and `Quot.sound`. Admitted proofs use ordinary kernel checking. Compiler-trusted proof evaluation is excluded.
* JSON parsing, numeric translation, Python execution, filesystem operations, Lean invocation and the pinned dependency cache require a trusted host. The byte-to-mathematics translation is tested, not formally proved. Hashes detect changes relative to a recorded snapshot; they do not establish an immutable root or authenticate an author.
* The abstract mathematical models and their assumptions are explicit. AION's formal probability is an eventual hitting functional of the embedded jump chain. A continuous-time path measure, nonexplosion correspondence and finite-time bounds are not constructed here.
* PRISM's actual-model membership, noiseless observation table and declared query are modeling assumptions. Its probabilistic extension has separate premises; deterministic JSON inputs are not automatically covered by that extension.
* Generic robust and compositional theorems do not certify the external Python robust-interval checker. Unsupported robust and time-bound input claims are rejected.
* No production PCS authority, certificate schema, existing PGSI proof, protected state or historical evidence is changed. These packages do not authorize deployment or model promotion.

## Formal contribution

Six new bridge theorems live in `formal/PCSScientific/Bridge.lean`: `checked_model_interval`, `model_envelope`, `terminal_query_identified`, `identified_risk_classification`, `optimal_identified_risk`, and `posterior_risk_interval`.

Eight concrete theorems live in `formal/PCSScientific/RiskDemo.lean`: `risk_closed`, `cert_ok`, `classifier_correct`, `optimal_safe_experiment`, `exact_optimal_cost`, `initial_risk_ambiguous`, `no_assay_cert`, and `no_assay_impossible`.

The mathematical ingredients are established methods, and no external novelty claim is made. Their checked composition and replay interface are new capabilities in this PCS branch. Existing PCS production authority is kept separate rather than treating imported scientific theorems as permission to execute arbitrary updates.

## Boundary for future integration

PRISM and AION retain their namespaces and original theorem statements. The only upstream runtime correction handles zero experiments in the PRISM emitter; the PCS wrapper removes metadata from emitted Lean. AION's provided numerical proof commands and emitter are changed from compiler-trusted evaluation to ordinary kernel evaluation without changing theorem statements. Admission of a supplied large numerical example requires successful compilation and an explicit audit; presence under `vendor/` alone is not admission.

Future Aristotle serialization and PGSI work should arrive as separate snapshots with exact hashes and complete differential tests. This integration does not assume those changes have arrived.
