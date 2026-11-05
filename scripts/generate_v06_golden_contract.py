from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from pcs.canonical_json import JCS_PROFILE, canonicalize_jcs_bytes
from pcs.certificate_v06 import finalize_certificate_hashes_v06
from pcs.crypto_domains_v06 import (
    CERTIFICATE_INTEGRITY_DOMAIN,
    CERTIFICATE_SEMANTIC_DOMAIN,
)
from pcs.package_v06 import build_package_manifest_v06, sign_package_manifest_v06
from pcs.normalized_set_v06 import build_normalized_set_v06
from pcs.signing import public_key_fingerprint
from pcs.signing_v06 import sign_certificate_v06


ROOT = Path(__file__).resolve().parents[1]
GOLDEN = ROOT / "tests" / "v06_golden"
TEST_SEED = bytes(range(1, 33))
ARTIFACT_BYTES = b"fixture artifact\n"


def build() -> dict[str, bytes]:
    private_key = Ed25519PrivateKey.from_private_bytes(TEST_SEED)
    public_key = private_key.public_key()
    certificate = finalize_certificate_hashes_v06(
        {
            "spec_version": "pcs-0.6",
            "checker_version": "pcs-python-kernel/0.6.0-dev",
            "canonical_json_profile": JCS_PROFILE,
            "semantic_hash_format": CERTIFICATE_SEMANTIC_DOMAIN,
            "integrity_hash_format": CERTIFICATE_INTEGRITY_DOMAIN,
            "generated_at": "2026-09-29T00:00:00+00:00",
            "subject": "PCS v0.6 byte-contract golden fixture",
            "mission_scope": "cross-language byte-contract fixture",
            "assumptions": [
                {"id": "A1", "statement": "fixture assumption", "scope": ["C1"]}
            ],
            "claims": [
                {
                    "id": "C1",
                    "statement": "The fixture reaction is atom-balanced.",
                    "kind": "computational",
                    "predicate": {
                        "type": "reaction_balance",
                        "reactants": [
                            {"formula": "H2", "coefficient": 2},
                            {"formula": "O2", "coefficient": 1},
                        ],
                        "products": [{"formula": "H2O", "coefficient": 2}],
                    },
                    "required_evidence": ["E1"],
                    "assumptions": ["A1"],
                    "assessment": {
                        "status": "COMPUTATIONALLY_SUPPORTED",
                        "reason": "all declared computational checks passed",
                    },
                }
            ],
            "artifacts": [],
            "evidence": [
                {
                    "id": "E1",
                    "kind": "computational_test",
                    "claim_ids": ["C1"],
                    "outcome": "PASS",
                    "checker": "pcs-python-kernel/0.6.0-dev",
                    "predicate": {
                        "type": "reaction_balance",
                        "reactants": [
                            {"formula": "H2", "coefficient": 2},
                            {"formula": "O2", "coefficient": 1},
                        ],
                        "products": [{"formula": "H2O", "coefficient": 2}],
                    },
                    "artifact_ids": [],
                    "check_spec": {
                        "type": "reaction_balance",
                        "reactants": [
                            {"formula": "H2", "coefficient": 2},
                            {"formula": "O2", "coefficient": 1},
                        ],
                        "products": [{"formula": "H2O", "coefficient": 2}],
                    },
                }
            ],
            "workflow": {"nodes": []},
            "workflow_summary": {"node_count": 0, "topological_order": []},
            "semantic_hash": "",
            "integrity_hash": "",
        }
    )
    certificate_bytes = canonicalize_jcs_bytes(certificate)
    certificate_signature = sign_certificate_v06(certificate, private_key)
    normalized_set = build_normalized_set_v06(certificate, {})
    normalized_files = normalized_set["files"]
    normalized_entry = normalized_set["index"]["entries"][0]
    normalized_wire_bytes = normalized_files[normalized_entry["path"]]

    files = {
        "certificate.json": {
            "sha256": hashlib.sha256(certificate_bytes).hexdigest(),
            "size": len(certificate_bytes),
        },
        "artifacts/fixture.bin": {
            "sha256": hashlib.sha256(ARTIFACT_BYTES).hexdigest(),
            "size": len(ARTIFACT_BYTES),
        },
    }
    for rel, raw in normalized_files.items():
        files[rel] = {
            "sha256": hashlib.sha256(raw).hexdigest(),
            "size": len(raw),
        }
    manifest = build_package_manifest_v06(certificate, files)
    package_signature = sign_package_manifest_v06(manifest, private_key)

    certificate_signature_bytes = canonicalize_jcs_bytes(certificate_signature)
    manifest_bytes = canonicalize_jcs_bytes(manifest)
    package_signature_bytes = canonicalize_jcs_bytes(package_signature)
    public_raw = public_key.public_bytes(
        serialization.Encoding.Raw,
        serialization.PublicFormat.Raw,
    )

    metadata = {
        "format": "pcs-v06-byte-contract-v1",
        "test_vector_only": True,
        "public_key_raw_base64": __import__("base64").b64encode(public_raw).decode("ascii"),
        "public_key_fingerprint": public_key_fingerprint(public_key),
        "certificate_byte_sha256": hashlib.sha256(certificate_bytes).hexdigest(),
        "certificate_semantic_hash": certificate["semantic_hash"],
        "certificate_integrity_hash": certificate["integrity_hash"],
        "certificate_signature_record_byte_sha256": hashlib.sha256(
            certificate_signature_bytes
        ).hexdigest(),
        "certificate_signature_payload_sha256": certificate_signature["payload_sha256"],
        "package_manifest_byte_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
        "package_signature_record_byte_sha256": hashlib.sha256(
            package_signature_bytes
        ).hexdigest(),
        "package_signature_payload_sha256": package_signature["payload_sha256"],
        "normalized_wire_path": normalized_entry["path"],
        "normalized_wire_byte_sha256": hashlib.sha256(normalized_wire_bytes).hexdigest(),
        "normalized_wire_semantic_hash": normalized_entry["wire_semantic_hash"],
        "normalized_index_byte_sha256": hashlib.sha256(
            normalized_files["normalized/index.json"]
        ).hexdigest(),
        "normalized_index_semantic_hash": normalized_set["index"]["index_semantic_hash"],
        "predicate_commitment": __import__("json").loads(
            normalized_wire_bytes.decode("utf-8")
        )["claim"]["predicate_commitment"],
        "artifact_sha256": hashlib.sha256(ARTIFACT_BYTES).hexdigest(),
    }
    metadata_bytes = (
        json.dumps(metadata, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    ).encode("utf-8")

    return {
        "certificate.json": certificate_bytes,
        "certificate_signature.json": certificate_signature_bytes,
        "package_manifest.json": manifest_bytes,
        "package_signature.json": package_signature_bytes,
        "artifacts/fixture.bin": ARTIFACT_BYTES,
        **normalized_files,
        "metadata.json": metadata_bytes,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate or verify the deterministic PCS v0.6 byte-contract corpus."
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="overwrite the frozen corpus instead of checking it",
    )
    args = parser.parse_args()

    expected = build()
    expected_paths = {Path(rel).as_posix() for rel in expected}
    actual_paths = {
        path.relative_to(GOLDEN).as_posix()
        for path in GOLDEN.rglob("*")
        if path.is_file()
    }

    if args.write:
        for stale in sorted(actual_paths - expected_paths):
            (GOLDEN / stale).unlink()
        for rel, raw in expected.items():
            path = GOLDEN / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
        print(
            f"WROTE {len(expected)} v0.6 golden files; "
            f"removed {len(actual_paths - expected_paths)} stale files"
        )
        return 0

    failures: list[str] = []
    for stale in sorted(actual_paths - expected_paths):
        failures.append(f"unexpected stale golden file {stale}")
    for missing in sorted(expected_paths - actual_paths):
        failures.append(f"missing {missing}")
    for rel, raw in expected.items():
        path = GOLDEN / rel
        if not path.is_file():
            continue
        actual = path.read_bytes()
        if actual != raw:
            failures.append(
                f"{rel}: expected sha256={hashlib.sha256(raw).hexdigest()} "
                f"actual sha256={hashlib.sha256(actual).hexdigest()}"
            )
    if failures:
        for failure in failures:
            print("FAIL", failure)
        return 1
    print(f"PASS {len(expected)} frozen v0.6 byte-contract files reproduce exactly")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
