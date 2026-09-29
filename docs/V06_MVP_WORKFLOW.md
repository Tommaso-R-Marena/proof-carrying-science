# PCS v0.6 MVP workflow

Status: **first complete producer-to-reviewer product path**.

## Product loop

The producer starts from the existing PCS project manifest format and exact source
artifacts:

```bash
pcs attest-v06 manifest.json \
  -o study.pcs.zip \
  --private-key organization-private.pem \
  --public-key organization-public.pem
```

The reviewer receives only the bundle plus a separately trusted public key or
fingerprint:

```bash
pcs verify-v06-bundle study.pcs.zip \
  --public-key trusted-public.pem \
  --expected-signer-fingerprint <trusted-fingerprint> \
  --receipt verification-receipt.json
```

## Producer invariants

The producer:

1. parses the project manifest with duplicate-key rejection and schema validation;
2. requires safe unique IDs;
3. copies every source artifact into the package before scientific checks execute;
4. hashes and checks the copied bytes, not the mutable source path;
5. replays supported built-in checks;
6. derives evidence outcomes and claim assessments rather than trusting recorded PASS;
7. requires exact claim/evidence predicate equality;
8. derives bidirectional assumption scope;
9. builds the typed v0.6 workflow and recomputes its DAG summary;
10. emits the canonical JCS v0.6 certificate;
11. derives the normalized decision set only after replay;
12. signs the certificate and exact package manifest with Ed25519;
13. independently verifies the generated package directory;
14. emits the deterministic delivery ZIP;
15. independently verifies the exact candidate ZIP and its SHA-256;
16. atomically publishes the bundle only after the post-build verification succeeds.

A producer keypair mismatch, artifact path escape, predicate substitution, package
tamper, normalized decision substitution, signer mismatch, or post-build archive
failure is fail-closed.

## Supported MVP evidence

The producer currently supports these executable checks:

- `csv_disjoint`
- `reaction_balance`
- `unit_compatible`
- `pkpd_contract`
- `pkpd_reference_match`

This is intentionally narrower than the certificate schema. External proof,
empirical, statistical, and provenance evidence remain explicit boundaries and are
not synthesized as verified PASS by the MVP producer.

## Reviewer-controlled acceptance

The reviewer may apply the external `pcs-acceptance-policy-v1` contract while
verifying the delivered ZIP:

```bash
pcs verify-v06-bundle study.pcs.zip \
  --public-key trusted-public.pem \
  --expected-signer-fingerprint <trusted-fingerprint> \
  --policy reviewer-policy.json \
  --receipt verification-receipt.json
```

The receipt deliberately separates:

```text
valid     = PCS accepted the package, signatures, replay and normalized decisions
accepted  = valid AND the external reviewer policy passed
```

This prevents reviewer preferences from rewriting the scientific record. For
example, a package may remain `valid: true` while `accepted: false` because the
reviewer requires `FORMALLY_VERIFIED_UNDER_ASSUMPTIONS` and the replayed claim is
only `COMPUTATIONALLY_SUPPORTED`.

Reviewer policy can require exact claim statuses, require authenticated delivery,
and independently pin the signer fingerprint. The verification receipt records
SHA-256 of the exact policy-file bytes used for that decision.

## Reviewer-signed audit receipts

The producer and reviewer use separate trust identities.

```text
producer Ed25519 key
    ↓
signs scientific certificate + package manifest

reviewer verification + reviewer policy
    ↓
deterministic receipt bytes

reviewer Ed25519 key
    ↓
signs exact receipt hash + package/policy/verdict commitments
```

The reviewer may create the signed audit record in the same verification command:

```bash
pcs verify-v06-bundle study.pcs.zip \
  --public-key producer-public.pem \
  --policy reviewer-policy.json \
  --receipt receipt.json \
  --reviewer-private-key reviewer-private.pem \
  --receipt-signature receipt.sig.json
```

Independent receipt audit is a separate operation:

```bash
pcs verify-receipt-v06 receipt.json \
  --signature receipt.sig.json \
  --reviewer-public-key reviewer-public.pem \
  --expected-reviewer-fingerprint <reviewer-fingerprint>
```

The signed payload binds the exact receipt SHA-256 plus the delivered bundle hash,
policy hash, certificate commitments, normalized-index commitment, PCS validity,
and reviewer acceptance. Changing a single byte of the receipt changes its hash
and invalidates the reviewer signature.

This layer provides non-repudiable review provenance under the selected Ed25519
key. It does not alter the underlying scientific decision.

## Honest negative results

PCS verification and scientific success are different axes.

A package can be fully authentic, replay-consistent, and valid while a claim has:

```text
FALSIFIED_OR_CHECK_FAILED
```

That behavior is required. PCS verifies that the delivered scientific record agrees
with independent replay; it does not suppress or relabel failed science.

## Current formal boundary

The executable v0.6 producer/reviewer path is not yet the same thing as the existing
Lean raw-wire-to-`Assures` theorem stack, which was proved over the older v0.5/v1
wire. Porting that proof onto the exact v0.6/v2 representation remains separate
formalization work.

Likewise, arbitrary Python/R/C++ programs, Ed25519 implementation correctness,
SHA-256 correctness against the mathematical standard, and ZIP parsing are not
claimed as formally verified.

## MVP criterion

For the initial computational-biopharma pilot, the minimum product loop is now
present:

```text
bounded project
  → one producer command
  → portable signed ZIP
  → one independent reviewer command
  → deterministic verification receipt
```

The next validation milestone is external use by a design partner on a workflow not
constructed by the PCS authors.
