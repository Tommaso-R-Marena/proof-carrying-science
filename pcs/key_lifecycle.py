from __future__ import annotations

import hashlib
import os
import tempfile
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from .canonical_json import canonicalize_jcs_bytes
from .jsonio import StrictJSONError, strict_json_loads
from .signing import public_key_fingerprint


KEY_REGISTRY_FORMAT = "pcs-key-registry-v1"
KEY_REGISTRY_HASH_FORMAT = "pcs-key-registry-sha256-v1"
KEY_STATUSES = frozenset({"ACTIVE", "RETIRED", "REVOKED"})
CUSTODY_MODES = frozenset(
    {"offline_encrypted", "hardware_backed", "reviewed_other"}
)
RECOVERY_CONTROLS = frozenset(
    {
        "encrypted_backup_verified",
        "hardware_recovery_verified",
        "no_recovery_reviewed",
    }
)
REVOCATION_SCOPES = frozenset({"from_time", "all_signatures"})
_HEX = frozenset("0123456789abcdef")


class KeyLifecycleError(ValueError):
    pass


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_time(value: str | None) -> str:
    if value is None:
        return _utc_now()
    if not isinstance(value, str) or not value:
        raise KeyLifecycleError("timestamp must be a non-empty ISO-8601 string")
    candidate = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError as exc:
        raise KeyLifecycleError(f"invalid ISO-8601 timestamp: {value!r}") from exc
    if parsed.tzinfo is None:
        raise KeyLifecycleError("timestamp must include an explicit timezone")
    return parsed.astimezone(timezone.utc).isoformat()


def _time(value: str) -> datetime:
    return datetime.fromisoformat(_normalize_time(value))


def _is_sha256(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(ch in _HEX for ch in value)
    )


def _projection(registry: Mapping[str, Any]) -> dict[str, Any]:
    value = deepcopy(dict(registry))
    value.pop("semantic_hash", None)
    return value


def registry_semantic_hash(registry: Mapping[str, Any]) -> str:
    payload = canonicalize_jcs_bytes(_projection(registry))
    return hashlib.sha256(b"PCS-KEY-REGISTRY-V1\0" + payload).hexdigest()


def _validate_key_entry(entry: Any) -> None:
    if not isinstance(entry, Mapping):
        raise KeyLifecycleError("key registry entry must be an object")
    required = {
        "key_id",
        "algorithm",
        "public_key_fingerprint",
        "public_key_spki_sha256",
        "status",
        "activated_at",
        "retired_at",
        "revoked_at",
        "revocation_scope",
        "revocation_reason",
        "superseded_by",
        "custody_mode",
        "recovery_control",
        "notes",
    }
    if set(entry) != required:
        raise KeyLifecycleError(
            "key registry entry fields differ from pcs-key-registry-v1"
        )
    if not isinstance(entry["key_id"], str) or not entry["key_id"].strip():
        raise KeyLifecycleError("key_id must be a non-empty string")
    if entry["algorithm"] != "Ed25519":
        raise KeyLifecycleError("only Ed25519 pilot signing keys are supported")
    for name in ("public_key_fingerprint", "public_key_spki_sha256"):
        if not _is_sha256(entry[name]):
            raise KeyLifecycleError(f"{name} must be 64 lowercase hex")
    if entry["status"] not in KEY_STATUSES:
        raise KeyLifecycleError(f"unsupported key status: {entry['status']!r}")
    _normalize_time(entry["activated_at"])
    if entry["custody_mode"] not in CUSTODY_MODES:
        raise KeyLifecycleError(
            f"unsupported custody_mode: {entry['custody_mode']!r}"
        )
    if entry["recovery_control"] not in RECOVERY_CONTROLS:
        raise KeyLifecycleError(
            f"unsupported recovery_control: {entry['recovery_control']!r}"
        )
    if not isinstance(entry["notes"], str):
        raise KeyLifecycleError("key notes must be a string")

    retired_at = entry["retired_at"]
    revoked_at = entry["revoked_at"]
    if retired_at is not None:
        _normalize_time(retired_at)
    if revoked_at is not None:
        _normalize_time(revoked_at)

    if entry["status"] == "ACTIVE":
        if any(
            entry[name] is not None
            for name in (
                "retired_at",
                "revoked_at",
                "revocation_scope",
                "revocation_reason",
                "superseded_by",
            )
        ):
            raise KeyLifecycleError(
                "ACTIVE key must not contain retirement/revocation metadata"
            )
    elif entry["status"] == "RETIRED":
        if retired_at is None:
            raise KeyLifecycleError("RETIRED key requires retired_at")
        if any(
            entry[name] is not None
            for name in ("revoked_at", "revocation_scope", "revocation_reason")
        ):
            raise KeyLifecycleError(
                "RETIRED key must not contain revocation metadata"
            )
        if entry["superseded_by"] is not None and not _is_sha256(
            entry["superseded_by"]
        ):
            raise KeyLifecycleError("superseded_by must be a SHA-256 fingerprint")
    else:
        if revoked_at is None:
            raise KeyLifecycleError("REVOKED key requires revoked_at")
        if entry["revocation_scope"] not in REVOCATION_SCOPES:
            raise KeyLifecycleError("REVOKED key requires a valid revocation_scope")
        if (
            not isinstance(entry["revocation_reason"], str)
            or not entry["revocation_reason"].strip()
        ):
            raise KeyLifecycleError("REVOKED key requires a non-empty reason")
        if entry["superseded_by"] is not None and not _is_sha256(
            entry["superseded_by"]
        ):
            raise KeyLifecycleError("superseded_by must be a SHA-256 fingerprint")


