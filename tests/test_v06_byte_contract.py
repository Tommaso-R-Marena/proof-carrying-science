from __future__ import annotations

import base64
import hashlib
import json
from copy import deepcopy
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from pcs.byte_contract_v06 import (
    V06ByteContractError,
    parse_certificate_bytes_v06,
    verify_package_file_map_v06,
    verify_signed_certificate_bytes_v06,
)
from pcs.canonical_json import canonicalize_jcs_bytes


ROOT = Path(__file__).resolve().parents[1]
GOLDEN = ROOT / "tests" / "v06_golden"
META = json.loads((GOLDEN / "metadata.json").read_text(encoding="utf-8"))


def _public_key() -> Ed25519PublicKey:
    return Ed25519PublicKey.from_public_bytes(
        base64.b64decode(META["public_key_raw_base64"], validate=True)
    )


def _raw(name: str) -> bytes:
    return (GOLDEN / name).read_bytes()


def _package_files() -> dict[str, bytes]:
    return {
        "certificate.json": _raw("certificate.json"),
        "artifacts/fixture.bin": _raw("artifacts/fixture.bin"),
        "normalized/C1.json": _raw("normalized/C1.json"),
    }


def test_frozen_v06_byte_hashes_are_exact():
    checks = {
        "certificate.json": META["certificate_byte_sha256"],
        "certificate_signature.json": META["certificate_signature_record_byte_sha256"],
        "package_manifest.json": META["package_manifest_byte_sha256"],
        "package_signature.json": META["package_signature_record_byte_sha256"],
        "artifacts/fixture.bin": META["artifact_sha256"],
        "normalized/C1.json": META["normalized_wire_byte_sha256"],
    }
    for rel, expected in checks.items():
        assert hashlib.sha256(_raw(rel)).hexdigest() == expected, rel


def test_frozen_v06_signed_certificate_accepts_from_raw_bytes():
    result = verify_signed_certificate_bytes_v06(
        _raw("certificate.json"),
        _raw("certificate_signature.json"),
        _public_key(),
        expected_fingerprint=META["public_key_fingerprint"],
    )
    assert result["valid"], result["errors"]
    assert result["certificate_semantic_hash"] == META["certificate_semantic_hash"]
    assert result["certificate_integrity_hash"] == META["certificate_integrity_hash"]


def test_frozen_v06_package_file_map_accepts_from_exact_bytes():
    result = verify_package_file_map_v06(
        _raw("package_manifest.json"),
        _raw("certificate.json"),
        _raw("package_signature.json"),
        _package_files(),
        _public_key(),
        expected_fingerprint=META["public_key_fingerprint"],
    )
    assert result["valid"], result["errors"]
    assert result["verified_members"] == [
        "artifacts/fixture.bin",
        "certificate.json",
        "normalized/C1.json",
    ]


def test_certificate_byte_contract_rejects_noncanonical_whitespace():
    certificate = _raw("certificate.json")
    for changed in (b" " + certificate, certificate + b"\n"):
        result = verify_signed_certificate_bytes_v06(
            changed,
            _raw("certificate_signature.json"),
            _public_key(),
        )
        assert not result["valid"]
        assert any("canonical JCS" in error for error in result["errors"])


def test_certificate_byte_contract_rejects_utf8_bom_and_invalid_utf8():
    certificate = _raw("certificate.json")
    for changed in (b"\xef\xbb\xbf" + certificate, b"\xff" + certificate):
        result = verify_signed_certificate_bytes_v06(
            changed,
            _raw("certificate_signature.json"),
            _public_key(),
        )
        assert not result["valid"]


def test_certificate_byte_contract_rejects_duplicate_decoded_key():
    certificate = _raw("certificate.json")
    duplicate = b'{"spec_version":"pcs-0.6",' + certificate[1:]
    result = verify_signed_certificate_bytes_v06(
        duplicate,
        _raw("certificate_signature.json"),
        _public_key(),
    )
    assert not result["valid"]
    assert any("duplicate JSON object key" in error for error in result["errors"])


def test_certificate_byte_contract_rejects_pretty_printed_equivalent_json():
    certificate = json.loads(_raw("certificate.json"))
    pretty = (json.dumps(certificate, indent=2, ensure_ascii=False) + "\n").encode()
    result = verify_signed_certificate_bytes_v06(
        pretty,
        _raw("certificate_signature.json"),
        _public_key(),
    )
    assert not result["valid"]
    assert any("canonical JCS" in error for error in result["errors"])


