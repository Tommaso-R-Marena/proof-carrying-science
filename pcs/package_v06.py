from __future__ import annotations

from pathlib import Path, PurePosixPath
from typing import Any
import unicodedata

from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

from .canonical_json import CanonicalJSONError, JCS_PROFILE, parse_jcs_json
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
from .hashing import sha256_file


PACKAGE_FORMAT_V06 = "pcs-package-v2"
EXCLUDED_PACKAGE_FILES_V06 = {"package_manifest.json", "package_signature.json"}
MAX_PACKAGE_FILES_V06 = 1000
MAX_PACKAGE_TOTAL_BYTES_V06 = 100 * 1024 * 1024
MAX_PACKAGE_SINGLE_FILE_V06 = 50 * 1024 * 1024
_PRIVATE_KEY_MARKERS_V06 = (
    b"-----BEGIN PRIVATE KEY-----",
    b"-----BEGIN ENCRYPTED PRIVATE KEY-----",
    b"-----BEGIN OPENSSH PRIVATE KEY-----",
    b"-----BEGIN RSA PRIVATE KEY-----",
    b"-----BEGIN EC PRIVATE KEY-----",
)

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


def _load_certificate_file_v06(path: Path) -> dict[str, Any]:
    try:
        value = parse_jcs_json(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, CanonicalJSONError) as exc:
        raise V06PackageError(f"invalid v0.6 certificate JSON: {type(exc).__name__}: {exc}") from exc
    if not isinstance(value, dict):
        raise V06PackageError("v0.6 certificate root must be an object")
    checked = verify_certificate_hashes_v06(value)
    if not checked["valid"]:
        raise V06PackageError(f"invalid v0.6 certificate: {checked['errors']}")
    return value


def _contains_private_key_material_v06(path: Path) -> bool:
    overlap = max(len(marker) for marker in _PRIVATE_KEY_MARKERS_V06) - 1
    tail = b""
    with path.open("rb") as fh:
        while True:
            chunk = fh.read(1024 * 1024)
            if not chunk:
                return False
            data = tail + chunk
            if any(marker in data for marker in _PRIVATE_KEY_MARKERS_V06):
                return True
            tail = data[-overlap:] if overlap else b""


def _inventory_package_directory_v06(root: Path) -> dict[str, dict[str, int | str]]:
    staged = sorted(root.rglob("*"))
    symlinks = [p.relative_to(root).as_posix() for p in staged if p.is_symlink()]
    if symlinks:
        raise V06PackageError(f"refusing staged symlinks in v0.6 package: {symlinks}")

    regular = [
        p for p in staged
        if p.is_file() and p.relative_to(root).as_posix() not in EXCLUDED_PACKAGE_FILES_V06
    ]
    if len(regular) > MAX_PACKAGE_FILES_V06:
        raise V06PackageError(
            f"v0.6 package has too many files: {len(regular)} > {MAX_PACKAGE_FILES_V06}"
        )

    files: dict[str, dict[str, int | str]] = {}
    total = 0
    for path in regular:
        rel = path.relative_to(root).as_posix()
        size = path.stat().st_size
        if size > MAX_PACKAGE_SINGLE_FILE_V06:
            raise V06PackageError(f"v0.6 package member too large: {rel!r}")
        total += size
        if total > MAX_PACKAGE_TOTAL_BYTES_V06:
            raise V06PackageError(
                f"v0.6 package exceeds total byte limit: {total} > {MAX_PACKAGE_TOTAL_BYTES_V06}"
            )
        if _contains_private_key_material_v06(path):
            raise V06PackageError(
                f"refusing apparent private-key material in v0.6 package: {rel!r}"
            )
        files[rel] = {"sha256": sha256_file(path), "size": size}

    validate_package_namespace_v06(files)
    return files


def build_package_manifest_from_directory_v06(root: str | Path) -> dict[str, Any]:
    root_path = Path(root).resolve()
    if not root_path.is_dir():
        raise V06PackageError(f"v0.6 package root is not a directory: {root_path}")
    certificate_path = root_path / "certificate.json"
    if not certificate_path.is_file():
        raise V06PackageError("v0.6 package lacks certificate.json")
    certificate = _load_certificate_file_v06(certificate_path)
    files = _inventory_package_directory_v06(root_path)
    if "certificate.json" not in files:
        raise V06PackageError("v0.6 package inventory omitted certificate.json")
    return build_package_manifest_v06(certificate, files)


def verify_package_directory_v06(
    root: str | Path,
    manifest: dict[str, Any],
) -> dict[str, Any]:
    root_path = Path(root).resolve()
    errors: list[str] = []
    if not root_path.is_dir():
        return {"valid": False, "errors": [f"v0.6 package root is not a directory: {root_path}"]}

    try:
        _validate_package_manifest_contract_v06(manifest)
        actual_files = _inventory_package_directory_v06(root_path)
    except V06PackageError as exc:
        return {"valid": False, "errors": [str(exc)]}

    expected_files = manifest.get("files", {})
    expected_names = set(expected_files)
    actual_names = set(actual_files)
    missing = sorted(expected_names - actual_names)
    unexpected = sorted(actual_names - expected_names)
    if missing:
        errors.append(f"v0.6 package files missing: {missing}")
    if unexpected:
        errors.append(f"unexpected v0.6 package files: {unexpected}")

    for name in sorted(expected_names & actual_names):
        expected = expected_files[name]
        actual = actual_files[name]
        if expected.get("sha256") != actual.get("sha256"):
            errors.append(f"v0.6 package hash mismatch: {name}")
        if expected.get("size") != actual.get("size"):
            errors.append(f"v0.6 package size mismatch: {name}")

    certificate_path = root_path / "certificate.json"
    try:
        certificate = _load_certificate_file_v06(certificate_path)
        bound = verify_package_manifest_v06(manifest, certificate)
        errors.extend(bound["errors"])
    except V06PackageError as exc:
        errors.append(str(exc))

    return {"valid": not errors, "errors": errors}


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
