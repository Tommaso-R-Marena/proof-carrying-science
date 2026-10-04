from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from .canonical_json import canonicalize_jcs_bytes
from .checks.splits import StrictCSVError, parse_strict_csv
from .decomposition_proposer_v06 import (
    DECOMPOSITION_PROPOSER_REQUEST_FORMAT_V06,
    V06DecompositionProposerError,
    verify_decomposition_proposer_request_v06,
)
from .discover_v06 import V06DiscoveryError, discover_project_v06
from .jsonio import StrictJSONError, strict_json_load, strict_json_loads
from .proof_search_v06 import V06ProofSearchError, verify_proof_search_session_v06


ARTIFACT_INSPECTION_QUERY_FORMAT_V06 = "pcs-artifact-inspection-query-v1"
ARTIFACT_INSPECTION_RESULT_FORMAT_V06 = "pcs-artifact-inspection-result-v1"
ARTIFACT_INSPECTION_PROTOCOL_V06 = "pcs-artifact-inspection-protocol/0.1"

MAX_INSPECTION_OPERATIONS_V06 = 8
MAX_JSON_FIELDS_V06 = 16
MAX_JSON_ARTIFACT_BYTES_V06 = 2 * 1024 * 1024
MAX_TEXT_ARTIFACT_BYTES_V06 = 2 * 1024 * 1024
MAX_TEXT_LINES_V06 = 40
MAX_TEXT_LINE_CHARS_V06 = 2048
MAX_CSV_HEADER_BYTES_V06 = 64 * 1024
MAX_JSON_VALUE_BYTES_V06 = 4096
MAX_INSPECTION_RESULT_BYTES_V06 = 64 * 1024

_ALLOWED_QUERY_KEYS = {
    "format",
    "decomposition_request_sha256",
    "search_id",
    "inventory_commitment_sha256",
    "operations",
}
_COMMON_OPERATION_KEYS = {"id", "artifact_id", "view"}


class V06ArtifactInspectionError(ValueError):
    pass


def artifact_inspection_contract_v06() -> dict[str, Any]:
    return {
        "query_format": ARTIFACT_INSPECTION_QUERY_FORMAT_V06,
        "result_format": ARTIFACT_INSPECTION_RESULT_FORMAT_V06,
        "protocol": ARTIFACT_INSPECTION_PROTOCOL_V06,
        "allowed_views": {
            "csv_header": {
                "required_fields": ["id", "artifact_id", "view"],
                "scope": "bounded strict-CSV header only; full checker reparses full artifact",
            },
            "json_fields": {
                "required_fields": ["id", "artifact_id", "view", "fields"],
                "max_fields": MAX_JSON_FIELDS_V06,
                "field_syntax": "RFC6901-style JSON pointer",
                "max_artifact_bytes": MAX_JSON_ARTIFACT_BYTES_V06,
            },
            "text_lines": {
                "required_fields": [
                    "id",
                    "artifact_id",
                    "view",
                    "start_line",
                    "max_lines",
                ],
                "max_lines": MAX_TEXT_LINES_V06,
                "max_line_chars": MAX_TEXT_LINE_CHARS_V06,
                "max_artifact_bytes": MAX_TEXT_ARTIFACT_BYTES_V06,
            },
        },
        "bounds": {
            "max_operations": MAX_INSPECTION_OPERATIONS_V06,
            "max_result_bytes": MAX_INSPECTION_RESULT_BYTES_V06,
            "max_csv_header_bytes": MAX_CSV_HEADER_BYTES_V06,
            "max_json_value_bytes": MAX_JSON_VALUE_BYTES_V06,
        },
        "authority": {
            "sets_authoritative": False,
            "changes_search_state": False,
            "filesystem_paths_supplied_by_model": False,
            "only_target_bound_artifact_ids_allowed": True,
            "full_artifact_sha256_rechecked_before_observation": True,
        },
    }


def _clone(value: Any) -> Any:
    return json.loads(json.dumps(value))


