from __future__ import annotations

import hashlib
import tempfile
from collections.abc import Mapping
from pathlib import Path, PurePosixPath
from typing import Any

from .canonical_json import CanonicalJSONError, canonicalize_jcs, parse_jcs_json
from .environment_v06 import (
    ENVIRONMENT_CAPTURE_FORMAT_V06,
    ENVIRONMENT_CONTRACT_NAMESPACE_V06,
    capture_environment_v06,
)
from .package_v06 import MAX_PACKAGE_SINGLE_FILE_V06, MAX_PACKAGE_TOTAL_BYTES_V06


ENVIRONMENT_BINDING_FORMAT_V06 = "pcs-environment-binding-v1"


class V06EnvironmentReplayError(ValueError):
    pass


def _safe_source_path(value: str) -> None:
    if not isinstance(value, str) or not value or "\\" in value:
        raise V06EnvironmentReplayError(f"unsafe environment source path: {value!r}")
    path = PurePosixPath(value)
    if (
        path.is_absolute()
        or path.as_posix() != value
        or value.endswith("/")
        or any(part in ("", ".", "..") for part in path.parts)
    ):
        raise V06EnvironmentReplayError(f"unsafe environment source path: {value!r}")


def environment_binding_v06(environment: dict[str, Any] | None) -> dict[str, Any] | None:
    if environment is None:
        return None
    if environment.get("format") != ENVIRONMENT_CAPTURE_FORMAT_V06:
        raise V06EnvironmentReplayError("unsupported environment capture format")
    if environment.get("human_confirmed") is not True:
        raise V06EnvironmentReplayError(
            "environment capture must be human-confirmed before attestation"
        )
    source_ids = environment.get("source_artifact_ids")
    if not isinstance(source_ids, list) or not all(isinstance(x, str) for x in source_ids):
        raise V06EnvironmentReplayError("environment source_artifact_ids must be strings")
    proposition = canonicalize_jcs(environment)
    if len(proposition.encode("utf-8")) > 1048576:
        raise V06EnvironmentReplayError("environment proposition exceeds 1 MiB limit")
    return {
        "format": ENVIRONMENT_BINDING_FORMAT_V06,
        "source_artifact_ids": list(source_ids),
        "contract": {
            "type": "external",
            "namespace": ENVIRONMENT_CONTRACT_NAMESPACE_V06,
            "proposition": proposition,
        },
    }


def _parse_binding(binding: dict[str, Any]) -> dict[str, Any]:
    if binding.get("format") != ENVIRONMENT_BINDING_FORMAT_V06:
        raise V06EnvironmentReplayError("unsupported environment binding format")
    contract = binding.get("contract")
    if not isinstance(contract, dict):
        raise V06EnvironmentReplayError("environment binding contract missing")
    if contract.get("type") != "external":
        raise V06EnvironmentReplayError("environment binding contract must be external")
    if contract.get("namespace") != ENVIRONMENT_CONTRACT_NAMESPACE_V06:
        raise V06EnvironmentReplayError("environment contract namespace mismatch")
    proposition = contract.get("proposition")
    if not isinstance(proposition, str):
        raise V06EnvironmentReplayError("environment proposition must be a string")
    try:
        value = parse_jcs_json(proposition)
    except CanonicalJSONError as exc:
        raise V06EnvironmentReplayError(
            f"environment proposition is invalid JCS: {exc}"
        ) from exc
    if canonicalize_jcs(value) != proposition:
        raise V06EnvironmentReplayError("environment proposition is not canonical JCS")
    if not isinstance(value, dict) or value.get("format") != ENVIRONMENT_CAPTURE_FORMAT_V06:
        raise V06EnvironmentReplayError("environment proposition format mismatch")
    if value.get("human_confirmed") is not True:
        raise V06EnvironmentReplayError("environment proposition is not human-confirmed")
    if value.get("static_only") is not True:
        raise V06EnvironmentReplayError("environment capture must declare static_only=true")
    if value.get("network_accessed") is not False:
        raise V06EnvironmentReplayError(
            "environment capture must declare network_accessed=false"
        )
    if value.get("user_code_executed") is not False:
        raise V06EnvironmentReplayError(
            "environment capture must declare user_code_executed=false"
        )
    return value


def environment_from_binding_v06(binding: dict[str, Any]) -> dict[str, Any]:
    return _parse_binding(binding)


