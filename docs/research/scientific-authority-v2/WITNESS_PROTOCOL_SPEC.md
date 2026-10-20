# PCS scientific witness v1: implemented protocol

This is an independently executable **research** witness, not a production
principal. Existing intent signatures retain their old semantics. The third,
distinct Ed25519 key signs post-verification witness statements after the actual
fixed scientific service has checked the exact candidate. No old module changes.

## Operator bootstrap and durable state

`WitnessStore.create(path, root, config, witness_key)` explicitly creates a new
SQLite store only when the path does not exist. It checks genesis with actual
Lean first. `WitnessStore(path, root, config, witness_key)` opens an existing
regular nonsymlink bounded store, checks exact schema/root/configuration/key,
replays its authenticated witness chain and reexecutes genesis checking. A missing,
corrupt, substituted or unsupported store does not become a fresh genesis.

The pinned old root has policy bytes `PCS-SCI-HISTORY-V1`, a checker equal to the
raw SHA256 of canonical `OperatorConfig.identity()`, genesis generation zero,
genesis identifier at most 256 bytes, and exact genesis artifact. Root identity is
`SHA256("PCS-SCI-WITNESS-ROOT-V1\\0" || root.encode())`. The two intent public keys
must differ, as in V1; the post-verification witness key must differ from both.
All bootstrap inputs are operator-owned; none can be selected by a request.

## Canonical wire and signatures

Protocol identifier: `PCS-SCI-WITNESS-V1`. Wire is exact canonical ASCII JSON:
sorted keys, no insignificant whitespace, ASCII escaping, finite values, no
additional/trailing bytes. Parser acquisition bounds precede JSON interpretation;
lexical nesting is limited to 32 independently of Python's recursion limit.
Strict request shapes reject unknown operations and fields.

Each signed envelope is exactly:

```
{"statement":{"protocol":...,"kind":...,"root_id":...,"checker":...,
              "witness_key":...,"nonce":...,"payload":...},"signature":...}
```

The signature is Ed25519 over `b"PCS-SCI-WITNESS-V1\x00" + canonical(statement)`.
All encoded bytes are lowercase hex. A receiver verifies against its independently
pinned witness public key and root/configuration, never against a key merely
presented in the envelope. Kinds separate `genesis`, `prepared`, `finalized`,
`checkpoint`, `export`, and `response:<action>`. Permanent statements use empty
nonce. Fresh RPC responses contain the requesting client's random 32-byte nonce;
old signed views cannot satisfy a different current-view challenge.

Anchor representation has exact fields `generation`, `incumbent`, `tip`,
`chain_digest`. Generation is a bounded integer, never a boolean. The chain
commitment and intent signatures use the unchanged V1 exact envelope algorithm.
A fenced adapter deliberately calls V1 `history._advance`; this is an explicit
private-API dependency with unchanged source and regression tests, not a new
cryptographic interpretation of the old event-class string.

## Operations

HTTP POST `/rpc` accepts exactly `{protocol,action,nonce}` plus the action-specific
field. Client methods generate nonces internally and authenticate every response.

- `checkpoint`: payload `{anchor,pending,finalized}`. `pending` is null or
  `{intent,intent_sha256,next_anchor,receipt}`. This fresh response, rather than
  an old permanent receipt, describes current witness state.
  `WitnessClient.checkpoint()` retains its payload-compatible interface;
  `checkpoint_evidence()` returns the complete actual signed response **after**
  the identical receiver-generated nonce/root/profile/key verification. This
  preserves independently replayable signature evidence. Its captured nonce is
  not a substitute for a later observer's own fresh currentness challenge.
- `prepare`: additional `intent` is exact old envelope bytes, hex-encoded.
  Authenticate old signatures/scope/generation/incumbent/predecessor/event
  freshness before launching Lean. Actual `ReceiverService` must return a signed,
  exact-raw/profile/result-bound mathematical acceptance. Reserve one successor
  durably. Return payload `{receipt: <permanent prepared envelope>}`.
- `finalize`: additional `intent_sha256` selects exactly the checked pending
  transition. Append retained intent, prepared and finalized receipts and update
  witness anchor/delete pending in one SQLite transaction. Return
  `{receipt: <permanent finalized envelope>}` only after COMMIT.
- `export`: checkpoint fields plus exact finalized `envelopes` in generation order,
  `receipts` containing intent/prepared/finalized records, and signed `genesis`.
  This supports independent signature checking and retrospective mathematical
  replay; it does not turn untrusted producer claims into a witness record.

Prepared payload contains exact `intent`, its SHA256, previous/next anchors and
`verification`. Verification contains the actual Lean JSON response, its SHA256
and SHA256 of the actual host receipt. Full inner ephemeral host receipts are not
retained in this store; witness signatures attest the scoped observation under
honest witness execution. Exact artifact and Lean response remain retained for
reconstruction/replay. Finalized payload binds the same intent SHA256, previous
anchor, finalized anchor and SHA256 of the exact prepared signed envelope.

Duplicate identical prepare/finalize requests are idempotent. An old finalized
intent may return its historical receipt; that receipt makes no current-head
claim. A different pending successor rejects. No abort, rotation, policy/checker
migration, key replacement or arbitrary verifier selection is implemented.

## Distributed meaning

PREPARE attests that this witness executed the fixed scientific check and reserved
this exact co-authorized successor. FINALIZED attests the witness's own durable
commitment. Neither statement claims the witness observed a coordinator's local
SQLite COMMIT. The coordinator's separate serving rule must require local state
matching a fresh finalized witness checkpoint and no unresolved pending record.
A caller can request finalize without proving its own local commit; this creates
no serving authority for missing/mismatched local bytes. Remote and local SQLite
transactions never become one atomic transaction by assertion.

Honest serial durable witness-state continuity excludes two incompatible accepted
successors of one predecessor. Witness-key compromise, witness-store rollback,
multiple independently forked witness copies or replacement of all trusted
bootstrap material are outside that property. Independent retained observers or
another protocol are required to detect those stronger adversaries.

## Resource and transport limits

Intent 40,000 bytes; scientific candidate/incumbent 8,192; event and genesis IDs
256; at most 32 finalized events; request 81,024 bytes; response 4 MiB; database
16 MiB and SQLite value 8 MiB; one pending event. SQLite uses DELETE journaling,
`BEGIN IMMEDIATE`, synchronous FULL, exact table schemas and checked sidecars.
A process crash is not a physical power-failure proof.

The service is serial and intentionally bounded. TLS handshake acquisition has
an absolute five-second deadline. HTTP headers plus body have an absolute
five-second deadline, not a trickle-resettable idle timer. Response writes have
a five-second socket timeout. Actual mathematical verification uses the fixed
host's separate deadline. Correctly authenticated expensive requests can still
occupy the serial service; admission control/denial-of-service protection is not
established.

Loopback HTTP is Profile A only. Nonloopback service binds require operator TLS
certificate/key. The client refuses nonloopback HTTP, verifies remote certificates
with the standard CA mechanism (or an operator-supplied CA), pins witness
Ed25519 identity separately and rejects redirects. TLS authenticates transport,
not scientific validity. No deployment has occurred.
