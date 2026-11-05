from __future__ import annotations

import base64
import hashlib
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from .canonical_json import JCS_PROFILE, canonicalize_jcs_bytes
from .environment import snapshot_environment, validate_environment
from .jsonio import StrictJSONError, strict_json_loads
from .schema_validation import (
    SchemaValidationError,
    validate_v06_provenance_index_shape,
)
from .signing import public_key_fingerprint


PROVENANCE_INDEX_FORMAT_V06 = "pcs-provenance-index-v1"
PROVENANCE_INDEX_HASH_FORMAT_V06 = "pcs-provenance-index-sha256-v1"
PROVENANCE_INDEX_PATH_V06 = "provenance/index.json"
SBOM_PATH_V06 = "provenance/sbom.json"
BUILD_PROVENANCE_PATH_V06 = "provenance/build-provenance.dsse.json"
BUILD_PROVENANCE_PUBLIC_KEY_PATH_V06 = "provenance/build-provenance-public-key.pem"

CYCLONEDX_SUPPORTED_VERSIONS = frozenset({"1.4", "1.5", "1.6", "1.7"})
SPDX_SUPPORTED_VERSIONS = frozenset({"SPDX-2.2", "SPDX-2.3"})
IN_TOTO_STATEMENT_V1 = "https://in-toto.io/Statement/v1"
IN_TOTO_PAYLOAD_TYPE = "application/vnd.in-toto+json"

MAX_SBOM_BYTES_V06 = 10 * 1024 * 1024
MAX_BUILD_PROVENANCE_BYTES_V06 = 10 * 1024 * 1024
MAX_PROVENANCE_PUBLIC_KEY_BYTES_V06 = 64 * 1024

_SHA256_HEX = frozenset("0123456789abcdef")


class V06ProvenanceError(ValueError):
    pass


def _is_sha256(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(ch in _SHA256_HEX for ch in value)
    )


def _read_regular_file(
    path: str | Path,
    *,
    label: str,
    max_bytes: int,
) -> bytes:
    source = Path(path).resolve()
    original = Path(path)
    if original.is_symlink():
        raise V06ProvenanceError(f"{label} must not be a symlink")
    if not source.is_file():
        raise V06ProvenanceError(f"{label} is not a regular file: {source}")
    size = source.stat().st_size
    if size > max_bytes:
        raise V06ProvenanceError(
            f"{label} exceeds byte limit: {size} > {max_bytes}"
        )
    raw = source.read_bytes()
    if len(raw) != size:
        raise V06ProvenanceError(f"{label} changed while being read")
    return raw


def _strict_json_bytes(raw: bytes, *, label: str) -> Any:
    try:
        return strict_json_loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, StrictJSONError) as exc:
        raise V06ProvenanceError(
            f"{label} is not strict UTF-8 JSON: {exc}"
        ) from exc


def detect_sbom_format_v06(value: Any) -> str:
    if not isinstance(value, Mapping):
        raise V06ProvenanceError("SBOM root must be a JSON object")

    if value.get("bomFormat") == "CycloneDX":
        version = value.get("specVersion")
        if version not in CYCLONEDX_SUPPORTED_VERSIONS:
            raise V06ProvenanceError(
                f"unsupported CycloneDX specVersion: {version!r}"
            )
        components = value.get("components", [])
        if not isinstance(components, list):
            raise V06ProvenanceError("CycloneDX components must be an array")
        return f"cyclonedx-json-{version}"

    spdx_version = value.get("spdxVersion")
    if spdx_version in SPDX_SUPPORTED_VERSIONS:
        if value.get("SPDXID") != "SPDXRef-DOCUMENT":
            raise V06ProvenanceError(
                "SPDX JSON must identify the document as SPDXRef-DOCUMENT"
            )
        packages = value.get("packages", [])
        if not isinstance(packages, list):
            raise V06ProvenanceError("SPDX packages must be an array")
        return f"spdx-json-{spdx_version.removeprefix('SPDX-')}"

    raise V06ProvenanceError(
        "unsupported SBOM; expected CycloneDX JSON 1.4/1.5/1.6/1.7 "
        "or SPDX JSON 2.2/2.3"
    )


