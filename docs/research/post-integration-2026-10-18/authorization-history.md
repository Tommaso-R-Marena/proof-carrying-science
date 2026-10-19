# Authenticated authorization history v1 — isolated research

This follow-up adds a pure Lean serial-history core and a runnable experimental
counterpart using real Ed25519 signatures and SQLite. It authenticates exact
authorization envelopes under receiver-pinned keys and rejects histories that
disagree with an externally retained checkpoint. It does **not** execute a
scientific checker, establish scientific acceptance, protect a signing service,
provide an independently administered witness, or replace an existing PCS gate.
The P2 production/independent-root completion gate remains open.

The code is confined to `research/authorization_history_v1/`; no existing
authority, certificate schema, serving path, or source gate is modified. The
previously misplaced proof file was moved from
`research/scientific_receiver_v1/formal/PCSScientificReceiver/History.lean` without
changing its bytes. Its SHA256 is
`ac0cfc0d6733c0b4f287dd15941795bdb67b8907c407c96be955aa69b52d65db`.
The standalone project pins Lean and Mathlib v4.28.0.

## Protocol and API

The receiver supplies a `Root`: distinct 32-byte authority and witness public
keys, exact policy/checker identity bytes, genesis event ID, genesis incumbent
bytes and genesis generation. Policy and checker identities are pinned labels;
the runtime does not prove their relationship to an executable or policy meaning.
The fixture generates fresh private keys in the test process. These are research
keys, with no hardware, protected process or separate administration claim.

Both Ed25519 signatures cover the same complete canonical payload, prefixed by
the domain `PCS-AUTHORIZATION-HISTORY-V1` followed by a zero byte. Payloads contain:

- Fixed format and event class `model-promotion-authorization`.
- Exact authority, witness, policy and checker identity bytes.
- Previous and fresh event IDs, previous chain digest, expected and next generation.
- Exact expected incumbent, candidate and certificate bytes.

The wire representation is ASCII JSON with sorted keys, compact separators and
lowercase hex byte strings. Decoding requires exact canonical re-encoding and an
exact field set. Duplicate fields, whitespace variants, alternate numeric types,
unknown fields/classes and uppercase hex fail closed. Each byte field is bounded
to 1 MiB, wire input to 16 MiB, and generations to signed SQLite integer range.
There is no candidate/certificate digest substitution: all bytes are signed and
persisted. No executable is invoked on these untrusted bytes.

Event IDs are opaque fresh labels. A compact external `Anchor` holds generation,
exact incumbent, tip and a SHA256 chain digest. The genesis digest covers a
separately domain-tagged exact root. Each next digest covers a fixed link domain,
the previous 32-byte digest, and the entire canonical envelope including both
signatures. The signed predecessor digest also prevents transplanting a successor
between two signed forks whose generation, incumbent and opaque tip happen to
match. This compact history commitment requires SHA256 collision/second
preimage resistance. It is not unconditional history authenticity and is not the
formal model's link-label theorem. The external anchor is trusted caller input,
not a signed or independently fetched witness publication.

Public operations in `history.py`:

| Operation | Required trusted inputs | Result |
| --- | --- | --- |
| `History.create(path, root)` | Receiver root; fresh exclusive path | New genesis store and handle |
| `History(path, root, expected_anchor)` | Receiver root and exact externally retained anchor | Full replay, or rejection; no default anchor |
| `snapshot()` | Handle's retained root/anchor | Fresh full replay and exact envelopes |
| `proposed_payload(root, expected, event_id=..., candidate=..., certificate=...)` | Expected state | Unsigned exact payload; no authorization claim |
| `append(envelope_bytes)` | Pinned handle; both actual signatures | One atomic local event/head commit; returns next anchor |
| `recover(path, root, previous=..., expected_envelope=...)` | External prior anchor **and exact externally retained intent** | Prior anchor or exact one-event committed successor; no append |

No signer service or scientific acceptance API is supplied. Tests sign with
actual generated Ed25519 private keys; the Lean finite fixtures use an explicitly
symbolic allowlist and make no cryptographic execution claim.

## State, linearization and deterministic recovery

All candidate/certificate bytes and the entire authorization event live in the
same SQLite database as the head. There are no cross-directory model files or
separate receipt files requiring an unproved atomicity claim. Every open, read,
append and recovery replays all records from the external root, checking exact
schema, root, canonical bytes, both signatures, pinned scopes, generation CAS,
expected incumbent, predecessor, fresh event IDs, stored generation and final
head. A malformed event is rejected, never skipped. Extra schema objects and
triggers are rejected. An absent database is not silently initialized.

