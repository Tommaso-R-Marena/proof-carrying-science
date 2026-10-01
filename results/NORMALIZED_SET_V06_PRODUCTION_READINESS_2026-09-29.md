# PCS v0.6 normalized-set production-readiness record — 2026-09-29

## Verdict

**PRODUCTION-READY SUBSYSTEM CHECKPOINT**, with one external infrastructure caveat:
the repository's GitHub-hosted runner did not allocate, so the automatic hosted gate
could not execute. Independent Python and Node execution passed.

Scope of this verdict: `pcs.normalized_wire_v06` and
`pcs.normalized_set_v06`, their schemas, frozen vectors, source-binding behavior,
resource bounds and package-level byte representation.

It is not a verdict on all PCS v0.6 components or on end-to-end formal verification.

## Closed design decisions

- normalized decisions are emitted only after successful executable certificate replay;
- normalized wire v2 is a derived artifact, not an independently trusted assertion;
- RFC 8785/JCS is the exact byte representation;
- predicate, wire and index hashes have distinct domains;
- claim IDs map to portable filenames using the complete SHA-256 digest of UTF-8 claim ID;
- every certificate claim appears exactly once in the normalized index and in certificate order;
- delivered normalized namespace must exactly equal replay-derived namespace;
- wire and index hashes are recomputed;
- exact replay-derived bytes defeat validly rehashed semantic substitution;
- per-wire/index and aggregate resource caps are explicit.

## Frozen values

```text
claim_id = C1
storage path =
normalized/ab861dc170dc2e43224e45278d3d31a675b9ebc34c9b0f48c066ca1eeaed8ee6.json

predicate commitment =
pcs-predicate-sha256-v2:41cca8b472be635d5e56b4ca09adee5868438c4977ac4cf42b239c8ca2822db7

wire semantic hash =
e7fe1b888698f8a06eba17e3f7d6d70142e08e2be2deb580e20c24411b3cd6a5

wire byte SHA-256 =
1b98a9cc7624067b84e254698dc3d8ef6511d895b2da1f01853d68b67e06a17a

index semantic hash =
19463c8ef3196ed3a9d4df9eefdcb7d13afbfadf8f20a55458e794afa074bafa

index byte SHA-256 =
5599ff4b82c5b498b6661326d9b98828c7575a3b4b7f9cbc6db41aef8b002773

package manifest byte SHA-256 =
08650a13f41b4e04f0659d5ec751c014ed614be44bc1d231d99518613ad81aae

package signature payload SHA-256 =
321f1b90cc528c6d4e762fd8133199cfcb150a6f0006ab6297db911022ec951f
```

## Execution evidence

Independent Python execution:

```text
PASS local normalized-set production harness: 11 checks
PASS py_compile + schemas + 25,000 deterministic storage-key/path cases; 0 collisions
```

Independent Node 22 execution:

```text
PASS independent Node: byte hashes, predicate/wire/index domains, full storage path,
2 Ed25519 signatures, package members
```

Adversarial cases exercised include noncanonical serialization, duplicate JSON keys,
missing/extra normalized members, hash/path/source substitutions, exact namespace
coverage, resource bounds, and a fully rehashed wire-plus-index semantic forgery.

## GitHub Actions evidence

Workflow:

```text
.github/workflows/v06-normalized-set.yml
```

First run:

```text
run_id = 36547775211
job_id = 109338223404
conclusion = failure
runner_id = 0
steps = []
```

No test step ran. This is recorded as **CI INFRASTRUCTURE UNAVAILABLE**, not a
verification failure.

## Remaining external dependencies

The subsystem still relies on the correctness of the Python/Node runtimes, JCS
implementation, SHA-256, Ed25519, JSON Schema engine, and the scientific replay
adapters it consumes. Those are explicit surrounding TCB/formalization targets.

The production-readiness claim here is that, given replay output and those explicit
dependencies, the normalized-set subsystem has a frozen deterministic contract,
fail-closed validation, adversarial coverage, resource bounds, cross-language
vectors and independent executable verification.