def build_cyclonedx_sbom_v06(
    runtime_snapshot: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    snapshot = (
        deepcopy(dict(runtime_snapshot))
        if runtime_snapshot is not None
        else snapshot_environment()
    )
    checked = validate_environment(snapshot)
    if checked.get("valid") is not True:
        raise V06ProvenanceError(
            "cannot export SBOM from invalid runtime snapshot: "
            + "; ".join(str(x) for x in checked.get("errors", []))
        )

    python_meta = snapshot.get("python", {})
    platform_meta = snapshot.get("platform", {})
    components = []
    for package in snapshot.get("packages", []):
        if not isinstance(package, Mapping):
            raise V06ProvenanceError("runtime package entry is not an object")
        name = package.get("name")
        version = package.get("version")
        if not isinstance(name, str) or not name:
            raise V06ProvenanceError("runtime package name is invalid")
        if not isinstance(version, str):
            raise V06ProvenanceError(
                f"runtime package version is invalid for {name!r}"
            )
        components.append(
            {
                "type": "library",
                "name": name,
                "version": version,
            }
        )

    properties = [
        {
            "name": "pcs:runtime-semantic-hash",
            "value": str(snapshot["semantic_hash"]),
        },
        {
            "name": "pcs:python-implementation",
            "value": str(python_meta.get("implementation", "")),
        },
        {
            "name": "pcs:python-version",
            "value": str(python_meta.get("version", "")),
        },
        {
            "name": "pcs:platform-system",
            "value": str(platform_meta.get("system", "")),
        },
        {
            "name": "pcs:platform-release",
            "value": str(platform_meta.get("release", "")),
        },
        {
            "name": "pcs:platform-machine",
            "value": str(platform_meta.get("machine", "")),
        },
    ]

    sbom = {
        "bomFormat": "CycloneDX",
        "specVersion": "1.7",
        "version": 1,
        "metadata": {
            "component": {
                "type": "application",
                "name": "pcs-observed-python-runtime",
                "version": str(python_meta.get("version", "")),
            },
            "properties": properties,
        },
        "components": components,
    }
    detect_sbom_format_v06(sbom)
    return sbom


def write_cyclonedx_sbom_v06(
    output: str | Path,
    *,
    overwrite: bool = False,
    runtime_snapshot: Mapping[str, Any] | None = None,
) -> Path:
    path = Path(output).resolve()
    if path.exists() and not overwrite:
        raise V06ProvenanceError(f"refusing to overwrite existing SBOM: {path}")
    sbom = build_cyclonedx_sbom_v06(runtime_snapshot)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonicalize_jcs_bytes(sbom))
    return path


def _load_ed25519_public_key(raw: bytes) -> Ed25519PublicKey:
    errors: list[str] = []
    for loader in (
        serialization.load_pem_public_key,
        serialization.load_der_public_key,
    ):
        try:
            key = loader(raw)
        except (ValueError, TypeError) as exc:
            errors.append(f"{type(exc).__name__}: {exc}")
            continue
        if not isinstance(key, Ed25519PublicKey):
            raise V06ProvenanceError(
                "build-provenance public key is not Ed25519"
            )
        return key
    raise V06ProvenanceError(
        "cannot decode build-provenance Ed25519 public key"
        + (f": {'; '.join(errors)}" if errors else "")
    )


def dsse_pae_v06(payload_type: str, payload: bytes) -> bytes:
    if not isinstance(payload_type, str) or not payload_type:
        raise V06ProvenanceError("DSSE payloadType must be a non-empty string")
    payload_type_bytes = payload_type.encode("utf-8")
    return (
        b"DSSEv1 "
        + str(len(payload_type_bytes)).encode("ascii")
        + b" "
        + payload_type_bytes
        + b" "
        + str(len(payload)).encode("ascii")
        + b" "
        + payload
    )


def _decode_base64(text: Any, *, label: str) -> bytes:
    if not isinstance(text, str) or not text:
        raise V06ProvenanceError(f"{label} must be a non-empty base64 string")
    try:
        return base64.b64decode(text, validate=True)
    except Exception as exc:
        raise V06ProvenanceError(f"{label} is invalid base64: {exc}") from exc