def _artifact_inventory(
    certificate: dict[str, Any],
    package_files: Mapping[str, bytes],
) -> tuple[list[dict[str, Any]], dict[str, bytes]]:
    inventory: list[dict[str, Any]] = []
    bytes_by_id: dict[str, bytes] = {}
    source_paths: set[str] = set()
    total = 0
    for artifact in certificate.get("artifacts", []):
        source_path = artifact.get("source_path")
        if not isinstance(source_path, str):
            continue
        _safe_source_path(source_path)
        if source_path in source_paths:
            raise V06EnvironmentReplayError(
                f"duplicate certificate source_path: {source_path!r}"
            )
        source_paths.add(source_path)
        package_path = artifact.get("path")
        raw = package_files.get(package_path)
        if not isinstance(raw, bytes):
            raise V06EnvironmentReplayError(
                f"environment artifact {artifact.get('id')} missing bytes"
            )
        if len(raw) > MAX_PACKAGE_SINGLE_FILE_V06:
            raise V06EnvironmentReplayError(
                f"environment artifact {artifact.get('id')} exceeds single-file limit"
            )
        total += len(raw)
        if total > MAX_PACKAGE_TOTAL_BYTES_V06:
            raise V06EnvironmentReplayError(
                "environment replay artifacts exceed total byte limit"
            )
        digest = hashlib.sha256(raw).hexdigest()
        if digest != artifact.get("sha256"):
            raise V06EnvironmentReplayError(
                f"environment artifact hash mismatch: {artifact.get('id')}"
            )
        inventory.append(
            {
                "artifact_id": artifact["id"],
                "path": source_path,
                "size": len(raw),
                "sha256": digest,
                "media_type": artifact.get("media_type", "application/octet-stream"),
                "role": artifact.get("role", "scientific-artifact"),
            }
        )
        bytes_by_id[artifact["id"]] = raw
    return inventory, bytes_by_id


def _replay_projection(value: dict[str, Any]) -> dict[str, Any]:
    out = dict(value)
    out.pop("human_confirmed", None)
    out.pop("confirmation_scope", None)
    return out


def verify_environment_replay_v06(
    certificate: dict[str, Any],
    package_files: Mapping[str, bytes],
) -> dict[str, Any]:
    """Re-derive a signed reproducibility-environment contract from delivered bytes.

    This verifies environment *description/provenance*. It does not run package
    managers, download dependencies, build containers, or execute user code.
    """
    binding = certificate.get("environment")
    if binding is None:
        return {
            "valid": True,
            "errors": [],
            "mode": "no-environment-contract",
            "hermeticity": None,
            "source_files_checked": 0,
            "replay_plan": None,
            "_authority_fresh_capture": None,
        }

    try:
        if not isinstance(binding, dict):
            raise V06EnvironmentReplayError("certificate environment must be an object")
        signed = _parse_binding(binding)
        inventory, bytes_by_id = _artifact_inventory(certificate, package_files)
        inventory_by_id = {item["artifact_id"]: item for item in inventory}

        bound_ids = binding.get("source_artifact_ids")
        if not isinstance(bound_ids, list) or len(bound_ids) != len(set(bound_ids)):
            raise V06EnvironmentReplayError(
                "environment source_artifact_ids must be a unique array"
            )
        signed_ids = signed.get("source_artifact_ids")
        if bound_ids != signed_ids:
            raise V06EnvironmentReplayError(
                "environment binding source ids differ from signed proposition"
            )
        for artifact_id in bound_ids:
            if artifact_id not in inventory_by_id:
                raise V06EnvironmentReplayError(
                    f"environment references unknown artifact {artifact_id!r}"
                )

        with tempfile.TemporaryDirectory(prefix="pcs-v06-environment-replay-") as tmp:
            root = Path(tmp)
            for item in inventory:
                target = root / item["path"]
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(bytes_by_id[item["artifact_id"]])
            fresh = capture_environment_v06(root, inventory)

        if canonicalize_jcs(_replay_projection(signed)) != canonicalize_jcs(fresh):
            raise V06EnvironmentReplayError(
                "signed environment contract differs from fresh capture over delivered bytes"
            )

        fresh_ids = fresh.get("source_artifact_ids", [])
        if bound_ids != fresh_ids:
            raise V06EnvironmentReplayError(
                "environment source artifact set differs from fresh capture"
            )

        return {
            "valid": True,
            "errors": [],
            "mode": "static-environment-rederived",
            "hermeticity": fresh.get("hermeticity"),
            "source_files_checked": len(fresh_ids),
            "dependency_records": fresh.get("summary", {}).get(
                "dependency_records", 0
            ),
            "unresolved_items": fresh.get("summary", {}).get(
                "unresolved_items", 0
            ),
            "replay_plan": fresh.get("replay_plan"),
            "_authority_fresh_capture": fresh,
        }
    except (V06EnvironmentReplayError, OSError, ValueError) as exc:
        return {
            "valid": False,
            "errors": [str(exc)],
            "mode": "static-environment-rederived",
            "hermeticity": None,
            "source_files_checked": 0,
            "dependency_records": 0,
            "unresolved_items": 0,
            "replay_plan": None,
            "_authority_fresh_capture": None,
        }
