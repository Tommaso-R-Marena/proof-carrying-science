from __future__ import annotations

from typing import Any

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


class V06PackageError(ValueError):
    pass


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
    try:
        validate_v06_package_manifest_shape(manifest)
    except SchemaValidationError as exc:
        raise V06PackageError(str(exc)) from exc
    return manifest


def verify_package_manifest_v06(
    manifest: dict[str, Any],
    certificate: dict[str, Any],
) -> dict[str, Any]:
    errors: list[str] = []
    try:
        validate_v06_package_manifest_shape(manifest)
    except SchemaValidationError as exc:
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
    try:
        validate_v06_package_manifest_shape(manifest)
    except SchemaValidationError as exc:
        raise V06PackageError(str(exc)) from exc
    return sign_jcs_payload(PACKAGE_SIGNATURE_DOMAIN, manifest, private_key)


def verify_package_signature_v06(
    manifest: dict[str, Any],
    record: dict[str, Any],
    public_key: Ed25519PublicKey,
    *,
    expected_fingerprint: str | None = None,
) -> dict[str, Any]:
    try:
        validate_v06_package_manifest_shape(manifest)
    except SchemaValidationError as exc:
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