def validate_registry(registry: Any) -> dict[str, Any]:
    if not isinstance(registry, Mapping):
        raise KeyLifecycleError("key registry root must be an object")
    required = {
        "format",
        "semantic_hash_format",
        "registry_id",
        "keys",
        "semantic_hash",
    }
    if set(registry) != required:
        raise KeyLifecycleError(
            "key registry fields differ from pcs-key-registry-v1"
        )
    if registry["format"] != KEY_REGISTRY_FORMAT:
        raise KeyLifecycleError(f"unsupported key registry format: {registry['format']!r}")
    if registry["semantic_hash_format"] != KEY_REGISTRY_HASH_FORMAT:
        raise KeyLifecycleError("unsupported key registry hash format")
    if not isinstance(registry["registry_id"], str) or not registry[
        "registry_id"
    ].strip():
        raise KeyLifecycleError("registry_id must be a non-empty string")
    if not isinstance(registry["keys"], list):
        raise KeyLifecycleError("keys must be an array")

    fingerprints: set[str] = set()
    key_ids: set[str] = set()
    active = 0
    for entry in registry["keys"]:
        _validate_key_entry(entry)
        fingerprint = entry["public_key_fingerprint"]
        key_id = entry["key_id"]
        if fingerprint in fingerprints:
            raise KeyLifecycleError("duplicate key fingerprint in registry")
        if key_id in key_ids:
            raise KeyLifecycleError("duplicate key_id in registry")
        fingerprints.add(fingerprint)
        key_ids.add(key_id)
        active += int(entry["status"] == "ACTIVE")
    if active > 1:
        raise KeyLifecycleError(
            "pilot key registry permits at most one ACTIVE producer signer"
        )

    supplied = registry["semantic_hash"]
    if not _is_sha256(supplied):
        raise KeyLifecycleError("registry semantic_hash must be 64 lowercase hex")
    expected = registry_semantic_hash(registry)
    if supplied != expected:
        raise KeyLifecycleError("key registry semantic hash mismatch")
    return deepcopy(dict(registry))


def new_registry(registry_id: str) -> dict[str, Any]:
    if not isinstance(registry_id, str) or not registry_id.strip():
        raise KeyLifecycleError("registry_id must be a non-empty string")
    value: dict[str, Any] = {
        "format": KEY_REGISTRY_FORMAT,
        "semantic_hash_format": KEY_REGISTRY_HASH_FORMAT,
        "registry_id": registry_id.strip(),
        "keys": [],
        "semantic_hash": "",
    }
    value["semantic_hash"] = registry_semantic_hash(value)
    return validate_registry(value)


def _decode_registry(raw: bytes) -> dict[str, Any]:
    try:
        value = strict_json_loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, StrictJSONError) as exc:
        raise KeyLifecycleError(f"invalid key registry JSON: {exc}") from exc
    return validate_registry(value)


def load_registry(path: str | Path) -> dict[str, Any]:
    source = Path(path).resolve()
    if source.is_symlink() or not source.is_file():
        raise KeyLifecycleError(f"key registry must be a regular file: {source}")
    return _decode_registry(source.read_bytes())


def _write_registry(
    path: str | Path,
    registry: Mapping[str, Any],
    *,
    overwrite: bool,
) -> Path:
    checked = validate_registry(registry)
    target = Path(path).resolve()
    if target.exists() and not overwrite:
        raise KeyLifecycleError(f"refusing to overwrite existing registry: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    raw = canonicalize_jcs_bytes(checked) + b"\n"
    fd, tmp_name = tempfile.mkstemp(
        prefix=f".{target.name}.", suffix=".tmp", dir=target.parent
    )
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, target)
    finally:
        try:
            os.unlink(tmp_name)
        except FileNotFoundError:
            pass
    return target


