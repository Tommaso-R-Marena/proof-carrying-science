from __future__ import annotations

import hashlib
import os
import tempfile
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Mapping

from .canonical_json import canonicalize_jcs_bytes
from .jsonio import StrictJSONError, strict_json_loads


PLAN_FORMAT = "pcs-pilot-closeout-plan-v1"
RECEIPT_FORMAT = "pcs-pilot-closeout-receipt-v1"
PLAN_HASH_FORMAT = "pcs-pilot-closeout-plan-sha256-v1"
RECEIPT_HASH_FORMAT = "pcs-pilot-closeout-receipt-sha256-v1"
ACTIONS = frozenset({"RETAIN", "DELETE"})
_HEX = frozenset("0123456789abcdef")


class PilotCloseoutError(ValueError):
    pass


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _is_sha256(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(ch in _HEX for ch in value)
    )


def _safe_rel(text: str) -> str:
    if not isinstance(text, str) or not text:
        raise PilotCloseoutError("closeout path must be a non-empty string")
    if "\\" in text:
        raise PilotCloseoutError(
            "closeout paths must use portable POSIX '/' separators"
        )
    path = PurePosixPath(text)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise PilotCloseoutError(f"unsafe closeout path: {text!r}")
    normalized = path.as_posix()
    if normalized != text:
        raise PilotCloseoutError(
            f"closeout path must already be normalized: {text!r}"
        )
    return normalized


def _resolve_workspace(root: str | Path) -> Path:
    workspace = Path(root).resolve()
    original = Path(root)
    if original.is_symlink() or not workspace.is_dir():
        raise PilotCloseoutError(
            f"pilot workspace must be a real directory, not a symlink: {workspace}"
        )
    return workspace


def _file_record(workspace: Path, rel: str, action: str) -> dict[str, Any]:
    if action not in ACTIONS:
        raise PilotCloseoutError(f"unsupported closeout action: {action!r}")
    safe = _safe_rel(rel)
    path = workspace / Path(*PurePosixPath(safe).parts)
    try:
        stat = path.lstat()
    except FileNotFoundError as exc:
        raise PilotCloseoutError(f"closeout file does not exist: {safe}") from exc
    if path.is_symlink():
        raise PilotCloseoutError(f"symlinks are prohibited in pilot closeout: {safe}")
    if not path.is_file():
        raise PilotCloseoutError(f"closeout entry is not a regular file: {safe}")
    raw = path.read_bytes()
    if len(raw) != stat.st_size:
        raise PilotCloseoutError(f"file changed while being read: {safe}")
    return {
        "path": safe,
        "action": action,
        "size": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
    }


def _scan_workspace(workspace: Path) -> list[str]:
    files: list[str] = []
    for path in sorted(workspace.rglob("*")):
        rel = path.relative_to(workspace).as_posix()
        if path.is_symlink():
            raise PilotCloseoutError(
                f"symlinks are prohibited in pilot closeout workspace: {rel}"
            )
        if path.is_file():
            files.append(rel)
    return files


def _plan_projection(plan: Mapping[str, Any]) -> dict[str, Any]:
    value = deepcopy(dict(plan))
    value.pop("plan_sha256", None)
    return value


def plan_sha256(plan: Mapping[str, Any]) -> str:
    return hashlib.sha256(
        b"PCS-PILOT-CLOSEOUT-PLAN-V1\0"
        + canonicalize_jcs_bytes(_plan_projection(plan))
    ).hexdigest()


def _receipt_projection(receipt: Mapping[str, Any]) -> dict[str, Any]:
    value = deepcopy(dict(receipt))
    value.pop("receipt_sha256", None)
    return value


def receipt_sha256(receipt: Mapping[str, Any]) -> str:
    return hashlib.sha256(
        b"PCS-PILOT-CLOSEOUT-RECEIPT-V1\0"
        + canonicalize_jcs_bytes(_receipt_projection(receipt))
    ).hexdigest()


