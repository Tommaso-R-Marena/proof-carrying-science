from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .hashing import sha256_json
from .schema_validation import (
    validate_pilot_intake_shape,
    validate_pilot_intake_lock_shape,
    SchemaValidationError,
)

INTAKE_FORMAT = "pcs-pilot-intake-v1"
LOCK_FORMAT = "pcs-pilot-intake-lock-v1"


class PilotIntakeError(ValueError):
    pass


def _ids(items: list[dict[str, Any]], label: str) -> set[str]:
    seen: set[str] = set()
    for item in items:
        ident = item.get("id")
        if ident in seen:
            raise PilotIntakeError(f"duplicate {label} id: {ident}")
        seen.add(str(ident))
    return seen


def validate_intake(intake: dict[str, Any]) -> dict[str, Any]:
    try:
        validate_pilot_intake_shape(intake)
    except SchemaValidationError as exc:
        raise PilotIntakeError(str(exc)) from exc
    claim_ids = _ids(intake.get("claims", []), "claim")
    assumption_ids = _ids(intake.get("assumptions", []), "assumption")
    if claim_ids & assumption_ids:
        raise PilotIntakeError("claim and assumption IDs must be disjoint")
    return intake


def intake_semantic_hash(intake: dict[str, Any]) -> str:
    validate_intake(intake)
    return sha256_json(intake)


def freeze_intake(intake: dict[str, Any]) -> dict[str, Any]:
    normalized = deepcopy(validate_intake(intake))
    lock = {
        "lock_format": LOCK_FORMAT,
        "frozen_at": datetime.now(timezone.utc).isoformat(),
        "intake_semantic_hash": sha256_json(normalized),
        "intake": normalized,
    }
    validate_lock(lock)
    return lock


def freeze_intake_file(input_path: str | Path, output_path: str | Path) -> dict[str, Any]:
    intake = json.loads(Path(input_path).read_text(encoding="utf-8"))
    lock = freeze_intake(intake)
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(lock, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return lock


def validate_lock(lock: dict[str, Any]) -> dict[str, Any]:
    try:
        validate_pilot_intake_lock_shape(lock)
    except SchemaValidationError as exc:
        raise PilotIntakeError(str(exc)) from exc
    intake = validate_intake(lock.get("intake"))
    expected = sha256_json(intake)
    if lock.get("intake_semantic_hash") != expected:
        raise PilotIntakeError("pilot intake semantic hash mismatch")
    return lock


def load_lock(path: str | Path) -> dict[str, Any]:
    lock = json.loads(Path(path).read_text(encoding="utf-8"))
    return validate_lock(lock)


def assert_lock_matches_certificate(lock: dict[str, Any], certificate: dict[str, Any]) -> None:
    lock = validate_lock(lock)
    intake = lock["intake"]
    locked_claims = {str(c["id"]) for c in intake.get("claims", [])}
    cert_claims = {str(c.get("id")) for c in certificate.get("claims", [])}
    if locked_claims != cert_claims:
        raise PilotIntakeError(
            f"certificate claim IDs differ from frozen intake: locked={sorted(locked_claims)} certificate={sorted(cert_claims)}"
        )
    locked_assumptions = {str(a["id"]) for a in intake.get("assumptions", [])}
    cert_assumptions = {str(a.get("id")) for a in certificate.get("assumptions", [])}
    if locked_assumptions != cert_assumptions:
        raise PilotIntakeError(
            f"certificate assumption IDs differ from frozen intake: locked={sorted(locked_assumptions)} certificate={sorted(cert_assumptions)}"
        )