def _commitment(value: Any) -> str:
    return hashlib.sha256(canonicalize_jcs_bytes(value)).hexdigest()


def _nonempty(value: Any, *, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise V06ArtifactInspectionError(
            f"{label} must be a non-empty string"
        )
    return value


def _stream_sha256(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as handle:
        while True:
            block = handle.read(1024 * 1024)
            if not block:
                break
            digest.update(block)
            size += len(block)
    return digest.hexdigest(), size


def _inventory_by_id(discovery: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    raw = discovery.get("inventory")
    if not isinstance(raw, list):
        raise V06ArtifactInspectionError(
            "project discovery inventory must be an array"
        )
    out: dict[str, Mapping[str, Any]] = {}
    for item in raw:
        if not isinstance(item, Mapping):
            continue
        artifact_id = item.get("artifact_id")
        if isinstance(artifact_id, str):
            out[artifact_id] = item
    return out


def _artifact_path(
    root: Path,
    item: Mapping[str, Any],
) -> Path:
    relative = item.get("path")
    if not isinstance(relative, str) or not relative:
        raise V06ArtifactInspectionError(
            "committed artifact lacks a valid relative path"
        )
    literal = root / relative
    if literal.is_symlink():
        raise V06ArtifactInspectionError(
            f"committed artifact became a symlink: {relative}"
        )
    resolved = literal.resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise V06ArtifactInspectionError(
            f"committed artifact escapes project root: {relative}"
        ) from exc
    if not resolved.is_file():
        raise V06ArtifactInspectionError(
            f"committed artifact is no longer a regular file: {relative}"
        )
    return resolved


def _verify_artifact_snapshot(
    root: Path,
    item: Mapping[str, Any],
) -> tuple[Path, str, int]:
    path = _artifact_path(root, item)
    digest, size = _stream_sha256(path)
    if digest != item.get("sha256") or size != item.get("size"):
        raise V06ArtifactInspectionError(
            f"artifact bytes changed since discovery: {item.get('artifact_id')}"
        )
    return path, digest, size


def _normalize_json_pointer(pointer: Any) -> str:
    if not isinstance(pointer, str):
        raise V06ArtifactInspectionError(
            "JSON field pointer must be a string"
        )
    if pointer == "":
        return pointer
    if not pointer.startswith("/"):
        raise V06ArtifactInspectionError(
            "JSON field pointer must be empty or start with '/'"
        )
    if len(pointer) > 1024:
        raise V06ArtifactInspectionError(
            "JSON field pointer is too long"
        )
    return pointer


def _pointer_tokens(pointer: str) -> list[str]:
    if pointer == "":
        return []
    tokens = []
    for raw in pointer[1:].split("/"):
        index = 0
        chars: list[str] = []
        while index < len(raw):
            if raw[index] != "~":
                chars.append(raw[index])
                index += 1
                continue
            if index + 1 >= len(raw) or raw[index + 1] not in {"0", "1"}:
                raise V06ArtifactInspectionError(
                    f"invalid JSON pointer escape in {pointer!r}"
                )
            chars.append("~" if raw[index + 1] == "0" else "/")
            index += 2
        tokens.append("".join(chars))
    return tokens


def _resolve_pointer(value: Any, pointer: str) -> tuple[bool, Any]:
    current = value
    for token in _pointer_tokens(pointer):
        if isinstance(current, Mapping):
            if token not in current:
                return False, None
            current = current[token]
            continue
        if isinstance(current, list):
            if not token.isdigit():
                return False, None
            index = int(token)
            if index < 0 or index >= len(current):
                return False, None
            current = current[index]
            continue
        return False, None
    return True, current


def _json_type(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, str):
        return "string"
    if isinstance(value, (int, float)):
        return "number"
    if isinstance(value, list):
        return "array"
    if isinstance(value, Mapping):
        return "object"
    return type(value).__name__


def _bounded_json_value(value: Any) -> dict[str, Any]:
    encoded = canonicalize_jcs_bytes(value)
    result: dict[str, Any] = {
        "type": _json_type(value),
        "canonical_size": len(encoded),
        "value_sha256": hashlib.sha256(encoded).hexdigest(),
    }
    if len(encoded) <= MAX_JSON_VALUE_BYTES_V06:
        result["value"] = _clone(value)
        result["truncated"] = False
    else:
        result["truncated"] = True
    return result


def _inspect_csv_header(path: Path) -> dict[str, Any]:
    with path.open("rb") as handle:
        prefix = handle.read(MAX_CSV_HEADER_BYTES_V06 + 1)
    newline = prefix.find(b"\n")
    if newline >= 0:
        header_bytes = prefix[: newline + 1]
    else:
        if len(prefix) > MAX_CSV_HEADER_BYTES_V06:
            raise V06ArtifactInspectionError(
                "CSV header exceeds bounded inspection limit"
            )
        header_bytes = prefix
    try:
        header, _ = parse_strict_csv(header_bytes)
        decoded = [field.decode("utf-8") for field in header]
    except (StrictCSVError, UnicodeDecodeError) as exc:
        raise V06ArtifactInspectionError(
            f"CSV header is outside the strict PCS subset: {exc}"
        ) from exc
    return {
        "profile": "pcs-strict-csv-v1-header-only",
        "columns": decoded,
        "column_count": len(decoded),
        "scope_warning": (
            "This observation validates only the bounded header parse. "
            "Any later CSV checker reparses the full committed artifact."
        ),
    }


def _inspect_json_fields(
    path: Path,
    *,
    fields: Sequence[str],
    size: int,
) -> dict[str, Any]:
    if size > MAX_JSON_ARTIFACT_BYTES_V06:
        raise V06ArtifactInspectionError(
            "JSON artifact exceeds bounded inspection size limit"
        )
    try:
        value = strict_json_loads(path.read_bytes().decode("utf-8"))
    except (OSError, UnicodeDecodeError, StrictJSONError) as exc:
        raise V06ArtifactInspectionError(
            f"artifact is not strict UTF-8 JSON: {exc}"
        ) from exc
    rows = []
    for pointer in fields:
        found, selected = _resolve_pointer(value, pointer)
        row: dict[str, Any] = {
            "pointer": pointer,
            "found": found,
        }
        if found:
            row.update(_bounded_json_value(selected))
        rows.append(row)
    return {
        "profile": "strict-json-bounded-pointer-v1",
        "fields": rows,
    }


def _inspect_text_lines(
    path: Path,
    *,
    start_line: int,
    max_lines: int,
    size: int,
) -> dict[str, Any]:
    if size > MAX_TEXT_ARTIFACT_BYTES_V06:
        raise V06ArtifactInspectionError(
            "text artifact exceeds bounded inspection size limit"
        )
    try:
        text = path.read_bytes().decode("utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise V06ArtifactInspectionError(
            f"artifact is not bounded UTF-8 text: {exc}"
        ) from exc
    lines = text.splitlines()
    start_index = start_line - 1
    chosen = lines[start_index : start_index + max_lines]
    rendered = []
    for offset, line in enumerate(chosen):
        truncated = len(line) > MAX_TEXT_LINE_CHARS_V06
        rendered.append(
            {
                "line": start_line + offset,
                "text": line[:MAX_TEXT_LINE_CHARS_V06],
                "truncated": truncated,
                "full_line_sha256": hashlib.sha256(
                    line.encode("utf-8")
                ).hexdigest(),
            }
        )
    return {
        "profile": "utf8-line-range-v1",
        "start_line": start_line,
        "requested_max_lines": max_lines,
        "returned_lines": rendered,
        "total_line_count": len(lines),
    }


def _normalize_operation(
    raw: Mapping[str, Any],
    *,
    allowed_artifact_ids: set[str],
) -> dict[str, Any]:
    operation_id = _nonempty(raw.get("id"), label="inspection operation id")
    artifact_id = _nonempty(
        raw.get("artifact_id"),
        label=f"inspection operation {operation_id} artifact_id",
    )
    if artifact_id not in allowed_artifact_ids:
        raise V06ArtifactInspectionError(
            f"inspection operation {operation_id!r} targets artifact "
            f"{artifact_id!r} outside the unresolved claim's bound artifacts"
        )
    view = raw.get("view")
    if view == "csv_header":
        allowed = _COMMON_OPERATION_KEYS
        normalized = {
            "id": operation_id,
            "artifact_id": artifact_id,
            "view": view,
        }
    elif view == "json_fields":
        allowed = _COMMON_OPERATION_KEYS | {"fields"}
        fields = raw.get("fields")
        if (
            not isinstance(fields, list)
            or not 1 <= len(fields) <= MAX_JSON_FIELDS_V06
        ):
            raise V06ArtifactInspectionError(
                f"inspection operation {operation_id!r} JSON fields must contain "
                f"1..{MAX_JSON_FIELDS_V06} pointers"
            )
        normalized_fields = [_normalize_json_pointer(item) for item in fields]
        if len(normalized_fields) != len(set(normalized_fields)):
            raise V06ArtifactInspectionError(
                f"inspection operation {operation_id!r} repeats a JSON pointer"
            )
        for pointer in normalized_fields:
            _pointer_tokens(pointer)
        normalized = {
            "id": operation_id,
            "artifact_id": artifact_id,
            "view": view,
            "fields": normalized_fields,
        }
    elif view == "text_lines":
        allowed = _COMMON_OPERATION_KEYS | {"start_line", "max_lines"}
        start_line = raw.get("start_line")
        max_lines = raw.get("max_lines")
        if (
            isinstance(start_line, bool)
            or not isinstance(start_line, int)
            or start_line < 1
        ):
            raise V06ArtifactInspectionError(
                f"inspection operation {operation_id!r} start_line must be >= 1"
            )
        if (
            isinstance(max_lines, bool)
            or not isinstance(max_lines, int)
            or not 1 <= max_lines <= MAX_TEXT_LINES_V06
        ):
            raise V06ArtifactInspectionError(
                f"inspection operation {operation_id!r} max_lines must be in "
                f"[1,{MAX_TEXT_LINES_V06}]"
            )
        normalized = {
            "id": operation_id,
            "artifact_id": artifact_id,
            "view": view,
            "start_line": start_line,
            "max_lines": max_lines,
        }
    else:
        raise V06ArtifactInspectionError(
            f"inspection operation {operation_id!r} uses unsupported view {view!r}"
        )
    unexpected = sorted(set(raw) - allowed)
    if unexpected:
        raise V06ArtifactInspectionError(
            f"inspection operation {operation_id!r} contains unsupported fields: "
            f"{unexpected}"
        )
    return normalized


def _normalize_query(
    session: Mapping[str, Any],
    decomposition_request: Mapping[str, Any],
    query: Mapping[str, Any],
) -> dict[str, Any]:
    unexpected = sorted(set(query) - _ALLOWED_QUERY_KEYS)
    if unexpected:
        raise V06ArtifactInspectionError(
            f"artifact inspection query contains unsupported fields: {unexpected}"
        )
    if query.get("format") != ARTIFACT_INSPECTION_QUERY_FORMAT_V06:
        raise V06ArtifactInspectionError(
            "artifact inspection query has unsupported format"
        )
    if query.get("decomposition_request_sha256") != decomposition_request.get(
        "decomposition_request_sha256"
    ):
        raise V06ArtifactInspectionError(
            "artifact inspection query is bound to a different decomposition request"
        )
    if query.get("search_id") != session.get("search_id"):
        raise V06ArtifactInspectionError(
            "artifact inspection query is bound to a different proof search"
        )
    if query.get("inventory_commitment_sha256") != session.get(
        "inventory_commitment_sha256"
    ):
        raise V06ArtifactInspectionError(
            "artifact inspection query is bound to a different project inventory"
        )
    target = decomposition_request.get("target")
    if not isinstance(target, Mapping):
        raise V06ArtifactInspectionError(
            "decomposition request lacks a target object"
        )
    allowed_artifact_ids = {
        str(item)
        for item in target.get("artifact_ids", [])
        if isinstance(item, str)
    }
    raw_operations = query.get("operations")
    if (
        not isinstance(raw_operations, list)
        or not 1 <= len(raw_operations) <= MAX_INSPECTION_OPERATIONS_V06
    ):
        raise V06ArtifactInspectionError(
            f"artifact inspection requires 1..{MAX_INSPECTION_OPERATIONS_V06} operations"
        )
    operations = [
        _normalize_operation(
            raw,
            allowed_artifact_ids=allowed_artifact_ids,
        )
        if isinstance(raw, Mapping)
        else (_ for _ in ()).throw(
            V06ArtifactInspectionError(
                "artifact inspection operation must be an object"
            )
        )
        for raw in raw_operations
    ]
    operation_ids = [item["id"] for item in operations]
    if len(operation_ids) != len(set(operation_ids)):
        raise V06ArtifactInspectionError(
            "artifact inspection operation ids must be unique"
        )
    return {
        "format": ARTIFACT_INSPECTION_QUERY_FORMAT_V06,
        "decomposition_request_sha256": decomposition_request[
            "decomposition_request_sha256"
        ],
        "search_id": session["search_id"],
        "inventory_commitment_sha256": session[
            "inventory_commitment_sha256"
        ],
        "operations": operations,
    }


def inspect_artifacts_v06(
    project_root: str | Path,
    session: Mapping[str, Any],
    decomposition_request: Mapping[str, Any],
    query: Mapping[str, Any],
) -> dict[str, Any]:
    try:
        verify_proof_search_session_v06(session)
        verify_decomposition_proposer_request_v06(
            project_root,
            session,
            decomposition_request,
        )
    except (V06ProofSearchError, V06DecompositionProposerError) as exc:
        raise V06ArtifactInspectionError(str(exc)) from exc
    if decomposition_request.get("format") != DECOMPOSITION_PROPOSER_REQUEST_FORMAT_V06:
        raise V06ArtifactInspectionError(
            "artifact inspection requires a decomposition proposer request"
        )

    normalized_query = _normalize_query(
        session,
        decomposition_request,
        query,
    )
    root = Path(project_root).resolve()
    try:
        discovery = discover_project_v06(
            root,
            subject=(
                str(session["subject"])
                if session.get("subject") is not None
                else None
            ),
        )
    except (OSError, V06DiscoveryError) as exc:
        raise V06ArtifactInspectionError(
            f"cannot reconstruct committed project inventory: {exc}"
        ) from exc
    if discovery.get("inventory_commitment_sha256") != session.get(
        "inventory_commitment_sha256"
    ):
        raise V06ArtifactInspectionError(
            "project inventory changed since proof search began"
        )
    inventory = _inventory_by_id(discovery)

    observations = []
    for operation in normalized_query["operations"]:
        artifact_id = operation["artifact_id"]
        item = inventory.get(artifact_id)
        if item is None:
            raise V06ArtifactInspectionError(
                f"inspection artifact {artifact_id!r} is absent from current inventory"
            )
        path, digest, size = _verify_artifact_snapshot(root, item)
        view = operation["view"]
        if view == "csv_header":
            payload = _inspect_csv_header(path)
        elif view == "json_fields":
            payload = _inspect_json_fields(
                path,
                fields=operation["fields"],
                size=size,
            )
        else:
            payload = _inspect_text_lines(
                path,
                start_line=operation["start_line"],
                max_lines=operation["max_lines"],
                size=size,
            )
        observation_core = {
            "operation_id": operation["id"],
            "artifact_id": artifact_id,
            "artifact_path": item.get("path"),
            "artifact_sha256": digest,
            "artifact_size": size,
            "view": view,
            "observation": payload,
        }
        observations.append(
            {
                **observation_core,
                "observation_sha256": _commitment(observation_core),
            }
        )

    query_sha256 = _commitment(normalized_query)
    result_core = {
        "format": ARTIFACT_INSPECTION_RESULT_FORMAT_V06,
        "protocol": ARTIFACT_INSPECTION_PROTOCOL_V06,
        "search_id": session["search_id"],
        "decomposition_request_sha256": decomposition_request[
            "decomposition_request_sha256"
        ],
        "inventory_commitment_sha256": session[
            "inventory_commitment_sha256"
        ],
        "artifact_inspection_query": normalized_query,
        "artifact_inspection_query_sha256": query_sha256,
        "observations": observations,
        "authority": {
            "sets_authoritative": False,
            "changes_search_state": False,
            "artifact_bytes_authority": "SHA256_BOUND_OBSERVATION_ONLY",
            "observations_require_later_deterministic_grounding": True,
            "model_may_not_treat_inspection_as_checker_acceptance": True,
            "human_confirmation_still_required": True,
            "replay_and_lean_authority_still_required": True,
        },
    }
    encoded = canonicalize_jcs_bytes(result_core)
    if len(encoded) > MAX_INSPECTION_RESULT_BYTES_V06:
        raise V06ArtifactInspectionError(
            "artifact inspection result exceeds bounded output size limit"
        )
    return {
        **result_core,
        "inspection_result_sha256": hashlib.sha256(encoded).hexdigest(),
    }


def verify_artifact_inspection_result_v06(
    project_root: str | Path,
    session: Mapping[str, Any],
    decomposition_request: Mapping[str, Any],
    result: Mapping[str, Any],
) -> None:
    if result.get("format") != ARTIFACT_INSPECTION_RESULT_FORMAT_V06:
        raise V06ArtifactInspectionError(
            "artifact inspection result has unsupported format"
        )
    query = result.get("artifact_inspection_query")
    if not isinstance(query, Mapping):
        raise V06ArtifactInspectionError(
            "artifact inspection result lacks embedded query"
        )
    expected = inspect_artifacts_v06(
        project_root,
        session,
        decomposition_request,
        query,
    )
    if result != expected:
        raise V06ArtifactInspectionError(
            "artifact inspection result does not exactly match committed project bytes"
        )


def load_artifact_inspection_query_v06(
    path: str | Path,
) -> dict[str, Any]:
    resolved = Path(path).resolve()
    try:
        value = strict_json_load(resolved)
    except (OSError, StrictJSONError) as exc:
        raise V06ArtifactInspectionError(
            f"cannot load artifact inspection query {resolved}: {exc}"
        ) from exc
    if not isinstance(value, dict):
        raise V06ArtifactInspectionError(
            "artifact inspection query root must be an object"
        )
    return value


def load_artifact_inspection_result_v06(
    path: str | Path,
) -> dict[str, Any]:
    resolved = Path(path).resolve()
    try:
        value = strict_json_load(resolved)
    except (OSError, StrictJSONError) as exc:
        raise V06ArtifactInspectionError(
            f"cannot load artifact inspection result {resolved}: {exc}"
        ) from exc
    if not isinstance(value, dict):
        raise V06ArtifactInspectionError(
            "artifact inspection result root must be an object"
        )
    return value


def write_artifact_inspection_result_v06(
    result: Mapping[str, Any],
    path: str | Path,
    *,
    overwrite: bool = False,
) -> str:
    if result.get("format") != ARTIFACT_INSPECTION_RESULT_FORMAT_V06:
        raise V06ArtifactInspectionError(
            "refusing to write invalid artifact inspection result"
        )
    output = Path(path).resolve()
    if output.exists() and not overwrite:
        raise V06ArtifactInspectionError(
            f"refusing to overwrite existing artifact inspection result: {output}"
        )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(
            dict(result),
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    return str(output)
