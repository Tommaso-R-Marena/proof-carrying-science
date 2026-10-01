from __future__ import annotations

import hashlib
import json
import tempfile
from collections.abc import Mapping
from pathlib import Path, PurePosixPath
from typing import Any

from .canonical_json import CanonicalJSONError, canonicalize_jcs, parse_jcs_json
from .package_v06 import MAX_PACKAGE_SINGLE_FILE_V06, MAX_PACKAGE_TOTAL_BYTES_V06
from .workflow_discovery_v06 import (
    WORKFLOW_DISCOVERY_FORMAT_V06,
    analyze_static_workflow_v06,
)


WORKFLOW_CONTRACT_NAMESPACE_V06 = "pcs-manifest-workflow-contract-v1"


class V06WorkflowReplayError(ValueError):
    pass


def _safe_source_path(value: str) -> None:
    if not isinstance(value, str) or not value or "\\" in value:
        raise V06WorkflowReplayError(f"unsafe workflow source path: {value!r}")
    path = PurePosixPath(value)
    if (
        path.is_absolute()
        or path.as_posix() != value
        or value.endswith("/")
        or any(part in ("", ".", "..") for part in path.parts)
    ):
        raise V06WorkflowReplayError(f"unsafe workflow source path: {value!r}")


def _static_contract(node: dict[str, Any]) -> dict[str, Any] | None:
    contract = node.get("contract")
    if not isinstance(contract, dict):
        return None
    if contract.get("type") != "external":
        return None
    if contract.get("namespace") != WORKFLOW_CONTRACT_NAMESPACE_V06:
        return None
    proposition = contract.get("proposition")
    if not isinstance(proposition, str):
        raise V06WorkflowReplayError(
            f"workflow node {node.get('id')!r} has non-string proposition"
        )
    try:
        value = parse_jcs_json(proposition)
    except CanonicalJSONError as exc:
        raise V06WorkflowReplayError(
            f"workflow node {node.get('id')!r} proposition is invalid JCS: {exc}"
        ) from exc
    if canonicalize_jcs(value) != proposition:
        raise V06WorkflowReplayError(
            f"workflow node {node.get('id')!r} proposition is not canonical JCS"
        )
    if not isinstance(value, dict):
        return None
    if value.get("inference_format") != WORKFLOW_DISCOVERY_FORMAT_V06:
        return None
    return value