| Stage | Visible committed state and recovery meaning |
| --- | --- |
| Genesis / external checkpoint retained | Only the exact anchored root/state is accepted |
| Caller retains signed intent externally | No commit; signatures authenticate intent, not publication |
| `BEGIN IMMEDIATE`, full audit, signature verification | Writer lock held; no scientific certificate verification occurs |
| Candidate/certificate/envelope insertion | Uncommitted event; cannot be returned by this API as a committed snapshot |
| Head generation CAS update | Still uncommitted; event and head are in the same transaction |
| SQLite `COMMIT` succeeds | **Local linearization point**: full event and head become committed together |
| Next anchor returned and externally retained/published | Separate caller operation; no atomic DB/witness publication protocol supplied |
| Restart / SQLite hot-journal handling | Exact replay plus external anchor; ambiguous states reject |

The runtime uses `synchronous=FULL`, and creates its databases with rollback
journal mode `DELETE`. Under honest SQLite/filesystem execution, a process death
after event insertion but before head update rolls back the entire transaction;
the same applies immediately before COMMIT. Immediately after COMMIT, the new
event/head survive process exit. This is tested with actual spawned processes
calling `os._exit`, without a cleanup/finally path. Power loss, malicious storage,
faulty hardware, filesystem durability guarantees and arbitrary corruption during
active execution are not proved or comprehensively fault-injected here.

After a commit but before external checkpoint retention, an ordinary reopen with
the old checkpoint rejects the ahead database. Explicit recovery accepts only
either the exact old state or one exact successor matching the independently
retained intent and prior prefix. It never commits the intent itself. A different
signed successor, missing prefix, multiple new commits, malformed record or
invalid retained intent rejects. If the caller lost its intent/checkpoint, safe
halt is permitted: no availability guarantee or automatic reconstruction from
producer receipts is claimed. Caller checkpoint publication can itself fail;
there is no distributed transaction between it and SQLite.

## Threat model and boundaries

The receiver's interpreter, dependencies, executable, runtime Root, external
Anchor and retained recovery intent must remain trusted. Ed25519 verification
and SHA256 commitment assumptions are explicit. Root/anchor protection is an
assumption supplied by a caller, **not implemented by this research fixture**.

| Adversary | Scope and limit |
| --- | --- |
| A: malicious scientific producer | May propose arbitrary candidate/certificate bytes. Cannot bypass pinned signatures under signature authenticity; scientific truth is unaddressed |
| B: compromised proposer/model | Same envelope boundary as A; no policy/root selection from requests |
| C: ordinary model-store writer | Between trusted executions, changes to this DB are audited against external root/anchor. Deletion or corruption can halt service. Arbitrary live-file replacement during a transaction is outside the SQLite execution assumption |
| D: rewrites receipts/local metadata | Exact full replay and compact externally retained chain commitment detect substitutions/rollback under stated crypto assumptions; local hashes alone do not establish completeness |
| E: crashes/scheduling | One honest SQLite DB serializes concurrent appenders; process-crash windows are exercised. Scheduling can indefinitely prevent progress |
| F: altered interpreter/executable/dependencies | Out of scope; can falsify verification or returned snapshots |
| G: host root/compromised OS | Out of scope; can replace trust inputs, code, private keys and persistence behavior |
| H: compromised/colluding governance keys | No semantic authorization guarantee against both signing any payload. An uncompromised required signer still prevents forgery of its signature. No independently operated witness or monotonic signing policy is implemented |

The same generated keys can sign two alternative histories in two databases.
Both can pass their own checkpoint checks. Serial CAS on one database is not
replica consensus, a globally non-equivocating witness or prevention of key-holder
equivocation. A valid later-generation authorization may deliberately reuse old
model bytes; that differs from silent generation rollback.

The tests preserve two necessary negative results. Replacing a committed store
with an old copy is accepted if the caller also reverts its supposedly trusted
external checkpoint. Replacing the database, root and external checkpoint with
an attacker-generated consistent signed history is accepted under those replaced
trust inputs. A receiver observing only that substituted world has the same
inputs as a legitimate receiver bootstrapped into it. No local algorithm or
additional local digest can distinguish the two worlds without a protected
external root/checkpoint or additional trusted observation.

## Established safety versus liveness