def _normalize_expected_subjects(values: list[str] | tuple[str, ...]) -> list[str]:
    if not values:
        raise V06ProvenanceError(
            "build provenance requires at least one expected subject SHA-256"
        )
    normalized: list[str] = []
    for value in values:
        if not _is_sha256(value):
            raise V06ProvenanceError(
                "expected build-provenance subject SHA-256 must be 64 lowercase hex"
            )
        normalized.append(value)
    if len(normalized) != len(set(normalized)):
        raise V06ProvenanceError(
            "expected build-provenance subject SHA-256 values must be unique"
        )
    return sorted(normalized)


def _statement_metadata(statement: Any) -> dict[str, Any]:
    if not isinstance(statement, Mapping):
        raise V06ProvenanceError("in-toto statement root must be an object")
    if statement.get("_type") != IN_TOTO_STATEMENT_V1:
        raise V06ProvenanceError(
            "build provenance must be an in-toto Statement v1"
        )
    predicate_type = statement.get("predicateType")
    if not isinstance(predicate_type, str) or not predicate_type:
        raise V06ProvenanceError(
            "in-toto statement predicateType must be a non-empty string"
        )
    subjects = statement.get("subject")
    if not isinstance(subjects, list) or not subjects:
        raise V06ProvenanceError(
            "in-toto statement must contain at least one subject"
        )

    subject_sha256: set[str] = set()
    for index, subject in enumerate(subjects):
        if not isinstance(subject, Mapping):
            raise V06ProvenanceError(
                f"in-toto subject {index} must be an object"
            )
        digest = subject.get("digest")
        if not isinstance(digest, Mapping) or not digest:
            raise V06ProvenanceError(
                f"in-toto subject {index} must contain at least one digest"
            )
        sha256 = digest.get("sha256")
        if sha256 is None:
            continue
        if not _is_sha256(sha256):
            raise V06ProvenanceError(
                f"in-toto subject {index} has invalid sha256 digest"
            )
        subject_sha256.add(str(sha256))

    if not subject_sha256:
        raise V06ProvenanceError(
            "in-toto statement contains no subject sha256 digest"
        )
    return {
        "predicate_type": predicate_type,
        "subject_sha256": sorted(subject_sha256),
    }


def verify_dsse_build_provenance_v06(
    envelope_raw: bytes,
    public_key_raw: bytes,
    *,
    expected_fingerprint: str,
    expected_subject_sha256: list[str] | tuple[str, ...],
) -> dict[str, Any]:
    if not _is_sha256(expected_fingerprint):
        raise V06ProvenanceError(
            "expected build-provenance signer fingerprint must be 64 lowercase hex"
        )
    expected_subjects = _normalize_expected_subjects(
        list(expected_subject_sha256)
    )
    envelope = _strict_json_bytes(
        envelope_raw,
        label="build-provenance DSSE envelope",
    )
    if not isinstance(envelope, Mapping):
        raise V06ProvenanceError("DSSE envelope root must be an object")
    required_envelope_fields = {"payloadType", "payload", "signatures"}
    missing_envelope_fields = sorted(required_envelope_fields - set(envelope))
    if missing_envelope_fields:
        raise V06ProvenanceError(
            "DSSE envelope is missing required fields: "
            + ", ".join(missing_envelope_fields)
        )

    payload_type = envelope.get("payloadType")
    if payload_type != IN_TOTO_PAYLOAD_TYPE:
        raise V06ProvenanceError(
            "build-provenance DSSE payloadType must be "
            f"{IN_TOTO_PAYLOAD_TYPE!r}"
        )
    payload = _decode_base64(
        envelope.get("payload"),
        label="DSSE payload",
    )
    statement = _strict_json_bytes(
        payload,
        label="in-toto statement payload",
    )
    statement_meta = _statement_metadata(statement)
    attested_subjects = set(statement_meta["subject_sha256"])
    missing_subjects = [
        digest for digest in expected_subjects if digest not in attested_subjects
    ]
    if missing_subjects:
        raise V06ProvenanceError(
            "build provenance does not attest the expected subject SHA-256: "
            + ", ".join(missing_subjects)
        )

    public_key = _load_ed25519_public_key(public_key_raw)
    fingerprint = public_key_fingerprint(public_key)
    if fingerprint != expected_fingerprint:
        raise V06ProvenanceError(
            "build-provenance public key does not match pinned fingerprint"
        )

    signatures = envelope.get("signatures")
    if not isinstance(signatures, list) or not signatures:
        raise V06ProvenanceError(
            "DSSE envelope must contain at least one signature"
        )
    pae = dsse_pae_v06(payload_type, payload)
    verified = False
    signature_errors: list[str] = []
    for index, record in enumerate(signatures):
        if not isinstance(record, Mapping) or "sig" not in record:
            raise V06ProvenanceError(
                f"DSSE signature {index} must contain sig"
            )
        keyid = record.get("keyid")
        if keyid is not None and not isinstance(keyid, str):
            raise V06ProvenanceError(
                f"DSSE signature {index} keyid must be a string when present"
            )
        # DSSE keyid is an unauthenticated hint only. PCS never uses it for
        # trust decisions; the receiver-selected Ed25519 fingerprint is the
        # trust anchor.
        signature = _decode_base64(
            record.get("sig"),
            label=f"DSSE signature {index}",
        )
        try:
            public_key.verify(signature, pae)
            verified = True
            break
        except Exception as exc:
            signature_errors.append(
                f"signature {index}: {type(exc).__name__}: {exc}"
            )
    if not verified:
        raise V06ProvenanceError(
            "no DSSE signature verified with the pinned Ed25519 key"
            + (f": {'; '.join(signature_errors)}" if signature_errors else "")
        )

    return {
        "valid": True,
        "payload_type": payload_type,
        "predicate_type": statement_meta["predicate_type"],
        "attested_subject_sha256": statement_meta["subject_sha256"],
        "expected_subject_sha256": expected_subjects,
        "public_key_fingerprint": fingerprint,
        "signature_count": len(signatures),
    }


