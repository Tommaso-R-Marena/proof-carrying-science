from __future__ import annotations

from copy import deepcopy

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from pcs.key_lifecycle import load_registry, register_active_key, revoke_key, rotate_key, write_new_registry
from pcs.signing import generate_keypair
from pcs.signing_policy_v1 import (
    POLICY_FORMAT, AuthenticatedPolicy, SigningPolicyError, TrustAnchors,
    authenticate_policy, observe_object, public_key_b64, sign_object, sign_policy, verify_object,
)

T0 = "2026-10-01T00:00:00Z"
T1 = "2026-10-02T00:00:00Z"
T2 = "2026-10-03T00:00:00Z"
T3 = "2026-10-04T00:00:00Z"
T4 = "2026-10-05T00:00:00Z"
T5 = "2026-10-06T00:00:00Z"
CONTENT = b'{"result":"checked fixture","pcs_authority":false}'


@pytest.fixture
def fixture(tmp_path):
    from cryptography.hazmat.primitives.serialization import load_pem_private_key
    root, observer = Ed25519PrivateKey.generate(), Ed25519PrivateKey.generate()
    private, public = tmp_path / "TEST-private.pem", tmp_path / "TEST-public.pem"
    fp = generate_keypair(private, public)["fingerprint"]
    signer = load_pem_private_key(private.read_bytes(), None)
    registry_path = tmp_path / "registry.json"
    write_new_registry(registry_path, "isolated-TEST-signers")
    register_active_key(registry_path, public, key_id="TEST-key", custody_mode="offline_encrypted",
                        recovery_control="encrypted_backup_verified", activated_at=T0)
    anchors = TrustAnchors(root.public_key(), observer.public_key(), "isolated-TEST-signers", 1)
    payload = {"format": POLICY_FORMAT, "revision": 1, "issued_at": T0, "valid_until": T5,
               "registry": load_registry(registry_path),
               "authorities": [{"public_key": public_key_b64(signer.public_key()), "fingerprint": fp,
                                 "expires_at": T4, "purpose": "test-evidence"}]}
    def auth(value=payload, now=T1, anchors_override=None):
        return authenticate_policy(sign_policy(value, root), anchors_override or anchors, now=now)
    return {"root": root, "observer": observer, "signer": signer, "fp": fp, "registry_path": registry_path,
            "payload": payload, "anchors": anchors, "auth": auth, "tmp": tmp_path}


def test_real_ed25519_positive_and_content_binding(fixture):
    policy = fixture["auth"]()
    signed = sign_object(CONTENT, fixture["signer"], policy, purpose="test-evidence", now=T1)
    assert verify_object(CONTENT, signed, policy, purpose="test-evidence", now=T2)["valid"]
    assert not verify_object(CONTENT + b" ", signed, policy, purpose="test-evidence", now=T2)["valid"]
    forged = deepcopy(signed)
    forged["payload"]["content_sha256"] = "0" * 64
    assert not verify_object(CONTENT, forged, policy, purpose="test-evidence", now=T2)["valid"]
    assert not verify_object(CONTENT, signed, policy, purpose="promotion", now=T2)["valid"]


def test_policy_digest_is_not_authority(fixture):
    forged = sign_policy(fixture["payload"], Ed25519PrivateKey.generate())
    with pytest.raises(SigningPolicyError, match="fingerprint"):
        authenticate_policy(forged, fixture["anchors"], now=T1)
    original = sign_policy(fixture["payload"], fixture["root"])
    original["payload"]["valid_until"] = "2030-01-01T00:00:00Z"
    with pytest.raises(SigningPolicyError, match="verification"):
        authenticate_policy(original, fixture["anchors"], now=T1)


def test_expired_not_yet_valid_and_rollback_policy(fixture):
    for now in ("2026-09-30T00:00:00Z", T5):
        with pytest.raises(SigningPolicyError, match="not yet valid or expired"):
            fixture["auth"](now=now)
    anchors = TrustAnchors(fixture["root"].public_key(), fixture["observer"].public_key(), "isolated-TEST-signers", 2)
    with pytest.raises(SigningPolicyError, match="rollback"):
        fixture["auth"](anchors_override=anchors)


