from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from pcs.certificate_v06 import finalize_certificate_hashes_v06
from pcs.crypto_domains_v06 import CERTIFICATE_SIGNATURE_DOMAIN
from pcs.package_v06 import (
    build_package_manifest_v06,
    sign_package_manifest_v06,
    verify_package_manifest_v06,
    verify_package_signature_v06,
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
