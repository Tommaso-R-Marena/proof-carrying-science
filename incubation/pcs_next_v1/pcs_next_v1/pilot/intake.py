"""External intake and content-bound freezing."""

from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..core.canonical import CanonicalError, canonical_hash, canonicalize, loads_strict
from ..core.errors import ErrorCode, PcsNextError
from ..core.hashing import sha256_file
from ..core.schemas import INTAKE_FORMAT, INTAKE_SCHEMA, LOCK_FORMAT, validate_schema


def validate_intake(intake: dict[str, Any]) -> dict[str, Any]:
    validate_schema(intake, INTAKE_SCHEMA, label="intake")
    claim_ids = [c["id"] for c in intake.get("claimed_conclusions", [])]
    assumption_ids = [a["id"] for a in intake.get("assumptions", [])]
    if len(claim_ids) != len(set(claim_ids)):
        raise PcsNextError(ErrorCode.SCHEMA_INVALID, "duplicate claimed_conclusion ids")
    if len(assumption_ids) != len(set(assumption_ids)):
        raise PcsNextError(ErrorCode.SCHEMA_INVALID, "duplicate assumption ids")
    if set(claim_ids) & set(assumption_ids):
        raise PcsNextError(ErrorCode.SCHEMA_INVALID, "claim and assumption ids must be disjoint")
    art_ids = [a["id"] for a in intake.get("artifacts", [])]
    if len(art_ids) != len(set(art_ids)):
        raise PcsNextError(ErrorCode.SCHEMA_INVALID, "duplicate artifact ids")
    return intake


def load_intake(path: str | Path) -> dict[str, Any]:
    raw = Path(path).read_bytes()
    try:
        data = loads_strict(raw)
    except CanonicalError as exc:
        raise PcsNextError(ErrorCode.CANONICAL_INVALID, str(exc)) from exc
    if not isinstance(data, dict):
        raise PcsNextError(ErrorCode.SCHEMA_INVALID, "intake must be a JSON object")
    return validate_intake(data)


def bind_artifact_hashes(intake: dict[str, Any], root: str | Path) -> dict[str, Any]:
    """Fill missing sha256 from filesystem; reject mismatches."""
    root_p = Path(root).resolve()
    out = deepcopy(validate_intake(intake))
    for art in out["artifacts"]:
        rel = art["path"]
        if Path(rel).is_absolute() or ".." in Path(rel).parts:
            raise PcsNextError(ErrorCode.PATH_ESCAPE, f"illegal artifact path: {rel}")
        target = (root_p / rel).resolve()
        if not str(target).startswith(str(root_p) + "/") and target != root_p:
            raise PcsNextError(ErrorCode.PATH_ESCAPE, f"path escapes root: {rel}")
        if not target.is_file():
            raise PcsNextError(ErrorCode.SCHEMA_INVALID, f"missing artifact file: {rel}")
        digest = sha256_file(target)
        if "sha256" in art and art["sha256"] != digest:
            raise PcsNextError(
                ErrorCode.HASH_MISMATCH,
                "artifact hash mismatch before freeze",
                details={"path": rel, "expected": art["sha256"], "actual": digest},
            )
        art["sha256"] = digest
    return out


def freeze_intake(
    intake: dict[str, Any],
    *,
    acceptance_policy: dict[str, Any] | None = None,
    frozen_at: str | None = None,
) -> dict[str, Any]:
    """Freeze intake into a content-bound lock.

    Timestamps are recorded for operational audit only — they are not part of
    the semantic identity hash of the intake body.
    """
    normalized = deepcopy(validate_intake(intake))
    semantic_hash = canonical_hash(normalized)
    policy_hash = canonical_hash(acceptance_policy) if acceptance_policy is not None else None
    lock = {
        "lock_format": LOCK_FORMAT,
        "frozen_at": frozen_at or datetime.now(timezone.utc).isoformat(),
        "intake_format": INTAKE_FORMAT,
        "intake_semantic_hash": semantic_hash,
        "acceptance_policy_hash": policy_hash,
        "intake": normalized,
        "acceptance_policy": deepcopy(acceptance_policy) if acceptance_policy is not None else None,
        "notes": (
            "frozen_at is operational metadata and is not used as prospective "
            "registration proof; semantic identity is intake_semantic_hash."
        ),
    }
    # Validate lock shape lightly
    if lock["lock_format"] != LOCK_FORMAT:
        raise PcsNextError(ErrorCode.SCHEMA_INVALID, "bad lock format")
    return lock


def write_lock(lock: dict[str, Any], path: str | Path, *, overwrite: bool = False) -> None:
    out = Path(path)
    if out.exists() and not overwrite:
        raise PcsNextError(ErrorCode.STATE_ILLEGAL, f"refusing to overwrite lock: {out}")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(canonicalize(lock) + b"\n")


def verify_lock_integrity(lock: dict[str, Any]) -> None:
    if lock.get("lock_format") != LOCK_FORMAT:
        raise PcsNextError(ErrorCode.SCHEMA_INVALID, "unexpected lock format")
    intake = lock.get("intake")
    if not isinstance(intake, dict):
        raise PcsNextError(ErrorCode.SCHEMA_INVALID, "lock missing intake")
    validate_intake(intake)
    expected = canonical_hash(intake)
    if lock.get("intake_semantic_hash") != expected:
        raise PcsNextError(
            ErrorCode.HASH_MISMATCH,
            "intake semantic hash mismatch",
            details={"expected": expected, "recorded": lock.get("intake_semantic_hash")},
        )
    policy = lock.get("acceptance_policy")
    ph = lock.get("acceptance_policy_hash")
    if policy is None:
        if ph is not None:
            raise PcsNextError(ErrorCode.HASH_MISMATCH, "policy hash present without policy")
    else:
        if ph != canonical_hash(policy):
            raise PcsNextError(ErrorCode.POLICY_SUBSTITUTION, "acceptance policy hash mismatch")


def detect_stale_substitution(
    lock: dict[str, Any],
    root: str | Path,
) -> list[dict[str, Any]]:
    """Return findings if frozen artifact hashes no longer match filesystem."""
    verify_lock_integrity(lock)
    findings: list[dict[str, Any]] = []
    root_p = Path(root).resolve()
    for art in lock["intake"]["artifacts"]:
        target = (root_p / art["path"]).resolve()
        if not target.is_file():
            findings.append({"kind": "missing_artifact", "path": art["path"]})
            continue
        digest = sha256_file(target)
        if digest != art.get("sha256"):
            findings.append(
                {
                    "kind": "stale_or_substituted_artifact",
                    "path": art["path"],
                    "frozen_sha256": art.get("sha256"),
                    "current_sha256": digest,
                }
            )
    return findings


def dump_json(path: str | Path, value: Any) -> None:
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
