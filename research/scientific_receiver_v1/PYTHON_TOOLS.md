# Research Python tooling

These tools belong to the frozen `PCS-SCI-BOUND-V1` experiment. Python produces data and supplies finite differential evidence; it does not define Lean acceptance or grant scientific/production authority.

`producer.py` constructs evidence using direct sums and encodes the exact wire grammar. Its strict JSON adapter requires exactly `protocol`, `referenceStep`, `unitCode`, `physical`, the eight rational fields named in `PROTOCOL.md`, and `firings`. Booleans are JSON booleans. Rationals are reduced `numerator/denominator` strings, including `0/1` and integer `1/1`. Duplicate/unknown keys, floats, negative zero, alternate rational spellings and coercions reject. This adapter validates syntax/resources; it deliberately does not grant scientific acceptance.

`reference.py` independently parses the raw bytes, without importing producer logic. It replays every exact rational transition and physical intermediate state. `assess(raw)` reports an explanatory decision; `receive(raw)` returns the scoped result or `None`. Its internal rational results are integer pairs. The differential runner compares these with the Lean CLI's canonical rational strings.

The preregistration is committed before pilot and actual Lean evaluation. The default seeded corpus has 10,774 cases, 778 independently labeled positive expectations and 44 named families. Its digest binds the ordered case names and bytes with four-byte big-endian lengths; this digest is experiment-local, not a signature or universal canonicalization standard. The corpus includes consistent changes as positive controls, so a changed initial value or schedule is not intrinsically rejected.

Run from the repository root with the project Python environment:

```bash
python -m pytest -q research/scientific_receiver_v1/tests
python -m research.scientific_receiver_v1.differential --checker /absolute/actual/receiver --out /fresh/differential/output
python -m research.scientific_receiver_v1.pilot --checker /absolute/actual/receiver --out /fresh/pilot/output
```

For the actual pinned Lean interpreter executing compiled IR, the harness also accepts repeatable executable arguments, for example `--checker /absolute/pinned/lake --checker-arg=env --checker-arg=lean --checker-arg=--run --checker-arg=/absolute/Main.lean --checker-cwd=/absolute/formal`. These are harness arguments, not fields admitted at the scientific receiving interface. The recorded command, executable hash, argument-file hashes and working directory distinguish native execution from Lean interpreter execution. No fake checker, Python stand-in or fabricated positive is used.

The CLI transport is four-byte unsigned big-endian length followed by exact bytes, with one JSON line per request. Bounded requests run in batches. Oversize framing is isolated because it terminates that process without consuming the payload. All bounded responses must echo the exact bytes and fixed protocol/scope metadata. Accepted results are compared field by field against the independent exact replay.

`differential.json` records counts, timing, hashes, disagreements and per-family outcomes. `decisions.jsonl` records actual responses, and `corpus-manifest.json` preserves every tested bytestring. The pilot records one actual Lean receiving case, original-path PK sampled replay, and original-path finite-SCM nonidentifiability. PK/SCM computational observations and unverified empirical claims retain separate labels. Zero observed disagreements is finite campaign evidence; it does not establish a general Python refinement theorem, compiler/IO/OS correspondence, an independently protected root or empirical science.
