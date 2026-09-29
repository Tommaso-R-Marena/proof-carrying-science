# PCS v0.6 Normalized Decision Set v2

Status: **production-ready subsystem checkpoint** for the PCS v0.6 research line.

This document defines the executable contract for deriving, serializing, indexing,
shipping, and verifying claim-scoped normalized decisions. It is intentionally
narrow: it does not define the entire PCS product and it does not broaden the
scientific claims made by PCS.

## Security objective

A delivered normalized decision must not become authoritative merely because its
bytes are well-formed, hashed, or signed.

The accepted chain is:

```text
typed/hash-valid v0.6 certificate
  -> fresh executable evidence replay
  -> recomputed claim assessment
  -> deterministic claim-scoped normalized wire
  -> deterministic normalized index
  -> canonical RFC 8785/JCS bytes
  -> package byte/hash/signature binding
```

The normalized set is therefore a **derived artifact**, not an independent source
of truth.

## Formats

Wire format:

```text
pcs-normalized-decision-v2
```

Index format:

```text
pcs-normalized-decision-index-v2
```

Canonical JSON profile:

```text
pcs-jcs-rfc8785-v1
```

Domain-separated hashes:

```text
pcs-predicate-sha256-v2
pcs-normalized-decision-sha256-v2
pcs-normalized-index-sha256-v2
```

The JSON Schemas are:

```text
pcs/schemas/normalized_decision_v06.schema.json
pcs/schemas/normalized_decision_index_v06.schema.json
```

Public copies under `schemas/` are required to remain byte-identical.

## Wire semantics

Each claim wire binds exactly:

- source certificate semantic and integrity hashes;
- PCS spec/checker version;
- claim ID and assurance kind;
- the claim predicate commitment;
- exact ordered assumption scope and assumption statements;
- exact ordered required-evidence scope;
- each evidence ID, kind, replay-established outcome and predicate commitment;
- the recomputed decision;
- the domain-separated wire semantic hash.

No recorded “valid” booleans are accepted as proof inputs.

Internal validation recomputes:

- source claim ID = normalized claim ID;
- evidence IDs are unique;
- evidence order/scope = required-evidence order/scope;
- context IDs are unique;
- context order/scope = claim assumption order/scope;
- every required evidence commitment = claim predicate commitment;
- decision = pure decision-kernel recomputation;
- wire semantic hash.

Verification against the source certificate additionally regenerates the entire wire
after fresh replay and requires exact object equality.

## Portable storage

Claim IDs are semantic identifiers and may contain characters unsuitable for
cross-platform filenames. They are never used directly as normalized filenames.

For a claim ID `C`:

```text
storage_key = hex(SHA256(UTF8(C)))
path        = normalized/<storage_key>.json
```

The full 256-bit SHA-256 digest is used. It is not truncated.

For the frozen claim `C1`:

```text
normalized/ab861dc170dc2e43224e45278d3d31a675b9ebc34c9b0f48c066ca1eeaed8ee6.json
```

## Normalized index

Every package carries:

```text
normalized/index.json
```

The index binds:

- source certificate semantic hash;
- source certificate integrity hash;
- exact certificate claim order/scope;
- each claim ID;
- its deterministic normalized-wire path;
- its recomputed decision;
- its wire semantic hash;
- the domain-separated index semantic hash.

Verification requires the normalized namespace to equal the replay-derived namespace
exactly. Missing files, extra files, duplicate claim IDs, duplicate paths, path
substitutions, source-hash substitutions, decision substitutions, wire substitutions
and claim-scope substitutions fail closed.

## Resource limits

```text
single normalized wire:  10 MiB
normalized index:        10 MiB
aggregate normalized set: 100 MiB
certificate claim count: bounded by certificate schema
```

The aggregate limit is enforced during deterministic set construction.

## Frozen golden vector

The current deterministic v0.6 corpus binds:

```text
predicate commitment
pcs-predicate-sha256-v2:41cca8b472be635d5e56b4ca09adee5868438c4977ac4cf42b239c8ca2822db7

wire semantic hash
e7fe1b888698f8a06eba17e3f7d6d70142e08e2be2deb580e20c24411b3cd6a5

wire byte SHA-256
1b98a9cc7624067b84e254698dc3d8ef6511d895b2da1f01853d68b67e06a17a

index semantic hash
19463c8ef3196ed3a9d4df9eefdcb7d13afbfadf8f20a55458e794afa074bafa

index byte SHA-256
5599ff4b82c5b498b6661326d9b98828c7575a3b4b7f9cbc6db41aef8b002773
```

The normalized wire and index are signed package members, so the package manifest and
package Ed25519 signature bind their exact bytes as well.

## Adversarial coverage

`tests/test_normalized_set_v06.py` covers, among other cases:

- noncanonical index bytes;
- duplicate raw JSON keys;
- index hash tampering;
- validly rehashed path substitution;
- missing normalized wire;
- unsigned/unexpected normalized member;
- validly rehashed empty index hiding a certificate claim;
- validly rehashed certificate-hash substitution;
- a wire forgery where the attacker changes context text, recomputes the wire hash,
  updates the index, and recomputes the index hash;
- aggregate resource-limit enforcement;
- multi-claim deterministic ordering and distinct full-SHA storage paths.

The last attack is important: internally self-consistent hashes do not make a forged
wire valid, because verification regenerates the normalized set from replayed source
certificate semantics and compares exact bytes.

## Independent execution evidence

On 2026-09-29 the exact normalized-set/wire implementation and schemas were
reconstructed from the branch and executed independently of GitHub Actions.

Python checks:

```text
PASS local normalized-set production harness: 11 checks
PASS py_compile + schemas + 25,000 deterministic storage-key/path cases; 0 collisions
```

The local production harness checked exact frozen regeneration, canonical parsing,
duplicate-key rejection, missing/extra-member rejection, fully rehashed
wire-plus-index forgery rejection, and resource bounds.

Independent Node 22 check:

```text
PASS independent Node: byte hashes, predicate/wire/index domains, full storage path,
2 Ed25519 signatures, package members
```

The Node path independently recomputed the predicate commitment, normalized-wire
hash, normalized-index hash, claim storage path, package member hashes/sizes, and
verified both frozen Ed25519 signatures from the raw test public key.

## CI infrastructure status

`.github/workflows/v06-normalized-set.yml` is an automatic production gate for this
branch and runs the repository v0.6 contract gate.

The first GitHub-hosted run (run 36547775211) failed before execution because GitHub
assigned no runner:

```text
runner_id = 0
steps = []
```

That is an infrastructure failure, not a failing test result. No workflow step ran.
The independent Python and Node executions above are therefore the current executable
evidence for this checkpoint. The hosted gate should be rerun when repository runner
allocation is restored.

## Trust boundary / non-claims

This subsystem establishes deterministic derivation and fail-closed binding of
normalized decisions to replayed certificate semantics.

It does **not** prove:

- the scientific truth of a model beyond the implemented replay checker;
- UTF-8/JSON/JCS/SHA-256/Ed25519 implementations mathematically correct;
- raw ZIP extraction correct;
- the future Lean serialized-byte refinement theorem.

Those remain separate PCS boundaries. This subsystem is specifically the executable
meeting-point representation that those lower/formal boundaries can target.
