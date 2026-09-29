from __future__ import annotations

import json
from importlib.resources import files
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker


class SchemaValidationError(ValueError):
    pass


_SCHEMA_PACKAGE = "pcs.schemas"


def _load_schema(name: str) -> dict[str, Any]:
    resource = files(_SCHEMA_PACKAGE).joinpath(name)
    return json.loads(resource.read_text(encoding="utf-8"))


def validate_shape(value: Any, schema_name: str, *, label: str) -> None:
    schema = _load_schema(schema_name)
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = sorted(
        validator.iter_errors(value),
        key=lambda e: tuple(str(x) for x in e.absolute_path),
    )
    if not errors:
        return
    formatted: list[str] = []
    for err in errors[:20]:
        path = "$"
        for part in err.absolute_path:
            if isinstance(part, int):
                path += f"[{part}]"
            else:
                path += f".{part}"
        formatted.append(f"{path}: {err.message}")
    suffix = "" if len(errors) <= 20 else f" (+{len(errors)-20} more)"
    raise SchemaValidationError(
        f"{label} failed JSON Schema validation: " + "; ".join(formatted) + suffix
    )


def validate_manifest_shape(value: Any) -> None:
    validate_shape(value, "manifest.schema.json", label="manifest")


def validate_certificate_shape(value: Any) -> None:
    validate_shape(value, "certificate.schema.json", label="certificate")


def validate_package_manifest_shape(value: Any) -> None:
    validate_shape(value, "package_manifest.schema.json", label="package manifest")


def validate_policy_shape(value: Any) -> None:
    validate_shape(value, "acceptance_policy.schema.json", label="acceptance policy")


def validate_verification_receipt_shape(value: Any) -> None:
    validate_shape(value, "verification_receipt.schema.json", label="verification receipt")


def validate_pilot_intake_shape(value: Any) -> None:
    validate_shape(value, "pilot_intake.schema.json", label="pilot intake")


def validate_pilot_intake_lock_shape(value: Any) -> None:
    validate_shape(value, "pilot_intake_lock.schema.json", label="pilot intake lock")
    validate_pilot_intake_shape(value.get("intake") if isinstance(value, dict) else None)


def validate_v06_hash_envelope_shape(value: Any) -> None:
    validate_shape(value, "hash_envelope_v06.schema.json", label="v0.6 hash envelope")


def validate_v06_signature_record_shape(value: Any) -> None:
    validate_shape(value, "signature_record_v06.schema.json", label="v0.6 signature record")


def validate_v06_certificate_shape(value: Any) -> None:
    validate_shape(value, "certificate_v06.schema.json", label="v0.6 certificate")


def validate_v06_package_manifest_shape(value: Any) -> None:
    validate_shape(value, "package_manifest_v06.schema.json", label="v0.6 package manifest")
