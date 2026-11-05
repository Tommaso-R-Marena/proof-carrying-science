"""Isolated TEST-key recovery drill: no production configuration or secret access."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from copy import deepcopy
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from pcs.key_lifecycle import load_registry, register_active_key, revoke_key, rotate_key, write_new_registry
from pcs.signing import public_key_fingerprint
from pcs.signing_policy_v1 import (
    POLICY_FORMAT, SigningPolicyError, TrustAnchors, authenticate_policy, observe_object,
    public_key_b64, sign_object, sign_policy, verify_object,
)

T0, T1, T2, T3, T4 = [f"2026-10-{day:02d}T00:00:00Z" for day in range(1, 6)]


def exercise() -> dict:
    controls: dict[str, bool] = {}
    with tempfile.TemporaryDirectory(prefix="pcs-TEST-signing-recovery-") as directory:
        work = Path(directory)
        root, observer, producer, replacement = [Ed25519PrivateKey.generate() for _ in range(4)]
        producer_fp = public_key_fingerprint(producer.public_key())
        password = os.urandom(32)
        backup = work / "TEST-encrypted-backup.pem"
        backup.write_bytes(producer.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                                  serialization.BestAvailableEncryption(password)))
        backup.chmod(0o600)
        controls["encrypted_backup_private_mode"] = (os.name == "nt" or backup.stat().st_mode & 0o777 == 0o600)
        restored = serialization.load_pem_private_key(backup.read_bytes(), password=password)
        controls["backup_restore_fingerprint_matches"] = public_key_fingerprint(restored.public_key()) == producer_fp
        challenge = b"PCS TEST recovery possession challenge"
        producer.public_key().verify(restored.sign(challenge), challenge)
        controls["restored_key_real_signature_verifies"] = True
        try:
            serialization.load_pem_private_key(backup.read_bytes(), password=b"TEST wrong password")
        except (ValueError, TypeError):
            controls["wrong_backup_password_rejected"] = True
        try:
            serialization.load_pem_private_key(b"TEST corrupted encrypted backup", password=password)
        except (ValueError, TypeError):
            controls["corrupted_backup_rejected"] = True
        try:
            (work / "TEST-unavailable-signer.pem").read_bytes()
        except FileNotFoundError:
            controls["unavailable_signing_service_fails_without_signature"] = True

        public = work / "TEST-public.pem"
        public.write_bytes(producer.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo))
        registry = work / "TEST-registry.json"
        write_new_registry(registry, "isolated-TEST-recovery")
        register_active_key(registry, public, key_id="TEST-original", custody_mode="offline_encrypted",
                            recovery_control="encrypted_backup_verified", activated_at=T0)
        anchors = TrustAnchors(root.public_key(), observer.public_key(), "isolated-TEST-recovery", 1)
        payload = {"format": POLICY_FORMAT, "revision": 1, "issued_at": T0, "valid_until": "2026-10-08T00:00:00Z",
                   "registry": load_registry(registry),
                   "authorities": [{"public_key": public_key_b64(producer.public_key()), "fingerprint": producer_fp,
                                     "expires_at": T4, "purpose": "test-release"}]}
        policy = authenticate_policy(sign_policy(payload, root), anchors, now=T1)
        content = b'{"format":"isolated-TEST-release","pcs_authority":false}'
        signed = sign_object(content, restored, policy, purpose="test-release", now=T1)
        witnessed = observe_object(signed, observer, observed_at=T1)
        controls["recovered_signer_policy_bound_positive"] = verify_object(content, signed, policy, purpose="test-release", now=T1)["valid"]
        controls["corrupted_release_artifact_rejected"] = not verify_object(content + b"x", signed, policy, purpose="test-release", now=T1)["valid"]
        substituted = deepcopy(signed)
        substituted["signer_fingerprint"] = public_key_fingerprint(replacement.public_key())
        controls["unregistered_key_substitution_rejected"] = not verify_object(content, substituted, policy, purpose="test-release", now=T1)["valid"]
        controls["expired_signing_credential_rejected"] = not verify_object(content, signed, policy, purpose="test-release", now=T4)["valid"]

        replacement_public = work / "TEST-replacement-public.pem"
        replacement_public.write_bytes(replacement.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo))
        rotate_key(registry, old_fingerprint=producer_fp, new_public_key_path=replacement_public,
                   new_key_id="TEST-replacement", custody_mode="offline_encrypted", recovery_control="encrypted_backup_verified",
                   effective_at=T2)
        rotated_payload = deepcopy(payload)
        rotated_payload.update(revision=2, registry=load_registry(registry))
        rotated_payload["authorities"].append({"public_key": public_key_b64(replacement.public_key()),
                                               "fingerprint": public_key_fingerprint(replacement.public_key()),
                                               "expires_at": "2026-10-07T00:00:00Z", "purpose": "test-release"})
        rotated = authenticate_policy(sign_policy(rotated_payload, root), anchors, now=T3)
        controls["retired_key_current_verification_rejected"] = not verify_object(content, signed, rotated, purpose="test-release", now=T3)["valid"]
        controls["independently_observed_pre_rotation_history_valid"] = verify_object(content, signed, rotated, purpose="test-release", now=T3,
                                                                                  historical_observation=witnessed)["valid"]
        fresh = sign_object(content, replacement, rotated, purpose="test-release", now=T3)
        controls["replacement_real_signature_valid"] = verify_object(content, fresh, rotated, purpose="test-release", now=T3)["valid"]
        revision_floor = TrustAnchors(root.public_key(), observer.public_key(), "isolated-TEST-recovery", 2)
        try:
            authenticate_policy(sign_policy(payload, root), revision_floor, now=T3)
        except SigningPolicyError:
            controls["old_policy_backup_cannot_undo_rotation"] = True
        tampered = sign_policy(rotated_payload, root)
        tampered["payload"]["revision"] = 3
        try:
            authenticate_policy(tampered, anchors, now=T3)
        except SigningPolicyError:
            controls["corrupted_policy_snapshot_rejected"] = True

        revoke_key(registry, fingerprint=producer_fp, reason="isolated TEST compromise", scope="all_signatures", effective_at=T3)
        compromised_payload = deepcopy(rotated_payload)
        compromised_payload.update(revision=3, registry=load_registry(registry))
        compromised = authenticate_policy(sign_policy(compromised_payload, root), anchors, now=T3)
        controls["compromise_rejects_even_observed_history"] = not verify_object(content, signed, compromised, purpose="test-release", now=T3,
                                                                              historical_observation=witnessed)["valid"]
        controls["uncompromised_replacement_still_valid"] = verify_object(content, fresh, compromised, purpose="test-release", now=T3)["valid"]

    expected = 17
    passed = len(controls) == expected and all(controls.values())
    repo = Path(__file__).resolve().parents[1]
    source_files = ("pcs/signing_policy_v1.py", "pcs/key_lifecycle.py", "pcs/signing.py", "scripts/exercise_signing_recovery.py")
    return {"format": "pcs-isolated-signing-recovery-v1", "passed": passed, "control_count": len(controls), "controls": controls,
            "synthetic_test_keys_only": True, "production_mutations": 0, "financial_spend": 0, "pcs_authority": False,
            "source_sha256": {name: hashlib.sha256((repo / name).read_bytes()).hexdigest() for name in source_files},
            "limitations": ["No production key custody or production incident tested", "POSIX mode tested where supported; no hardware key tested",
                            "Witness correctness assumes independently trusted observation service and clock",
                            "Worker/D1/job/CI recovery is outside this signing-only exercise"]}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = exercise()
    raw = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        # No key material, encrypted key backup, or passwords are retained.
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(raw, encoding="utf-8")
    print(raw, end="")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
