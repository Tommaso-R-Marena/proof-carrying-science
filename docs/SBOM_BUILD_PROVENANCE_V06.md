# PCS v0.6 SBOM and Build Provenance

## Purpose

PCS v0.6 can bind supply-chain and build provenance into the same signed package that carries the scientific assurance artifact.

This layer answers a narrower question than scientific verification:

> **What software/build artifact did an identified provenance source describe, and are those exact provenance bytes part of the signed PCS package?**

It does **not** establish that a dependency is safe, that a builder was uncompromised, that an SBOM is complete, or that a scientific claim is true.

## Three distinct provenance levels

PCS keeps three concepts separate.

### 1. Observed runtime

The existing runtime/environment machinery records what PCS observed or reconstructed:

- Python/platform/architecture;
- package/dependency state;
- environment semantic hashes;
- signed restoration inputs;
- realized replay environment.

This evidence is descriptive. It depends on the runtime/platform metadata sources PCS observes.

### 2. Standard SBOM

PCS may bind one software bill of materials under:

```text
provenance/sbom.json
```

Accepted input formats are:

- CycloneDX JSON 1.4, 1.5, 1.6, or 1.7;
- SPDX JSON 2.2 or 2.3.

PCS validates the recognizable top-level standard/version shape and binds the **exact SBOM bytes** by SHA-256 into `provenance/index.json`, whose exact bytes are themselves covered by the signed v0.6 package manifest.

PCS does not reinterpret an SBOM as proof that every dependency is actually present or absent. A forged-but-well-formed SBOM remains false provenance unless some independent process attests it.

### 3. Externally signed build provenance

PCS may additionally bind an external build-provenance statement using:

- DSSE envelope semantics;
- an in-toto Statement v1 payload;
- a pinned Ed25519 public-key fingerprint;
- one or more reviewer/producer-specified expected subject SHA-256 digests.

The package contains:

```text
provenance/build-provenance.dsse.json
provenance/build-provenance-public-key.pem
```

Before PCS signs its package, it verifies that:

1. the envelope is strict JSON and contains the required `payloadType`, `payload`, and `signatures` fields; unrecognized extension fields are ignored for in-toto forward compatibility;
2. `payloadType` is `application/vnd.in-toto+json`;
3. the payload is an in-toto Statement v1;
4. every statement subject carries at least one digest and the statement carries at least one SHA-256 subject;
5. every explicitly expected subject SHA-256 is actually attested;
6. the provided Ed25519 key hashes to the explicitly pinned fingerprint;
7. at least one DSSE signature verifies under that pinned key.

Verification repeats those checks from the signed package bytes.

This establishes at producer packaging time:

> The supplied external Ed25519 key signed this in-toto Statement, and that statement names the expected SHA-256 subject(s).

At review time, the receiver can independently require a particular external signer
fingerprint and subject digest(s), rather than inheriting the producer's trust choice.

It does **not** establish:

- that the signer is trustworthy unless the reviewer has independently chosen/trusted that key;
- that the builder was uncompromised;
- that the build process was hermetic;
- that the subject is malware-free;
- that an OCI image or binary is scientifically correct;
- that the in-toto predicate's claims are themselves true beyond the chosen trust model.

## Provenance index

When any provenance artifact is present, PCS creates:

```text
provenance/index.json
```

with format:

```text
pcs-provenance-index-v1
```

The index is canonical JCS and carries a domain-separated semantic hash:

```text
pcs-provenance-index-sha256-v1
```

The index records the exact SHA-256 and size of each provenance artifact plus the build-provenance signer/subject commitments where applicable.

The verifier requires the `provenance/` namespace to exactly equal the index:

- missing indexed provenance bytes fail verification;
- substituted bytes fail SHA-256 checks;
- extra unindexed provenance files fail verification;
- a stale/wrong expected build subject fails verification;
- a wrong build-provenance signer key/fingerprint fails verification;
- an invalid DSSE signature fails verification.

The PCS package manifest separately signs the exact provenance files and index as ordinary package members. The provenance index is therefore an interpretation/commitment layer inside the already authenticated package, not a competing package signature scheme.

## Exporting an observed-runtime CycloneDX SBOM

PCS can produce a deterministic CycloneDX 1.7 inventory from the local observed Python runtime:

```bash
pcs export-sbom-v06 -o runtime.cdx.json
```

The exported document includes installed Python package name/version records and PCS properties tying it to the observed runtime semantic hash.

This export describes the environment visible to PCS. It is not independently attested build provenance.

## Binding an SBOM to a v0.6 delivery

```bash
pcs attest-v06 manifest.json \
  -o study.pcs.zip \
  --private-key signing-private.pem \
  --public-key signing-public.pem \
  --sbom runtime.cdx.json
```

The exact SBOM bytes become signed package members.