| Property | Evidence and qualification |
| --- | --- |
| No unsigned/wrong-scope append | Lean admission theorem conditional on verifier soundness; real signature and mutation tests. Signature intent is not scientific validity |
| Generation monotonicity / no same-generation double commit | Lean serial CAS proofs; two spawned processes against one honest SQLite DB produce exactly one commit |
| Exact append-only envelope links | Pure Lean exact-list extension/link proofs; runtime all-record replay and signature checks |
| Externally anchored rollback/substitution rejection | Runtime exact Anchor check plus computational SHA256 commitment; external protection assumed, not formalized |
| No untrusted policy/checker identity | Pinned identity equality in proof/runtime; no executable or policy-semantics correspondence theorem |
| No partial event/head publication after tested process crashes | SQLite single-transaction experiment at three crash points; no Lean filesystem/crash theorem |
| Deterministic one-intent recovery | Runtime tests for before/after commit and ambiguous recovery; no Lean recovery refinement theorem |
| No serving of a scientifically unverified model | **Not established**: this experiment has no model-serving path or scientific verifier |
| Eventual recovery / progress | Only if honest OS/SQLite operations eventually complete and exact root/prior anchor/intent survive. General liveness, witness availability and distributed recovery remain open |

## Formal/runtime correspondence analysis

The standalone proof retains exact `Root`, `Payload`, `Envelope`, `State`,
`Admissible`, `transition`, serial `run` and linked histories. Its 28 theorems
establish accepted authentication under an explicit `signatureSound` premise,
scope pinning, CAS/predecessor checks, rejection preserving state, generation
monotonicity, append-only extension, replay rejection, serial conflicting-request
rejection, authenticated/link invariants and exact commit counts. Finite
positive/negative fixtures establish nonvacuity using kernel reduction.

| Pure core | Runtime counterpart | Correspondence limit |
| --- | --- | --- |
| Byte lists and exact payload | Python `bytes` and strict canonical codec | No proved codec/injectivity refinement |
| `verify key payload signature` | OpenSSL-backed `cryptography` Ed25519 verification over domain + full payload | Crypto/FFI implementation and signature soundness are assumptions |
| `Admissible` | `_advance` scope, CAS, links, freshness and signature checks | Runtime adds signed predecessor chain digest, strict bounds/nonempty identities/distinct keys; no formal Python refinement |
| Atomic `transition` | Locked audit + SQL insert/head CAS + COMMIT | SQLite/OS atomicity assumption; abstract model contains no precommit states |
| `State.history`, `run_linked` | Exact ordered envelopes replayed from genesis | Runtime rejects every inadmissible stored event; it never uses `run`'s rejection-skipping semantics to excuse a stored row |
| Pure opaque tip labels | Same labels plus signed predecessor digest and runtime SHA256 external chain commitment | The extra payload field, digest/antirollback and checkpoint publication are absent from Lean model; projection to pure payload is not a proved signature-verifier refinement |
| Receiver root/current state parameter | Root plus mandatory external Anchor | Root protection, crash recovery and liveness are unproved |

No theorem states that the Python implementation refines Lean, that abstract
serial proofs imply filesystem safety, or that cryptographic authenticity proves
scientific correctness. Policy rotation, checker upgrades, authority rotation,
retirement/revocation events and independent witness checkpoint publication need
a later protocol; unknown event classes currently fail closed.

## Reproduction and recorded results

From the repository root, using Python with `requirements.txt` installed:

```sh
python -m unittest research.authorization_history_v1.test_history -v
python research/authorization_history_v1/check_formal.py \
  --lean /path/to/lean-4.28.0/bin/lean \
  --cache-root /path/to/repository-with-compatible-mathlib-cache
```

The checker writes only this experiment's `.lake/build/`; it reads existing
Mathlib/import caches without downloading, copying or modifying them. For an
independent clean dependency setup, `cd research/authorization_history_v1/formal`
and `lake build` use this project's pinned configuration. That network/bootstrap
path was not run in this session; fresh source compilation used the existing
v4.28.0 cache and direct pinned Lean executable.

Recorded reports live in `research/authorization_history_v1/reports/`. Refreshed
on 2026-10-19 after workspace restoration: all 17 runtime tests and all 28 theorem
axiom closures pass; retained logs were not lost. Runtime tests use Python
3.12.14, actual Ed25519 with cryptography 50.0.2, SQLite 3.53.1, real temporary
database files and independent spawned processes. Tests cover all signed payload
fields, both signatures, canonical ambiguity, trusted scopes, replay, stale CAS,
whole-store rollback, a signed history fork with identical tip/model/generation,
schema/root/head/event tampering, concurrent writers, pre/post-COMMIT crashes,
deterministic recovery, and the deliberately undetectable trust-root substitution.
The Lean report recompiles the moved proof and standalone root library, then
prints **every theorem's** axiom closure, allowing only `propext`,
`Classical.choice` and `Quot.sound`. There is no `sorryAx`, custom axiom or
`Lean.ofReduceBool` dependency. These reports establish the limited research
properties above; they do not close the broader independent-root milestone.
