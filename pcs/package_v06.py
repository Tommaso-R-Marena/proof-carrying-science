from __future__ import annotations

from pathlib import PurePosixPath
from typing import Any
import unicodedata

from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

from .canonical_json import JCS_PROFILE
from .certificate_v06 import SPEC_VERSION_V06, verify_certificate_hashes_v06
from .crypto_domains_v06 import (
    CERTIFICATE_INTEGRITY_DOMAIN,
    CERTIFICATE_SEMANTIC_DOMAIN,
    PACKAGE_SIGNATURE_DOMAIN,
)
from .schema_validation import (
    SchemaValidationError,
    validate_v06_package_manifest_shape,
)
from .signing_v06 import sign_jcs_payload, verify_jcs_signature


PACKAGE_FORMAT_V06 = "pcs-package-v2"

_WINDOWS_FORBIDDEN_V06 = set('<>:"|?*')
_WINDOWS_RESERVED_V06 = {
    "con", "prn", "aux", "nul",
    *(f"com{i}" for i in range(1, 10)),
    *(f"lpt{i}" for i in range(1, 10)),
}


class V06PackageError(ValueError):
    pass


def validate_package_namespace_v06(files: dict[str, Any]) -> None:
    """Require one canonical, portable interpretation of every signed file name."""
    if not isinstance(files, dict):
        raise V06PackageError("v0.6 package files must be an object")

    portable: dict[str, str] = {}
    names = set(files)
    for name in names:
        if not isinstance(name, str) or not name:
            raise V06PackageError("v0.6 package member names must be non-empty strings")
        if "\\" in name:
            raise V06PackageError(f"v0.6 package member uses backslash: {name!r}")

        path = PurePosixPath(name)
        canonical = path.as_posix()
        if path.is_absolute() or canonical != name or name.endswith("/"):
            raise V06PackageError(f"non-canonical v0.6 package member: {name!r}")
        if any(part in ("", ".", "..") for part in path.parts):
            raise V06PackageError(f"unsafe v0.6 package member: {name!r}")

        portable_parts: list[str] = []
        for segment in path.parts:
            nfc = unicodedata.normalize("NFC", segment)
            if segment != nfc:
                raise V06PackageError(
                    f"non-NFC v0.6 package member segment is not portable: {segment!r}"
                )
            if any(
                ord(ch) < 32 or ord(ch) == 127 or ch in _WINDOWS_FORBIDDEN_V06
                for ch in segment
            ):
                raise V06PackageError(
                    f"v0.6 package member contains non-portable characters: {segment!r}"
                )
            if segment.endswith((" ", ".")):
                raise V06PackageError(
                    f"v0.6 package member has trailing space/dot: {segment!r}"
                )
            stem = segment.split(".", 1)[0].casefold()
            if stem in _WINDOWS_RESERVED_V06:
                raise V06PackageError(
                    f"v0.6 package member uses Windows-reserved filename: {segment!r}"
                )
            portable_parts.append(nfc.casefold())

        key = "/".join(portable_parts)
        other = portable.get(key)
        if other is not None and other != name:
            raise V06PackageError(
                f"cross-platform v0.6 package name collision: {other!r} vs {name!r}"
            )
        portable[key] = name

    # A file cannot simultaneously act as a parent directory of another file.
    for name in names:
        parts = PurePosixPath(name).parts
        for i in range(1, len(parts)):
            prefix = PurePosixPath(*parts[:i]).as_posix()
            if prefix in names:
                raise V06PackageError(
                    f"v0.6 package namespace collision: file {prefix!r} "
                    f"is parent of {name!r}"
                )


def _validate_package_manifest_contract_v06(manifest: dict[str, Any]) -> None:
    try:
        validate_v06_package_manifest_shape(manifest)
    except SchemaValidationError as exc:
        raise V06PackageError(str(exc)) from exc
    validate_package_namespace_v06(manifest.get("files", {}))


def build_package_manifest_v06(
    certificate: dict[str, Any],
    files: dict[str, dict[str, int | str]],
) -> dict[str, Any]:
    checked = verify_certificate_hashes_v06(certificate)
    if not checked["valid"]:
        raise V06PackageError(
            f"cannot build package manifest for invalid v0.6 certificate: {checked['errors']}"
        )
    manifest = {
        "package_format": PACKAGE_FORMAT_V06,
        "canonical_json_profile": JCS_PROFILE,
        "certificate_spec_version": SPEC_VERSION_V06,
        "certificate_semantic_hash_format": CERTIFICATE_SEMANTIC_DOMAIN,
        "certificate_integrity_hash_format": CERTIFICATE_INTEGRITY_DOMAIN,
        "certificate_semantic_hash": certificate["semantic_hash"],
        "certificate_integrity_hash": certificate["integrity_hash"],
        "files": files,
    }
    _validate_package_manifest_contract_v06(manifest)
    return manifest


def verify_package_manifest_v06(
    manifest: dict[str, Any],
    certificate: dict[str, Any],
) -> dict[str, Any]:
    errors: list[str] = []
    try:
        _validate_package_manifest_contract_v06(manifest)
    except V06PackageError as exc:
        return {"valid": False, "errors": [str(exc)]}

    certificate_check = verify_certificate_hashes_v06(certificate)
    if not certificate_check["valid"]:
        errors.extend(certificate_check["errors"])
    if manifest.get("certificate_semantic_hash") != certificate.get("semantic_hash"):
        errors.append("v0.6 package manifest certificate semantic hash mismatch")
    if manifest.get("certificate_integrity_hash") != certificate.get("integrity_hash"):
        errors.append("v0.6 package manifest certificate integrity hash mismatch")

    return {"valid": not errors, "errors": errors}


def sign_package_manifest_v06(
    manifest: dict[str, Any],
    private_key: Ed25519PrivateKey,
) -> dict[str, Any]:
    _validate_package_manifest_contract_v06(manifest)
    return sign_jcs_payload(PACKAGE_SIGNATURE_DOMAIN, manifest, private_key)


def verify_package_signature_v06(
    manifest: dict[str, Any],
    record: dict[str, Any],
    public_key: Ed25519PublicKey,
    *,
    expected_fingerprint: str | None = None,
) -> dict[str, Any]:
    try:
        _validate_package_manifest_contract_v06(manifest)
    except V06PackageError as exc:
        return {"valid": False, "errors": [str(exc)]}

    envelope = record.get("payload")
    if not isinstance(envelope, dict) or envelope.get("payload") != manifest:
        return {
            "valid": False,
            "errors": ["signature payload does not match v0.6 package manifest"],
        }

    return verify_jcs_signature(
        record,
        public_key,
        expected_domain=PACKAGE_SIGNATURE_DOMAIN,
        expected_fingerprint=expected_fingerprint,
    )
