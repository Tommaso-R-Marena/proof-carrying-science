from __future__ import annotations

from copy import deepcopy
from typing import Any

from .canonical_json import JCS_PROFILE, load_jcs_json_file, write_jcs_json_file
from .crypto_domains_v06 import (
    CERTIFICATE_INTEGRITY_DOMAIN,
    CERTIFICATE_SEMANTIC_DOMAIN,
    domain_sha256,
)
from .schema_validation import SchemaValidationError, validate_v06_certificate_shape


SPEC_VERSION_V06 = "pcs-0.6"


class V06CertificateError(ValueError):
    pass


def semantic_projection_v06(certificate: dict[str, Any]) -> dict[str, Any]:
    out = deepcopy(certificate)
    out.pop("generated_at", None)
    out.pop("semantic_hash", None)
    out.pop("integrity_hash", None)
    return out


def integrity_projection_v06(certificate: dict[str, Any]) -> dict[str, Any]:
    out = deepcopy(certificate)
    out.pop("integrity_hash", None)
    return out


def finalize_certificate_hashes_v06(certificate: dict[str, Any]) -> dict[str, Any]:
    out = deepcopy(certificate)
    if out.get("spec_version") != SPEC_VERSION_V06:
        raise V06CertificateError("v0.6 certificate must use spec_version pcs-0.6")
    if out.get("canonical_json_profile") != JCS_PROFILE:
        raise V06CertificateError("v0.6 certificate must declare pcs-jcs-rfc8785-v1")
    if out.get("semantic_hash_format") != CERTIFICATE_SEMANTIC_DOMAIN:
        raise V06CertificateError("v0.6 certificate semantic hash domain mismatch")
    if out.get("integrity_hash_format") != CERTIFICATE_INTEGRITY_DOMAIN:
        raise V06CertificateError("v0.6 certificate integrity hash domain mismatch")

    out["semantic_hash"] = domain_sha256(
        CERTIFICATE_SEMANTIC_DOMAIN,
        semantic_projection_v06(out),
    )
    out["integrity_hash"] = domain_sha256(
        CERTIFICATE_INTEGRITY_DOMAIN,
        integrity_projection_v06(out),
    )
    try:
        validate_v06_certificate_shape(out)
    except SchemaValidationError as exc:
        raise V06CertificateError(str(exc)) from exc
    return out


def verify_certificate_hashes_v06(certificate: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    try:
        validate_v06_certificate_shape(certificate)
    except SchemaValidationError as exc:
        return {"valid": False, "errors": [str(exc)]}

    expected_semantic = domain_sha256(
        CERTIFICATE_SEMANTIC_DOMAIN,
        semantic_projection_v06(certificate),
    )
    expected_integrity = domain_sha256(
        CERTIFICATE_INTEGRITY_DOMAIN,
        integrity_projection_v06(certificate),
    )
    if certificate.get("semantic_hash") != expected_semantic:
        errors.append("v0.6 certificate semantic hash mismatch")
    if certificate.get("integrity_hash") != expected_integrity:
        errors.append("v0.6 certificate integrity hash mismatch")

    return {
        "valid": not errors,
        "errors": errors,
        "semantic_hash": expected_semantic,
        "integrity_hash": expected_integrity,
    }



def write_certificate_v06(path: str, certificate: dict[str, Any]) -> None:
    checked = verify_certificate_hashes_v06(certificate)
    if not checked["valid"]:
        raise V06CertificateError(
            f"refusing to write invalid v0.6 certificate: {checked['errors']}"
        )
    write_jcs_json_file(path, certificate)


def load_certificate_v06(path: str) -> dict[str, Any]:
    value = load_jcs_json_file(path)
    if not isinstance(value, dict):
        raise V06CertificateError("v0.6 certificate root must be an object")
    checked = verify_certificate_hashes_v06(value)
    if not checked["valid"]:
        raise V06CertificateError(f"invalid v0.6 certificate: {checked['errors']}")
    return value
