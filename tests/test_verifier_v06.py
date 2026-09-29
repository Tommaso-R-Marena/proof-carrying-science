from __future__ import annotations

import base64
import hashlib
import json
from copy import deepcopy
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

from pcs.byte_contract_v06 import parse_certificate_bytes_v06
from pcs.canonical_json import canonicalize_jcs_bytes
from pcs.certificate_v06 import finalize_certificate_hashes_v06
from pcs.normalized_set_v06 import (
    INDEX_PATH_V06,
    index_semantic_hash_v06,
)
from pcs.normalized_wire_v06 import wire_semantic_hash_v06
from pcs.package_v06 import build_package_manifest_v06, sign_package_manifest_v06
from pcs.signing_v06 import sign_certificate_v06
from pcs.verifier_v06 import verify_end_to_end_v06


ROOT = Path(__file__).resolve().parents[1]
GOLDEN = ROOT / "tests" / "v06_golden"
META = json.loads((GOLDEN / "metadata.json").read_text(encoding="utf-8"))
TEST_PRIVATE_KEY = Ed25519PrivateKey.from_private_bytes(bytes(range(1, 33)))


def _raw(rel: str) -> bytes:
    return (GOLDEN / rel).read_bytes()


def _public_key() -> Ed25519PublicKey:
    return Ed25519PublicKey.from_public_bytes(
        base64.b64decode(META["public_key_raw_base64"], validate=True)
    )


def _golden_files() -> dict[str, bytes]:
    return {
        "certificate.json": _raw("certificate.json"),
        "artifacts/fixture.bin": _raw("artifacts/fixture.bin"),
        META["normalized_wire_path"]: _raw(META["normalized_wire_path"]),
        INDEX_PATH_V06: _raw(INDEX_PATH_V06),
    }


def _signed_inputs(
    certificate: dict,
    files: dict[str, bytes],
) -> tuple[bytes, bytes, bytes, bytes]:
    certificate_bytes = canonicalize_jcs_bytes(certificate)
    files = dict(files)
    files["certificate.json"] = certificate_bytes
    inventory = {
        name: {"sha256": hashlib.sha256(raw).hexdigest(), "size": len(raw)}
        for name, raw in files.items()
    }
    manifest = build_package_manifest_v06(certificate, inventory)
    certificate_signature = sign_certificate_v06(certificate, TEST_PRIVATE_KEY)
    package_signature = sign_package_manifest_v06(manifest, TEST_PRIVATE_KEY)
    return (
        certificate_bytes,
        canonicalize_jcs_bytes(certificate_signature),
        canonicalize_jcs_bytes(manifest),
        canonicalize_jcs_bytes(package_signature),
    )


def _verify(
    *,
    certificate_bytes: bytes,
    certificate_signature_bytes: bytes,
    package_manifest_bytes: bytes,
    package_signature_bytes: bytes,
    files: dict[str, bytes],
):
    return verify_end_to_end_v06(
        certificate_bytes=certificate_bytes,
        certificate_signature_bytes=certificate_signature_bytes,
        package_manifest_bytes=package_manifest_bytes,
        package_signature_bytes=package_signature_bytes,
        package_files=files,
        public_key=_public_key(),
        expected_fingerprint=META["public_key_fingerprint"],
    )


def test_golden_package_passes_single_end_to_end_entry_point():
    result = _verify(
        certificate_bytes=_raw("certificate.json"),
        certificate_signature_bytes=_raw("certificate_signature.json"),
        package_manifest_bytes=_raw("package_manifest.json"),
        package_signature_bytes=_raw("package_signature.json"),
        files=_golden_files(),
    )

    assert result["valid"], result["errors"]
    assert result["failed_stage"] is None
    assert all(result["stages"].values())
    assert result["certificate_semantic_hash"] == META["certificate_semantic_hash"]
    assert result["normalized_index_semantic_hash"] == META[
        "normalized_index_semantic_hash"
    ]
    assert result["claims"] == [
        {
            "claim_id": "C1",
            "kind": "computational",
            "decision": "COMPUTATIONALLY_SUPPORTED",
            "predicate": {
                "type": "reaction_balance",
                "reactants": [
                    {"formula": "H2", "coefficient": 2},
                    {"formula": "O2", "coefficient": 1},
                ],
                "products": [{"formula": "H2O", "coefficient": 2}],
            },
            "normalized_path": META["normalized_wire_path"],
            "wire_semantic_hash": META["normalized_wire_semantic_hash"],
        }
    ]