def _index_projection(index: Mapping[str, Any]) -> dict[str, Any]:
    projection = deepcopy(dict(index))
    projection.pop("semantic_hash", None)
    return projection


def provenance_index_semantic_hash_v06(index: Mapping[str, Any]) -> str:
    payload = canonicalize_jcs_bytes(_index_projection(index))
    return hashlib.sha256(
        b"PCS-PROVENANCE-INDEX-V1\0" + payload
    ).hexdigest()


def validate_provenance_index_v06(index: Any) -> dict[str, Any]:
    try:
        validate_v06_provenance_index_shape(index)
    except SchemaValidationError as exc:
        raise V06ProvenanceError(str(exc)) from exc
    if not isinstance(index, Mapping):
        raise V06ProvenanceError("provenance index root must be an object")
    supplied = index.get("semantic_hash")
    expected = provenance_index_semantic_hash_v06(index)
    if supplied != expected:
        raise V06ProvenanceError("provenance index semantic hash mismatch")
    entries = index.get("entries")
    assert isinstance(entries, list)
    kinds = [entry.get("kind") for entry in entries if isinstance(entry, Mapping)]
    if kinds != sorted(kinds):
        raise V06ProvenanceError(
            "provenance index entries must be sorted by kind"
        )
    if len(kinds) != len(set(kinds)):
        raise V06ProvenanceError(
            "provenance index contains duplicate entry kinds"
        )
    return deepcopy(dict(index))


