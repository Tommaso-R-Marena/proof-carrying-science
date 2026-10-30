# Strict preflight and complete parallel qualification

This change is stacked on PR #181 at
`2892716e062cbbab66a148476a050432f44b5b0e`. All existing Lean definitions,
theorem statements, axiom policies, tool pins, model/certificate formats and
production authority remain unchanged.

## Reproduced boundary defect

The parent revision compared producer receipt dictionaries with Python equality.
An actual receiving replay accepted a capture whose second action changed from
integer `1` to Boolean `true`, and whose final transition count changed from `4`
to floating-point `4.0`. The original event digest was not recomputed. Python
considers those numeric values equal, so the fresh native/SQL run succeeded and
its dictionary comparison failed to reject the producer's altered representation.

This did not authorize arbitrary tools or an unsafe SQL transition. It was a
real defect in the claim that the exact captured receipts had been reproduced.
The reproduction used actual Lean compilation, native decisions and SQL effects;
it did not substitute an affirmative verifier response. The parent source and
failure observation are retained separately, not relabeled as current results.

## Entire-input preflight

`intake.py` detaches a bounded JSON tree while preserving Boolean/integer/float
distinctions. It validates the complete input before output-directory creation,
verifier startup, ledger creation or tool execution:

- Exact schemas and integer/Boolean types; bounded names, lists, depth and size.
- Canonical lowercase hex, exact model/certificate bytes and current source map.
- Recomputed canonical receipt digests, original proposal bytes/classification,
  native packet fields, source binding, contiguous generations and hash chain.
- Admitted transitions and the fixed synthetic fixture's observed read branch.
- Identical retries, post-goal observations, complete final state and public rows.

The result is an immutable `ReplayPlan`: byte strings and tuples, with no retained
caller dictionary references. A later caller mutation cannot change what replay
consumes. Runtime comparison uses exact canonical receipt bytes after strict type
validation. It cannot accept Python's numeric equality aliases.

A plan supplies **no verification authority**. Replay still builds/checks the
actual native Lean implementation, executes fresh SQL effects, compares every
receipt/final snapshot, and kernel-checks the observed packets/path. The Python
preflight is a fail-early intake check, not a Lean-certified SQL implementation.
No assertion about a proposal's provenance or consent is established by replay.

## Source ownership

`binding.py` captures one immutable source/model identity shared by the builder,
broker and preflight. Broker receipt seeds use that captured identity directly.
Published diagnostic manifests are detached copies; editing a returned manifest
cannot change a later ledger's source identity. These immutable Python values
prevent accidental aliasing; they do not establish an immutable host or a
same-user process security boundary.

The source inventory now includes `binding.py` and `intake.py`. Old captures must
still be replayed at their exact old revision. No compatibility bypass, producer
binary adoption, historical evidence overwrite or production registration is added.

## CI engineering

The original combined research job took 38 minutes. Independent worker, replay,
authority/baseline, codec and pure-intake groups now run in bounded parallel jobs.
Each native group obtains the pinned toolchain and builds its own checked images;
no verifier image or positive decision is transferred between runners. The same
real demonstrations, receiving replays and original-model negative certificate
remain required in a separate evidence job.

`ci.py` discovers every research test module and refuses unassigned, missing or
duplicate assignments and omitted predecessor baselines. The workflow matrix is
generated from this one assignment table. Its final status requires every job to
succeed. It also requires complete, unique, zero-failure/error/skip JUnit reports
covering all assigned modules. Unknown, missing, malformed or DTD-bearing reports
cannot produce aggregate success. The reports are observations, not authority.

Run locally with the same shard commands as CI:

```sh
python -m research.progress_supervisor_v1.ci matrix
python -m research.progress_supervisor_v1.ci test intake /tmp/new-intake-results
source scripts/activate_lean_428.sh
python -m research.progress_supervisor_v1.ci test replay /tmp/new-replay-results
```

Exact execution counts, timings, commits and run URLs are recorded in the stacked
PR and immutable qualification artifacts. Structural fixture tests intentionally
use untrusted claimed receipts; they never claim successful Lean authorization.
Real native/SQL and separate receiving tests remain independent requirements.

The outstanding trust obligations remain Python/SQL/compiler/IO correspondence,
faithful and complete modeling/observation/mediation, and a protected restart
anchor. There is no new real-model safety experiment, general alignment claim,
production merge or deployment.