def test_certificate_byte_contract_rejects_v05_downgrade_object():
    legacy_like = {
        "spec_version": "pcs-0.5",
        "checker_version": "pcs-python-kernel/0.5.1",
        "subject": "legacy",
        "assumptions": [],
        "claims": [],
        "artifacts": [],
        "evidence": [],
        "workflow": {},
        "workflow_summary": {},
        "semantic_hash": "0" * 64,
        "integrity_hash": "0" * 64,
    }
    raw = canonicalize_jcs_bytes(legacy_like)
    try:
        parse_certificate_bytes_v06(raw)
    except V06ByteContractError as exc:
        assert "validation" in str(exc) or "verification failed" in str(exc)
    else:
        raise AssertionError("v0.5-like object must not enter the v0.6 byte contract")


def test_package_contract_rejects_artifact_tamper():
    files = _package_files()
    files["artifacts/fixture.bin"] = b"tampered artifact\n"
    result = verify_package_file_map_v06(
        _raw("package_manifest.json"),
        _raw("certificate.json"),
        _raw("package_signature.json"),
        files,
        _public_key(),
    )
    assert not result["valid"]
    assert any("hash mismatch" in error or "size mismatch" in error for error in result["errors"])


def test_package_contract_rejects_unsigned_extra_member():
    files = _package_files()
    files["extra.txt"] = b"not signed"
    result = verify_package_file_map_v06(
        _raw("package_manifest.json"),
        _raw("certificate.json"),
        _raw("package_signature.json"),
        files,
        _public_key(),
    )
    assert not result["valid"]
    assert any("unsigned members" in error for error in result["errors"])


def test_package_contract_rejects_missing_signed_member():
    files = _package_files()
    del files["artifacts/fixture.bin"]
    result = verify_package_file_map_v06(
        _raw("package_manifest.json"),
        _raw("certificate.json"),
        _raw("package_signature.json"),
        files,
        _public_key(),
    )
    assert not result["valid"]
    assert any("missing signed members" in error for error in result["errors"])


def test_package_contract_requires_byte_identical_certificate_member():
    files = _package_files()
    files["certificate.json"] = files["certificate.json"] + b"\n"
    result = verify_package_file_map_v06(
        _raw("package_manifest.json"),
        _raw("certificate.json"),
        _raw("package_signature.json"),
        files,
        _public_key(),
    )
    assert not result["valid"]
    assert any("byte-identical" in error for error in result["errors"])


def test_package_contract_rejects_signature_domain_substitution():
    record = json.loads(_raw("package_signature.json"))
    bad = deepcopy(record)
    bad["payload"]["domain"] = "pcs-certificate-signature-v2"
    bad_bytes = canonicalize_jcs_bytes(bad)
    result = verify_package_file_map_v06(
        _raw("package_manifest.json"),
        _raw("certificate.json"),
        bad_bytes,
        _package_files(),
        _public_key(),
    )
    assert not result["valid"]


def test_golden_generator_reproduces_exact_files():
    import subprocess
    import sys

    proc = subprocess.run(
        [sys.executable, "scripts/generate_v06_golden_contract.py"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "reproduce exactly" in proc.stdout


def test_certificate_byte_contract_enforces_raw_size_bound(monkeypatch):
    import pcs.byte_contract_v06 as byte_contract

    certificate = _raw("certificate.json")
    monkeypatch.setattr(
        byte_contract,
        "MAX_CERTIFICATE_BYTES_V06",
        len(certificate) - 1,
    )
    result = byte_contract.verify_signed_certificate_bytes_v06(
        certificate,
        _raw("certificate_signature.json"),
        _public_key(),
    )
    assert not result["valid"]
    assert any("exceeds byte limit" in error for error in result["errors"])


def test_certificate_byte_contract_rejects_non_bytes_input():
    result = verify_signed_certificate_bytes_v06(
        bytearray(_raw("certificate.json")),
        _raw("certificate_signature.json"),
        _public_key(),
    )
    assert not result["valid"]
    assert any("immutable bytes" in error for error in result["errors"])


def test_package_contract_rejects_non_string_member_key_cleanly():
    files = _package_files()
    files[7] = b"bad key"
    result = verify_package_file_map_v06(
        _raw("package_manifest.json"),
        _raw("certificate.json"),
        _raw("package_signature.json"),
        files,
        _public_key(),
    )
    assert not result["valid"]
    assert result["errors"] == ["v0.6 package file-map keys must be strings"]
