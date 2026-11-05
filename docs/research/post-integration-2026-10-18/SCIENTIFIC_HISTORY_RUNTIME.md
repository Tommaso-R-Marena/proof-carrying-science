# Scientific receiving ledger: runtime composition experiment

This isolated wrapper connects `scientific_receiver_v1.host.ReceiverService` to
`authorization_history_v1.history.History` without modifying either API. It
requires fresh execution of the fixed scientific verifier before a new co-signed
artifact can be appended. Returned snapshots contain immutable checked candidate
bytes, exact rational results and a committed anchor. Restart freshly checks the
current incumbent rather than treating signatures or an old receipt as evidence
that mathematical verification occurred in the past.

The scope is **admitted scientific-artifact intake**. Each `PCS-SCI-BOUND-V1`
wire declares its own initial state, transition schedule, unit/physical flags,
environment and bounded claim. The policy does not preserve a fixed scientific
problem, establish empirical truth, improve model quality, prevent forgetting,
promote neural models or authorize production serving. The inherited history
event-class string `model-promotion-authorization` is unchanged serialization
framing; it supplies none of those stronger claims. Snapshot flags
`scientific_acceptance`, `production_authority`, `promotion_authority` and
`historical_scientific_audit` are explicitly false.

## Fixed operator boundary and request bytes

The operator constructs:

```python
ScientificReceivingLedger(path, root, external_anchor, config)
```

Here `root` and `external_anchor` are the unchanged history API's externally
retained trust inputs; `config` is the unchanged host's frozen `OperatorConfig`.
The wrapper rejects any root whose exact policy is not `b'PCS-SCI-HISTORY-V1'` or
whose checker identity differs from:

```python
hashlib.sha256(host._canonical(config.identity())).digest()
```

This is exactly the 32 bytes obtained by decoding the corresponding hexadecimal
SHA256 string. It binds the operator identity representation used by the host,
including executable/source/import pins, command/cwd, environment-value hashes,
toolchain declaration and resource limits. It does not prove that this inventory
is complete, that hashes attest executable semantics or that the host/OS executes
the declared code honestly. The root and config are operator inputs, never
requester-selected fields. Private Python attributes organize the interface;
they are not a security boundary against in-process or host compromise.

The constructor opens `History(path, root, external_anchor)`, constructs its own
`ReceiverService(config)`, and actually verifies the authenticated current
incumbent before making any current snapshot available. No injected verifier,
request callback, requester command, config path or signer service is accepted.
Creation of a genesis store uses the existing operator-owned
`History.create(path, root)` separately; an invalid scientific genesis still
fails the wrapper's startup check.

The only submission argument is an exact immutable `bytes` envelope:

```python
snapshot = ledger.submit(cosigned_envelope_bytes)
```

Its history payload candidate is the **entire canonical scientific wire**, with
model declarations and claim in the same bytes. The auxiliary history certificate
must be empty (`b''`) on every new submission; it is reserved, never interpreted
as a historical scientific-verification receipt. Authority/witness/policy/checker
scope is pinned before scientific execution. Authority and witness sign the same
full unchanged history payload, including candidate, empty certificate,
predecessor chain digest, expected generation/incumbent and next generation.

## Verification, commit and snapshot behavior

The wrapper captures the immutable signed envelope once and decodes it once for
inspection. Under its lock, it first audits the current store/checkpoint/cache and
calls the unchanged private history `_advance` helper as a read-only signature,
scope, link, freshness and generation/incumbent CAS preflight. Invalid signatures,
stale requests and replays reject before launching the scientific service. This
private helper dependency is intentional research composition, not a new public
history API or modification of the old implementation. The preflight's result
is never treated as a committed state.

Only a request passing preflight reaches the wrapper's own host service's
`verify_bytes` on the exact candidate. It requires actual acceptance, no errors,
all host checks true, exact
raw bytes/SHA256/length, exact operator-profile identity, the service's valid
ephemeral receipt signature and a correctly bound verifier response. The
unchanged host's exact raw echo/result validation is repeated before rational
results are copied into frozen `Fraction` fields and typed step/unit/physical
metadata. The host itself runs the configured process and independently compares
the exact result against the Python reference; the positive tests execute actual
Lean, not a synthesized successful response.

Only after these scientific checks does the wrapper call unchanged `History.append` with
the **same original signed envelope bytes**. That operation verifies both real
Ed25519 signatures, full payload/root scope, predecessor, generation/incumbent
CAS, freshness, resource limits, exact replay and the atomic SQLite event/head
commit. These transactional checks run independently again after preflight and
scientific execution, so a concurrent winner still causes final CAS rejection.
A scientific positive is insufficient if signature verification, stale
CAS, SQLite persistence or any other append check fails. No new snapshot is
returned or cached before append reports a successful COMMIT. A per-instance
lock serializes `submit` and `current`; separate ledgers still rely on SQLite's
CAS to reject conflicting intents.

The admitted snapshot is a frozen value containing exact candidate bytes,
`history.Anchor`, raw SHA256, checker identity and a frozen `RationalResult` with
seven `Fraction` values, step count and two boolean declaration flags. Reading
that value never reopens a model path or database and never executes arbitrary
candidate code. It is a historical checked artifact, not an unforgeable Python
capability or perpetual assertion that it remains current.

