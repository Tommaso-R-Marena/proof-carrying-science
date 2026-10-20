# Scientific Authority V2 research

Exact scientific bytes pass a fixed actual Lean receiver, signed authorization
and a separately executable durable witness before local/witness-matching artifact
eligibility. Complete history replay checks genesis and every retained artifact.
Crash recovery uses exact retained authorized material or refuses.

This is a research artifact intake system, not production authority, neural
promotion or empirical scientific acceptance. Separate processes on one host
are Profile A. Independent administration remains unestablished.

Start with `docs/research/scientific-authority-v2/EXECUTIVE_RESEARCH_RESULT.md`,
the witness protocol and full-history audit reports, the complete formal
declaration inventory and `INDEPENDENT_REPRODUCTION.md`.

After independently building/reviewing a scientific qualification:

```sh
python -m research.scientific_authority_v2.bootstrap --qualification /new/qualification --qualification-sha256 REVIEWED_SHA256 --out /new/operator.json
python -m research.scientific_authority_v2.demo --config /new/operator.json --out /new/demo
```

The demo uses actual Lean, Ed25519, SQLite, a real server process and exact
scientific/history replay. No positive mocked verifier fallback exists. Operator
bootstrap/configuration is separate from requester-supplied signed intent bytes.
See the crash matrix for safe halts, recovery behavior and retained rollback
counterexamples. Existing PCS source files and authority are unchanged.