def validate_plan(plan: Any) -> dict[str, Any]:
    if not isinstance(plan, Mapping):
        raise PilotCloseoutError("closeout plan root must be an object")
    required = {
        "format",
        "hash_format",
        "pilot_id",
        "workspace_label",
        "entries",
        "plan_sha256",
    }
    if set(plan) != required:
        raise PilotCloseoutError(
            "closeout plan fields differ from pcs-pilot-closeout-plan-v1"
        )
    if plan["format"] != PLAN_FORMAT or plan["hash_format"] != PLAN_HASH_FORMAT:
        raise PilotCloseoutError("unsupported closeout plan format/hash format")
    if not isinstance(plan["pilot_id"], str) or not plan["pilot_id"].strip():
        raise PilotCloseoutError("pilot_id must be a non-empty string")
    if not isinstance(plan["workspace_label"], str) or not plan[
        "workspace_label"
    ].strip():
        raise PilotCloseoutError("workspace_label must be a non-empty string")
    if not isinstance(plan["entries"], list) or not plan["entries"]:
        raise PilotCloseoutError("closeout plan entries must be a non-empty array")
    paths: set[str] = set()
    for entry in plan["entries"]:
        if not isinstance(entry, Mapping) or set(entry) != {
            "path",
            "action",
            "size",
            "sha256",
        }:
            raise PilotCloseoutError("invalid closeout plan entry shape")
        path = _safe_rel(entry["path"])
        if path in paths:
            raise PilotCloseoutError("duplicate path in closeout plan")
        paths.add(path)
        if entry["action"] not in ACTIONS:
            raise PilotCloseoutError("invalid closeout action")
        if not isinstance(entry["size"], int) or entry["size"] < 0:
            raise PilotCloseoutError("closeout entry size must be non-negative")
        if not _is_sha256(entry["sha256"]):
            raise PilotCloseoutError("closeout entry SHA-256 must be lowercase hex")
    expected = plan_sha256(plan)
    if plan["plan_sha256"] != expected:
        raise PilotCloseoutError("closeout plan semantic hash mismatch")
    return deepcopy(dict(plan))


def validate_receipt(receipt: Any) -> dict[str, Any]:
    if not isinstance(receipt, Mapping):
        raise PilotCloseoutError("closeout receipt root must be an object")
    required = {
        "format",
        "hash_format",
        "pilot_id",
        "workspace_label",
        "plan_sha256",
        "applied_at",
        "deleted",
        "retained",
        "receipt_sha256",
    }
    if set(receipt) != required:
        raise PilotCloseoutError(
            "closeout receipt fields differ from pcs-pilot-closeout-receipt-v1"
        )
    if (
        receipt["format"] != RECEIPT_FORMAT
        or receipt["hash_format"] != RECEIPT_HASH_FORMAT
    ):
        raise PilotCloseoutError("unsupported closeout receipt format/hash format")
    if not _is_sha256(receipt["plan_sha256"]):
        raise PilotCloseoutError("receipt plan_sha256 must be lowercase hex")
    if not isinstance(receipt["applied_at"], str) or not receipt["applied_at"]:
        raise PilotCloseoutError("receipt applied_at must be non-empty")
    for field in ("deleted", "retained"):
        if not isinstance(receipt[field], list):
            raise PilotCloseoutError(f"receipt {field} must be an array")
        for entry in receipt[field]:
            if not isinstance(entry, Mapping) or set(entry) != {
                "path",
                "size",
                "sha256",
            }:
                raise PilotCloseoutError(f"invalid receipt {field} entry")
            _safe_rel(entry["path"])
            if not isinstance(entry["size"], int) or entry["size"] < 0:
                raise PilotCloseoutError("receipt entry size must be non-negative")
            if not _is_sha256(entry["sha256"]):
                raise PilotCloseoutError("receipt entry SHA-256 must be lowercase hex")
    expected = receipt_sha256(receipt)
    if receipt["receipt_sha256"] != expected:
        raise PilotCloseoutError("closeout receipt semantic hash mismatch")
    return deepcopy(dict(receipt))


def build_closeout_plan(
    workspace: str | Path,
    *,
    pilot_id: str,
    retain_paths: list[str] | tuple[str, ...],
    delete_paths: list[str] | tuple[str, ...],
) -> dict[str, Any]:
    root = _resolve_workspace(workspace)
    retained = {_safe_rel(path) for path in retain_paths}
    deleted = {_safe_rel(path) for path in delete_paths}
    overlap = sorted(retained & deleted)
    if overlap:
        raise PilotCloseoutError(
            f"paths cannot be both RETAIN and DELETE: {overlap}"
        )
    actual = set(_scan_workspace(root))
    classified = retained | deleted
    if actual != classified:
        raise PilotCloseoutError(
            "every regular file in the pilot workspace must be explicitly "
            f"classified; unclassified={sorted(actual - classified)} "
            f"missing={sorted(classified - actual)}"
        )
    entries = [
        _file_record(root, path, "RETAIN")
        for path in sorted(retained)
    ] + [
        _file_record(root, path, "DELETE")
        for path in sorted(deleted)
    ]
    entries.sort(key=lambda item: item["path"])
    plan: dict[str, Any] = {
        "format": PLAN_FORMAT,
        "hash_format": PLAN_HASH_FORMAT,
        "pilot_id": pilot_id.strip(),
        "workspace_label": root.name,
        "entries": entries,
        "plan_sha256": "",
    }
    if not plan["pilot_id"]:
        raise PilotCloseoutError("pilot_id must be non-empty")
    plan["plan_sha256"] = plan_sha256(plan)
    return validate_plan(plan)