def test_expired_producer_cannot_sign_or_current_verify(fixture):
    policy = fixture["auth"]()
    signed = sign_object(CONTENT, fixture["signer"], policy, purpose="test-evidence", now=T1)
    with pytest.raises(SigningPolicyError, match="expired signing"):
        sign_object(CONTENT, fixture["signer"], policy, purpose="test-evidence", now=T4)
    assert not verify_object(CONTENT, signed, policy, purpose="test-evidence", now=T4)["valid"]


def _rotated(fixture):
    from cryptography.hazmat.primitives.serialization import load_pem_private_key
    private, public = fixture["tmp"] / "TEST-next-private.pem", fixture["tmp"] / "TEST-next-public.pem"
    fp = generate_keypair(private, public)["fingerprint"]
    key = load_pem_private_key(private.read_bytes(), None)
    rotate_key(fixture["registry_path"], old_fingerprint=fixture["fp"], new_public_key_path=public,
               new_key_id="TEST-next", custody_mode="offline_encrypted", recovery_control="encrypted_backup_verified",
               effective_at=T2)
    payload = deepcopy(fixture["payload"])
    payload["revision"] = 2
    payload["registry"] = load_registry(fixture["registry_path"])
    payload["authorities"].append({"public_key": public_key_b64(key.public_key()), "fingerprint": fp,
                                    "expires_at": T5, "purpose": "test-evidence"})
    return fixture["auth"](payload, now=T3)


def test_rotation_history_requires_independent_exact_observation(fixture):
    policy = fixture["auth"]()
    signed = sign_object(CONTENT, fixture["signer"], policy, purpose="test-evidence", now=T1)
    observation = observe_object(signed, fixture["observer"], observed_at=T1)
    rotated = _rotated(fixture)
    assert not verify_object(CONTENT, signed, rotated, purpose="test-evidence", now=T3)["valid"]
    history = verify_object(CONTENT, signed, rotated, purpose="test-evidence", now=T3, historical_observation=observation)
    assert history["valid"] and history["mode"] == "historical_observed_existence"
    assert history["pcs_authority"] is False
    late = observe_object(signed, fixture["observer"], observed_at=T2)
    assert not verify_object(CONTENT, signed, rotated, purpose="test-evidence", now=T3, historical_observation=late)["valid"]
    different = sign_object(CONTENT + b"x", fixture["signer"], policy, purpose="test-evidence", now=T1)
    wrong = observe_object(different, fixture["observer"], observed_at=T1)
    assert not verify_object(CONTENT, signed, rotated, purpose="test-evidence", now=T3, historical_observation=wrong)["valid"]


@pytest.mark.parametrize("scope,valid", [("all_signatures", False), ("from_time", True)])
def test_compromise_or_administrative_revocation(fixture, scope, valid):
    policy = fixture["auth"]()
    signed = sign_object(CONTENT, fixture["signer"], policy, purpose="test-evidence", now=T1)
    observation = observe_object(signed, fixture["observer"], observed_at=T1)
    revoke_key(fixture["registry_path"], fingerprint=fixture["fp"], reason="TEST incident", scope=scope, effective_at=T2)
    payload = deepcopy(fixture["payload"])
    payload.update(revision=2, registry=load_registry(fixture["registry_path"]))
    revoked = fixture["auth"](payload, now=T3)
    result = verify_object(CONTENT, signed, revoked, purpose="test-evidence", now=T3, historical_observation=observation)
    assert result["valid"] is valid
    with pytest.raises(SigningPolicyError):
        sign_object(CONTENT, fixture["signer"], revoked, purpose="test-evidence", now=T3)


def test_fake_observer_or_caller_timestamp_cannot_save_history(fixture):
    policy = fixture["auth"]()
    signed = sign_object(CONTENT, fixture["signer"], policy, purpose="test-evidence", now=T1)
    rotated = _rotated(fixture)
    forged = observe_object(signed, Ed25519PrivateKey.generate(), observed_at=T1)
    assert not verify_object(CONTENT, signed, rotated, purpose="test-evidence", now=T3, historical_observation=forged)["valid"]
    witness = observe_object(signed, fixture["observer"], observed_at=T1)
    witness["payload"]["observed_at"] = T0
    assert not verify_object(CONTENT, signed, rotated, purpose="test-evidence", now=T3, historical_observation=witness)["valid"]