def write_new_registry(path: str | Path, registry_id: str) -> dict[str, Any]:
    registry = new_registry(registry_id)
    target = _write_registry(path, registry, overwrite=False)
    return {"registry": str(target), **registry}


def _public_key_metadata(path: str | Path) -> tuple[str, str]:
    source = Path(path).resolve()
    if source.is_symlink() or not source.is_file():
        raise KeyLifecycleError(f"public key must be a regular file: {source}")
    try:
        key = serialization.load_pem_public_key(source.read_bytes())
    except (ValueError, TypeError) as exc:
        raise KeyLifecycleError(f"cannot decode public key: {exc}") from exc
    if not isinstance(key, Ed25519PublicKey):
        raise KeyLifecycleError("pilot signer public key must be Ed25519")
    spki = key.public_bytes(
        serialization.Encoding.DER,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return public_key_fingerprint(key), hashlib.sha256(spki).hexdigest()


def _entry(
    *,
    key_id: str,
    fingerprint: str,
    spki_sha256: str,
    activated_at: str,
    custody_mode: str,
    recovery_control: str,
    notes: str,
) -> dict[str, Any]:
    if custody_mode not in CUSTODY_MODES:
        raise KeyLifecycleError(f"unsupported custody_mode: {custody_mode!r}")
    if recovery_control not in RECOVERY_CONTROLS:
        raise KeyLifecycleError(
            f"unsupported recovery_control: {recovery_control!r}"
        )
    if not isinstance(key_id, str) or not key_id.strip():
        raise KeyLifecycleError("key_id must be a non-empty string")
    return {
        "key_id": key_id.strip(),
        "algorithm": "Ed25519",
        "public_key_fingerprint": fingerprint,
        "public_key_spki_sha256": spki_sha256,
        "status": "ACTIVE",
        "activated_at": _normalize_time(activated_at),
        "retired_at": None,
        "revoked_at": None,
        "revocation_scope": None,
        "revocation_reason": None,
        "superseded_by": None,
        "custody_mode": custody_mode,
        "recovery_control": recovery_control,
        "notes": notes or "",
    }


def _finalize(registry: dict[str, Any]) -> dict[str, Any]:
    registry["keys"] = sorted(
        registry["keys"],
        key=lambda item: (item["activated_at"], item["key_id"]),
    )
    registry["semantic_hash"] = registry_semantic_hash(registry)
    return validate_registry(registry)


def register_active_key(
    registry_path: str | Path,
    public_key_path: str | Path,
    *,
    key_id: str,
    custody_mode: str,
    recovery_control: str,
    activated_at: str | None = None,
    notes: str = "",
) -> dict[str, Any]:
    registry = load_registry(registry_path)
    if any(item["status"] == "ACTIVE" for item in registry["keys"]):
        raise KeyLifecycleError(
            "registry already has an ACTIVE key; use rotation instead"
        )
    fingerprint, spki = _public_key_metadata(public_key_path)
    if any(
        item["public_key_fingerprint"] == fingerprint for item in registry["keys"]
    ):
        raise KeyLifecycleError("public key fingerprint is already registered")
    if any(item["key_id"] == key_id for item in registry["keys"]):
        raise KeyLifecycleError("key_id is already registered")
    registry["keys"].append(
        _entry(
            key_id=key_id,
            fingerprint=fingerprint,
            spki_sha256=spki,
            activated_at=_normalize_time(activated_at),
            custody_mode=custody_mode,
            recovery_control=recovery_control,
            notes=notes,
        )
    )
    registry = _finalize(registry)
    _write_registry(registry_path, registry, overwrite=True)
    return {
        "registry": str(Path(registry_path).resolve()),
        "public_key_fingerprint": fingerprint,
        "status": "ACTIVE",
        "semantic_hash": registry["semantic_hash"],
    }


def _find(registry: Mapping[str, Any], fingerprint: str) -> dict[str, Any]:
    normalized = fingerprint.lower()
    for item in registry["keys"]:
        if item["public_key_fingerprint"] == normalized:
            return item
    raise KeyLifecycleError(f"signer fingerprint is not registered: {fingerprint}")


def rotate_key(
    registry_path: str | Path,
    *,
    old_fingerprint: str,
    new_public_key_path: str | Path,
    new_key_id: str,
    custody_mode: str,
    recovery_control: str,
    effective_at: str | None = None,
    notes: str = "",
) -> dict[str, Any]:
    registry = load_registry(registry_path)
    old = _find(registry, old_fingerprint)
    if old["status"] != "ACTIVE":
        raise KeyLifecycleError("rotation source key must be ACTIVE")
    effective = _normalize_time(effective_at)
    if _time(effective) < _time(old["activated_at"]):
        raise KeyLifecycleError("rotation time predates old-key activation")

    new_fingerprint, spki = _public_key_metadata(new_public_key_path)
    if new_fingerprint == old["public_key_fingerprint"]:
        raise KeyLifecycleError("rotation requires a distinct new public key")
    if any(
        item["public_key_fingerprint"] == new_fingerprint
        for item in registry["keys"]
    ):
        raise KeyLifecycleError("new public key fingerprint is already registered")
    if any(item["key_id"] == new_key_id for item in registry["keys"]):
        raise KeyLifecycleError("new key_id is already registered")

    old["status"] = "RETIRED"
    old["retired_at"] = effective
    old["superseded_by"] = new_fingerprint
    registry["keys"].append(
        _entry(
            key_id=new_key_id,
            fingerprint=new_fingerprint,
            spki_sha256=spki,
            activated_at=effective,
            custody_mode=custody_mode,
            recovery_control=recovery_control,
            notes=notes,
        )
    )
    registry = _finalize(registry)
    _write_registry(registry_path, registry, overwrite=True)
    return {
        "registry": str(Path(registry_path).resolve()),
        "retired_fingerprint": old["public_key_fingerprint"],
        "active_fingerprint": new_fingerprint,
        "effective_at": effective,
        "semantic_hash": registry["semantic_hash"],
    }


def revoke_key(
    registry_path: str | Path,
    *,
    fingerprint: str,
    reason: str,
    scope: str = "all_signatures",
    effective_at: str | None = None,
) -> dict[str, Any]:
    if scope not in REVOCATION_SCOPES:
        raise KeyLifecycleError(f"unsupported revocation scope: {scope!r}")
    if not isinstance(reason, str) or not reason.strip():
        raise KeyLifecycleError("revocation reason must be non-empty")
    registry = load_registry(registry_path)
    entry = _find(registry, fingerprint)
    if entry["status"] == "REVOKED":
        raise KeyLifecycleError("key is already revoked")
    effective = _normalize_time(effective_at)
    if _time(effective) < _time(entry["activated_at"]):
        raise KeyLifecycleError("revocation time predates key activation")
    entry["status"] = "REVOKED"
    entry["revoked_at"] = effective
    entry["revocation_scope"] = scope
    entry["revocation_reason"] = reason.strip()
    registry = _finalize(registry)
    _write_registry(registry_path, registry, overwrite=True)
    return {
        "registry": str(Path(registry_path).resolve()),
        "public_key_fingerprint": entry["public_key_fingerprint"],
        "status": "REVOKED",
        "revoked_at": effective,
        "revocation_scope": scope,
        "semantic_hash": registry["semantic_hash"],
    }


def assess_signer(
    registry: Mapping[str, Any],
    fingerprint: str,
    *,
    signed_at: str,
) -> dict[str, Any]:
    checked = validate_registry(registry)
    entry = _find(checked, fingerprint)
    moment = _time(signed_at)
    activated = _time(entry["activated_at"])
    errors: list[str] = []
    if moment < activated:
        errors.append("signature timestamp predates key activation")

    if entry["status"] == "RETIRED":
        retired = _time(entry["retired_at"])
        if moment >= retired:
            errors.append("signature timestamp is at/after key retirement")
    elif entry["status"] == "REVOKED":
        if entry["revocation_scope"] == "all_signatures":
            errors.append("key revocation invalidates all signatures")
        else:
            revoked = _time(entry["revoked_at"])
            if moment >= revoked:
                errors.append("signature timestamp is at/after key revocation")
        if entry["retired_at"] is not None:
            retired = _time(entry["retired_at"])
            if moment >= retired:
                errors.append("signature timestamp is at/after key retirement")

    return {
        "valid": not errors,
        "errors": errors,
        "registry_id": checked["registry_id"],
        "registry_semantic_hash": checked["semantic_hash"],
        "key_id": entry["key_id"],
        "public_key_fingerprint": entry["public_key_fingerprint"],
        "status": entry["status"],
        "signed_at": _normalize_time(signed_at),
        "activated_at": entry["activated_at"],
        "retired_at": entry["retired_at"],
        "revoked_at": entry["revoked_at"],
        "revocation_scope": entry["revocation_scope"],
    }


def assess_signer_file(
    registry_path: str | Path,
    fingerprint: str,
    *,
    signed_at: str,
) -> dict[str, Any]:
    return assess_signer(
        load_registry(registry_path),
        fingerprint,
        signed_at=signed_at,
    )
