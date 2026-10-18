"""Versioned JSON schemas for PCS Next artifacts."""

from __future__ import annotations

from typing import Any

import jsonschema

from .errors import ErrorCode, PcsNextError

INTAKE_FORMAT = "pcs-next-intake-v1"
LOCK_FORMAT = "pcs-next-intake-lock-v1"
POLICY_FORMAT = "pcs-next-acceptance-policy-v1"
EVIDENCE_FORMAT = "pcs-next-evidence-bundle-v1"
RECEIPT_FORMAT = "pcs-next-independent-receipt-v1"
CLAIM_IR_FORMAT = "pcs-next-claim-ir-v1"
POG_FORMAT = "pcs-next-pog-v1"

INTAKE_SCHEMA: dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "additionalProperties": False,
    "required": [
        "format",
        "project_id",
        "scientific_domain",
        "workflow_purpose",
        "artifacts",
        "claimed_conclusions",
        "computational_assertions",
        "assumptions",
        "models",
        "software_dependencies",
        "numerical_methods",
        "verification_boundaries",
        "expected_outputs",
        "data_handling_classification",
        "publication_permissions",
        "unresolved_questions",
    ],
    "properties": {
        "format": {"const": INTAKE_FORMAT},
        "project_id": {"type": "string", "minLength": 1, "maxLength": 128, "pattern": "^[A-Za-z0-9._:-]+$"},
        "scientific_domain": {"type": "string", "minLength": 1},
        "workflow_purpose": {"type": "string", "minLength": 1},
        "artifacts": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["id", "path", "role"],
                "properties": {
                    "id": {"type": "string", "minLength": 1},
                    "path": {"type": "string", "minLength": 1},
                    "role": {"type": "string", "enum": ["input", "output", "model", "code", "metadata", "other"]},
                    "media_type": {"type": "string"},
                    "sha256": {"type": "string", "pattern": "^[a-f0-9]{64}$"},
                },
            },
        },
        "claimed_conclusions": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["id", "text"],
                "properties": {
                    "id": {"type": "string"},
                    "text": {"type": "string"},
                    "kind": {"type": "string"},
                },
            },
        },
        "computational_assertions": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["id", "statement"],
                "properties": {
                    "id": {"type": "string"},
                    "statement": {"type": "string"},
                    "method": {"type": "string"},
                },
            },
        },
        "assumptions": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["id", "text"],
                "properties": {
                    "id": {"type": "string"},
                    "text": {"type": "string"},
                    "discharged": {"type": "boolean"},
                },
            },
        },
        "models": {"type": "array", "items": {"type": "object"}},
        "software_dependencies": {"type": "array", "items": {"type": "object"}},
        "numerical_methods": {"type": "array", "items": {"type": "object"}},
        "verification_boundaries": {"type": "array", "items": {"type": "string"}},
        "expected_outputs": {"type": "array", "items": {"type": "object"}},
        "acceptance_policy_ref": {"type": "string"},
        "reviewer_identities": {"type": "array", "items": {"type": "object"}},
        "data_handling_classification": {
            "type": "string",
            "enum": ["synthetic", "public", "licensed", "restricted", "unknown"],
        },
        "publication_permissions": {"type": "string"},
        "unresolved_questions": {"type": "array", "items": {"type": "string"}},
    },
}

POLICY_SCHEMA: dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "additionalProperties": False,
    "required": [
        "format",
        "policy_id",
        "policy_version",
        "protocol_version",
        "required_checks",
        "allowed_claim_statuses",
        "max_artifact_bytes",
        "fail_closed_unknown_versions",
        "pinned_signer_fingerprints",
    ],
    "properties": {
        "format": {"const": POLICY_FORMAT},
        "policy_id": {"type": "string", "minLength": 1},
        "policy_version": {"type": "string", "minLength": 1},
        "protocol_version": {"type": "string", "minLength": 1},
        "required_checks": {
            "type": "array",
            "minItems": 1,
            "items": {"type": "string"},
        },
        "allowed_claim_statuses": {
            "type": "array",
            "items": {"type": "string"},
        },
        "max_artifact_bytes": {"type": "integer", "minimum": 1},
        "fail_closed_unknown_versions": {"type": "boolean"},
        "pinned_signer_fingerprints": {
            "type": "array",
            "items": {"type": "string", "pattern": "^[a-f0-9]{64}$"},
        },
        "notes": {"type": "string"},
    },
}


def validate_schema(instance: dict[str, Any], schema: dict[str, Any], *, label: str) -> dict[str, Any]:
    try:
        jsonschema.validate(instance, schema)
    except jsonschema.ValidationError as exc:
        raise PcsNextError(
            ErrorCode.SCHEMA_INVALID,
            f"{label} schema validation failed: {exc.message}",
            details={"path": list(exc.absolute_path), "validator": exc.validator},
        ) from exc
    return instance
