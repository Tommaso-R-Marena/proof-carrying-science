# Normalized Decision Wire v1

## Purpose

`pcs-normalized-decision-v1` is the deliberately small serialization boundary
between an independently replay-verified PCS certificate and the Lean decision
semantics.

It is claim-scoped. One wire object represents one claim, only the assumptions
that claim names, and only the evidence IDs that claim requires.

This reduces the formal refinement surface and prevents unrelated certificate
state from becoming part of the trusted decision input.

## Executable flow

```text
certificate.json + packaged artifacts
        |
        | verify_certificate
        |   - strict JSON/schema
        |   - certificate hashes
        |   - artifact hashes
        |   - evidence replay
        |   - claim/evidence references
        |   - semantic predicate validation
        |   - claim reassessment
        |   - workflow replay
        v
verified PCS v0.5 certificate
        |
        | pcs normalize-decision --claim C
        v
pcs-normalized-decision-v1
        |
        v
Lean wire decoder / refinement theorem
        |
        v
Normalized.DecisionInput
        |
        v
machine-checked decision soundness
```

The normalizer refuses to emit a wire object when certificate replay fails.

## Exact predicate commitment

Python predicates can contain domain-specific fields that the current minimal
Lean `Predicate` datatype does not model directly. For example,
`pkpd_reference_match` includes:

- model artifact;
- output artifact;
- time/concentration/effect columns;
- relative tolerance;
- absolute tolerance.

Projecting that richer object down to only model/output IDs would weaken the
semantic binding before entering Lean.

The wire format therefore uses:

```text
pcs-predicate-sha256:<64 lowercase hex chars>
```

where the digest is over the complete canonical JSON predicate.

Every required evidence object must produce exactly the same commitment as the
claim predicate before normalization succeeds.

The Lean wire layer treats this commitment as an opaque predicate identity. The
cryptographic correctness of SHA-256 and the JSON canonicalizer remain in the
executable serialization/refinement TCB until separately verified.

## Additional normalization constraints

The wire exporter rejects:

- unknown claim IDs;
- repeated required evidence IDs;
- repeated assumption IDs;
- missing required evidence;
- missing named assumptions;
- any required evidence whose normalized predicate commitment differs from the
  claim commitment;
- any certificate whose recorded claim assessment differs from the pure Python
  decision kernel;
- any certificate that does not independently replay-verify first.

## CLI

```bash
pcs normalize-decision evidence/certificate.json \
  --claim C_PK_REPLAY \
  -o normalized-C_PK_REPLAY.json
```

The output is validated against
`pcs/schemas/normalized_decision.schema.json`.

A reviewer can independently recompute the wire invariants:

```bash
pcs verify-normalized normalized-C_PK_REPLAY.json
```

and can additionally require that the wire be reproduced *exactly* from a
specific independently replay-verified source certificate:

```bash
pcs verify-normalized normalized-C_PK_REPLAY.json \
  --certificate evidence/certificate.json
```

The second form prevents an internally self-consistent wire object from being
silently substituted for the state actually derived from the cited certificate.

## Scope and non-claim

This wire format does not prove that Python's JSON parser, SHA-256
implementation, domain checkers, or serializer are correct.

Its purpose is to make that remaining boundary explicit, deterministic, small,
versioned, adversarially testable, and suitable for a direct Lean refinement
theorem.
