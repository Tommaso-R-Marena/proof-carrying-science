from __future__ import annotations

import base64
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

from pcs.bundle_v06 import V06BundleBuildError, create_verified_bundle_v06
from pcs.byte_contract_v06 import parse_certificate_bytes_v06
from pcs.canonical_json import canonicalize_jcs_bytes
from pcs.package_v06 import build_package_manifest_v06, sign_package_manifest_v06
from pcs.verifier_zip_v06 import verify_package_zip_end_to_end_v06


ROOT = Path(__file__).resolve().parents[1]
GOLDEN = ROOT / "tests" / "v06_golden"
META = json.loads((GOLDEN / "metadata.json").read_text(encoding="utf-8"))
TEST_PRIVATE_KEY = Ed25519PrivateKey.from_private_bytes(bytes(range(1, 33)))


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


def test_v06_bundle_builder_is_byte_for_byte_reproducible(tmp_path):
    package = _copy_package(tmp_path)
    public_key = tmp_path / "public.pem"
    first = tmp_path / "first.zip"
    second = tmp_path / "second.zip"
    _write_public_key(public_key)

    a = create_verified_bundle_v06(
        package,
        first,
        public_key,
        expected_fingerprint=META["public_key_fingerprint"],
    )
    b = create_verified_bundle_v06(
        package,
        second,
        public_key,
        expected_fingerprint=META["public_key_fingerprint"],
    )

    assert first.read_bytes() == second.read_bytes()
    assert a["bundle_sha256"] == b["bundle_sha256"]
    assert a["bundle_sha256"] == hashlib.sha256(first.read_bytes()).hexdigest()
    assert a["format"] == "pcs-v06-zip-stored-v1"
    assert a["members"] == sorted(
        [
            "certificate.json",
            "certificate_signature.json",
            "package_manifest.json",
            "package_signature.json",
            "artifacts/fixture.bin",
            "normalized/index.json",
            META["normalized_wire_path"],
        ]
    )


def test_v06_bundle_builder_round_trips_through_archive_verifier(tmp_path):
    package = _copy_package(tmp_path)
    public_key = tmp_path / "public.pem"
    bundle = tmp_path / "delivery.zip"
    _write_public_key(public_key)

    built = create_verified_bundle_v06(
        package,
        bundle,
        public_key,
        expected_fingerprint=META["public_key_fingerprint"],
    )
    checked = verify_package_zip_end_to_end_v06(
        bundle,
        public_key,
        expected_fingerprint=META["public_key_fingerprint"],
    )

    assert checked["valid"], checked["errors"]
    assert checked["bundle_sha256"] == built["bundle_sha256"]
    assert checked["certificate_semantic_hash"] == META["certificate_semantic_hash"]


def test_bundle_v06_cli_creates_verified_reproducible_archive(tmp_path):
    package = _copy_package(tmp_path)
    public_key = tmp_path / "public.pem"
    bundle = tmp_path / "delivery.zip"
    _write_public_key(public_key)

    proc = _run(
        "bundle-v06",
        str(package),
        "-o",
        str(bundle),
        "--public-key",
        str(public_key),
        "--expected-signer-fingerprint",
        META["public_key_fingerprint"],
    )

    assert proc.returncode == 0, proc.stdout + proc.stderr
    result = json.loads(proc.stdout)
    assert result["bundle_sha256"] == hashlib.sha256(bundle.read_bytes()).hexdigest()
    assert result["certificate_semantic_hash"] == META["certificate_semantic_hash"]


def test_v06_bundle_builder_refuses_tampered_package(tmp_path):
    package = _copy_package(tmp_path)
    public_key = tmp_path / "public.pem"
    bundle = tmp_path / "delivery.zip"
    _write_public_key(public_key)
    (package / "artifacts/fixture.bin").write_bytes(b"tampered\n")

    with pytest.raises(V06BundleBuildError, match="does not pass end-to-end verification"):
        create_verified_bundle_v06(package, bundle, public_key)

    assert not bundle.exists()


def test_v06_bundle_builder_refuses_unsigned_extra_file(tmp_path):
    package = _copy_package(tmp_path)
    public_key = tmp_path / "public.pem"
    bundle = tmp_path / "delivery.zip"
    _write_public_key(public_key)
    (package / "unsigned-extra.txt").write_text("extra", encoding="utf-8")

    with pytest.raises(V06BundleBuildError, match="does not pass end-to-end verification"):
        create_verified_bundle_v06(package, bundle, public_key)

    assert not bundle.exists()


def test_v06_bundle_builder_requires_output_outside_package_root(tmp_path):
    package = _copy_package(tmp_path)
    public_key = tmp_path / "public.pem"
    _write_public_key(public_key)

    with pytest.raises(V06BundleBuildError, match="outside the package directory"):
        create_verified_bundle_v06(
            package,
            package / "delivery.zip",
            public_key,
        )


def test_v06_bundle_builder_refuses_overwrite_without_force(tmp_path):
    package = _copy_package(tmp_path)
    public_key = tmp_path / "public.pem"
    bundle = tmp_path / "delivery.zip"
    _write_public_key(public_key)
    bundle.write_bytes(b"sentinel")

    with pytest.raises(V06BundleBuildError, match="refusing to overwrite"):
        create_verified_bundle_v06(package, bundle, public_key)

    assert bundle.read_bytes() == b"sentinel"

    result = create_verified_bundle_v06(
        package,
        bundle,
        public_key,
        overwrite=True,
    )
    assert bundle.read_bytes() != b"sentinel"
    assert result["bundle_sha256"] == hashlib.sha256(bundle.read_bytes()).hexdigest()


def test_v06_bundle_builder_rejects_private_key_material_even_when_resigned(tmp_path):
    package = _copy_package(tmp_path)
    public_key = tmp_path / "public.pem"
    bundle = tmp_path / "delivery.zip"
    _write_public_key(public_key)

    artifact = package / "artifacts/fixture.bin"
    artifact.write_bytes(
        b"prefix\n-----BEGIN PRIVATE KEY-----\nnot-a-real-private-key\n"
    )

    certificate = parse_certificate_bytes_v06(
        (package / "certificate.json").read_bytes()
    )
    signed_files = {}
    for rel in [
        "certificate.json",
        "artifacts/fixture.bin",
        "normalized/index.json",
        META["normalized_wire_path"],
    ]:
        raw = (package / rel).read_bytes()
        signed_files[rel] = {
            "sha256": hashlib.sha256(raw).hexdigest(),
            "size": len(raw),
        }

    manifest = build_package_manifest_v06(certificate, signed_files)
    package_signature = sign_package_manifest_v06(manifest, TEST_PRIVATE_KEY)
    (package / "package_manifest.json").write_bytes(canonicalize_jcs_bytes(manifest))
    (package / "package_signature.json").write_bytes(
        canonicalize_jcs_bytes(package_signature)
    )

    # The package remains cryptographically valid and replay-valid, but the
    # delivery builder refuses to distribute apparent private-key material.
    with pytest.raises(V06BundleBuildError, match="private-key material"):
        create_verified_bundle_v06(
            package,
            bundle,
            public_key,
            expected_fingerprint=META["public_key_fingerprint"],
        )

    assert not bundle.exists()
