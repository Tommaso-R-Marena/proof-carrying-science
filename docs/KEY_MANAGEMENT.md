# Pilot Signing-Key Management

This is an engineering baseline for early pilots, not a substitute for enterprise key-management policy.

## Rule 1: private keys never enter source control or evidence packages

- Keep signing private keys outside the repository and outside attestation output directories.
- `.gitignore` excludes common private-key extensions.
- PCS bundle creation also scans for standard PEM/OpenSSH private-key headers and fails closed if apparent private-key material is staged for delivery.
- Public keys may be distributed to reviewers.

## Key scope

For early design partners, prefer a dedicated signing key per organization or per pilot series rather than one global founder key.

Record:

- key purpose;
- creation date;
- public-key SHA-256 fingerprint;
- pilots/releases authorized by the key;
- storage location class, not the secret path/password;
- rotation/revocation date.

## Reviewer pinning

A signature is not useful if an attacker can replace both the package and public key.

Transmit or establish the expected public-key fingerprint through an independent trusted channel. Reviewer policy should pin that fingerprint where practical.

## Rotation

Rotate a key when:

- private-key confidentiality is uncertain;
- a device/account containing it is lost or compromised;
- personnel authorization changes;
- the agreed pilot scope ends and long-lived reuse is unnecessary;
- cryptographic policy requires rotation.

A rotated key does not retroactively invalidate old correctly signed bundles. Preserve the old public fingerprint and authorization record.

## Compromise response

On suspected exposure:

1. stop signing new PCS packages with the key;
2. record the earliest plausible compromise time;
3. notify affected pilot reviewers;
4. generate a replacement key;
5. distribute and pin the replacement fingerprint through a trusted channel;
6. identify packages signed after the suspected compromise time for re-review/re-signing;
7. preserve incident evidence.

PCS does not yet implement a public revocation/transparency service. Until it does, key authorization/revocation is an operational responsibility.

## Production direction

Before regulated/enterprise deployment, move signing into a managed HSM/KMS or comparable controlled signing service with access logging, role separation, rotation, and revocation policy.
