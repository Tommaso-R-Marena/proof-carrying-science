# Security and Trust Model — v0.4

## Core rule

The producer of a certificate is not trusted merely because it produced the certificate. A verifier should reconstruct as much acceptance evidence as possible from the packaged artifacts and check specifications.

## Current trusted computing base

### v0.6 production boundary (authoritative)

For Lean-authoritative v0.6 verification (`pcs verify-v06-bundle` / `pcs-lean-authority`):

- the compiled Lean authority accepting exact canonical ZIP / package bytes;
- the receiver-owned public-key fingerprint pin and Ed25519 verification assumptions;
- Python archive I/O, observation transcript capture, and workflow/environment prechecks that must agree with Lean before `valid: true`;
- the operating system/filesystem used to read delivered bytes.

See `docs/LEAN_KERNEL_STATUS.md` and `docs/TRUST_BOUNDARY_ASSESSMENT_INDEPENDENT_PILOT_V1.md` for the separation of kernel-proved guarantees, independently tested properties, and unproved environmental assumptions. Reviewer receipts may be signed; unsigned receipts remain audit records of a verifier invocation only.

### Historical v0.4/v0.5 note (retained)

For the legacy v0.4/v0.5 path documented below:

- the Python PCS checker;
- the Python runtime and relevant standard-library behavior;
- cryptographic primitives supplied by the `cryptography` package for Ed25519 operations;
- the operating system/filesystem used to read packaged bytes.

That older note treated Lean as not-yet-executable TCB; it is superseded for the production v0.6 ZIP path but retained so historical certificates remain interpretable.

## Integrity layers

1. Artifact SHA-256 hashes bind certificate records to packaged bytes.
2. The semantic hash identifies stable scientific content independent of generation time.
3. The integrity hash binds the complete certificate envelope.
4. An optional Ed25519 signature authenticates the certificate integrity/semantic identity using an external public key.
5. A reproducible ZIP creates an archive/handoff object with a stable SHA-256 for the exact evidence package.

## Threats already tested

The adversarial suite targets:
- artifact modification;
- forged PASS values;
- forged evidence details;
- forged claim status;
- forged workflow summaries;
- path traversal;
- evidence/claim semantic misbinding;
- PK concentration tampering;
- PD effect tampering.

Passing a finite attack suite is not a security proof.

## Key-management rule for pilots

Do not store a production signing private key in a repository or evidence bundle. For early pilots, use a dedicated project signing key stored outside source control. Rotate immediately on suspected exposure.

## Data-handling default

Early pilots should prefer synthetic, public, de-identified, or locally processed data. PCS should be able to certify hashes and evidence without requiring the company to centralize sensitive biological or clinical datasets unless a later enterprise deployment explicitly requires it.


## v0.5 package trust boundary

The certificate signature alone is not sufficient for a human-facing assurance delivery because an attacker could alter an unsigned report while leaving the certificate untouched. v0.5 therefore adds a deterministic `package_manifest.json` enumerating every delivered file except the manifest/signature themselves, with SHA-256 and size. `package_signature.json` signs the manifest with Ed25519.

Verification can pin an expected signer fingerprint supplied out of band. This prevents an attacker from replacing both the bundle and the public key with a self-signed substitute.

Acceptance criteria are deliberately external to the producer bundle. A reviewer supplies an independent `pcs-acceptance-policy-v1` document naming required claims, allowed statuses, signature requirements, and optionally a pinned signer fingerprint. A producer-valid bundle can therefore still be rejected by the reviewer.


## Reviewer verification receipts

`pcs verify-bundle --receipt <path>` can persist a v1 verification receipt. The receipt records the verifier version, exact bundle SHA-256, exact reviewer-policy SHA-256 when supplied, signature/policy requirements, assurance dimensions, and the verification result.

The receipt is an **audit record of a verifier invocation**, not an authenticated statement of reviewer identity. v1 receipts are not separately signed. If reviewer identity/non-repudiation becomes a customer requirement, add a distinct reviewer-signing layer rather than reusing the producer's signing identity.
