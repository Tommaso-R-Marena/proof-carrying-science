# Scientific receiving ledger — artifact-intake research

`ScientificReceivingLedger` joins the unchanged scientific host and authenticated
history APIs. New artifacts must pass the actual operator-pinned mathematical
verifier and the co-signed history append/CAS checks. A frozen snapshot retains
exact checked bytes and rational result metadata. Restart rechecks the current
artifact; older entries are **not** scientifically replayed.

This is not empirical scientific acceptance, model improvement, neural promotion
or production serving. Each wire declares its own problem/schedule/claim. All
`scientific_acceptance`, `production_authority`, `promotion_authority` and
`historical_scientific_audit` snapshot flags are false.

See the [protocol, tests and boundaries](../../docs/research/post-integration-2026-10-18/SCIENTIFIC_HISTORY_RUNTIME.md).

After preparing the real Lean 4.28.0 receiver environment, from the repository root:

```sh
export PCS_SCIENTIFIC_LEAN=/absolute/path/to/lean-4.28.0/bin/lean
export PCS_SCIENTIFIC_MAIN=/absolute/path/to/scientific_receiver_v1/formal/Main.lean
export PCS_SCIENTIFIC_CWD=/absolute/path/to/scientific_receiver_v1/formal
export LEAN_PATH=/absolute/path/to/compiled/receiver/imports:other-required-imports
python -m unittest research.scientific_history_v1.test_receiver -v
```

Tests require actual Lean and real Ed25519 signatures. Missing real-tool inputs
fail the suite; no mocked-success fallback exists. Their explicitly partial pin
inventory is a research fixture, not a complete trusted execution/root profile.