def stage_provenance_inputs_v06(
    *,
    sbom_path: str | Path | None = None,
    build_provenance_path: str | Path | None = None,
    build_provenance_public_key_path: str | Path | None = None,
    expected_build_provenance_fingerprint: str | None = None,
    expected_build_subject_sha256: list[str] | tuple[str, ...] | None = None,
) -> dict[str, Any]:
    build_related = (
        build_provenance_path,
        build_provenance_public_key_path,
        expected_build_provenance_fingerprint,
        expected_build_subject_sha256,
    )
    if build_provenance_path is None and any(
        value not in (None, [], ()) for value in build_related[1:]
    ):
        raise V06ProvenanceError(
            "build-provenance trust inputs require --build-provenance"
        )

    files: dict[str, bytes] = {}
    entries: list[dict[str, Any]] = []

    if sbom_path is not None:
        sbom_raw = _read_regular_file(
            sbom_path,
            label="SBOM",
            max_bytes=MAX_SBOM_BYTES_V06,
        )
        sbom_value = _strict_json_bytes(sbom_raw, label="SBOM")
        sbom_format = detect_sbom_format_v06(sbom_value)
        files[SBOM_PATH_V06] = sbom_raw
        entries.append(
            {
                "kind": "sbom",
                "path": SBOM_PATH_V06,
                "format": sbom_format,
                "sha256": hashlib.sha256(sbom_raw).hexdigest(),
                "size": len(sbom_raw),
            }
        )

    if build_provenance_path is not None:
        if build_provenance_public_key_path is None:
            raise V06ProvenanceError(
                "build provenance requires --build-provenance-public-key"
            )
        if expected_build_provenance_fingerprint is None:
            raise V06ProvenanceError(
                "build provenance requires a pinned signer fingerprint"
            )
        if not expected_build_subject_sha256:
            raise V06ProvenanceError(
                "build provenance requires at least one expected subject SHA-256"
            )

        envelope_raw = _read_regular_file(
            build_provenance_path,
            label="build-provenance DSSE envelope",
            max_bytes=MAX_BUILD_PROVENANCE_BYTES_V06,
        )
        public_key_raw = _read_regular_file(
            build_provenance_public_key_path,
            label="build-provenance public key",
            max_bytes=MAX_PROVENANCE_PUBLIC_KEY_BYTES_V06,
        )
        verified = verify_dsse_build_provenance_v06(
            envelope_raw,
            public_key_raw,
            expected_fingerprint=expected_build_provenance_fingerprint,
            expected_subject_sha256=list(expected_build_subject_sha256),
        )
        files[BUILD_PROVENANCE_PATH_V06] = envelope_raw
        files[BUILD_PROVENANCE_PUBLIC_KEY_PATH_V06] = public_key_raw
        entries.append(
            {
                "kind": "build_provenance",
                "path": BUILD_PROVENANCE_PATH_V06,
                "format": "dsse-in-toto-statement-v1-ed25519",
                "sha256": hashlib.sha256(envelope_raw).hexdigest(),
                "size": len(envelope_raw),
                "public_key_path": BUILD_PROVENANCE_PUBLIC_KEY_PATH_V06,
                "public_key_fingerprint": verified[
                    "public_key_fingerprint"
                ],
                "expected_subject_sha256": verified[
                    "expected_subject_sha256"
                ],
                "attested_subject_sha256": verified[
                    "attested_subject_sha256"
                ],
                "payload_type": verified["payload_type"],
                "predicate_type": verified["predicate_type"],
            }
        )

    if not entries:
        return {
            "mode": "none",
            "files": {},
            "index": None,
        }

    entries.sort(key=lambda item: str(item["kind"]))
    index: dict[str, Any] = {
        "format": PROVENANCE_INDEX_FORMAT_V06,
        "canonical_json_profile": JCS_PROFILE,
        "semantic_hash_format": PROVENANCE_INDEX_HASH_FORMAT_V06,
        "entries": entries,
        "semantic_hash": "",
    }
    index["semantic_hash"] = provenance_index_semantic_hash_v06(index)
    index = validate_provenance_index_v06(index)
    files[PROVENANCE_INDEX_PATH_V06] = canonicalize_jcs_bytes(index)
    return {
        "mode": "bound",
        "files": files,
        "index": index,
    }


