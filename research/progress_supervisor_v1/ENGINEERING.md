# Protocol refinement and process-owned execution

This extension is stacked on research commit
`ce726e17b998052518dab54178581da75dae417c`. It leaves protected core sources,
production authority, the website pin, Aristotle/PGSI work and historical evidence
unchanged. `RESULTS.md` and `evidence/local-306a024/` retain the preceding snapshot's
observations. They are not relabeled as tests of the new implementation.

## Closed formal obligations

`Codec.lean` adds eleven ordinary-kernel theorems:

1. `request_roundtrip`: bounded typed requests decode from their encoding.
2. `request_injective`: bounded requests cannot share an encoding.
3. `request_decode_canonical`: any successfully decoded request fits the wire and
   re-encodes to exactly its original bytes. Padding/flag aliases are excluded.
4. `selected_roundtrip`: selected action and rank decode exactly within bounds.
5. `typed_roundtrip`: every typed reply round-trips under `FitsWire`.
6. `process_selected_sound`: parsing a raw selected reply recovers the exact
   authorized choice and rank for the decoded request.
7. `raw_selected_all_outcomes`: every declared outcome of that raw selected
   reply preserves safety and strictly lowers the returned rank.
8. `typed_octets`: every integer emitted by typed-reply encoding is a byte.
9. `process_octets`: the raw request processor emits only bytes.
10. `batch_octets`: the batch processor emits only bytes, including malformed
    trailing frames.
11. `native_octets_roundtrip`: Main's conversion to UInt8 and back preserves the
    complete response list; no integer truncation can change a checked reply.

The generated `PCSProgressData.wire_bounds` is a twelfth new proof obligation. It
checks the concrete certificate's action IDs and ranks rather than assuming they
fit the wire. The authority audits all **34** generic/typed/codec/concrete closures,
fresh-checks `Main`'s import closure, and compiles those same definitions to native
code. Existing `Progress.lean` and `Wire.lean` statements and definitions are
unchanged. No proof specification was weakened and no new axiom was introduced.

These proofs close the Lean-side protocol gap. They do **not** prove the Python
encoder, code generator, C compiler, IO primitives, SQLite or external tools
faithful to Lean. Independent runtime differential tests remain necessary.

## Process interface and failure behavior

`serve` launches the same actual native authority and fixed SQL workflow in a
separate Python process. Only LF-delimited proposal bytes enter the producer
channel. The process owns state, generation, verifier selection and request IDs.
No producer-selected verifier, state override, artifact path, arbitrary tool or
Python callback is accepted. Unsupported fields use the preauthorized malformed
fallback; they never authorize the requested bypass.

Frames have a 4,096-byte maximum and a whole-frame deadline that does not reset
when partial bytes arrive. Reads and buffers are bounded. Oversized, truncated,
silent and slow frames terminate the session; framing errors never resynchronize
to a later attacker-chosen command. A trusted request budget bounds session turns.
Completion closes the session before processing any subsequent queued input.

READY is sent only after real compilation, fresh object checking and fixed-ledger
construction. COMPLETE is sent only after actual effect completion and fresh
ordinary-kernel packet/path checks. EOF/turn exhaustion is INCOMPLETE. Framing,
toolchain and SQLite errors return structured refusal and stop. A process crash,
lost stdout consumer, faulty host or scheduler can still interrupt availability.
Existing ledgers continue to refuse unanchored restart.

This narrows the in-process producer interface. Same-user process/file access,
the host interpreter, compiler, shared libraries and operating system remain
trusted; there is no independently administered or immutable authority root.
Only the authored synthetic SQL tools are qualified. There is no real-model or
empirical AI-safety validation, production registration, merge or deployment.

## Implementation corrections

- Deep bounded JSON nesting now follows the malformed-proposal fallback instead
  of escaping through a Python recursion exception.
- Batch and worker evidence share one publication path. It distinguishes repeated
  observations of one idempotent receipt from separate committed transitions;
  retries do not inflate the kernel path length.
- Both entry points handle actual SQLite failures without an affirmative verdict.
- Generated proofs belong to each workflow's own output directory. A regression
  test exposed `FileExistsError` when a second workflow reused the verified image
  but attempted to reuse a fixed proof filename. The earlier run failed closed
  (21 tests passed before the failure); it is not counted as a passing campaign.
  Sequential retry replay and concurrent workflows now exercise the correction.
  Shared build-command logging is serialized across concurrent proof requests.
- New host/source fingerprints include all execution/evidence entry points. An
  old capsule must be replayed at its exact old revision; historical evidence is
  retained, and no source-integrity check is loosened for compatibility.
- Process inputs have unverified provenance/consent even though the tools are
  synthetic. Worker captures record this explicitly, receiving replay preserves
  the annotation, and results deny automatic training eligibility. No proof of
  provenance, consent or the truth of a producer annotation is implied by replay.
- A maximum-size valid graph (32 states, 16 actions, 512 transitions) exposed
  Lean's default elaboration recursion limit. It correctly refused support.
  Lean elaboration now uses a fixed depth budget of 4,096 for builds and capture
  proofs; the 2,048 MiB memory, command timeouts, fresh kernel and axiom checks
  remain unchanged. A regression exercises the full graph, 544 native decisions
  and an actual captured-packet kernel proof without changing any specification.

## Reproducible qualification

The expanded CI runs the original baseline, existing exhaustive/adversarial/native
tests, fresh-process/crash/retry tests, and real worker sessions. The full-width
campaign checks all 65,536 state IDs and all 65,536 proposal IDs on a model whose
actual IDs cross 255/256 and reach 65,535: **131,072 native request/reply cases**.
This is two exhaustive one-field sweeps, not all 2^32 state/action pairs. JUnit
records the actual sweep count and elapsed native-plus-oracle time.

Worker tests execute real compiler/Lean processes, real SQL effects, separate
receiving replay, malformed and oversized frames, unterminated input, turn limits,
a live silent producer deadline, and injected database failure. Negative controls
use no fabricated positive verifier. The session capture and new receiving replay
are also generated as CI artifacts. Exact test/CI results belong to the current
commit's runs and PR report; source-level contracts above are not empirical claims.

The next strongest obligations are concrete Python/SQL correspondence and a
protected restart anchor. Broader deployment additionally needs independently
validated transition models, trusted observations and complete effect mediation.
