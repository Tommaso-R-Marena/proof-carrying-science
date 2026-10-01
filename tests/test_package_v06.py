from __future__ import annotations

from copy import deepcopy
import json
import os
from pathlib import Path

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from pcs.certificate_v06 import finalize_certificate_hashes_v06
from pcs.crypto_domains_v06 import CERTIFICATE_SIGNATURE_DOMAIN
from pcs.package_v06 import (
    build_package_manifest_v06,
    build_package_manifest_from_directory_v06,
    sign_package_manifest_v06,
    verify_package_manifest_v06,
    verify_package_directory_v06,
    verify_package_signature_v06,
    validate_package_namespace_v06,
    V06PackageError,
)
from pcs.signing_v06 import sign_jcs_payload


ROOT = Path(__file__).resolve().parents[1]


def certificate(subject: str = "package fixture") -> dict:
    return finalize_certificate_hashes_v06(
        {
            "spec_version": "pcs-0.6",
            "checker_version": "pcs-python-kernel/0.6.0-dev",
            "canonical_json_profile": "pcs-jcs-rfc8785-v1",
            "semantic_hash_format": "pcs-certificate-semantic-sha256-v2",
            "integrity_hash_format": "pcs-certificate-integrity-sha256-v2",
            "generated_at": "2026-09-29T00:00:00+00:00",
            "subject": subject,
            "mission_scope": "package binding fixture",
            "assumptions": [],
            "claims": [],
            "artifacts": [],
            "evidence": [],
            "workflow": {"nodes": []},
            "workflow_summary": {"node_count": 0, "topological_order": []},
            "semantic_hash": "",
            "integrity_hash": "",
        }
    )


FILES = {
    "certificate.json": {"sha256": "a" * 64, "size": 123},
    "artifacts/abc/payload": {"sha256": "b" * 64, "size": 456},
}


def test_v06_package_manifest_round_trip():
    cert = certificate()
    manifest = build_package_manifest_v06(cert, FILES)
    result = verify_package_manifest_v06(manifest, cert)
    assert result["valid"], result["errors"]


def test_v06_package_manifest_rejects_certificate_substitution():
    cert = certificate()
    other = certificate("different certificate")
    manifest = build_package_manifest_v06(cert, FILES)

    result = verify_package_manifest_v06(manifest, other)
    assert not result["valid"]


def test_v06_package_signature_round_trip():
    key = Ed25519PrivateKey.generate()
    manifest = build_package_manifest_v06(certificate(), FILES)
    record = sign_package_manifest_v06(manifest, key)

    result = verify_package_signature_v06(
        manifest,
        record,
        key.public_key(),
    )
    assert result["valid"], result["errors"]


def test_v06_package_signature_detects_manifest_tamper():
    key = Ed25519PrivateKey.generate()
    manifest = build_package_manifest_v06(certificate(), FILES)
    record = sign_package_manifest_v06(manifest, key)

    tampered = deepcopy(manifest)
    tampered["files"]["certificate.json"]["size"] += 1
    result = verify_package_signature_v06(
        tampered,
        record,
        key.public_key(),
    )
    assert not result["valid"]
    assert "signature payload does not match v0.6 package manifest" in result["errors"]


def test_certificate_domain_signature_cannot_be_used_as_package_signature():
    key = Ed25519PrivateKey.generate()
    manifest = build_package_manifest_v06(certificate(), FILES)
    wrong_domain_record = sign_jcs_payload(
        CERTIFICATE_SIGNATURE_DOMAIN,
        manifest,
        key,
    )

    result = verify_package_signature_v06(
        manifest,
        wrong_domain_record,
        key.public_key(),
    )
    assert not result["valid"]


def test_public_and_packaged_v06_package_schemas_match():
    assert (ROOT / "schemas/package_manifest_v06.schema.json").read_bytes() == (
        ROOT / "pcs/schemas/package_manifest_v06.schema.json"
    ).read_bytes()



@pytest.mark.parametrize(
    "name",
    [
        "../escape",
        "/absolute",
        "./dot",
        "a//b",
        "a\\b",
        "C:/drive",
        "CON.txt",
        "aux",
        "trail.",
        "trail ",
        "control\x1fchar",
        "delete\x7fchar",
        "e\u0301.txt",
        ".",
        "package_manifest.json",
        "package_signature.json",
        "CON .txt",
        "a" * 256,
        "/".join(["a" * 200] * 6),
    ],
)
def test_v06_package_namespace_rejects_nonportable_member_names(name: str):
    with pytest.raises(V06PackageError):
        validate_package_namespace_v06({name: {"sha256": "a" * 64, "size": 1}})


def test_v06_package_namespace_rejects_casefold_collision():
    with pytest.raises(V06PackageError, match="cross-platform"):
        validate_package_namespace_v06(
            {
                "Artifact.txt": {"sha256": "a" * 64, "size": 1},
                "artifact.txt": {"sha256": "b" * 64, "size": 1},
            }
        )


def test_v06_package_namespace_rejects_file_parent_collision():
    with pytest.raises(V06PackageError, match="is parent"):
        validate_package_namespace_v06(
            {
                "artifacts": {"sha256": "a" * 64, "size": 1},
                "artifacts/x/payload": {"sha256": "b" * 64, "size": 2},
            }
        )


def test_v06_package_builder_and_signer_refuse_unsafe_namespace():
    key = Ed25519PrivateKey.generate()
    cert = certificate()
    with pytest.raises(V06PackageError):
        build_package_manifest_v06(
            cert,
            {"../escape": {"sha256": "a" * 64, "size": 1}},
        )

    safe = build_package_manifest_v06(cert, FILES)
    unsafe = deepcopy(safe)
    unsafe["files"]["../escape"] = {"sha256": "c" * 64, "size": 1}
    with pytest.raises(V06PackageError):
        sign_package_manifest_v06(unsafe, key)



