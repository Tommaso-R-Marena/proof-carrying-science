from __future__ import annotations

import hashlib
import re
from copy import deepcopy
from typing import Any, Mapping

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

from .jsonio import StrictJSONError, strict_json_loads
from .signing import public_key_fingerprint
from .signing_v06 import sign_jcs_payload, verify_jcs_signature


EXTERNAL_VALIDATOR_RECEIPT_FORMAT_V06 = "pcs-external-validator-receipt-v1"
EXTERNAL_VALIDATOR_TRUST_CONTRACT_FORMAT_V06 = (
    "pcs-external-validator-trust-contract-v1"
)
EXTERNAL_VALIDATOR_TRUST_MODEL_V06 = "pinned-ed25519-validator-receipt-v1"
EXTERNAL_VALIDATOR_SIGNATURE_DOMAIN_V06 = (
    "pcs-external-validator-receipt-signature-v1"
)
EXTERNAL_VALIDATOR_CHECK_TYPES_V06 = frozenset(
    {
        "external_empirical_validation",
        "external_statistical_validation",
    }
)

_SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
_SHA256 = re.compile(r"^[a-f0-9]{64}$")

_REQUIRED_ADAPTER_FIELDS = (
    "receipt_format",
    "trust_model",
    "receipt_artifact",
    "validator_public_key_artifact",
    "validator_public_key_fingerprint",
    "bound_artifact_ids",
)

EXTERNAL_VALIDATOR_TRUST_CONTRACT_V06: dict[str, Any] = {
    "format": EXTERNAL_VALIDATOR_TRUST_CONTRACT_FORMAT_V06,
    "pcs_verifies": [
        "ed25519_receipt_signature",
        "pinned_validator_key_fingerprint",
        "exact_external_predicate",
        "exact_artifact_sha256_bindings",
        "reported_outcome",
    ],
    "pcs_does_not_verify": [
        "validator_algorithm_correctness",
        "validator_policy_scientific_adequacy",
        "biological_or_clinical_truth",
    ],
    "pass_meaning": (
        "PASS means only that the pinned validator key signed PASS for the exact "
        "predicate and artifact bytes named by this receipt."
    ),
}


class V06ExternalValidatorError(ValueError):
    pass


def _safe_id(value: Any, *, label: str) -> str:
    if not isinstance(value, str) or not _SAFE_ID.fullmatch(value):
        raise V06ExternalValidatorError(
            f"{label} must be a PCS-safe identifier"
        )
    return value


