# Independently executable scientific witness research

This versioned prototype adds a durable third-key post-verification witness to
unchanged PCS scientific/history V1. It checks actual Lean, reserves a pending
co-signed successor, finalizes its own durable checkpoint, signs nonce-fresh views
and exports exact retained artifacts and witness statements. It does not attest
observation of a remote coordinator's local SQLite transaction.

Operator-only explicit initialization and a separate server process:

```sh
python -m research.scientific_witness_v1.server init --db STORE --root ROOT_JSON --config FIXED_VERIFIER_JSON --key RAW32_PRIVATE_KEY
python -m research.scientific_witness_v1.server serve --db STORE --root ROOT_JSON --config FIXED_VERIFIER_JSON --key RAW32_PRIVATE_KEY --port 0 --ready-file READY_JSON
```

The key file is regular, nonsymlink and mode0600; mode alone is not a security
root. It must differ from both intent keys. Existing missing/corrupt state is not
silently initialized. Client pins key/root/configuration independently; nonce-
fresh checkpoint equality is required for current-state claims. An old permanent
receipt cannot make a rolled-back producer current.

Tests use real Ed25519, actual pinned Lean4.28.0 and a real subprocess server:

```sh
python -m unittest research.scientific_witness_v1.test_protocol research.scientific_witness_v1.test_transport research.scientific_witness_v1.test_runtime -v
```

Supply the existing scientific receiver test environment (`PCS_SCIENTIFIC_LEAN`,
`PCS_SCIENTIFIC_MAIN`, `PCS_SCIENTIFIC_CWD`, `LEAN_PATH`) and pinned cryptography
requirements. Missing real tools fail tests, never become a successful mock.
Their source/import pin inventory is explicitly partial. Local CPU/RAM capacity
must permit the two-actual-Lean concurrency control. No GPU is required.

[Protocol](../../docs/research/scientific-authority-v2/WITNESS_PROTOCOL_SPEC.md),
[trust model](../../docs/research/scientific-authority-v2/WITNESS_TRUST_MODEL.md),
and [bootstrap/deployment](../../docs/research/scientific-authority-v2/WITNESS_BOOTSTRAP_AND_KEYS.md)
explain exact supported scope. Loopback subprocesses are Profile A, one underlying
host/administrator. Profile C independent administration remains external; the
software and deployment instructions do not demonstrate it. Whole-witness-store
rollback or simultaneous replacement of all trusted bootstrap material remain
preserved counterexamples. No production authority or deployment is enabled.