def _stage_v06_package(root: Path) -> dict:
    cert = certificate()
    (root / "certificate.json").write_text(
        json.dumps(cert, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    artifact = root / "artifacts" / "abc" / "payload"
    artifact.parent.mkdir(parents=True)
    artifact.write_bytes(b"fixture bytes\n")
    return cert


def test_v06_directory_manifest_round_trip(tmp_path: Path):
    _stage_v06_package(tmp_path)
    manifest = build_package_manifest_from_directory_v06(tmp_path)
    assert set(manifest["files"]) == {"certificate.json", "artifacts/abc/payload"}

    result = verify_package_directory_v06(tmp_path, manifest)
    assert result["valid"], result["errors"]


def test_v06_directory_verifier_detects_artifact_tamper(tmp_path: Path):
    _stage_v06_package(tmp_path)
    manifest = build_package_manifest_from_directory_v06(tmp_path)
    (tmp_path / "artifacts" / "abc" / "payload").write_bytes(b"tampered bytes\n")

    result = verify_package_directory_v06(tmp_path, manifest)
    assert not result["valid"]
    assert any("package hash mismatch" in error for error in result["errors"])


def test_v06_directory_verifier_detects_missing_and_unexpected_files(tmp_path: Path):
    _stage_v06_package(tmp_path)
    manifest = build_package_manifest_from_directory_v06(tmp_path)

    (tmp_path / "artifacts" / "abc" / "payload").unlink()
    (tmp_path / "unexpected.txt").write_text("unexpected", encoding="utf-8")
    result = verify_package_directory_v06(tmp_path, manifest)

    assert not result["valid"]
    assert any("files missing" in error for error in result["errors"])
    assert any("unexpected v0.6 package files" in error for error in result["errors"])


def test_v06_directory_verifier_detects_certificate_content_tamper(tmp_path: Path):
    _stage_v06_package(tmp_path)
    manifest = build_package_manifest_from_directory_v06(tmp_path)

    cert_path = tmp_path / "certificate.json"
    raw = json.loads(cert_path.read_text(encoding="utf-8"))
    raw["subject"] = "tampered without rehash"
    cert_path.write_text(json.dumps(raw, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    result = verify_package_directory_v06(tmp_path, manifest)
    assert not result["valid"]
    assert any(
        "certificate" in error.lower() or "hash mismatch" in error.lower()
        for error in result["errors"]
    )


def test_v06_directory_builder_excludes_manifest_and_signature_files(tmp_path: Path):
    _stage_v06_package(tmp_path)
    (tmp_path / "package_manifest.json").write_text("{}", encoding="utf-8")
    (tmp_path / "package_signature.json").write_text("{}", encoding="utf-8")

    manifest = build_package_manifest_from_directory_v06(tmp_path)
    assert "package_manifest.json" not in manifest["files"]
    assert "package_signature.json" not in manifest["files"]


def test_v06_directory_builder_refuses_private_key_material(tmp_path: Path):
    _stage_v06_package(tmp_path)
    (tmp_path / "oops.pem").write_bytes(
        b"prefix\n-----BEGIN PRIVATE KEY-----\nnot-a-real-key\n"
    )
    with pytest.raises(V06PackageError, match="private-key"):
        build_package_manifest_from_directory_v06(tmp_path)


def test_v06_directory_builder_refuses_nonportable_case_collision(tmp_path: Path):
    _stage_v06_package(tmp_path)
    (tmp_path / "Artifact.txt").write_text("one", encoding="utf-8")
    try:
        (tmp_path / "artifact.txt").write_text("two", encoding="utf-8")
    except OSError:
        pytest.skip("filesystem does not permit case-distinct fixture names")

    with pytest.raises(V06PackageError, match="cross-platform"):
        build_package_manifest_from_directory_v06(tmp_path)


def test_v06_directory_builder_refuses_symlink(tmp_path: Path):
    _stage_v06_package(tmp_path)
    target = tmp_path / "target.txt"
    target.write_text("target", encoding="utf-8")
    link = tmp_path / "linked.txt"
    try:
        os.symlink(target, link)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks are unavailable in this environment")

    with pytest.raises(V06PackageError, match="symlinks"):
        build_package_manifest_from_directory_v06(tmp_path)


def test_v06_directory_builder_enforces_single_file_limit(tmp_path: Path, monkeypatch):
    import pcs.package_v06 as package_v06

    _stage_v06_package(tmp_path)
    monkeypatch.setattr(package_v06, "MAX_PACKAGE_SINGLE_FILE_V06", 4)
    with pytest.raises(V06PackageError, match="too large"):
        build_package_manifest_from_directory_v06(tmp_path)



def test_v06_package_manifest_requires_certificate_member():
    cert = certificate()
    with pytest.raises(V06PackageError, match="must bind certificate.json"):
        build_package_manifest_v06(
            cert,
            {"artifact.txt": {"sha256": "a" * 64, "size": 1}},
        )


def test_v06_signer_rejects_manifest_that_self_binds_signature_file():
    key = Ed25519PrivateKey.generate()
    manifest = build_package_manifest_v06(certificate(), FILES)
    bad = deepcopy(manifest)
    bad["files"]["package_signature.json"] = {"sha256": "c" * 64, "size": 10}
    with pytest.raises(V06PackageError, match="self-referential"):
        sign_package_manifest_v06(bad, key)