def _artifact_bytes(
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
            raise V06WorkflowReplayError(
                f"duplicate certificate source_path: {source_path!r}"
            )
        source_paths.add(source_path)

        package_path = artifact["path"]
        raw = package_files.get(package_path)
        if not isinstance(raw, bytes):
            raise V06WorkflowReplayError(
                f"workflow artifact {artifact['id']} missing bytes at {package_path!r}"
            )
        if len(raw) > MAX_PACKAGE_SINGLE_FILE_V06:
            raise V06WorkflowReplayError(
                f"workflow artifact {artifact['id']} exceeds single-file limit"
            )
        total += len(raw)
        if total > MAX_PACKAGE_TOTAL_BYTES_V06:
            raise V06WorkflowReplayError(
                "workflow replay artifacts exceed total byte limit"
            )
        digest = hashlib.sha256(raw).hexdigest()
        if digest != artifact["sha256"]:
            raise V06WorkflowReplayError(
                f"workflow artifact hash mismatch: {artifact['id']}"
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


def _reference_key(ref: dict[str, Any]) -> tuple[str, str, str]:
    return (
        str(ref.get("kind")),
        str(ref.get("path")),
        str(ref.get("artifact_id")),
    )


def _validate_claim_contract(
    node: dict[str, Any],
    signed: dict[str, Any],
    fresh_source: dict[str, Any],
    fresh_node: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    node_id = node["id"]

    required_truths = {
        "static_only": True,
        "user_code_executed": False,
        "human_confirmed": True,
    }
    for key, expected in required_truths.items():
        if signed.get(key) is not expected:
            errors.append(
                f"workflow node {node_id} requires {key}={expected!r}"
            )

    if signed.get("inference_id") != fresh_source.get("id"):
        errors.append(
            f"workflow node {node_id} inference id does not match fresh source analysis"
        )
    if signed.get("source_path") != fresh_source.get("source_path"):
        errors.append(
            f"workflow node {node_id} source path does not match fresh source analysis"
        )
    if signed.get("source_kind") != fresh_source.get("source_kind"):
        errors.append(
            f"workflow node {node_id} source kind does not match fresh source analysis"
        )

    mode = signed.get("dependency_claim_mode")
    if mode not in {"exact_resolved_set", "claimed_subset"}:
        errors.append(
            f"workflow node {node_id} has unsupported dependency_claim_mode {mode!r}"
        )
        return errors

    source_artifact = fresh_source["source_artifact_id"]
    claimed_inputs = set(node.get("inputs", []))
    fresh_inputs = set(fresh_node.get("inputs", []))
    claimed_outputs = set(node.get("outputs", []))
    fresh_outputs = set(fresh_node.get("outputs", []))

    if source_artifact not in claimed_inputs:
        errors.append(
            f"workflow node {node_id} does not include its source artifact as input"
        )

    if mode == "exact_resolved_set":
        if claimed_inputs != fresh_inputs:
            errors.append(
                f"workflow node {node_id} input set differs from fresh static analysis"
            )
        if claimed_outputs != fresh_outputs:
            errors.append(
                f"workflow node {node_id} output set differs from fresh static analysis"
            )
        if signed.get("analysis_mode") != fresh_source.get("analysis_mode"):
            errors.append(
                f"workflow node {node_id} analysis mode differs from fresh static analysis"
            )
        if float(signed.get("confidence", -1.0)) != float(
            fresh_source.get("confidence", -2.0)
        ):
            errors.append(
                f"workflow node {node_id} confidence differs from fresh static analysis"
            )
    else:
        if not claimed_inputs.issubset(fresh_inputs):
            errors.append(
                f"workflow node {node_id} claims an input not rediscovered from source"
            )
        if not claimed_outputs.issubset(fresh_outputs):
            errors.append(
                f"workflow node {node_id} claims an output not rediscovered from source"
            )

    fresh_refs = {
        _reference_key(ref)
        for ref in fresh_source.get("resolved_references", [])
        if isinstance(ref, dict)
    }
    for ref in signed.get("resolved_references", []):
        if not isinstance(ref, dict):
            errors.append(
                f"workflow node {node_id} has malformed resolved reference"
            )
            continue
        if _reference_key(ref) not in fresh_refs:
            errors.append(
                f"workflow node {node_id} signed reference was not rediscovered: "
                f"{ref.get('path')!r}"
            )

    operation_expected = f"static_{fresh_source['source_kind']}_workflow"
    if node.get("operation") != operation_expected:
        errors.append(
            f"workflow node {node_id} operation mismatch: "
            f"{node.get('operation')!r} != {operation_expected!r}"
        )

    return errors


def verify_static_workflow_replay_v06(
    certificate: dict[str, Any],
    package_files: Mapping[str, bytes],
) -> dict[str, Any]:
    """Recompute signed static workflow claims from exact delivered artifact bytes.

    Only workflow nodes carrying the PCS static-workflow inference proposition are
    replayed here. Other workflow nodes remain structurally/hash bound but are not
    upgraded to independent runtime provenance by this function.
    """
    try:
        static_nodes: list[tuple[dict[str, Any], dict[str, Any]]] = []
        for node in certificate.get("workflow", {}).get("nodes", []):
            signed = _static_contract(node)
            if signed is not None:
                static_nodes.append((node, signed))

        if not static_nodes:
            return {
                "valid": True,
                "errors": [],
                "nodes_checked": 0,
                "mode": "no-static-workflow-claims",
                "details": [],
            }

        inventory, bytes_by_id = _artifact_bytes(certificate, package_files)
        inventory_by_id = {item["artifact_id"]: item for item in inventory}

        with tempfile.TemporaryDirectory(prefix="pcs-v06-workflow-replay-") as tmp:
            root = Path(tmp)
            for item in inventory:
                target = root / item["path"]
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(bytes_by_id[item["artifact_id"]])

            fresh = analyze_static_workflow_v06(root, inventory)

        fresh_sources = {
            source["id"]: source for source in fresh.get("sources", [])
        }
        fresh_nodes = {
            node.get("contract", {}).get("inference_id"): node
            for node in fresh.get("nodes", [])
            if isinstance(node.get("contract"), dict)
        }

        errors: list[str] = []
        details: list[dict[str, Any]] = []
        for node, signed in static_nodes:
            inference_id = signed.get("inference_id")
            source = fresh_sources.get(inference_id)
            fresh_node = fresh_nodes.get(inference_id)
            if source is None or fresh_node is None:
                errors.append(
                    f"workflow node {node['id']} was not reproduced by fresh static analysis"
                )
                details.append(
                    {
                        "node_id": node["id"],
                        "inference_id": inference_id,
                        "reproduced": False,
                    }
                )
                continue

            node_errors = _validate_claim_contract(
                node,
                signed,
                source,
                fresh_node,
            )
            errors.extend(node_errors)
            details.append(
                {
                    "node_id": node["id"],
                    "inference_id": inference_id,
                    "reproduced": not node_errors,
                    "dependency_claim_mode": signed.get("dependency_claim_mode"),
                    "fresh_confidence": source.get("confidence"),
                    "fresh_analysis_mode": source.get("analysis_mode"),
                    "fresh_inputs": fresh_node.get("inputs", []),
                    "fresh_outputs": fresh_node.get("outputs", []),
                }
            )

        return {
            "valid": not errors,
            "errors": errors,
            "nodes_checked": len(static_nodes),
            "mode": "static-source-replay",
            "details": details,
        }
    except (
        OSError,
        UnicodeError,
        ValueError,
        TypeError,
        KeyError,
        V06WorkflowReplayError,
    ) as exc:
        return {
            "valid": False,
            "errors": [f"static workflow replay failed: {type(exc).__name__}: {exc}"],
            "nodes_checked": 0,
            "mode": "static-source-replay",
            "details": [],
        }