`ledger.current()` first reaudits the database against the handle's retained
anchor and verifies that the authenticated incumbent equals the cached checked
bytes/anchor. It returns only that cached immutable snapshot. It does not rerun
Lean on every `current()` call; construction/restart does rerun Lean. A tampered
or ahead database makes `current()` fail closed, even if a previously returned
snapshot remains readable as an immutable historical value.

## History validity and recovery limits

The wrapper freshly checks the current incumbent on startup and checks candidates
newly submitted through this wrapper. It does **not** replay every older signed
entry scientifically. History replay authenticates signatures and exact links;
it does not establish that the signers previously ran any scientific checker.
An explicit negative test creates a correctly co-signed mathematically invalid
older entry through the lower-level history API, follows it with a valid current
entry, and shows that reopening this wrapper accepts only the valid current
artifact while retaining `historical_scientific_audit=False`.

Thus no whole-history scientific-validity theorem is claimed from this runtime
interface. Any abstract whole-trace invariant requires a separate premise that
the initial history was scientifically valid and that every later admission used
the checked transition. A wrapper constructor accepting a current state is not
evidence for that initial-history premise. Full historical scientific replay is
outside this experiment.

External publication/retention of each returned anchor remains the caller's
obligation. It is not atomic with SQLite. A crash after actual mathematical
verification but before append leaves the old committed state. A crash after
append COMMIT but before returning/publishing the anchor leaves an ahead store;
ordinary reopen with the old external anchor rejects it. Recovery uses the
existing explicit `history.recover(path, root, previous=..., expected_envelope=...)`
with a protected prior anchor and exact independently retained signed intent.
It performs no automatic append. After recovery the caller explicitly constructs
a new ledger, which rechecks the recovered current scientific bytes under the
fixed profile. A lost return after actual COMMIT also leaves the live wrapper's
cached snapshot inconsistent with its advanced history handle; both `current()`
and further `submit()` calls reject until explicit recovery and reconstruction.
Lost/ambiguous intents and unknown suffixes safely halt; eventual
recovery and independently witnessed publication are not established.

The authority/witness signatures are signed intent. The host receipt is a fresh
ephemeral service statement within the trusted host. Neither is an independently
protected credential or attestation of historical occurrence. The wrapper does
not add a signing service, monotonic witness, key protection, authority rotation,
distributed consensus or production root. Whole-store plus trusted-root/anchor
substitution remains outside the threat model, as in the history experiment.
Interpreter/compiler/import/OS compromise and transient file replacement remain
outside the host guarantee. There is no general Python-to-Lean refinement proof.

## Reproduction and runtime evidence

Run from the repository root with cryptography installed and a real qualified
Lean 4.28.0 environment:

```sh
export PCS_SCIENTIFIC_LEAN=/absolute/path/to/lean-4.28.0/bin/lean
export PCS_SCIENTIFIC_MAIN=/absolute/path/to/scientific_receiver_v1/formal/Main.lean
export PCS_SCIENTIFIC_CWD=/absolute/path/to/scientific_receiver_v1/formal
export LEAN_PATH=/absolute/path/to/receiver/imports:other-required-imports
python -m unittest research.scientific_history_v1.test_receiver -v
```

The test helper searches `LEAN_PATH` for compiled `PCSScientificReceiver` modules
and requires actual Lean v4.28.0. It verifies that the selected Main/module source
bytes equal this combined checkout's receiver source. Local defaults use the
pinned executable at `/workspace/.onboarding/tools/lean-4.28.0-linux/bin/lean`,
the source-identical primary receiver Main, and the qualified v3 environment at
`/workspace/.onboarding/receiver-final-qualified-profile-v3/environment.json`.
Missing actual tooling/imports fail; no mocked-success fallback or skipped
positive control is supplied.

This test configuration pins an explicitly **partial** source/import inventory,
including the wrapper, host/reference, Main, scientific modules and scientific
module oleans. It is not a complete executable/loader/dependency-root attestation.
The co-signature fixture generates two actual fresh Ed25519 keypairs in the test
process; neither is protected or independently administered. No private signing
keys are saved in the reports.

The suite covers actual valid append/current/restart, frozen exact rational
results, truly co-signed false scientific claims, wrong reserved certificate and
root scopes, wrong operator profile, mutable/path/callback rejection, unsigned
candidate tampering and invalid signature/stale/replay rejection before any
scientific launch, a real successful verifier response for substituted bytes,
two actually verified concurrent intents with one CAS winner, current-store
tampering, invalid genesis/current startup, the invalid-older/valid-current
negative boundary, post-verification write/lost-return failures, and actual process exits
before append and after real COMMIT followed by explicit recovery and fresh
startup verification. Fault injection causes rejection or process exit only;
positive verdicts always come from the actual Lean process through the unchanged
host API.

Reports are stored under `research/scientific_history_v1/reports/`. The retained
`development-source-pin-interruption.txt` is an **unqualified development run**:
the wrapper source was edited while its fixture profile was pinned, so the last
test correctly rejected the changed profile instead of reaching its intended
write-failure injection. It is not passing qualification evidence. The separate
`before-auth-preflight-tests.txt` preserves a subsequent stable 14-test passing
run before the read-only authorization preflight and authority-flag naming
changes. The final runtime report uses stable pinned source for the full expanded
run. Pure
formal composition and its CI/audit artifacts are managed in the sibling formal
workstream; this runtime report does not present those proofs as an executable
refinement theorem or as proof of physical scientific validity.