def _external_predicate(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise V06ExternalValidatorError(
            "external validator predicate must be an object"
        )
    predicate = deepcopy(dict(value))
    if set(predicate) != {"type", "namespace", "proposition"}:
        raise V06ExternalValidatorError(
            "external validator predicate must contain exactly "
            "type/namespace/proposition"
        )
    if predicate.get("type") != "external":
        raise V06ExternalValidatorError(
            "external validator predicate.type must be 'external'"
        )
    namespace = predicate.get("namespace")
    proposition = predicate.get("proposition")
    if (
        not isinstance(namespace, str)
        or not namespace
        or len(namespace) > 256
    ):
        raise V06ExternalValidatorError(
            "external validator predicate namespace is invalid"
        )
    if (
        not isinstance(proposition, str)
        or not proposition
        or len(proposition) > 16384
    ):
        raise V06ExternalValidatorError(
            "external validator predicate proposition is invalid"
        )
    return predicate


def external_validator_adapter_missing_fields_v06(
    check: Mapping[str, Any],
) -> list[str]:
    return [
        field
        for field in _REQUIRED_ADAPTER_FIELDS
        if field not in check
    ]


def normalize_external_validator_check_spec_v06(
    check: Mapping[str, Any],
) -> dict[str, Any]:
    allowed_keys = {
        "id",
        "type",
        "claim_ids",
        "validator",
        "predicate",
        "receipt_format",
        "trust_model",
        "receipt_artifact",
        "validator_public_key_artifact",
        "validator_public_key_fingerprint",
        "bound_artifact_ids",
    }
    unexpected = sorted(set(check) - allowed_keys)
    if unexpected:
        raise V06ExternalValidatorError(
            f"external validator check contains forbidden fields: {unexpected}"
        )

    check_type = check.get("type")
    if check_type not in EXTERNAL_VALIDATOR_CHECK_TYPES_V06:
        raise V06ExternalValidatorError(
            f"unsupported signed external-validator check type: {check_type!r}"
        )

    missing = external_validator_adapter_missing_fields_v06(check)
    if missing:
        raise V06ExternalValidatorError(
            "external validator adapter is incomplete; missing "
            + ", ".join(missing)
        )

    validator = check.get("validator")
    if (
        not isinstance(validator, str)
        or not validator.strip()
        or len(validator) > 512
    ):
        raise V06ExternalValidatorError(
            "external validator identity must be a non-empty string"
        )

    if check.get("receipt_format") != EXTERNAL_VALIDATOR_RECEIPT_FORMAT_V06:
        raise V06ExternalValidatorError(
            "unsupported external validator receipt format"
        )
    if check.get("trust_model") != EXTERNAL_VALIDATOR_TRUST_MODEL_V06:
        raise V06ExternalValidatorError(
            "unsupported external validator trust model"
        )

    receipt_artifact = _safe_id(
        check.get("receipt_artifact"),
        label="receipt_artifact",
    )
    key_artifact = _safe_id(
        check.get("validator_public_key_artifact"),
        label="validator_public_key_artifact",
    )
    if receipt_artifact == key_artifact:
        raise V06ExternalValidatorError(
            "receipt artifact and validator public-key artifact must differ"
        )

    fingerprint = check.get("validator_public_key_fingerprint")
    if (
        not isinstance(fingerprint, str)
        or not _SHA256.fullmatch(fingerprint)
    ):
        raise V06ExternalValidatorError(
            "validator_public_key_fingerprint must be 64 lowercase hex characters"
        )

    raw_bound = check.get("bound_artifact_ids")
    if (
        not isinstance(raw_bound, list)
        or not raw_bound
        or not all(isinstance(item, str) for item in raw_bound)
    ):
        raise V06ExternalValidatorError(
            "bound_artifact_ids must be a non-empty array of PCS artifact IDs"
        )
    bound = [
        _safe_id(item, label="bound_artifact_id")
        for item in raw_bound
    ]
    if len(bound) != len(set(bound)):
        raise V06ExternalValidatorError(
            "bound_artifact_ids must not contain duplicates"
        )
    if receipt_artifact in bound or key_artifact in bound:
        raise V06ExternalValidatorError(
            "receipt/key artifacts must not be self-included in bound_artifact_ids"
        )

    return {
        "type": check_type,
        "validator": validator,
        "predicate": _external_predicate(check.get("predicate")),
        "receipt_format": EXTERNAL_VALIDATOR_RECEIPT_FORMAT_V06,
        "trust_model": EXTERNAL_VALIDATOR_TRUST_MODEL_V06,
        "receipt_artifact": receipt_artifact,
        "validator_public_key_artifact": key_artifact,
        "validator_public_key_fingerprint": fingerprint,
        "bound_artifact_ids": sorted(bound),
    }


def is_signed_external_validator_spec_v06(
    check: Mapping[str, Any],
) -> bool:
    if check.get("type") not in EXTERNAL_VALIDATOR_CHECK_TYPES_V06:
        return False
    return not external_validator_adapter_missing_fields_v06(check)


def external_validator_artifact_ids_v06(
    spec: Mapping[str, Any],
) -> list[str]:
    normalized = normalize_external_validator_check_spec_v06(spec)
    return sorted(
        [
            *normalized["bound_artifact_ids"],
            normalized["receipt_artifact"],
            normalized["validator_public_key_artifact"],
        ]
    )


def external_validator_evidence_kind_v06(check_type: str) -> str:
    if check_type == "external_empirical_validation":
        return "empirical_validation"
    if check_type == "external_statistical_validation":
        return "statistical_validation"
    raise V06ExternalValidatorError(
        f"unsupported external validator check type: {check_type!r}"
    )


def _artifact_bindings(
    bound_artifact_ids: list[str],
    artifact_bytes: Mapping[str, bytes],
) -> list[dict[str, str]]:
    bindings: list[dict[str, str]] = []
    for artifact_id in sorted(bound_artifact_ids):
        raw = artifact_bytes.get(artifact_id)
        if not isinstance(raw, bytes):
            raise V06ExternalValidatorError(
                f"missing exact bytes for bound artifact {artifact_id!r}"
            )
        bindings.append(
            {
                "artifact_id": artifact_id,
                "sha256": hashlib.sha256(raw).hexdigest(),
            }
        )
    return bindings


def build_external_validator_receipt_payload_v06(
    *,
    check_type: str,
    validator: str,
    predicate: Mapping[str, Any],
    bound_artifact_ids: list[str],
    artifact_bytes: Mapping[str, bytes],
    outcome: str,
) -> dict[str, Any]:
    if check_type not in EXTERNAL_VALIDATOR_CHECK_TYPES_V06:
        raise V06ExternalValidatorError(
            f"unsupported external validator receipt check type: {check_type!r}"
        )
    if (
        not isinstance(validator, str)
        or not validator.strip()
        or len(validator) > 512
    ):
        raise V06ExternalValidatorError(
            "external validator identity must be a non-empty string"
        )
    if outcome not in {"PASS", "FAIL"}:
        raise V06ExternalValidatorError(
            "external validator receipt outcome must be PASS or FAIL"
        )
    normalized_bound = [
        _safe_id(item, label="bound_artifact_id")
        for item in bound_artifact_ids
    ]
    if not normalized_bound or len(normalized_bound) != len(set(normalized_bound)):
        raise V06ExternalValidatorError(
            "external validator receipt requires unique bound artifact IDs"
        )

    return {
        "format": EXTERNAL_VALIDATOR_RECEIPT_FORMAT_V06,
        "validator": validator,
        "check_type": check_type,
        "predicate": _external_predicate(predicate),
        "artifact_bindings": _artifact_bindings(
            sorted(normalized_bound),
            artifact_bytes,
        ),
        "outcome": outcome,
        "trust_contract": deepcopy(EXTERNAL_VALIDATOR_TRUST_CONTRACT_V06),
    }


def sign_external_validator_receipt_v06(
    payload: Mapping[str, Any],
    private_key: Ed25519PrivateKey,
) -> dict[str, Any]:
    _validate_receipt_payload_v06(payload)
    return sign_jcs_payload(
        EXTERNAL_VALIDATOR_SIGNATURE_DOMAIN_V06,
        dict(payload),
        private_key,
    )


def _load_public_key(raw: bytes) -> Ed25519PublicKey:
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
            raise V06ExternalValidatorError(
                "external validator public key is not Ed25519"
            )
        return key
    raise V06ExternalValidatorError(
        "cannot decode external validator Ed25519 public key"
        + (f": {'; '.join(errors)}" if errors else "")
    )


def _validate_receipt_payload_v06(
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        raise V06ExternalValidatorError(
            "external validator signed payload must be an object"
        )
    value = deepcopy(dict(payload))
    expected_keys = {
        "format",
        "validator",
        "check_type",
        "predicate",
        "artifact_bindings",
        "outcome",
        "trust_contract",
    }
    if set(value) != expected_keys:
        raise V06ExternalValidatorError(
            "external validator receipt payload has unexpected or missing fields"
        )
    if value.get("format") != EXTERNAL_VALIDATOR_RECEIPT_FORMAT_V06:
        raise V06ExternalValidatorError(
            "external validator receipt payload format mismatch"
        )
    if value.get("check_type") not in EXTERNAL_VALIDATOR_CHECK_TYPES_V06:
        raise V06ExternalValidatorError(
            "external validator receipt payload check type is unsupported"
        )
    validator = value.get("validator")
    if (
        not isinstance(validator, str)
        or not validator.strip()
        or len(validator) > 512
    ):
        raise V06ExternalValidatorError(
            "external validator receipt validator identity is invalid"
        )
    value["predicate"] = _external_predicate(value.get("predicate"))
    if value.get("outcome") not in {"PASS", "FAIL"}:
        raise V06ExternalValidatorError(
            "external validator receipt outcome must be PASS or FAIL"
        )
    if value.get("trust_contract") != EXTERNAL_VALIDATOR_TRUST_CONTRACT_V06:
        raise V06ExternalValidatorError(
            "external validator receipt trust contract is not the PCS v0.6 contract"
        )

    bindings = value.get("artifact_bindings")
    if not isinstance(bindings, list) or not bindings:
        raise V06ExternalValidatorError(
            "external validator receipt artifact_bindings must be non-empty"
        )
    normalized: list[dict[str, str]] = []
    seen: set[str] = set()
    for index, binding in enumerate(bindings):
        if (
            not isinstance(binding, Mapping)
            or set(binding) != {"artifact_id", "sha256"}
        ):
            raise V06ExternalValidatorError(
                f"external validator artifact binding {index} is malformed"
            )
        artifact_id = _safe_id(
            binding.get("artifact_id"),
            label=f"artifact binding {index} artifact_id",
        )
        digest = binding.get("sha256")
        if not isinstance(digest, str) or not _SHA256.fullmatch(digest):
            raise V06ExternalValidatorError(
                f"external validator artifact binding {artifact_id!r} has invalid SHA-256"
            )
        if artifact_id in seen:
            raise V06ExternalValidatorError(
                f"duplicate external validator artifact binding: {artifact_id}"
            )
        seen.add(artifact_id)
        normalized.append(
            {
                "artifact_id": artifact_id,
                "sha256": digest,
            }
        )
    if normalized != sorted(normalized, key=lambda item: item["artifact_id"]):
        raise V06ExternalValidatorError(
            "external validator artifact_bindings must be sorted by artifact_id"
        )
    value["artifact_bindings"] = normalized
    return value


def verify_external_validator_receipt_v06(
    spec: Mapping[str, Any],
    artifact_bytes: Mapping[str, bytes],
) -> dict[str, Any]:
    try:
        normalized = normalize_external_validator_check_spec_v06(spec)
        all_ids = external_validator_artifact_ids_v06(normalized)
        missing = [
            artifact_id
            for artifact_id in all_ids
            if not isinstance(artifact_bytes.get(artifact_id), bytes)
        ]
        if missing:
            raise V06ExternalValidatorError(
                f"external validator evidence is missing artifact bytes: {missing}"
            )

        public_key = _load_public_key(
            artifact_bytes[normalized["validator_public_key_artifact"]]
        )
        fingerprint = public_key_fingerprint(public_key)
        if fingerprint != normalized["validator_public_key_fingerprint"]:
            raise V06ExternalValidatorError(
                "external validator public key does not match pinned fingerprint"
            )

        receipt_raw = artifact_bytes[normalized["receipt_artifact"]]
        try:
            receipt_value = strict_json_loads(receipt_raw.decode("utf-8"))
        except (UnicodeDecodeError, StrictJSONError) as exc:
            raise V06ExternalValidatorError(
                f"external validator receipt is not strict UTF-8 JSON: {exc}"
            ) from exc
        if not isinstance(receipt_value, dict):
            raise V06ExternalValidatorError(
                "external validator receipt root must be an object"
            )

        signature = verify_jcs_signature(
            receipt_value,
            public_key,
            expected_domain=EXTERNAL_VALIDATOR_SIGNATURE_DOMAIN_V06,
            expected_fingerprint=normalized[
                "validator_public_key_fingerprint"
            ],
        )
        if signature.get("valid") is not True:
            raise V06ExternalValidatorError(
                "external validator receipt signature is invalid: "
                + "; ".join(str(x) for x in signature.get("errors", []))
            )

        envelope = receipt_value.get("payload")
        if not isinstance(envelope, Mapping):
            raise V06ExternalValidatorError(
                "external validator signature payload envelope is missing"
            )
        payload = _validate_receipt_payload_v06(envelope.get("payload"))

        if payload["validator"] != normalized["validator"]:
            raise V06ExternalValidatorError(
                "external validator receipt identity differs from check specification"
            )
        if payload["check_type"] != normalized["type"]:
            raise V06ExternalValidatorError(
                "external validator receipt check type differs from check specification"
            )
        if payload["predicate"] != normalized["predicate"]:
            raise V06ExternalValidatorError(
                "external validator receipt predicate differs from check specification"
            )

        expected_bindings = _artifact_bindings(
            normalized["bound_artifact_ids"],
            artifact_bytes,
        )
        if payload["artifact_bindings"] != expected_bindings:
            raise V06ExternalValidatorError(
                "external validator receipt artifact bindings do not match exact package bytes"
            )

        return {
            "valid": True,
            "errors": [],
            "outcome": payload["outcome"],
            "kind": external_validator_evidence_kind_v06(
                normalized["type"]
            ),
            "validator": normalized["validator"],
            "validator_public_key_fingerprint": fingerprint,
            "receipt_payload_sha256": receipt_value.get("payload_sha256"),
            "artifact_bindings": deepcopy(payload["artifact_bindings"]),
            "trust_contract": deepcopy(
                EXTERNAL_VALIDATOR_TRUST_CONTRACT_V06
            ),
            "semantic_authority": "EXTERNAL_VALIDATOR_TRUST_REQUIRED",
        }
    except V06ExternalValidatorError as exc:
        return {
            "valid": False,
            "errors": [str(exc)],
            "outcome": "FAIL",
            "kind": (
                external_validator_evidence_kind_v06(str(spec.get("type")))
                if spec.get("type") in EXTERNAL_VALIDATOR_CHECK_TYPES_V06
                else "provenance"
            ),
            "semantic_authority": "EXTERNAL_VALIDATOR_TRUST_REQUIRED",
        }