def verify_provenance_package_v06(
    package_files: Mapping[str, bytes],
    *,
    expected_build_provenance_fingerprint: str | None = None,
    expected_build_subject_sha256: list[str] | tuple[str, ...] | None = None,
) -> dict[str, Any]:
    provenance_names = sorted(
        name for name in package_files if name.startswith("provenance/")
    )
    try:
        reviewer_subjects = (
            _normalize_expected_subjects(list(expected_build_subject_sha256))
            if expected_build_subject_sha256
            else []
        )
    except V06ProvenanceError as exc:
        return {
            "valid": False,
            "errors": [str(exc)],
            "mode": "invalid",
            "entries": [],
            "semantic_hash": None,
        }
    if (
        expected_build_provenance_fingerprint is not None
        and not _is_sha256(expected_build_provenance_fingerprint)
    ):
        return {
            "valid": False,
            "errors": [
                "reviewer build-provenance fingerprint must be 64 lowercase hex"
            ],
            "mode": "invalid",
            "entries": [],
            "semantic_hash": None,
        }

    reviewer_has_fingerprint = expected_build_provenance_fingerprint is not None
    reviewer_has_subjects = bool(reviewer_subjects)
    if reviewer_has_fingerprint != reviewer_has_subjects:
        return {
            "valid": False,
            "errors": [
                "reviewer build-provenance trust requires both a pinned signer "
                "fingerprint and at least one expected subject SHA-256"
            ],
            "mode": "invalid",
            "entries": [],
            "semantic_hash": None,
            "reviewer_expectations": {
                "applied": True,
                "build_provenance_fingerprint": (
                    expected_build_provenance_fingerprint
                ),
                "subject_sha256": reviewer_subjects,
            },
        }

    reviewer_requires_build = reviewer_has_fingerprint and reviewer_has_subjects

    if not provenance_names:
        if reviewer_requires_build:
            return {
                "valid": False,
                "errors": [
                    "reviewer requires external build provenance but the package has none"
                ],
                "mode": "invalid",
                "entries": [],
                "semantic_hash": None,
            }
        return {
            "valid": True,
            "errors": [],
            "mode": "none",
            "entries": [],
            "semantic_hash": None,
            "reviewer_expectations": {
                "applied": False,
                "build_provenance_fingerprint": None,
                "subject_sha256": [],
            },
        }

    errors: list[str] = []
    raw_index = package_files.get(PROVENANCE_INDEX_PATH_V06)
    if not isinstance(raw_index, bytes):
        return {
            "valid": False,
            "errors": [
                "provenance namespace is present without provenance/index.json"
            ],
            "mode": "invalid",
            "entries": [],
            "semantic_hash": None,
        }

    try:
        index_value = _strict_json_bytes(
            raw_index,
            label="provenance index",
        )
        index = validate_provenance_index_v06(index_value)
        if canonicalize_jcs_bytes(index) != raw_index:
            raise V06ProvenanceError(
                "provenance index bytes are not canonical JCS"
            )
    except V06ProvenanceError as exc:
        return {
            "valid": False,
            "errors": [str(exc)],
            "mode": "invalid",
            "entries": [],
            "semantic_hash": None,
        }

    expected_names = {PROVENANCE_INDEX_PATH_V06}
    verified_entries: list[dict[str, Any]] = []
    for entry in index["entries"]:
        kind = entry["kind"]
        path = entry["path"]
        expected_names.add(path)
        raw = package_files.get(path)
        if not isinstance(raw, bytes):
            errors.append(f"provenance entry is missing signed bytes: {path}")
            continue
        if len(raw) != entry["size"]:
            errors.append(f"provenance size mismatch: {path}")
        if hashlib.sha256(raw).hexdigest() != entry["sha256"]:
            errors.append(f"provenance SHA-256 mismatch: {path}")

        if kind == "sbom":
            try:
                value = _strict_json_bytes(raw, label="SBOM")
                detected = detect_sbom_format_v06(value)
                if detected != entry["format"]:
                    errors.append(
                        "SBOM format differs from provenance index: "
                        f"{detected!r} != {entry['format']!r}"
                    )
            except V06ProvenanceError as exc:
                errors.append(str(exc))
            verified_entries.append(
                {
                    "kind": kind,
                    "format": entry["format"],
                    "sha256": entry["sha256"],
                }
            )
            continue

        if kind == "build_provenance":
            key_path = entry["public_key_path"]
            expected_names.add(key_path)
            key_raw = package_files.get(key_path)
            if not isinstance(key_raw, bytes):
                errors.append(
                    f"build-provenance public key is missing: {key_path}"
                )
                continue
            try:
                verified = verify_dsse_build_provenance_v06(
                    raw,
                    key_raw,
                    expected_fingerprint=entry[
                        "public_key_fingerprint"
                    ],
                    expected_subject_sha256=entry[
                        "expected_subject_sha256"
                    ],
                )
                if verified["payload_type"] != entry["payload_type"]:
                    errors.append(
                        "build-provenance payload type differs from index"
                    )
                if verified["predicate_type"] != entry["predicate_type"]:
                    errors.append(
                        "build-provenance predicate type differs from index"
                    )
                if (
                    verified["attested_subject_sha256"]
                    != entry["attested_subject_sha256"]
                ):
                    errors.append(
                        "build-provenance attested subjects differ from index"
                    )
                if (
                    expected_build_provenance_fingerprint is not None
                    and verified["public_key_fingerprint"]
                    != expected_build_provenance_fingerprint
                ):
                    errors.append(
                        "build-provenance signer does not match reviewer-pinned fingerprint"
                    )
                missing_reviewer_subjects = [
                    digest
                    for digest in reviewer_subjects
                    if digest not in verified["attested_subject_sha256"]
                ]
                if missing_reviewer_subjects:
                    errors.append(
                        "build provenance does not attest reviewer-required subject SHA-256: "
                        + ", ".join(missing_reviewer_subjects)
                    )
            except V06ProvenanceError as exc:
                errors.append(str(exc))
            verified_entries.append(
                {
                    "kind": kind,
                    "format": entry["format"],
                    "sha256": entry["sha256"],
                    "public_key_fingerprint": entry[
                        "public_key_fingerprint"
                    ],
                    "expected_subject_sha256": entry[
                        "expected_subject_sha256"
                    ],
                }
            )

    actual_names = set(provenance_names)
    has_build_provenance = any(
        entry.get("kind") == "build_provenance"
        for entry in index["entries"]
        if isinstance(entry, Mapping)
    )
    if reviewer_requires_build and not has_build_provenance:
        errors.append(
            "reviewer requires external build provenance but the provenance index has none"
        )

    if actual_names != expected_names:
        missing = sorted(expected_names - actual_names)
        unexpected = sorted(actual_names - expected_names)
        errors.append(
            "provenance namespace does not exactly match index: "
            f"missing={missing} unexpected={unexpected}"
        )

    return {
        "valid": not errors,
        "errors": errors,
        "mode": "bound" if not errors else "invalid",
        "entries": verified_entries,
        "semantic_hash": index["semantic_hash"],
        "reviewer_expectations": {
            "applied": reviewer_requires_build,
            "build_provenance_fingerprint": (
                expected_build_provenance_fingerprint
            ),
            "subject_sha256": reviewer_subjects,
        },
    }


