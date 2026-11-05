# Pilot Signing-Key Custody, Rotation, and Revocation

This document is an engineering operations baseline for PCS pilot signing keys. It is not legal advice, a substitute for an organizational key-management policy, or a claim that local PEM custody is equivalent to an HSM/KMS.

## Objective

A real pilot must not depend on undocumented founder memory for:

- which signer is currently authorized;
- when an old signer stopped being authorized;
- whether a key was merely retired or should be treated as compromised;
- whether historical signatures remain acceptable;
- how recovery/backup was reviewed.

PCS therefore keeps **private key material outside the repository** and records only public lifecycle metadata in a versioned, hash-bound registry.

The registry format is `pcs-key-registry-v1`.

## Non-negotiable rules

1. Never commit a private signing key, seed, passphrase, or recovery secret.
2. Never put private key material in a PCS evidence bundle, issue, CI log, pilot closeout receipt, or key registry.
3. Public keys and fingerprints may be retained indefinitely when needed to verify historical evidence.
4. Use one ACTIVE pilot producer signer at a time unless a later, explicitly reviewed policy introduces a multi-signer authority model.
5. A rotation is not a revocation. Rotation preserves signatures made before retirement. Revocation may invalidate signatures depending on the declared scope.
6. Do not silently delete an old public key after rotation; historical verification needs it.

## Practical small-team custody baseline

For the first external design-partner pilots, use one of these reviewed custody modes:

- `offline_encrypted`: private key generated on a trusted local system and stored encrypted/offline, with a separately protected recovery copy;
- `hardware_backed`: signing key held by a hardware-backed mechanism with recovery/export policy reviewed;
- `reviewed_other`: an explicitly documented alternative reviewed before use.

The lifecycle registry separately records one recovery control:

- `encrypted_backup_verified`;
- `hardware_recovery_verified`;
- `no_recovery_reviewed`.

These fields are operational declarations, not cryptographic proof that custody is sound.

## Registry workflow

Initialize a registry outside the partner data workspace:

```bash
python scripts/pilot_key_lifecycle.py init \
  --registry pilot-signers.json \
  --registry-id pcs-pilot-producer-signers
```

Generate the Ed25519 keypair with the existing PCS key generator. Keep the private file out of the repository and pilot delivery directory.

Register the public key:

```bash
python scripts/pilot_key_lifecycle.py register \
  --registry pilot-signers.json \
  --public-key signing-public.pem \
  --key-id pilot-2026-q4-a \
  --custody-mode offline_encrypted \
  --recovery-control encrypted_backup_verified
```

The registry stores only:

- key ID;
- Ed25519 public-key fingerprint;
- stable SPKI SHA-256;
- activation/retirement/revocation metadata;
- custody/recovery declarations;
- non-secret notes;
- a semantic hash over the registry.

## Rotation

Generate the new key before changing the old registry entry. Verify recovery/custody for the new key, then rotate atomically:

```bash
python scripts/pilot_key_lifecycle.py rotate \
  --registry pilot-signers.json \
  --old-fingerprint <old-fingerprint> \
  --new-public-key signing-public-2027.pem \
  --new-key-id pilot-2027-q1-a \
  --custody-mode hardware_backed \
  --recovery-control hardware_recovery_verified
```

Rotation marks the old key RETIRED and the new key ACTIVE at the same effective timestamp.

A historical package signed before the retirement timestamp may still be accepted under the lifecycle record.

## Revocation

Use revocation when authorization must be withdrawn because of compromise, suspected compromise, policy violation, or another integrity event.

Two scopes exist:

### `all_signatures`

Use when the private key may have been compromised at an unknown earlier time. All signatures from that key are treated as invalid by lifecycle policy, including historical ones.

```bash
python scripts/pilot_key_lifecycle.py revoke \
  --registry pilot-signers.json \
  --fingerprint <fingerprint> \
  --scope all_signatures \
  --reason "private key compromise suspected"
```

### `from_time`

Use only when the earlier authorization remains trustworthy and the key is being deauthorized from a known effective time.

Historical signatures strictly before the revocation timestamp remain acceptable under the lifecycle record.

## Historical signer check

PCS certificates contain a generated timestamp. Before releasing or accepting a pilot package, check the package signer against the registry at the relevant signature/certificate time:

```bash
python scripts/pilot_key_lifecycle.py status \
  --registry pilot-signers.json \
  --fingerprint <fingerprint> \
  --signed-at 2026-10-05T12:00:00+00:00
```

A valid Ed25519 signature and a lifecycle-acceptable signer are separate requirements. One does not substitute for the other.

## Compromise procedure

If compromise is credible:

1. stop signing and stop releasing packages with the affected key;
2. preserve the affected public key, fingerprint, registry, issued package hashes, and minimal incident evidence;
3. revoke with the appropriate scope;
4. identify packages signed by that fingerprint;
5. determine whether previously issued packages must be withdrawn/reissued;
6. generate and register a distinct replacement key;
7. communicate the replacement fingerprint through the approved partner channel;
8. record the incident under `docs/RELEASE_AND_INCIDENT_RESPONSE.md`.

## What remains external/trusted

This repository does not prove:

- that an encrypted backup is actually inaccessible to an attacker;
- that a hardware-backed implementation is uncompromised;
- that organizational identity behind a key is legally authoritative;
- that a revocation notice reached every relying party;
- that a transparency service preserved every issued package.

Those are organizational/infrastructure trust controls and should be strengthened as PCS moves beyond founder-operated pilots.
