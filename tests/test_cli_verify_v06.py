from __future__ import annotations

import base64
import json
import shutil
import subprocess
import sys
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey


ROOT = Path(__file__).resolve().parents[1]
GOLDEN = ROOT / "tests" / "v06_golden"
META = json.loads((GOLDEN / "metadata.json").read_text(encoding="utf-8"))


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


def _copy_package(tmp_path: Path) -> Path:
    package = tmp_path / "package"
    package.mkdir()

    for rel in [
        "certificate.json",
        "certificate_signature.json",
        "package_manifest.json",
        "package_signature.json",
        "artifacts/fixture.bin",
        "normalized/index.json",
        META["normalized_wire_path"],
    ]:
        src = GOLDEN / rel
        dst = package / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)
    return package


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "pcs.cli", *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def test_verify_v06_cli_accepts_golden_package_and_writes_receipt(tmp_path):
    package = _copy_package(tmp_path)
    public_key = tmp_path / "public.pem"
    receipt = tmp_path / "receipt.json"
    _write_public_key(public_key)

    proc = _run(
        "verify-v06",
        str(package),
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

    assert output["valid"] is True
    assert output["failed_stage"] is None
    assert all(output["stages"].values())
    assert output["receipt_written"] == str(receipt.resolve())
    assert "receipt_written" not in saved
    assert saved["valid"] is True
    assert saved["certificate_semantic_hash"] == META["certificate_semantic_hash"]
    assert saved["normalized_index_semantic_hash"] == META[
        "normalized_index_semantic_hash"
    ]


def test_verify_v06_cli_returns_one_for_verification_rejection(tmp_path):
    package = _copy_package(tmp_path)
    public_key = tmp_path / "public.pem"
    _write_public_key(public_key)

    (package / "artifacts/fixture.bin").write_bytes(b"tampered artifact\n")

    proc = _run(
        "verify-v06",
        str(package),
        "--public-key",
        str(public_key),
    )

    assert proc.returncode == 1, proc.stdout + proc.stderr
    result = json.loads(proc.stdout)
    assert result["valid"] is False
    assert result["failed_stage"] == "package_binding"
    assert result["stages"]["canonical_inputs"] is True
    assert result["stages"]["certificate_signature"] is True
    assert result["stages"]["package_binding"] is False


def test_verify_v06_cli_returns_two_for_operational_error(tmp_path):
    package = _copy_package(tmp_path)
    public_key = tmp_path / "public.pem"
    _write_public_key(public_key)
    (package / "package_signature.json").unlink()

    proc = _run(
        "verify-v06",
        str(package),
        "--public-key",
        str(public_key),
    )

    assert proc.returncode == 2
    assert proc.stdout == ""
    assert "missing required v0.6 control file" in proc.stderr


def test_verify_v06_cli_refuses_receipt_overwrite_without_force(tmp_path):
    package = _copy_package(tmp_path)
    public_key = tmp_path / "public.pem"
    receipt = tmp_path / "receipt.json"
    _write_public_key(public_key)
    receipt.write_text("sentinel\n", encoding="utf-8")

    proc = _run(
        "verify-v06",
        str(package),
        "--public-key",
        str(public_key),
        "--receipt",
        str(receipt),
    )

    assert proc.returncode == 2
    assert receipt.read_text(encoding="utf-8") == "sentinel\n"
    assert "refusing to overwrite existing verification receipt" in proc.stderr


def test_verify_v06_cli_force_receipt_is_explicit(tmp_path):
    package = _copy_package(tmp_path)
    public_key = tmp_path / "public.pem"
    receipt = tmp_path / "receipt.json"
    _write_public_key(public_key)
    receipt.write_text("old\n", encoding="utf-8")

    proc = _run(
        "verify-v06",
        str(package),
        "--public-key",
        str(public_key),
        "--receipt",
        str(receipt),
        "--force-receipt",
    )

    assert proc.returncode == 0, proc.stdout + proc.stderr
    saved = json.loads(receipt.read_text(encoding="utf-8"))
    assert saved["valid"] is True
