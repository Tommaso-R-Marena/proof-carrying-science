from __future__ import annotations

import hashlib
from collections.abc import Mapping
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from .canonical_json import CanonicalJSONError, canonicalize_jcs_bytes, parse_jcs_json
from .certificate_v06 import verify_certificate_hashes_v06
from .package_v06 import (
    MAX_PACKAGE_FILES_V06,
    MAX_PACKAGE_SINGLE_FILE_V06,
    MAX_PACKAGE_TOTAL_BYTES_V06,
    V06PackageError,
    validate_package_namespace_v06,
    verify_package_manifest_v06,
    verify_package_signature_v06,
)
from .schema_validation import (
    SchemaValidationError,
    validate_v06_package_manifest_shape,
    validate_v06_signature_record_shape,
)
from .signing_v06 import verify_certificate_signature_v06


UTF8_BOM = b"\xef\xbb\xbf"
MAX_CERTIFICATE_BYTES_V06 = 10 * 1024 * 1024
MAX_SIGNATURE_RECORD_BYTES_V06 = 16 * 1024 * 1024
MAX_PACKAGE_MANIFEST_BYTES_V06 = 10 * 1024 * 1024


class V06ByteContractError(ValueError):
    pass


def _parse_canonical_json_bytes(
    raw: bytes,
    *,
    label: str,
    max_bytes: int,
) -> Any:
    if not isinstance(raw, bytes):
        raise V06ByteContractError(f"{label} must be supplied as immutable bytes")
    if len(raw) > max_bytes:
        raise V06ByteContractError(
            f"{label} exceeds byte limit: {len(raw)} > {max_bytes}"
        )
    if raw.startswith(UTF8_BOM):
        raise V06ByteContractError(f"{label} must not contain a UTF-8 BOM")
    try:
        text = raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise V06ByteContractError(f"{label} is not valid UTF-8: {exc}") from exc
    try:
        value = parse_jcs_json(text)
        canonical = canonicalize_jcs_bytes(value)
    except (CanonicalJSONError, RecursionError) as exc:
        raise V06ByteContractError(f"{label} is not valid strict JCS JSON: {exc}") from exc
    if canonical != raw:
        raise V06ByteContractError(
            f"{label} is valid JSON but not the exact canonical JCS byte representation"
        )
    return value


def parse_certificate_bytes_v06(raw: bytes) -> dict[str, Any]:
    value = _parse_canonical_json_bytes(
        raw,
        label="v0.6 certificate",
        max_bytes=MAX_CERTIFICATE_BYTES_V06,
    )
    if not isinstance(value, dict):
        raise V06ByteContractError("v0.6 certificate root must be an object")
    checked = verify_certificate_hashes_v06(value)
    if not checked["valid"]:
        raise V06ByteContractError(
            "v0.6 certificate hash/schema verification failed: "
            + "; ".join(checked["errors"])
        )
    return value


def parse_signature_record_bytes_v06(raw: bytes) -> dict[str, Any]:
    value = _parse_canonical_json_bytes(
        raw,
        label="v0.6 signature record",
        max_bytes=MAX_SIGNATURE_RECORD_BYTES_V06,
    )
    if not isinstance(value, dict):
        raise V06ByteContractError("v0.6 signature record root must be an object")
    try:
        validate_v06_signature_record_shape(value)
    except SchemaValidationError as exc:
        raise V06ByteContractError(str(exc)) from exc
    return value


def parse_package_manifest_bytes_v06(raw: bytes) -> dict[str, Any]:
    value = _parse_canonical_json_bytes(
        raw,
        label="v0.6 package manifest",
        max_bytes=MAX_PACKAGE_MANIFEST_BYTES_V06,
    )
    if not isinstance(value, dict):
        raise V06ByteContractError("v0.6 package manifest root must be an object")
    try:
        validate_v06_package_manifest_shape(value)
        validate_package_namespace_v06(value.get("files", {}))
    except (SchemaValidationError, V06PackageError) as exc:
        raise V06ByteContractError(str(exc)) from exc
    return value