def test_end_to_end_fails_at_package_binding_before_replay_on_artifact_tamper():
    files = _golden_files()
    files["artifacts/fixture.bin"] = b"tampered artifact\n"

    result = _verify(
        certificate_bytes=_raw("certificate.json"),
        certificate_signature_bytes=_raw("certificate_signature.json"),
        package_manifest_bytes=_raw("package_manifest.json"),
        package_signature_bytes=_raw("package_signature.json"),
        files=files,
    )

    assert not result["valid"]
    assert result["failed_stage"] == "package_binding"
    assert result["stages"] == {
        "canonical_inputs": True,
        "certificate_signature": True,
        "package_binding": False,
        "replay": False,
        "normalized_set": False,
    }


def test_fully_rehashed_and_resigned_false_pass_fails_at_replay():
    certificate = parse_certificate_bytes_v06(_raw("certificate.json"))
    forged = deepcopy(certificate)
    false_predicate = {
        "type": "reaction_balance",
        "reactants": [{"formula": "H2", "coefficient": 1}],
        "products": [{"formula": "H2O", "coefficient": 1}],
    }
    forged["claims"][0]["predicate"] = deepcopy(false_predicate)
    forged["evidence"][0]["predicate"] = deepcopy(false_predicate)
    forged["evidence"][0]["check_spec"] = deepcopy(false_predicate)
    # Leave the recorded PASS and COMPUTATIONALLY_SUPPORTED assessment in place.
    # They are structurally consistent but scientifically false for this predicate.
    forged["semantic_hash"] = ""
    forged["integrity_hash"] = ""
    forged = finalize_certificate_hashes_v06(forged)

    files = _golden_files()
    cert_bytes, cert_sig, manifest_bytes, package_sig = _signed_inputs(forged, files)
    files["certificate.json"] = cert_bytes

    result = _verify(
        certificate_bytes=cert_bytes,
        certificate_signature_bytes=cert_sig,
        package_manifest_bytes=manifest_bytes,
        package_signature_bytes=package_sig,
        files=files,
    )

    assert not result["valid"]
    assert result["failed_stage"] == "replay"
    assert result["stages"]["canonical_inputs"]
    assert result["stages"]["certificate_signature"]
    assert result["stages"]["package_binding"]
    assert not result["stages"]["replay"]
    assert any("replay outcome mismatch" in error for error in result["errors"])


def test_resigned_normalized_forgery_fails_at_normalized_set():
    certificate = parse_certificate_bytes_v06(_raw("certificate.json"))
    files = _golden_files()

    wire = json.loads(files[META["normalized_wire_path"]])
    wire["context"][0]["statement"] = "attacker-controlled context"
    wire["wire_semantic_hash"] = wire_semantic_hash_v06(wire)
    files[META["normalized_wire_path"]] = canonicalize_jcs_bytes(wire)

    index = json.loads(files[INDEX_PATH_V06])
    index["entries"][0]["wire_semantic_hash"] = wire["wire_semantic_hash"]
    index["index_semantic_hash"] = index_semantic_hash_v06(index)
    files[INDEX_PATH_V06] = canonicalize_jcs_bytes(index)

    cert_bytes, cert_sig, manifest_bytes, package_sig = _signed_inputs(
        certificate,
        files,
    )
    files["certificate.json"] = cert_bytes

    result = _verify(
        certificate_bytes=cert_bytes,
        certificate_signature_bytes=cert_sig,
        package_manifest_bytes=manifest_bytes,
        package_signature_bytes=package_sig,
        files=files,
    )

    assert not result["valid"]
    assert result["failed_stage"] == "normalized_set"
    assert result["stages"]["canonical_inputs"]
    assert result["stages"]["certificate_signature"]
    assert result["stages"]["package_binding"]
    assert result["stages"]["replay"]
    assert not result["stages"]["normalized_set"]
    assert any("replay-derived bytes" in error for error in result["errors"])


def test_end_to_end_executes_scientific_replay_once(monkeypatch):
    import pcs.verifier_v06 as verifier

    calls = 0
    original = verifier.verify_certificate_replay_v06

    def counted(*args, **kwargs):
        nonlocal calls
        calls += 1
        return original(*args, **kwargs)

    monkeypatch.setattr(verifier, "verify_certificate_replay_v06", counted)
    result = _verify(
        certificate_bytes=_raw("certificate.json"),
        certificate_signature_bytes=_raw("certificate_signature.json"),
        package_manifest_bytes=_raw("package_manifest.json"),
        package_signature_bytes=_raw("package_signature.json"),
        files=_golden_files(),
    )

    assert result["valid"], result["errors"]
    assert calls == 1