## Binding external DSSE/in-toto build provenance

Suppose an external builder or provenance service gives:

- `build.dsse.json`;
- `builder-public.pem`;
- the independently pinned builder-key fingerprint;
- the expected SHA-256 digest of the image/binary/artifact that should be attested.

Use:

```bash
pcs attest-v06 manifest.json \
  -o study.pcs.zip \
  --private-key signing-private.pem \
  --public-key signing-public.pem \
  --build-provenance build.dsse.json \
  --build-provenance-public-key builder-public.pem \
  --expected-build-provenance-fingerprint <64-hex-fingerprint> \
  --build-provenance-subject-sha256 <64-hex-subject-sha256>
```

`--build-provenance-subject-sha256` is repeatable when multiple exact build subjects must be attested.

PCS deliberately does not infer the expected subject from the untrusted attestation itself. The expected digest must come from the caller/reviewer context.

## Combining SBOM and build provenance

Both may be present:

```bash
pcs attest-v06 manifest.json \
  -o study.pcs.zip \
  --private-key signing-private.pem \
  --public-key signing-public.pem \
  --sbom runtime.cdx.json \
  --build-provenance build.dsse.json \
  --build-provenance-public-key builder-public.pem \
  --expected-build-provenance-fingerprint <fingerprint> \
  --build-provenance-subject-sha256 <subject-sha256>
```

The verification result/receipt reports a `provenance` summary distinct from the scientific claims.

## Reviewer-owned provenance trust

Producer-side validation prevents a PCS producer from accidentally packaging provenance
that does not match the builder key/digest commitments they supplied. A reviewer may
need a stronger condition: **the reviewer, not the producer, chooses which builder key
and build digest are acceptable**.

For a delivered bundle, use:

```bash
pcs verify-v06-bundle study.pcs.zip \
  --public-key trusted-pcs-producer.pem \
  --expected-signer-fingerprint <pcs-producer-fingerprint> \
  --expected-build-provenance-fingerprint <reviewer-trusted-builder-fingerprint> \
  --expected-build-provenance-subject-sha256 <reviewer-expected-build-sha256> \
  --receipt verification-receipt.json
```

The subject flag is repeatable. Reviewer-owned build-provenance trust is fail-closed:
the reviewer must supply **both** a pinned builder fingerprint and at least one expected
subject SHA-256. Supplying only one is rejected rather than silently inheriting the
other trust choice from the producer. If the bundle has no external build provenance,
the builder fingerprint is wrong, or any reviewer-required digest is absent from the
signed in-toto statement, verification fails at the `provenance` stage before
scientific replay is accepted.

The resulting verification receipt records the reviewer provenance expectations so a
reviewer-signed receipt preserves whether these independent pins were applied.

The same requirement can be stored in a `pcs-verifier-trust-v1` profile:

```json
{
  "format": "pcs-verifier-trust-v1",
  "public_key": "producer-public.pem",
  "expected_signer_fingerprint": "<pcs-producer-fingerprint>",
  "expected_build_provenance_fingerprint": "<builder-fingerprint>",
  "expected_build_subject_sha256": [
    "<expected-build-sha256>"
  ]
}
```

This closes an important trust distinction: a package may carry a cryptographically
valid external build attestation without the reviewer trusting its signer. Reviewer
pinning makes that trust choice explicit.

## Reviewer-facing comparison

Extract or retain the `provenance/index.json` files from two signed packages and run:

```bash
pcs provenance-diff-v06 left-index.json right-index.json
```

The diff reports:

- provenance kinds added or removed;
- changed exact SHA-256 values;
- SBOM format changes;
- build-provenance signer changes;
- expected build-subject changes.

PCS does not automatically turn a provenance difference into scientific claim failure. A reviewer policy may decide that a particular workflow requires exact build identity.

## Hardware identity

PCS does **not** make hardware identity a universal baseline requirement.

Hardware/TPM/TEE identity is workflow- and threat-model-specific. If a future workflow needs hardware-rooted attestation, it should be added as a separately named trust contract rather than silently treating `platform.machine()` or other self-reported host metadata as hardware attestation.

This is intentional: the baseline provenance model distinguishes observed runtime facts from independently attested build provenance rather than overstating host identity.

## Trust summary

| Layer | PCS checks | PCS does not thereby prove |
|---|---|---|
| Observed runtime | normalized captured/reconstructed environment metadata | host/runtime honesty or correctness |
| SBOM | recognized standard/version and exact signed SBOM bytes | SBOM completeness/truth |
| DSSE/in-toto build provenance | pinned Ed25519 signature + exact expected subject digest(s) | builder integrity or predicate truth |
| Scientific assurance | existing PCS replay/formal claim logic | biological/clinical/regulatory truth outside declared scope |

Supply-chain provenance and scientific assurance are intentionally adjacent but non-interchangeable.
