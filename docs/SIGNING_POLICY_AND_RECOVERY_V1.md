# Authenticated signing policy and isolated recovery evidence

This optional layer adds authenticated signing eligibility to the existing pilot
key inventory. It does not change certificate formats, existing canonical
verification, public request authentication, or scientific acceptance rules.
Production deployments do not acquire this policy automatically. A valid
signature or policy result always has `pcs_authority: false` here; a separate
existing checker must establish the artifact's meaning and validity.

## Implemented boundary

`pcs/signing_policy_v1.py` authenticates an exact canonical, domain-separated
Ed25519 policy envelope under a human-controlled root public key. The envelope
contains the existing `pcs-key-registry-v1` inventory, revision, validity window,
and exact public key, expiry and signing purpose for every inventoried producer.
Raw-key fingerprints and DER SPKI hashes must both match. Root, observation
authority and producer keys must be distinct. This is a bounded single-purpose
producer policy; it is not a general organizational RBAC framework.

`TrustAnchors(root_public_key, observation_public_key, registry_id,
minimum_revision)` is verifier/operator configuration. Never accept these fields
from an artifact submission. The registry's semantic hash detects accidental
change; it is **not authentication**. Authentication comes from the pinned root
signature. A deployment must advance `minimum_revision` after a policy update;
otherwise an earlier still-valid signed policy can be replayed until its expiry.
The library deliberately does not invent an online authority, production root
key, policy distribution service, or automated root rotation mechanism.

`authenticate_policy(envelope, anchors, now=trusted_clock)` rejects invalid root
signatures, wrong registry identity, expired/future snapshots, revisions below
the installed floor, invalid authority windows, wrong keys and overlapping
roles. `AuthenticatedPolicy` stores immutable canonical bytes; every signing
and verification operation reauthenticates them and reevaluates the policy TTL.
Constructing that dataclass directly cannot bypass authentication.

`sign_object(content_bytes, private_key, policy, purpose=..., now=...)` checks
current ACTIVE authority before signing an exact SHA-256 content binding. It
does not call a scientific verifier and must not be used as a replacement for
the existing guarded `sign_certificate` API. Signature records are a distinct
optional object format, not v0.5/v0.6 certificate signatures.

`verify_object(content_bytes, envelope, policy, purpose=..., now=...)` verifies
the exact digest, purpose, Ed25519 signature and current signing authority.
Retired, revoked, expired and unknown producer keys cannot pass current mode.
Every result explicitly reports `pcs_authority: false`.

## Historical evidence and compromise

A producer-written `signed_at` field does not establish when a signature
existed. Historical mode requires `historical_observation`: a separate pinned
Ed25519 observation authority's signature over the exact envelope digest and
its independently trusted observation time. `observe_object` is the observation
service's authoring helper; a deployment must supply its real trusted clock.
The existence witness does not prove the exact signing instant, an external
timestamp standard, semantic correctness, or a public transparency log.

Both the claimed signing time and the trusted observation time must be in the
eligible window. Observations at/after retirement or expiry fail. A `from_time`
administrative revocation preserves independently observed eligible earlier
history. An `all_signatures` compromise revocation rejects all evidence from the
key, including earlier witnessed evidence. Current policy authentication and
revision-floor enforcement are still required to verify historical evidence.
Trusted root distribution, monotone floor persistence and observation clocks
remain deployment assumptions; they are not proved by these cryptographic tests.

## Executed test-key recovery

Run from the core repository with its installed environment:

```sh
python scripts/exercise_signing_recovery.py \
  --output research/platform-security-v1/signing-recovery.json
python -m pytest -q tests/test_signing_policy_v1.py \
  tests/test_signing_recovery_drill.py tests/test_key_lifecycle.py \
  tests/test_key_custody.py tests/test_signing_v06.py \
  tests/test_receipt_signature_v06.py
```

The executable drill creates four fresh TEST keys in a temporary directory,
encrypts a PKCS8 backup with a random password, restores it, checks its
fingerprint, and verifies an actual Ed25519 possession challenge. It then checks
policy-bound signing, invalid artifact rejection, producer expiry, rotation,
historical observation, policy rollback/corruption and retrospective compromise.
All 17 named controls passed. The backup, password and private keys are deleted
when the temporary directory closes. The committed report contains source
digests and control outcomes, with no key material or passwords. This is an
automated isolated exercise, not a test of production custody or hardware keys.

| Incident | Actual isolated outcome |
| --- | --- |
| Encrypted signing backup lost from active service | Restored test key produces a verified signature with original fingerprint |
| Wrong password or corrupted backup | Decryption/load rejected |
| Signing service unavailable | Missing test-key file raises failure; no signature produced |
| Altered release object | Exact content binding rejects it |
| Expired producer | Current signing/verification denied |
| Producer rotation | Old current signer denied; independently observed old history accepted |
| Attempted old policy restore | Installed revision floor rejects it |
| Corrupted signed policy snapshot | Root verification rejects it |
| Suspected TEST producer compromise | `all_signatures` revocation rejects even witnessed history |
| Replacement unaffected by that compromise | Current replacement signature still verifies |

No Worker deployment rollback, D1 backup/restore, migration recovery, job-state
recovery, failed-CI release recovery or partial-submission recovery is established
by this signing-only drill. Those require their own executed platform exercises.

## Production procedure and rights/provenance boundary

An operator adopting this optional policy should keep the root private key
offline, pin public keys in controlled verifier configuration, record the minimum
accepted revision outside submitted objects, stage signed policy updates, execute
the test-key drill and existing verification tests, and inspect exact test
results before release. In a real compromise, suspend affected signing, establish
the human-reviewed revocation scope, distribute a new root-signed policy and
revision floor, and recheck retained evidence. Never overwrite production
signing material or erase the previous public audit record as a convenience.

All new source files use the repository's existing Apache-2.0 license. Drill
payloads are developer-authored synthetic test objects with no human participant
data, external models or third-party datasets. No production secrets were read,
exported or rotated; no financial information was entered and no paid resource
was created. This bounded evidence does not resolve any unrelated source or
dataset rights issue. Repository-wide inventory and distribution controls are
tracked independently.

There is no formal proof here of Ed25519, secure custody, Python execution,
wall-clock correctness or production incident readiness. Existing Lean authority
and source-refinement claims remain unchanged.