def load_provenance_index_file_v06(path: str | Path) -> dict[str, Any]:
    raw = _read_regular_file(
        path,
        label="provenance index",
        max_bytes=MAX_SBOM_BYTES_V06,
    )
    value = _strict_json_bytes(raw, label="provenance index")
    return validate_provenance_index_v06(value)


def diff_provenance_indexes_v06(
    left: Mapping[str, Any],
    right: Mapping[str, Any],
) -> dict[str, Any]:
    left_index = validate_provenance_index_v06(left)
    right_index = validate_provenance_index_v06(right)

    left_entries = {entry["kind"]: entry for entry in left_index["entries"]}
    right_entries = {entry["kind"]: entry for entry in right_index["entries"]}
    left_kinds = set(left_entries)
    right_kinds = set(right_entries)

    changed: dict[str, Any] = {}
    for kind in sorted(left_kinds & right_kinds):
        left_entry = left_entries[kind]
        right_entry = right_entries[kind]
        if left_entry != right_entry:
            changed[kind] = {
                "same_sha256": left_entry.get("sha256")
                == right_entry.get("sha256"),
                "left_sha256": left_entry.get("sha256"),
                "right_sha256": right_entry.get("sha256"),
                "format_changed": left_entry.get("format")
                != right_entry.get("format"),
                "signer_changed": left_entry.get(
                    "public_key_fingerprint"
                )
                != right_entry.get("public_key_fingerprint"),
                "expected_subject_changed": left_entry.get(
                    "expected_subject_sha256"
                )
                != right_entry.get("expected_subject_sha256"),
            }

    return {
        "format": "pcs-provenance-diff-v1",
        "same_semantic_hash": left_index["semantic_hash"]
        == right_index["semantic_hash"],
        "kinds_added": sorted(right_kinds - left_kinds),
        "kinds_removed": sorted(left_kinds - right_kinds),
        "changed": changed,
    }


def diff_provenance_files_v06(
    left_path: str | Path,
    right_path: str | Path,
) -> dict[str, Any]:
    return diff_provenance_indexes_v06(
        load_provenance_index_file_v06(left_path),
        load_provenance_index_file_v06(right_path),
    )