def _atomic_write(path: str | Path, value: Mapping[str, Any], *, overwrite: bool) -> Path:
    target = Path(path).resolve()
    if target.exists() and not overwrite:
        raise PilotCloseoutError(f"refusing to overwrite closeout record: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    raw = canonicalize_jcs_bytes(value) + b"\n"
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


def write_closeout_plan(
    output: str | Path,
    plan: Mapping[str, Any],
    *,
    overwrite: bool = False,
) -> Path:
    checked = validate_plan(plan)
    return _atomic_write(output, checked, overwrite=overwrite)


def load_closeout_plan(path: str | Path) -> dict[str, Any]:
    source = Path(path).resolve()
    if source.is_symlink() or not source.is_file():
        raise PilotCloseoutError(f"closeout plan must be a regular file: {source}")
    try:
        value = strict_json_loads(source.read_text(encoding="utf-8"))
    except StrictJSONError as exc:
        raise PilotCloseoutError(f"invalid closeout plan JSON: {exc}") from exc
    return validate_plan(value)


def apply_closeout_plan(
    workspace: str | Path,
    plan: Mapping[str, Any],
    *,
    confirm_plan_sha256: str,
    applied_at: str | None = None,
) -> dict[str, Any]:
    root = _resolve_workspace(workspace)
    checked = validate_plan(plan)
    if confirm_plan_sha256 != checked["plan_sha256"]:
        raise PilotCloseoutError(
            "explicit confirmation hash does not match closeout plan"
        )
    if root.name != checked["workspace_label"]:
        raise PilotCloseoutError(
            "workspace label differs from the planned workspace"
        )

    current_paths = set(_scan_workspace(root))
    planned_paths = {entry["path"] for entry in checked["entries"]}
    if current_paths != planned_paths:
        raise PilotCloseoutError(
            "workspace file set changed after planning; aborting closeout"
        )

    by_path = {entry["path"]: entry for entry in checked["entries"]}
    for rel in sorted(planned_paths):
        current = _file_record(root, rel, by_path[rel]["action"])
        expected = by_path[rel]
        if current["size"] != expected["size"] or current["sha256"] != expected["sha256"]:
            raise PilotCloseoutError(
                f"workspace file changed after planning; aborting closeout: {rel}"
            )

    deleted: list[dict[str, Any]] = []
    retained: list[dict[str, Any]] = []
    for entry in checked["entries"]:
        record = {
            "path": entry["path"],
            "size": entry["size"],
            "sha256": entry["sha256"],
        }
        target = root / Path(*PurePosixPath(entry["path"]).parts)
        if entry["action"] == "DELETE":
            if target.is_symlink() or not target.is_file():
                raise PilotCloseoutError(
                    f"delete target changed type before unlink: {entry['path']}"
                )
            target.unlink()
            deleted.append(record)
        else:
            retained.append(record)

    for entry in deleted:
        target = root / Path(*PurePosixPath(entry["path"]).parts)
        if target.exists() or target.is_symlink():
            raise PilotCloseoutError(
                f"delete target still exists after unlink: {entry['path']}"
            )
    for entry in retained:
        current = _file_record(root, entry["path"], "RETAIN")
        if current["size"] != entry["size"] or current["sha256"] != entry["sha256"]:
            raise PilotCloseoutError(
                f"retained file changed during closeout: {entry['path']}"
            )

    receipt: dict[str, Any] = {
        "format": RECEIPT_FORMAT,
        "hash_format": RECEIPT_HASH_FORMAT,
        "pilot_id": checked["pilot_id"],
        "workspace_label": checked["workspace_label"],
        "plan_sha256": checked["plan_sha256"],
        "applied_at": applied_at or _utc_now(),
        "deleted": sorted(deleted, key=lambda item: item["path"]),
        "retained": sorted(retained, key=lambda item: item["path"]),
        "receipt_sha256": "",
    }
    receipt["receipt_sha256"] = receipt_sha256(receipt)
    return validate_receipt(receipt)


def write_closeout_receipt(
    output: str | Path,
    receipt: Mapping[str, Any],
    *,
    overwrite: bool = False,
) -> Path:
    checked = validate_receipt(receipt)
    return _atomic_write(output, checked, overwrite=overwrite)
