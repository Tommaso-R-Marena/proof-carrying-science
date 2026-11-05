# Serialized refinement threat model

## Goal

Connect delivered PCS evidence packages to the already machine-checked assurance
decision semantics without pretending that every byte parser, cryptographic
primitive, scientific replay routine, and serializer has already been proved in
Lean.

## Boundary decomposition

PCS now treats the path as four distinct layers:

```text
A. Raw delivery bytes
   ZIP namespace / file bytes / JSON text / signatures

B. Executable certificate verification
   strict parse + schema + hashes + scientific replay + claim reassessment

C. Claim-scoped normalized wire
   exact context/evidence scope + predicate commitments + decision

D. Lean typed decision semantics
   DecisionWire -> Normalized.DecisionInput -> Assures Γ L C E
```

The point of the normalized wire is to make B -> D small enough to reason about
directly instead of claiming that arbitrary Python execution has somehow become
formal proof.

## Threat: self-consistent forged wire

An attacker could create a perfectly self-consistent normalized wire unrelated
to the certificate that a reviewer actually received.

Mitigation:

`pcs verify-normalized wire.json --certificate certificate.json` independently
replays the certificate, reproduces the expected wire, and requires exact object
equality.

The delivered bundle verifier also validates the packaged normalized set against
the delivered certificate.

## Threat: weakened predicate projection

A Python predicate may contain more semantic fields than Lean models directly.
For example PK/PD replay binds model/output artifacts, column names, relative
tolerance and absolute tolerance.

Dropping those fields before Lean would permit two operationally different
checks to become the same logical predicate.

Mitigation:

The complete canonical Python predicate is committed as:

```text
pcs-predicate-sha256:<digest>
```

and Lean maps that commitment to an opaque predicate identity.

This does **not** prove SHA-256 correctness. It preserves exact identity across
the current refinement boundary without weakening the predicate.

## Threat: valid cryptographic re-signing of false provenance

A compromised or malicious signing process can correctly sign an altered package.
Cryptographic authenticity alone therefore cannot prove that the normalized
state corresponds to the scientific certificate.

Mitigation:

Normalized-state source reproduction is checked independently of the package
signature. Tests explicitly model an altered normalized wire followed by a
fresh valid package signature and require rejection.

## Threat: unrelated evidence smuggling

A certificate may contain many evidence objects. Unrelated passing evidence must
not affect a claim's normalized decision state.

Mitigation:

The wire is claim-scoped and contains only the claim's `required_evidence`,
in the same order. The wire verifier requires exact evidence scope.

## Threat: hidden assumption context

A superset or substituted assumption context can make a claim appear supported
under conditions different from those declared by the certificate.

Mitigation:

The Python wire verifier requires the normalized context IDs to match the
claim's assumption list exactly. Lean requires at minimum `ContextCovers`.

## Threat: duplicate identifiers

Duplicate required IDs or evidence IDs create parser/selection ambiguity.

Mitigation:

The normalizer rejects repeated required IDs and the wire verifier independently
checks both required-ID and evidence-ID uniqueness.

## Remaining trusted components

After PR #17, the following remain outside the machine-checked theorem:

- strict JSON decoding correctness;
- JSON Schema implementation correctness;
- Python scientific/domain checker correctness;
- Python canonical JSON hashing semantics;
- SHA-256 implementation correctness;
- Ed25519 implementation correctness;
- mapping from JSON enum strings into typed Lean constructors;
- the code that establishes `PCS.Wire.WellFormed` from a verified wire object.

These are explicit targets, not hidden assumptions.

## Next theorem target

The strongest useful next step is not “formalize ZIP in Lean.” It is to prove
soundness of a small executable/typed wire validator:

```text
wireCheck w = true
        ->
PCS.Wire.WellFormed (decode w)
```

where `wireCheck` covers source identity, exact evidence scope, uniqueness,
context coverage, predicate commitment equality, and recorded decision equality.

Once that theorem is established, the already proved wire-level soundness yields:

```text
wireCheck w = true
  + accepted recorded status
        ->
Γ ; E ⊢ C @ L
```

The lower JSON/SHA parser boundary remains explicit and can then be attacked
separately with golden vectors, differential testing, or verified decoding.
