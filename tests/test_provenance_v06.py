from __future__ import annotations

import base64
import json
from copy import deepcopy
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from pcs.canonical_json import canonicalize_jcs_bytes
from pcs.environment import runtime_semantic_hash
from pcs.provenance_v06 import (
    BUILD_PROVENANCE_PATH_V06,
    BUILD_PROVENANCE_PUBLIC_KEY_PATH_V06,
    IN_TOTO_PAYLOAD_TYPE,
    IN_TOTO_STATEMENT_V1,
    PROVENANCE_INDEX_PATH_V06,
    SBOM_PATH_V06,
    V06ProvenanceError,
    build_cyclonedx_sbom_v06,
    diff_provenance_indexes_v06,
    dsse_pae_v06,
    stage_provenance_inputs_v06,
    verify_dsse_build_provenance_v06,
    verify_provenance_package_v06,
    write_cyclonedx_sbom_v06,
)
from pcs.signing import public_key_fingerprint


ROOT = Path(__file__).resolve().parents[1]


def _runtime(version: str = "3.12.7") -> dict:
    snapshot = {
        "format": "pcs-runtime-v1",
        "python": {
            "implementation": "CPython",
            "version": version,
            "version_info": [3, 12, 7],
        },
        "platform": {
            "system": "Linux",
            "release": "fixture",
            "machine": "x86_64",
            "architecture": "64bit",
        },
        "packages": [
            {"name": "cryptography", "version": "42.0.0"},
            {"name": "jsonschema", "version": "4.23.0"},
        ],
    }
    snapshot["semantic_hash"] = runtime_semantic_hash(snapshot)
    return snapshot


def _write_sbom(path: Path, *, version: str = "3.12.7") -> Path:
    path.write_bytes(canonicalize_jcs_bytes(build_cyclonedx_sbom_v06(_runtime(version))))
    return path


def _dsse_fixture(
    subject_sha256: str,
) -> tuple[bytes, bytes, str]:
    key = Ed25519PrivateKey.generate()
    statement = {
        "_type": IN_TOTO_STATEMENT_V1,
        "subject": [
            {
                "name": "oci-image",
                "digest": {"sha256": subject_sha256},
            }
        ],
        "predicateType": "https://slsa.dev/provenance/v1",
        "predicate": {
            "buildDefinition": {"buildType": "https://example.invalid/build/v1"},
            "runDetails": {},
        },
    }
    payload = canonicalize_jcs_bytes(statement)
    signature = key.sign(dsse_pae_v06(IN_TOTO_PAYLOAD_TYPE, payload))
    envelope = {
        "payloadType": IN_TOTO_PAYLOAD_TYPE,
        "payload": base64.b64encode(payload).decode("ascii"),
        "signatures": [
            {
                "keyid": "fixture",
                "sig": base64.b64encode(signature).decode("ascii"),
            }
        ],
    }
    public_key = key.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return (
        canonicalize_jcs_bytes(envelope),
        public_key,
        public_key_fingerprint(key.public_key()),
    )


def test_public_and_packaged_provenance_schemas_match():
    assert (ROOT / "schemas/provenance_index_v06.schema.json").read_bytes() == (
        ROOT / "pcs/schemas/provenance_index_v06.schema.json"
    ).read_bytes()


def test_cyclonedx_export_is_deterministic_and_runtime_scoped(tmp_path):
    left = build_cyclonedx_sbom_v06(_runtime())
    right = build_cyclonedx_sbom_v06(_runtime())
    assert left == right
    assert left["bomFormat"] == "CycloneDX"
    assert left["specVersion"] == "1.7"
    assert [item["name"] for item in left["components"]] == [
        "cryptography",
        "jsonschema",
    ]
    properties = {
        item["name"]: item["value"]
        for item in left["metadata"]["properties"]
    }
    assert properties["pcs:runtime-semantic-hash"] == _runtime()["semantic_hash"]

    output = tmp_path / "runtime.cdx.json"
    written = write_cyclonedx_sbom_v06(
        output,
        runtime_snapshot=_runtime(),
    )
    assert written == output.resolve()
    assert output.read_bytes() == canonicalize_jcs_bytes(left)


