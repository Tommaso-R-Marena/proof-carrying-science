from __future__ import annotations

import base64
import hashlib
import json
import shutil
import stat
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from pcs.verifier_zip_v06 import (
    V06BundleVerificationError,
    load_package_zip_v06,
    verify_package_zip_end_to_end_v06,
)


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


def _write_public_key(path: Path) -> None:
    key = Ed25519PublicKey.from_public_bytes(
        base64.b64decode(META["public_key_raw_base64"], validate=True)
    )
    path.write_bytes(
        key.public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )


def _golden_zip(path: Path, *, compression: int = zipfile.ZIP_STORED) -> None:
    with zipfile.ZipFile(path, "w", compression=compression) as zf:
        for rel in MEMBERS:
            info = zipfile.ZipInfo(rel, (1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            info.compress_type = compression
            zf.writestr(info, (GOLDEN / rel).read_bytes(), compress_type=compression)


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "pcs.cli", *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def test_v06_zip_verifier_accepts_golden_without_extraction(tmp_path):
    bundle = tmp_path / "golden.zip"
    public_key = tmp_path / "public.pem"
    _golden_zip(bundle)
    _write_public_key(public_key)

    result = verify_package_zip_end_to_end_v06(
        bundle,
        public_key,
        expected_fingerprint=META["public_key_fingerprint"],
    )

    assert result["valid"], result["errors"]
    assert result["archive_format"] == "zip"
    assert result["bundle_sha256"] == hashlib.sha256(bundle.read_bytes()).hexdigest()
    assert result["claims"][0]["claim_id"] == "C1"


def test_v06_zip_cli_accepts_and_receipt_binds_archive_bytes(tmp_path):
    bundle = tmp_path / "golden.zip"
    public_key = tmp_path / "public.pem"
    receipt = tmp_path / "receipt.json"
    _golden_zip(bundle)
    _write_public_key(public_key)

    proc = _run(
        "verify-v06-bundle",
        str(bundle),
        "--public-key",
        str(public_key),
        "--expected-signer-fingerprint",
        META["public_key_fingerprint"],
        "--receipt",
        str(receipt),
    )

    assert proc.returncode == 0, proc.stdout + proc.stderr
    output = json.loads(proc.stdout)
    saved = json.loads(receipt.read_text(encoding="utf-8"))
    expected = hashlib.sha256(bundle.read_bytes()).hexdigest()
    assert output["valid"] is True
    assert output["bundle_sha256"] == expected
    assert saved["bundle_sha256"] == expected
    assert saved["archive_format"] == "zip"


def test_v06_zip_tampered_signed_member_is_verification_rejection(tmp_path):
    bundle = tmp_path / "tampered.zip"
    public_key = tmp_path / "public.pem"
    _write_public_key(public_key)

    with zipfile.ZipFile(bundle, "w", compression=zipfile.ZIP_STORED) as zf:
        for rel in MEMBERS:
            raw = (
                b"tampered artifact\n"
                if rel == "artifacts/fixture.bin"
                else (GOLDEN / rel).read_bytes()
            )
            zf.writestr(rel, raw)

    proc = _run(
        "verify-v06-bundle",
        str(bundle),
        "--public-key",
        str(public_key),
    )

    assert proc.returncode == 1, proc.stdout + proc.stderr
    result = json.loads(proc.stdout)
    assert result["valid"] is False
    assert result["failed_stage"] == "package_binding"


def test_v06_zip_rejects_path_traversal_before_verification(tmp_path):
    bundle = tmp_path / "traversal.zip"
    _golden_zip(bundle)
    with zipfile.ZipFile(bundle, "a") as zf:
        zf.writestr("../escape.txt", b"escape")

    with pytest.raises(V06BundleVerificationError, match="unsafe|canonical"):
        load_package_zip_v06(bundle)


def test_v06_zip_rejects_duplicate_member(tmp_path):
    bundle = tmp_path / "duplicate.zip"
    _golden_zip(bundle)
    with zipfile.ZipFile(bundle, "a") as zf:
        zf.writestr("certificate.json", (GOLDEN / "certificate.json").read_bytes())

    with pytest.raises(V06BundleVerificationError, match="duplicate"):
        load_package_zip_v06(bundle)


def test_v06_zip_rejects_symlink_member(tmp_path):
    bundle = tmp_path / "symlink.zip"
    _golden_zip(bundle)
    with zipfile.ZipFile(bundle, "a") as zf:
        info = zipfile.ZipInfo("linked.txt")
        info.create_system = 3
        info.external_attr = (stat.S_IFLNK | 0o777) << 16
        zf.writestr(info, b"certificate.json")

    with pytest.raises(V06BundleVerificationError, match="symlink"):
        load_package_zip_v06(bundle)


def test_v06_zip_rejects_cross_platform_case_collision(tmp_path):
    bundle = tmp_path / "collision.zip"
    _golden_zip(bundle)
    with zipfile.ZipFile(bundle, "a") as zf:
        zf.writestr("Artifact.txt", b"one")
        zf.writestr("artifact.txt", b"two")

    with pytest.raises(V06BundleVerificationError, match="cross-platform"):
        load_package_zip_v06(bundle)


def test_v06_zip_rejects_encrypted_flag(tmp_path):
    bundle = tmp_path / "encrypted-flag.zip"
    _golden_zip(bundle)
    # Python's writer cannot create encrypted entries, so patch a member's flag in
    # memory and exercise the namespace validator through the real archive metadata
    # is not portable. Keep the contract assertion at the source-level helper by
    # mutating ZipInfo returned from the archive.
    with zipfile.ZipFile(bundle, "r") as zf:
        infos = zf.infolist()
        infos[0].flag_bits |= 0x1
        from pcs.verifier_zip_v06 import _validate_archive_namespace_v06
        with pytest.raises(V06BundleVerificationError, match="encrypted"):
            _validate_archive_namespace_v06(infos)


def test_v06_zip_streaming_limit_is_enforced(tmp_path, monkeypatch):
    import pcs.verifier_zip_v06 as zip_v06

    bundle = tmp_path / "limit.zip"
    _golden_zip(bundle)
    monkeypatch.setattr(zip_v06, "MAX_PACKAGE_SINGLE_FILE_V06", 4)

    with pytest.raises(V06BundleVerificationError, match="byte limit"):
        load_package_zip_v06(bundle)


def test_v06_zip_cli_returns_two_for_unsafe_archive(tmp_path):
    bundle = tmp_path / "unsafe.zip"
    public_key = tmp_path / "public.pem"
    _write_public_key(public_key)
    _golden_zip(bundle)
    with zipfile.ZipFile(bundle, "a") as zf:
        zf.writestr("../escape.txt", b"escape")

    proc = _run(
        "verify-v06-bundle",
        str(bundle),
        "--public-key",
        str(public_key),
    )

    assert proc.returncode == 2
    assert proc.stdout == ""
    assert "ZIP member" in proc.stderr