def verify_signed_certificate_bytes_v06(
    certificate_bytes: bytes,
    signature_record_bytes: bytes,
    public_key: Ed25519PublicKey,
    *,
    expected_fingerprint: str | None = None,
) -> dict[str, Any]:
    try:
        certificate = parse_certificate_bytes_v06(certificate_bytes)
        record = parse_signature_record_bytes_v06(signature_record_bytes)
    except V06ByteContractError as exc:
        return {"valid": False, "errors": [str(exc)]}

    signature = verify_certificate_signature_v06(
        certificate,
        record,
        public_key,
        expected_fingerprint=expected_fingerprint,
    )
    return {
        "valid": signature["valid"],
        "errors": list(signature["errors"]),
        "certificate_semantic_hash": certificate.get("semantic_hash"),
        "certificate_integrity_hash": certificate.get("integrity_hash"),
        "certificate_byte_sha256": hashlib.sha256(certificate_bytes).hexdigest(),
        "public_key_fingerprint": signature.get("public_key_fingerprint"),
    }


def verify_package_file_map_v06(
    manifest_bytes: bytes,
    certificate_bytes: bytes,
    signature_record_bytes: bytes,
    files: Mapping[str, bytes],
    public_key: Ed25519PublicKey,
    *,
    expected_fingerprint: str | None = None,
) -> dict[str, Any]:
    """Verify the complete signed package contract over exact member bytes.

    The file map contains signed package members only. package_manifest.json and
    package_signature.json are supplied separately because the manifest excludes
    those self-referential records.
    """
    errors: list[str] = []
    try:
        manifest = parse_package_manifest_bytes_v06(manifest_bytes)
        certificate = parse_certificate_bytes_v06(certificate_bytes)
        signature_record = parse_signature_record_bytes_v06(signature_record_bytes)
    except V06ByteContractError as exc:
        return {"valid": False, "errors": [str(exc)]}

    if not isinstance(files, Mapping):
        return {"valid": False, "errors": ["v0.6 package file map must be a mapping"]}

    expected_files = manifest.get("files", {})
    names = list(files.keys())
    if any(not isinstance(name, str) for name in names):
        errors.append("v0.6 package file-map keys must be strings")
    else:
        try:
            validate_package_namespace_v06({name: expected_files.get(name, {}) for name in names})
        except V06PackageError as exc:
            errors.append(str(exc))

    expected_names = set(expected_files)
    actual_names = set(names)
    missing = sorted(expected_names - actual_names)
    unexpected = sorted(actual_names - expected_names)
    if missing:
        errors.append(f"v0.6 package file map is missing signed members: {missing}")
    if unexpected:
        errors.append(f"v0.6 package file map contains unsigned members: {unexpected}")

    if len(actual_names) > MAX_PACKAGE_FILES_V06:
        errors.append("v0.6 package file map exceeds member-count limit")

    total = 0
    for name in sorted(expected_names & actual_names):
        raw = files[name]
        if not isinstance(raw, bytes):
            errors.append(f"v0.6 package member {name!r} must be immutable bytes")
            continue
        size = len(raw)
        total += size
        if size > MAX_PACKAGE_SINGLE_FILE_V06:
            errors.append(f"v0.6 package member too large: {name!r}")
        meta = expected_files[name]
        if meta.get("size") != size:
            errors.append(f"v0.6 package size mismatch: {name}")
        digest = hashlib.sha256(raw).hexdigest()
        if meta.get("sha256") != digest:
            errors.append(f"v0.6 package hash mismatch: {name}")

    if total > MAX_PACKAGE_TOTAL_BYTES_V06:
        errors.append("v0.6 package file map exceeds total byte limit")

    if files.get("certificate.json") != certificate_bytes:
        errors.append("certificate.json member is not byte-identical to verified certificate bytes")

    binding = verify_package_manifest_v06(manifest, certificate)
    errors.extend(binding["errors"])

    signature = verify_package_signature_v06(
        manifest,
        signature_record,
        public_key,
        expected_fingerprint=expected_fingerprint,
    )
    errors.extend(signature["errors"])

    return {
        "valid": not errors,
        "errors": errors,
        "manifest_byte_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
        "certificate_byte_sha256": hashlib.sha256(certificate_bytes).hexdigest(),
        "certificate_semantic_hash": certificate.get("semantic_hash"),
        "certificate_integrity_hash": certificate.get("integrity_hash"),
        "public_key_fingerprint": signature.get("public_key_fingerprint"),
        "verified_members": sorted(expected_names & actual_names),
    }