def test_sbom_is_bound_by_provenance_index_and_substitution_is_rejected(tmp_path):
    sbom = _write_sbom(tmp_path / "sbom.json")
    staged = stage_provenance_inputs_v06(sbom_path=sbom)
    assert staged["mode"] == "bound"
    assert set(staged["files"]) == {
        PROVENANCE_INDEX_PATH_V06,
        SBOM_PATH_V06,
    }

    verified = verify_provenance_package_v06(staged["files"])
    assert verified["valid"], verified["errors"]
    assert verified["entries"][0]["kind"] == "sbom"

    substituted = dict(staged["files"])
    substituted[SBOM_PATH_V06] = b'{"bomFormat":"CycloneDX","specVersion":"1.5","version":1}'
    rejected = verify_provenance_package_v06(substituted)
    assert not rejected["valid"]
    assert any("SHA-256 mismatch" in error for error in rejected["errors"])

    omitted = dict(staged["files"])
    omitted.pop(SBOM_PATH_V06)
    rejected = verify_provenance_package_v06(omitted)
    assert not rejected["valid"]
    assert any("missing signed bytes" in error for error in rejected["errors"])


def test_dsse_in_toto_build_provenance_requires_pinned_signer_and_subject(tmp_path):
    subject = "a" * 64
    envelope_raw, public_key_raw, fingerprint = _dsse_fixture(subject)
    envelope = tmp_path / "build.dsse.json"
    public = tmp_path / "builder.pem"
    envelope.write_bytes(envelope_raw)
    public.write_bytes(public_key_raw)

    staged = stage_provenance_inputs_v06(
        build_provenance_path=envelope,
        build_provenance_public_key_path=public,
        expected_build_provenance_fingerprint=fingerprint,
        expected_build_subject_sha256=[subject],
    )
    assert set(staged["files"]) == {
        PROVENANCE_INDEX_PATH_V06,
        BUILD_PROVENANCE_PATH_V06,
        BUILD_PROVENANCE_PUBLIC_KEY_PATH_V06,
    }
    verified = verify_provenance_package_v06(
        staged["files"],
        expected_build_provenance_fingerprint=fingerprint,
        expected_build_subject_sha256=[subject],
    )
    assert verified["valid"], verified["errors"]
    assert verified["reviewer_expectations"]["applied"] is True
    assert verified["reviewer_expectations"][
        "build_provenance_fingerprint"
    ] == fingerprint
    assert verified["reviewer_expectations"]["subject_sha256"] == [subject]
    entry = verified["entries"][0]
    assert entry["kind"] == "build_provenance"
    assert entry["public_key_fingerprint"] == fingerprint
    assert entry["expected_subject_sha256"] == [subject]

    wrong_reviewer = verify_provenance_package_v06(
        staged["files"],
        expected_build_provenance_fingerprint="e" * 64,
        expected_build_subject_sha256=[subject],
    )
    assert not wrong_reviewer["valid"]
    assert any(
        "reviewer-pinned fingerprint" in error
        for error in wrong_reviewer["errors"]
    )

    stale_reviewer = verify_provenance_package_v06(
        staged["files"],
        expected_build_provenance_fingerprint=fingerprint,
        expected_build_subject_sha256=["f" * 64],
    )
    assert not stale_reviewer["valid"]
    assert any(
        "reviewer-required subject" in error
        for error in stale_reviewer["errors"]
    )

    with pytest.raises(V06ProvenanceError, match="does not attest"):
        stage_provenance_inputs_v06(
            build_provenance_path=envelope,
            build_provenance_public_key_path=public,
            expected_build_provenance_fingerprint=fingerprint,
            expected_build_subject_sha256=["b" * 64],
        )

    with pytest.raises(V06ProvenanceError, match="pinned fingerprint"):
        stage_provenance_inputs_v06(
            build_provenance_path=envelope,
            build_provenance_public_key_path=public,
            expected_build_provenance_fingerprint="c" * 64,
            expected_build_subject_sha256=[subject],
        )


def test_dsse_optional_keyid_and_extension_fields_are_interoperable():
    subject = "1" * 64
    envelope_raw, public_key_raw, fingerprint = _dsse_fixture(subject)
    envelope = json.loads(envelope_raw.decode("utf-8"))
    envelope["signatures"][0].pop("keyid")
    envelope["signatures"][0]["x-pcs-test-extension"] = "ignored"
    envelope["x-pcs-envelope-extension"] = {"ignored": True}

    verified = verify_dsse_build_provenance_v06(
        canonicalize_jcs_bytes(envelope),
        public_key_raw,
        expected_fingerprint=fingerprint,
        expected_subject_sha256=[subject],
    )

    assert verified["valid"] is True
    assert verified["public_key_fingerprint"] == fingerprint
    assert verified["attested_subject_sha256"] == [subject]


