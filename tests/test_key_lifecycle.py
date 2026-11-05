from __future__ import annotations

from pathlib import Path

import pytest

from pcs.key_lifecycle import (
    KeyLifecycleError,
    assess_signer,
    load_registry,
    register_active_key,
    revoke_key,
    rotate_key,
    write_new_registry,
)
from pcs.signing import generate_keypair


T0 = "2026-10-01T00:00:00+00:00"
T1 = "2026-10-02T00:00:00+00:00"
T2 = "2026-10-03T00:00:00+00:00"


def _key(tmp_path: Path, stem: str):
    private = tmp_path / f"{stem}-private.pem"
    public = tmp_path / f"{stem}-public.pem"
    generated = generate_keypair(private, public)
    return private, public, generated["fingerprint"]


def test_register_rotate_and_historical_assessment(tmp_path):
    registry = tmp_path / "registry.json"
    write_new_registry(registry, "pcs-pilot-signers")
    _old_private, old_public, old_fp = _key(tmp_path, "old")
    _new_private, new_public, new_fp = _key(tmp_path, "new")

    registered = register_active_key(
        registry,
        old_public,
        key_id="pilot-2026-q4-a",
        custody_mode="offline_encrypted",
        recovery_control="encrypted_backup_verified",
        activated_at=T0,
    )
    assert registered["public_key_fingerprint"] == old_fp

    rotated = rotate_key(
        registry,
        old_fingerprint=old_fp,
        new_public_key_path=new_public,
        new_key_id="pilot-2026-q4-b",
        custody_mode="hardware_backed",
        recovery_control="hardware_recovery_verified",
        effective_at=T1,
    )
    assert rotated["active_fingerprint"] == new_fp

    value = load_registry(registry)
    assert assess_signer(value, old_fp, signed_at=T0)["valid"] is True
    assert assess_signer(value, old_fp, signed_at=T1)["valid"] is False
    assert assess_signer(value, new_fp, signed_at=T1)["valid"] is True


def test_registry_refuses_parallel_active_keys_and_duplicate_ids(tmp_path):
    registry = tmp_path / "registry.json"
    write_new_registry(registry, "pcs-pilot-signers")
    _one_private, one_public, _ = _key(tmp_path, "one")
    _two_private, two_public, _ = _key(tmp_path, "two")

    register_active_key(
        registry,
        one_public,
        key_id="one",
        custody_mode="offline_encrypted",
        recovery_control="encrypted_backup_verified",
        activated_at=T0,
    )
    with pytest.raises(KeyLifecycleError, match="already has an ACTIVE key"):
        register_active_key(
            registry,
            two_public,
            key_id="two",
            custody_mode="offline_encrypted",
            recovery_control="encrypted_backup_verified",
            activated_at=T1,
        )


def test_revoke_all_signatures_is_retrospective(tmp_path):
    registry = tmp_path / "registry.json"
    write_new_registry(registry, "pcs-pilot-signers")
    _private, public, fingerprint = _key(tmp_path, "signer")
    register_active_key(
        registry,
        public,
        key_id="signer-a",
        custody_mode="offline_encrypted",
        recovery_control="encrypted_backup_verified",
        activated_at=T0,
    )
    revoke_key(
        registry,
        fingerprint=fingerprint,
        reason="private key compromise suspected",
        scope="all_signatures",
        effective_at=T2,
    )
    result = assess_signer(
        load_registry(registry),
        fingerprint,
        signed_at=T1,
    )
    assert result["valid"] is False
    assert "invalidates all signatures" in result["errors"][0]


def test_revoke_from_time_preserves_pre_revocation_history(tmp_path):
    registry = tmp_path / "registry.json"
    write_new_registry(registry, "pcs-pilot-signers")
    _private, public, fingerprint = _key(tmp_path, "signer")
    register_active_key(
        registry,
        public,
        key_id="signer-a",
        custody_mode="hardware_backed",
        recovery_control="hardware_recovery_verified",
        activated_at=T0,
    )
    revoke_key(
        registry,
        fingerprint=fingerprint,
        reason="administrative deauthorization",
        scope="from_time",
        effective_at=T2,
    )
    value = load_registry(registry)
    assert assess_signer(value, fingerprint, signed_at=T1)["valid"] is True
    assert assess_signer(value, fingerprint, signed_at=T2)["valid"] is False


def test_registry_detects_tampering(tmp_path):
    registry = tmp_path / "registry.json"
    write_new_registry(registry, "pcs-pilot-signers")
    text = registry.read_text(encoding="utf-8")
    registry.write_text(text.replace("pcs-pilot-signers", "pcs-pilot-signers-x"), encoding="utf-8")
    with pytest.raises(KeyLifecycleError, match="semantic hash mismatch"):
        load_registry(registry)


def test_registry_never_contains_private_key_paths_or_bytes(tmp_path):
    registry = tmp_path / "registry.json"
    write_new_registry(registry, "pcs-pilot-signers")
    private, public, _fingerprint = _key(tmp_path, "signer")
    register_active_key(
        registry,
        public,
        key_id="signer-a",
        custody_mode="offline_encrypted",
        recovery_control="encrypted_backup_verified",
        activated_at=T0,
    )
    raw = registry.read_bytes()
    assert private.name.encode() not in raw
    assert private.read_bytes() not in raw
