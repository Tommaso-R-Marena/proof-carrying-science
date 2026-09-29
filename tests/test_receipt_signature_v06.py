from __future__ import annotations

import base64
import hashlib
import json
import subprocess
import sys
import zipfile
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

from pcs.receipt_signature_v06 import (
    sign_verification_receipt_v06,
    verify_verification_receipt_signature_v06,
)
from pcs.signing import public_key_fingerprint


ROOT = Path(__file__).resolve().parents[1]
GOLDEN = ROOT / "tests" / "v06_golden"
META = json.loads((GOLDEN / "metadata.json").read_text(encoding="utf-8"))
MEMBERS = [
    "certificate.json",
    "certificate_signature.json",
    "package_manifest.json",
    "package_signature.json",
    "artifacts/fixture.bin",
    "normalized/index.json",
    META["normalized_wire_path"],
]


def _reviewer_keys(tmp_path: Path, seed_start: int = 31):
    private = Ed25519PrivateKey.from_private_bytes(
        bytes(range(seed_start, seed_start + 32))
    )
    public = private.public_key()
    private_path = tmp_path / f"reviewer-{seed_start}-private.pem"
    public_path = tmp_path / f"reviewer-{seed_start}-public.pem"
    private_path.write_bytes(
        private.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )
    public_path.write_bytes(
        public.public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )
    return private_path, public_path, public_key_fingerprint(public)


def _producer_public_key(path: Path) -> None:
    key = Ed25519PublicKey.from_public_bytes(
        base64.b64decode(META["public_key_raw_base64"], validate=True)
    )
    path.write_bytes(
        key.public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )


def _golden_zip(path: Path) -> None:
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_STORED) as zf:
        for rel in MEMBERS:
            info = zipfile.ZipInfo(rel, (1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            info.compress_type = zipfile.ZIP_STORED
            zf.writestr(info, (GOLDEN / rel).read_bytes())


def _policy(path: Path) -> bytes:
    value = {
        "policy_version": "pcs-acceptance-policy-v1",
        "require_signature": True,
        "expected_signer_fingerprint": META["public_key_fingerprint"],
        "required_claims": {
            "C1": ["COMPUTATIONALLY_SUPPORTED"],
        },
    }
    raw = json.dumps(value, indent=2, sort_keys=True).encode("utf-8") + b"\n"
    path.write_bytes(raw)
    return raw


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "pcs.cli", *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def test_reviewer_signature_binds_exact_receipt_bytes_and_summary(tmp_path):
    receipt = tmp_path / "receipt.json"
    signature = tmp_path / "receipt.sig.json"
    private_key, public_key, fingerprint = _reviewer_keys(tmp_path)
    receipt_obj = {
        "format": "pcs-end-to-end-verifier-v06-v1",
        "valid": True,
        "accepted": False,
        "bundle_sha256": "a" * 64,
        "certificate_semantic_hash": "b" * 64,
        "certificate_integrity_hash": "c" * 64,
        "normalized_index_semantic_hash": "d" * 64,
        "reviewer_policy": {
            "applied": True,
            "pass": False,
            "policy_sha256": "e" * 64,
            "failures": [{"type": "claim_status"}],
        },
    }
    raw = json.dumps(
        receipt_obj,
        indent=2,
        sort_keys=True,
        ensure_ascii=False,
    ).encode("utf-8") + b"\n"
    receipt.write_bytes(raw)

    record = sign_verification_receipt_v06(
        receipt,
        private_key,
        signature,
    )
    checked = verify_verification_receipt_signature_v06(
        receipt,
        signature,
        public_key,
        expected_reviewer_fingerprint=fingerprint,
    )

    assert checked["valid"], checked["errors"]
    assert checked["receipt_sha256"] == hashlib.sha256(raw).hexdigest()
    assert checked["bundle_sha256"] == "a" * 64
    assert checked["policy_sha256"] == "e" * 64
    assert checked["pcs_valid"] is True
    assert checked["reviewer_accepted"] is False
    assert record["payload"]["receipt_sha256"] == checked["receipt_sha256"]
    assert record["payload"]["accepted"] is False


def test_one_byte_receipt_change_breaks_reviewer_signature(tmp_path):
    receipt = tmp_path / "receipt.json"
    signature = tmp_path / "receipt.sig.json"
    private_key, public_key, _ = _reviewer_keys(tmp_path)
    receipt.write_text(
        json.dumps({"format": "x", "valid": True, "accepted": True}) + "\n",
        encoding="utf-8",
    )
    sign_verification_receipt_v06(receipt, private_key, signature)

    raw = bytearray(receipt.read_bytes())
    raw[-2] = ord(" ")
    receipt.write_bytes(bytes(raw))

    checked = verify_verification_receipt_signature_v06(
        receipt,
        signature,
        public_key,
    )
    assert not checked["valid"]
    assert any(
        "payload does not match exact receipt" in error
        or "signature verification failed" in error
        for error in checked["errors"]
    )


def test_wrong_reviewer_key_and_fingerprint_are_rejected(tmp_path):
    receipt = tmp_path / "receipt.json"
    signature = tmp_path / "receipt.sig.json"
    private_key, _, fingerprint = _reviewer_keys(tmp_path, 31)
    _, wrong_public, wrong_fingerprint = _reviewer_keys(tmp_path, 63)
    receipt.write_text(
        json.dumps({"format": "x", "valid": True, "accepted": True}) + "\n",
        encoding="utf-8",
    )
    sign_verification_receipt_v06(receipt, private_key, signature)

    checked = verify_verification_receipt_signature_v06(
        receipt,
        signature,
        wrong_public,
        expected_reviewer_fingerprint=wrong_fingerprint,
    )
    assert not checked["valid"]
    assert "reviewer public key fingerprint mismatch" in checked["errors"]
    assert any("signature verification failed" in error for error in checked["errors"])

    _, correct_public, _ = _reviewer_keys(tmp_path, 31)
    pin_mismatch = verify_verification_receipt_signature_v06(
        receipt,
        signature,
        correct_public,
        expected_reviewer_fingerprint="0" * 64,
    )
    assert not pin_mismatch["valid"]
    assert "reviewer fingerprint does not match expected reviewer" in pin_mismatch["errors"]
    assert fingerprint != "0" * 64


def test_verify_bundle_can_emit_reviewer_signed_receipt_in_one_command(tmp_path):
    bundle = tmp_path / "golden.zip"
    producer_public = tmp_path / "producer-public.pem"
    policy = tmp_path / "policy.json"
    receipt = tmp_path / "receipt.json"
    receipt_signature = tmp_path / "receipt.sig.json"
    reviewer_private, reviewer_public, reviewer_fingerprint = _reviewer_keys(tmp_path)
    _golden_zip(bundle)
    _producer_public_key(producer_public)
    policy_raw = _policy(policy)

    proc = _run(
        "verify-v06-bundle",
        str(bundle),
        "--public-key",
        str(producer_public),
        "--expected-signer-fingerprint",
        META["public_key_fingerprint"],
        "--policy",
        str(policy),
        "--receipt",
        str(receipt),
        "--reviewer-private-key",
        str(reviewer_private),
        "--receipt-signature",
        str(receipt_signature),
    )

    assert proc.returncode == 0, proc.stdout + proc.stderr
    output = json.loads(proc.stdout)
    assert output["valid"] is True
    assert output["accepted"] is True
    assert output["receipt_written"] == str(receipt.resolve())
    assert output["receipt_signature_written"] == str(receipt_signature.resolve())

    checked = verify_verification_receipt_signature_v06(
        receipt,
        receipt_signature,
        reviewer_public,
        expected_reviewer_fingerprint=reviewer_fingerprint,
    )
    assert checked["valid"], checked["errors"]
    assert checked["bundle_sha256"] == hashlib.sha256(bundle.read_bytes()).hexdigest()
    assert checked["policy_sha256"] == hashlib.sha256(policy_raw).hexdigest()


def test_verify_receipt_v06_cli_is_independent_audit_step(tmp_path):
    receipt = tmp_path / "receipt.json"
    signature = tmp_path / "receipt.sig.json"
    private_key, public_key, fingerprint = _reviewer_keys(tmp_path)
    receipt.write_text(
        json.dumps(
            {
                "format": "pcs-end-to-end-verifier-v06-v1",
                "valid": True,
                "accepted": True,
                "bundle_sha256": "a" * 64,
                "reviewer_policy": {
                    "applied": False,
                    "pass": None,
                    "policy_sha256": None,
                    "failures": [],
                },
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    sign_verification_receipt_v06(receipt, private_key, signature)

    proc = _run(
        "verify-receipt-v06",
        str(receipt),
        "--signature",
        str(signature),
        "--reviewer-public-key",
        str(public_key),
        "--expected-reviewer-fingerprint",
        fingerprint,
    )

    assert proc.returncode == 0, proc.stdout + proc.stderr
    result = json.loads(proc.stdout)
    assert result["valid"] is True
    assert result["reviewer_accepted"] is True
    assert result["bundle_sha256"] == "a" * 64