def test_dsse_signature_substitution_is_rejected(tmp_path):
    subject = "d" * 64
    envelope_raw, public_key_raw, fingerprint = _dsse_fixture(subject)
    envelope = json.loads(envelope_raw.decode("utf-8"))
    envelope["signatures"][0]["sig"] = base64.b64encode(b"\x00" * 64).decode("ascii")

    with pytest.raises(V06ProvenanceError, match="no DSSE signature verified"):
        verify_dsse_build_provenance_v06(
            canonicalize_jcs_bytes(envelope),
            public_key_raw,
            expected_fingerprint=fingerprint,
            expected_subject_sha256=[subject],
        )


def test_provenance_namespace_rejects_unindexed_extra_member(tmp_path):
    staged = stage_provenance_inputs_v06(
        sbom_path=_write_sbom(tmp_path / "sbom.json")
    )
    files = dict(staged["files"])
    files["provenance/untracked.json"] = b"{}"
    result = verify_provenance_package_v06(files)
    assert not result["valid"]
    assert any("unexpected" in error for error in result["errors"])


def test_provenance_diff_is_stable_and_reports_changed_sbom(tmp_path):
    left = stage_provenance_inputs_v06(
        sbom_path=_write_sbom(tmp_path / "left.json", version="3.12.7")
    )["index"]
    right = stage_provenance_inputs_v06(
        sbom_path=_write_sbom(tmp_path / "right.json", version="3.12.8")
    )["index"]
    assert left is not None
    assert right is not None
    diff = diff_provenance_indexes_v06(left, right)
    assert diff["format"] == "pcs-provenance-diff-v1"
    assert diff["same_semantic_hash"] is False
    assert diff["kinds_added"] == []
    assert diff["kinds_removed"] == []
    assert diff["changed"]["sbom"]["same_sha256"] is False


def test_provenance_index_semantic_hash_rejects_tamper(tmp_path):
    staged = stage_provenance_inputs_v06(
        sbom_path=_write_sbom(tmp_path / "sbom.json")
    )
    files = dict(staged["files"])
    index = json.loads(files[PROVENANCE_INDEX_PATH_V06].decode("utf-8"))
    tampered = deepcopy(index)
    tampered["entries"][0]["size"] += 1
    files[PROVENANCE_INDEX_PATH_V06] = canonicalize_jcs_bytes(tampered)
    result = verify_provenance_package_v06(files)
    assert not result["valid"]
    assert any("semantic hash mismatch" in error for error in result["errors"])



def test_reviewer_build_provenance_pins_must_be_supplied_as_a_pair(tmp_path):
    sbom = _write_sbom(tmp_path / "sbom.json")
    staged = stage_provenance_inputs_v06(sbom_path=sbom)

    fingerprint_only = verify_provenance_package_v06(
        staged["files"],
        expected_build_provenance_fingerprint="a" * 64,
    )
    assert fingerprint_only["valid"] is False
    assert any("requires both" in error for error in fingerprint_only["errors"])

    subject_only = verify_provenance_package_v06(
        staged["files"],
        expected_build_subject_sha256=["b" * 64],
    )
    assert subject_only["valid"] is False
    assert any("requires both" in error for error in subject_only["errors"])



def test_in_toto_statement_rejects_subject_without_any_digest():
    key = Ed25519PrivateKey.generate()
    statement = {
        "_type": IN_TOTO_STATEMENT_V1,
        "subject": [{"name": "missing-digest", "digest": {}}],
        "predicateType": "https://slsa.dev/provenance/v1",
        "predicate": {},
    }
    payload = canonicalize_jcs_bytes(statement)
    signature = key.sign(dsse_pae_v06(IN_TOTO_PAYLOAD_TYPE, payload))
    envelope = canonicalize_jcs_bytes({
        "payloadType": IN_TOTO_PAYLOAD_TYPE,
        "payload": base64.b64encode(payload).decode("ascii"),
        "signatures": [{
            "keyid": "fixture",
            "sig": base64.b64encode(signature).decode("ascii"),
        }],
    })
    public_key = key.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    with pytest.raises(V06ProvenanceError, match="at least one digest"):
        verify_dsse_build_provenance_v06(
            envelope,
            public_key,
            expected_fingerprint=public_key_fingerprint(key.public_key()),
            expected_subject_sha256=["a" * 64],
        )