def test_key_substitution_separation_and_mutation(fixture):
    payload = deepcopy(fixture["payload"])
    payload["authorities"][0]["public_key"] = public_key_b64(Ed25519PrivateKey.generate().public_key())
    with pytest.raises(SigningPolicyError, match="substitution"):
        fixture["auth"](payload)
    with pytest.raises(SigningPolicyError, match="distinct"):
        TrustAnchors(fixture["root"].public_key(), fixture["root"].public_key(), "test", 1)
    policy = fixture["auth"]()
    # A directly constructed AuthenticatedPolicy cannot bypass verification.
    malicious = AuthenticatedPolicy(b'{"payload":{}}', policy.anchors)
    signed = sign_object(CONTENT, fixture["signer"], policy, purpose="test-evidence", now=T1)
    assert not verify_object(CONTENT, signed, malicious, purpose="test-evidence", now=T2)["valid"]
    fixture["payload"]["authorities"][0]["expires_at"] = T0
    assert verify_object(CONTENT, signed, policy, purpose="test-evidence", now=T2)["valid"]


@pytest.mark.parametrize("revision", [True, 0, -1, 2**31, 1.0])
def test_invalid_revision_fails_closed(fixture, revision):
    payload = deepcopy(fixture["payload"])
    payload["revision"] = revision
    with pytest.raises(SigningPolicyError, match="revision"):
        fixture["auth"](payload)


def test_future_and_naive_timestamps_fail_closed(fixture):
    policy = fixture["auth"]()
    signed = sign_object(CONTENT, fixture["signer"], policy, purpose="test-evidence", now=T2)
    assert not verify_object(CONTENT, signed, policy, purpose="test-evidence", now=T1)["valid"]
    with pytest.raises(SigningPolicyError, match="timezone"):
        fixture["auth"](now="2026-10-02T00:00:00")


def test_unknown_fields_not_ignored(fixture):
    payload = deepcopy(fixture["payload"])
    payload["approved"] = True
    with pytest.raises(SigningPolicyError, match="fields"):
        fixture["auth"](payload)


@pytest.mark.parametrize("authority", ["root", "observer"])
def test_producer_cannot_be_root_or_observation_authority(fixture, authority):
    from pcs.key_lifecycle import registry_semantic_hash
    from pcs.signing import public_key_fingerprint
    from cryptography.hazmat.primitives import serialization
    import hashlib
    payload = deepcopy(fixture["payload"])
    key = fixture[authority].public_key()
    fp = public_key_fingerprint(key)
    spki = key.public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)
    payload["registry"]["keys"][0].update(public_key_fingerprint=fp, public_key_spki_sha256=hashlib.sha256(spki).hexdigest())
    payload["registry"]["semantic_hash"] = registry_semantic_hash(payload["registry"])
    payload["authorities"][0].update(public_key=public_key_b64(key), fingerprint=fp)
    with pytest.raises(SigningPolicyError, match="cannot share"):
        fixture["auth"](payload)


def test_authenticated_policy_rechecked_after_ttl(fixture):
    policy = fixture["auth"]()
    signed = sign_object(CONTENT, fixture["signer"], policy, purpose="test-evidence", now=T1)
    witness = observe_object(signed, fixture["observer"], observed_at=T1)
    assert not verify_object(CONTENT, signed, policy, purpose="test-evidence", now=T5,
                             historical_observation=witness)["valid"]
    with pytest.raises(SigningPolicyError, match="expired"):
        sign_object(CONTENT, fixture["signer"], policy, purpose="test-evidence", now=T5)


def test_historical_witness_future_observation_rejected(fixture):
    policy = fixture["auth"]()
    signed = sign_object(CONTENT, fixture["signer"], policy, purpose="test-evidence", now=T1)
    witness = observe_object(signed, fixture["observer"], observed_at=T3)
    assert not verify_object(CONTENT, signed, policy, purpose="test-evidence", now=T2,
                             historical_observation=witness)["valid"]
