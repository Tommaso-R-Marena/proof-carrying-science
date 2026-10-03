from __future__ import annotations

import csv
import hashlib
import json
import mimetypes
import re
from pathlib import Path
from typing import Any

from .canonical_json import canonicalize_jcs_bytes
from .jsonio import StrictJSONError, strict_json_load
from .package_v06 import (
    MAX_PACKAGE_FILES_V06,
    MAX_PACKAGE_SINGLE_FILE_V06,
    MAX_PACKAGE_TOTAL_BYTES_V06,
)
from .schema_validation import SchemaValidationError, validate_manifest_shape
from .workflow_discovery_v06 import (
    WORKFLOW_DISCOVERY_FORMAT_V06,
    analyze_static_workflow_v06,
)
from .environment_v06 import (
    ENVIRONMENT_CAPTURE_FORMAT_V06,
    capture_environment_v06,
    environment_artifact_ids_v06,
)


DISCOVERY_FORMAT_V06 = "pcs-project-discovery-v1"
MANIFEST_DRAFT_FORMAT_V06 = "pcs-manifest-draft-v1"
MAX_DISCOVERY_FILES_V06 = min(2000, MAX_PACKAGE_FILES_V06 * 4)
MAX_DISCOVERY_TOTAL_BYTES_V06 = MAX_PACKAGE_TOTAL_BYTES_V06 * 2
MAX_INSPECT_BYTES_V06 = 2 * 1024 * 1024

_SKIP_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "venv",
    "env",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "dist",
    "build",
    ".pcs",
}
_SKIP_FILENAMES = {
    "pcs-manifest.draft.json",
    "pcs-discovery.json",
    "pcs-proof-translation.json",
    "pcs-proof-repair-request.json",
    "pcs-proof-repair-response.json",
    "pcs-proof-repaired-proposals.json",
    "pcs-proof-search.json",
    "pcs-proof-search.request.json",
    "pcs-proof-search.trajectory.json",
    "pcs-proof-search-corpus.json",
    "manifest.draft.json",
    "discovery.json",
}
_PRIVATE_KEY_MARKERS = (
    b"-----BEGIN PRIVATE KEY-----",
    b"-----BEGIN ENCRYPTED PRIVATE KEY-----",
    b"-----BEGIN OPENSSH PRIVATE KEY-----",
    b"-----BEGIN RSA PRIVATE KEY-----",
    b"-----BEGIN EC PRIVATE KEY-----",
)
_KEY_SUFFIXES = {".pem", ".key", ".p12", ".pfx"}
_ID_SANITIZE = re.compile(r"[^A-Za-z0-9_.:-]+")
_SPLIT_TOKENS = {
    "train": {"train", "training"},
    "test": {"test", "testing", "holdout"},
    "validation": {"val", "valid", "validation", "dev"},
}
_KEY_PRIORITY = (
    "subject_id",
    "patient_id",
    "sample_id",
    "participant_id",
    "record_id",
    "id",
    "rownames",
    "subject",
    "patient",
    "sample",
)


class V06DiscoveryError(ValueError):
    pass


def _safe_rel(root: Path, path: Path) -> str:
    root = root.resolve()
    resolved = path.resolve()
    try:
        rel = resolved.relative_to(root)
    except ValueError as exc:
        raise V06DiscoveryError(f"path escapes project root: {path}") from exc
    return rel.as_posix()


def _stream_sha256(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as fh:
        while True:
            chunk = fh.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
            size += len(chunk)
    return digest.hexdigest(), size


def _artifact_id(relative: str, used: set[str]) -> str:
    stem = relative.rsplit(".", 1)[0].replace("/", "_")
    base = _ID_SANITIZE.sub("_", stem).strip("_.:-") or "artifact"
    base = ("artifact_" + base)[:100]
    candidate = base
    if candidate in used:
        suffix = hashlib.sha256(relative.encode("utf-8")).hexdigest()[:10]
        candidate = f"{base[:88]}_{suffix}"
    index = 2
    original = candidate
    while candidate in used:
        candidate = f"{original[:115]}_{index}"
        index += 1
    used.add(candidate)
    return candidate


def _media_type(path: Path) -> str:
    guessed, _ = mimetypes.guess_type(path.name)
    if guessed:
        return guessed
    if path.suffix.lower() == ".csv":
        return "text/csv"
    if path.suffix.lower() == ".json":
        return "application/json"
    return "application/octet-stream"


def _role_guess(relative: str) -> str:
    name = Path(relative).name.lower()
    if name.endswith(".csv"):
        if any(token in name for token in ("prediction", "output", "result")):
            return "tabular-output"
        if any(token in name for token in ("train", "test", "valid", "val", "dev")):
            return "dataset-split"
        return "tabular-data"
    if name.endswith(".json"):
        if "model" in name:
            return "model-specification"
        if "reaction" in name:
            return "reaction-specification"
        if "unit" in name:
            return "unit-specification"
        return "structured-data"
    if name.endswith((".py", ".r", ".jl", ".ipynb")):
        return "source-code"
    return "scientific-artifact"


def _read_prefix(path: Path, limit: int = MAX_INSPECT_BYTES_V06) -> bytes:
    with path.open("rb") as fh:
        return fh.read(limit + 1)


def _looks_private_key(path: Path, prefix: bytes) -> bool:
    if path.suffix.lower() in _KEY_SUFFIXES:
        return True
    return any(marker in prefix for marker in _PRIVATE_KEY_MARKERS)


def _csv_header(path: Path) -> list[str] | None:
    try:
        with path.open("r", encoding="utf-8", newline="") as fh:
            reader = csv.reader(fh)
            row = next(reader, None)
    except (OSError, UnicodeDecodeError, csv.Error):
        return None
    if not row or any(not isinstance(x, str) for x in row):
        return None
    return [x.strip() for x in row]


def _json_object(path: Path) -> dict[str, Any] | None:
    if path.stat().st_size > MAX_INSPECT_BYTES_V06:
        return None
    try:
        value = strict_json_load(path)
    except (OSError, UnicodeDecodeError, StrictJSONError):
        return None
    return value if isinstance(value, dict) else None


_PCS_CONTROL_DOCUMENT_FORMATS = {
    DISCOVERY_FORMAT_V06,
    "pcs-proof-translation-v1",
    "pcs-proof-proposals-v1",
    "pcs-proof-repair-request-v1",
    "pcs-proof-repair-proposals-v1",
    "pcs-proof-repair-search-v1",
    "pcs-proof-repair-trajectory-v1",
    "pcs-proof-search-corpus-v1",
}


def _is_pcs_control_document(path: Path) -> bool:
    if path.suffix.lower() != ".json":
        return False
    value = _json_object(path)
    if not isinstance(value, dict):
        return False
    if value.get("format") in _PCS_CONTROL_DOCUMENT_FORMATS:
        return True
    intake = value.get("pcs_intake")
    return (
        isinstance(intake, dict)
        and intake.get("format") == MANIFEST_DRAFT_FORMAT_V06
    )


def _split_kind(name: str) -> str | None:
    tokens = set(re.split(r"[^a-z0-9]+", name.lower()))
    for kind, variants in _SPLIT_TOKENS.items():
        if tokens & variants:
            return kind
    return None


def _artifact_entry(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": item["artifact_id"],
        "path": item["path"],
        "role": item["role"],
        "media_type": item["media_type"],
        "metadata": {
            "pcs_discovery_sha256": item["sha256"],
            "pcs_discovery_size": item["size"],
        },
    }


def _claim(
    claim_id: str,
    statement: str,
    evidence_id: str,
    predicate: dict[str, Any],
    assumptions: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "id": claim_id,
        "statement": statement,
        "kind": "computational",
        "required_evidence": [evidence_id],
        "assumptions": assumptions or [],
        "predicate": predicate,
    }


def _recommend_pkpd(
    inventory: list[dict[str, Any]],
    json_objects: dict[str, dict[str, Any]],
    csv_headers: dict[str, list[str]],
) -> list[dict[str, Any]]:
    models = []
    predictions = []
    for item in inventory:
        obj = json_objects.get(item["path"])
        if (
            isinstance(obj, dict)
            and obj.get("model_type") == "one_compartment_iv_bolus"
            and isinstance(obj.get("pd"), dict)
            and obj["pd"].get("model_type") == "direct_emax"
            and all(k in obj for k in ("dose", "volume", "clearance"))
        ):
            models.append(item)
        header = csv_headers.get(item["path"], [])
        if {"time", "concentration", "effect"}.issubset(set(header)):
            predictions.append(item)

    recs: list[dict[str, Any]] = []
    for model in models:
        recs.append(
            {
                "id": f"R_PKPD_CONTRACT_{model['artifact_id']}",
                "detector": "restricted-pkpd-model",
                "confidence": 1.0,
                "reason": "JSON exactly declares one_compartment_iv_bolus with direct_emax PD fields.",
                "artifact_ids": [model["artifact_id"]],
                "check": {
                    "id": f"E_PKPD_CONTRACT_{model['artifact_id']}",
                    "type": "pkpd_contract",
                    "claim_ids": [f"C_PKPD_CONTRACT_{model['artifact_id']}"],
                    "model_artifact": model["artifact_id"],
                },
                "claim": _claim(
                    f"C_PKPD_CONTRACT_{model['artifact_id']}",
                    "The discovered PK/PD model satisfies the restricted PCS positivity and dimensional contract.",
                    f"E_PKPD_CONTRACT_{model['artifact_id']}",
                    {
                        "type": "pkpd_contract",
                        "model_artifact": model["artifact_id"],
                    },
                    [f"A_PKPD_{model['artifact_id']}"],
                ),
                "assumption": {
                    "id": f"A_PKPD_{model['artifact_id']}",
                    "statement": "The restricted one-compartment IV-bolus PK plus direct Emax PD equations are the declared computational model; this is not a claim of biological or clinical adequacy.",
                    "rationale": "Separates computational replay from empirical model validity.",
                },
            }
        )
        if len(models) == 1 and len(predictions) == 1:
            output = predictions[0]
            recs.append(
                {
                    "id": f"R_PKPD_REPLAY_{model['artifact_id']}_{output['artifact_id']}",
                    "detector": "pkpd-output-columns",
                    "confidence": 1.0,
                    "reason": "Exactly one CSV exposes time, concentration, and effect columns.",
                    "artifact_ids": [model["artifact_id"], output["artifact_id"]],
                    "check": {
                        "id": f"E_PKPD_REPLAY_{model['artifact_id']}",
                        "type": "pkpd_reference_match",
                        "claim_ids": [f"C_PKPD_REPLAY_{model['artifact_id']}"],
                        "model_artifact": model["artifact_id"],
                        "output_artifact": output["artifact_id"],
                        "time_column": "time",
                        "concentration_column": "concentration",
                        "effect_column": "effect",
                        "rel_tol": 1e-9,
                        "abs_tol": 1e-12,
                    },
                    "claim": _claim(
                        f"C_PKPD_REPLAY_{model['artifact_id']}",
                        "The discovered prediction table matches the declared restricted PK/PD equations within the PCS numeric tolerance.",
                        f"E_PKPD_REPLAY_{model['artifact_id']}",
                        {
                            "type": "pkpd_reference_match",
                            "model_artifact": model["artifact_id"],
                            "output_artifact": output["artifact_id"],
                            "time_column": "time",
                            "concentration_column": "concentration",
                            "effect_column": "effect",
                            "rel_tol": 1e-9,
                            "abs_tol": 1e-12,
                        },
                        [f"A_PKPD_{model['artifact_id']}"],
                    ),
                    "assumption": {
                        "id": f"A_PKPD_{model['artifact_id']}",
                        "statement": "The restricted one-compartment IV-bolus PK plus direct Emax PD equations are the declared computational model; this is not a claim of biological or clinical adequacy.",
                        "rationale": "Separates computational replay from empirical model validity.",
                    },
                    "workflow_node": {
                        "id": f"N_PKPD_{model['artifact_id']}",
                        "operation": "restricted_one_compartment_iv_bolus_direct_emax",
                        "inputs": [model["artifact_id"]],
                        "outputs": [output["artifact_id"]],
                        "contract": {
                            "equations": [
                                "C(t)=(Dose/V)*exp(-(CL/V)*t)",
                                "E(C)=E0+Emax*C/(EC50+C)",
                            ],
                            "validation_scope": "computational replay only; not empirical adequacy",
                        },
                    },
                }
            )
    return recs


def _recommend_csv_splits(
    inventory: list[dict[str, Any]],
    csv_headers: dict[str, list[str]],
) -> list[dict[str, Any]]:
    csv_items = [x for x in inventory if x["path"] in csv_headers]
    recs: list[dict[str, Any]] = []
    for i, left in enumerate(csv_items):
        lk = _split_kind(Path(left["path"]).stem)
        if lk is None:
            continue
        for right in csv_items[i + 1 :]:
            rk = _split_kind(Path(right["path"]).stem)
            if rk is None or rk == lk:
                continue
            if {lk, rk}.isdisjoint({"train", "test", "validation"}):
                continue
            common = set(csv_headers[left["path"]]) & set(csv_headers[right["path"]])
            key = next((candidate for candidate in _KEY_PRIORITY if candidate in common), None)
            if key is None:
                continue
            pair = sorted([left, right], key=lambda x: x["path"])
            left2, right2 = pair
            rec_id = f"R_SPLIT_{left2['artifact_id']}_{right2['artifact_id']}"
            ev_id = f"E_SPLIT_{left2['artifact_id']}_{right2['artifact_id']}"
            cl_id = f"C_SPLIT_{left2['artifact_id']}_{right2['artifact_id']}"
            predicate = {
                "type": "csv_disjoint",
                "left_artifact": left2["artifact_id"],
                "right_artifact": right2["artifact_id"],
                "key": key,
            }
            recs.append(
                {
                    "id": rec_id,
                    "detector": "named-dataset-split",
                    "confidence": 0.96,
                    "reason": (
                        f"Files are named as different dataset splits and share high-priority key column {key!r}."
                    ),
                    "artifact_ids": [left2["artifact_id"], right2["artifact_id"]],
                    "check": {
                        "id": ev_id,
                        "type": "csv_disjoint",
                        "claim_ids": [cl_id],
                        "left_artifact": left2["artifact_id"],
                        "right_artifact": right2["artifact_id"],
                        "key": key,
                    },
                    "claim": _claim(
                        cl_id,
                        f"The discovered dataset splits {left2['path']} and {right2['path']} are disjoint on {key}.",
                        ev_id,
                        predicate,
                    ),
                }
            )
    # Avoid duplicate semantic pairs when train/test/validation naming creates repeats.
    unique: dict[tuple[str, str, str], dict[str, Any]] = {}
    for rec in recs:
        check = rec["check"]
        key = (
            check["left_artifact"],
            check["right_artifact"],
            check["key"],
        )
        unique[key] = rec
    return list(unique.values())


def _recommend_structured_checks(
    inventory: list[dict[str, Any]],
    json_objects: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    recs: list[dict[str, Any]] = []
    for item in inventory:
        obj = json_objects.get(item["path"])
        if not isinstance(obj, dict):
            continue
        if set(("reactants", "products")).issubset(obj):
            if isinstance(obj["reactants"], list) and isinstance(obj["products"], list):
                ev = f"E_REACTION_{item['artifact_id']}"
                cl = f"C_REACTION_{item['artifact_id']}"
                spec = {
                    "type": "reaction_balance",
                    "reactants": obj["reactants"],
                    "products": obj["products"],
                }
                recs.append(
                    {
                        "id": f"R_REACTION_{item['artifact_id']}",
                        "detector": "reaction-json",
                        "confidence": 0.99,
                        "reason": "JSON exposes reactants/products arrays compatible with the PCS reaction-balance checker.",
                        "artifact_ids": [item["artifact_id"]],
                        "check": {
                            "id": ev,
                            "type": "reaction_balance",
                            "claim_ids": [cl],
                            "reactants": obj["reactants"],
                            "products": obj["products"],
                        },
                        "claim": _claim(
                            cl,
                            "The discovered reaction specification is element-balanced under the PCS formula parser.",
                            ev,
                            spec,
                        ),
                    }
                )
        if isinstance(obj.get("left_unit"), str) and isinstance(obj.get("right_unit"), str):
            ev = f"E_UNITS_{item['artifact_id']}"
            cl = f"C_UNITS_{item['artifact_id']}"
            spec = {
                "type": "unit_compatible",
                "left_unit": obj["left_unit"],
                "right_unit": obj["right_unit"],
            }
            recs.append(
                {
                    "id": f"R_UNITS_{item['artifact_id']}",
                    "detector": "unit-pair-json",
                    "confidence": 0.99,
                    "reason": "JSON explicitly declares left_unit/right_unit for compatibility checking.",
                    "artifact_ids": [item["artifact_id"]],
                    "check": {
                        "id": ev,
                        "type": "unit_compatible",
                        "claim_ids": [cl],
                        "left_unit": obj["left_unit"],
                        "right_unit": obj["right_unit"],
                    },
                    "claim": _claim(
                        cl,
                        "The discovered unit expressions are dimensionally compatible under the PCS unit checker.",
                        ev,
                        spec,
                    ),
                }
            )
    return recs


def _dedupe_by_id(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for item in items:
        out[item["id"]] = item
    return list(out.values())


def _selected_manifest(
    *,
    root: Path,
    subject: str,
    inventory: list[dict[str, Any]],
    recommendations: list[dict[str, Any]],
    minimum_confidence: float,
    workflow_map: dict[str, Any],
    minimum_workflow_confidence: float,
    environment_capture: dict[str, Any],
) -> dict[str, Any]:
    selected = [
        rec for rec in recommendations
        if float(rec["confidence"]) >= minimum_confidence
    ]
    selected_workflow_inferences = {
        source["id"]
        for source in workflow_map.get("sources", [])
        if float(source.get("confidence", 0.0)) >= minimum_workflow_confidence
    }
    selected_workflow_nodes = [
        node
        for node in workflow_map.get("nodes", [])
        if isinstance(node.get("contract"), dict)
        and node["contract"].get("inference_id") in selected_workflow_inferences
    ]

    artifact_ids = {
        artifact_id
        for rec in selected
        for artifact_id in rec.get("artifact_ids", [])
    }
    artifact_ids.update(
        artifact_id
        for node in selected_workflow_nodes
        for artifact_id in node.get("inputs", []) + node.get("outputs", [])
    )
    artifact_ids.update(environment_artifact_ids_v06(environment_capture))
    inventory_by_id = {x["artifact_id"]: x for x in inventory}

    claims = _dedupe_by_id(
        [rec["claim"] for rec in selected if isinstance(rec.get("claim"), dict)]
    )
    checks = _dedupe_by_id(
        [rec["check"] for rec in selected if isinstance(rec.get("check"), dict)]
    )
    assumptions = _dedupe_by_id(
        [rec["assumption"] for rec in selected if isinstance(rec.get("assumption"), dict)]
    )
    for assumption in assumptions:
        assumption_id = assumption["id"]
        assumption["scope"] = [
            claim["id"]
            for claim in claims
            if assumption_id in claim.get("assumptions", [])
        ]

    semantic_workflow_nodes = _dedupe_by_id(
        [
            rec["workflow_node"]
            for rec in selected
            if isinstance(rec.get("workflow_node"), dict)
        ]
    )

    # Static source analysis is a stronger provenance statement about which source
    # appears to read/write an artifact. Avoid creating two workflow producers for
    # the same output when a domain recommendation already describes that relation.
    static_outputs = {
        artifact_id
        for node in selected_workflow_nodes
        for artifact_id in node.get("outputs", [])
    }
    adjusted_semantic_nodes: list[dict[str, Any]] = []
    for node in semantic_workflow_nodes:
        adjusted = json.loads(json.dumps(node))
        adjusted["outputs"] = [
            artifact_id
            for artifact_id in adjusted.get("outputs", [])
            if artifact_id not in static_outputs
        ]
        if adjusted["outputs"]:
            adjusted_semantic_nodes.append(adjusted)

    workflow_nodes = _dedupe_by_id(
        [*selected_workflow_nodes, *adjusted_semantic_nodes]
    )

    manifest = {
        "subject": subject,
        "assumptions": assumptions,
        "claims": claims,
        "artifacts": [
            _artifact_entry(inventory_by_id[artifact_id])
            for artifact_id in sorted(artifact_ids)
        ],
        "checks": checks,
        "workflow": {"nodes": workflow_nodes},
        "environment": {
            **json.loads(json.dumps(environment_capture)),
            "human_confirmed": False,
            "confirmation_scope": (
                "Environment capture is a static declaration and reconstruction plan; "
                "it does not prove package availability, installer correctness, ABI "
                "compatibility, or successful environment reconstruction."
            ),
        },
        "pcs_intake": {
            "format": MANIFEST_DRAFT_FORMAT_V06,
            "status": "draft",
            "requires_confirmation": True,
            "project_root_name": root.name,
            "minimum_selected_confidence": minimum_confidence,
            "selected_recommendations": [rec["id"] for rec in selected],
            "recommendation_count": len(recommendations),
            "selected_recommendation_count": len(selected),
            "workflow_discovery_format": workflow_map.get("format"),
            "minimum_workflow_confidence": minimum_workflow_confidence,
            "selected_workflow_inferences": sorted(selected_workflow_inferences),
            "workflow_inference_count": len(workflow_map.get("sources", [])),
            "selected_workflow_inference_count": len(selected_workflow_inferences),
            "environment_capture_format": environment_capture.get("format"),
            "environment_source_artifacts": environment_artifact_ids_v06(
                environment_capture
            ),
            "environment_hermeticity": environment_capture.get("hermeticity"),
        },
    }
    return manifest


def discover_project_v06(
    project_root: str | Path,
    *,
    subject: str | None = None,
    minimum_confidence: float = 0.95,
    minimum_workflow_confidence: float = 0.95,
    exclude_paths: list[str | Path] | tuple[str | Path, ...] | None = None,
) -> dict[str, Any]:
    root = Path(project_root).resolve()
    excluded_relative: set[str] = set()
    for excluded in exclude_paths or []:
        resolved = Path(excluded).resolve()
        try:
            excluded_relative.add(resolved.relative_to(root).as_posix())
        except ValueError:
            # Out-of-tree proposer/control inputs are already outside discovery.
            pass
    if not root.is_dir():
        raise V06DiscoveryError(f"project root is not a directory: {root}")
    if not 0.0 <= minimum_confidence <= 1.0:
        raise V06DiscoveryError("minimum_confidence must be between 0 and 1")
    if not 0.0 <= minimum_workflow_confidence <= 1.0:
        raise V06DiscoveryError(
            "minimum_workflow_confidence must be between 0 and 1"
        )

    inventory: list[dict[str, Any]] = []
    skipped: list[dict[str, str]] = []
    used_ids: set[str] = set()
    total_bytes = 0

    paths = sorted(root.rglob("*"), key=lambda p: p.as_posix())
    for path in paths:
        rel_parts = path.relative_to(root).parts
        if any(part in _SKIP_DIRS for part in rel_parts[:-1]):
            continue
        if path.is_dir():
            continue
        relative_literal = path.relative_to(root).as_posix()
        if relative_literal in excluded_relative:
            continue
        if Path(relative_literal).name in _SKIP_FILENAMES:
            continue
        if path.is_symlink():
            skipped.append({"path": relative_literal, "reason": "symlink"})
            continue
        if not path.is_file():
            skipped.append({"path": relative_literal, "reason": "not-regular-file"})
            continue
        if _is_pcs_control_document(path):
            skipped.append({"path": relative_literal, "reason": "pcs-control-document"})
            continue
        if len(inventory) >= MAX_DISCOVERY_FILES_V06:
            raise V06DiscoveryError(
                f"project exceeds discovery file limit {MAX_DISCOVERY_FILES_V06}"
            )

        size = path.stat().st_size
        if size > MAX_PACKAGE_SINGLE_FILE_V06:
            skipped.append({"path": relative_literal, "reason": "exceeds-package-single-file-limit"})
            continue
        total_bytes += size
        if total_bytes > MAX_DISCOVERY_TOTAL_BYTES_V06:
            raise V06DiscoveryError(
                f"project exceeds discovery byte limit {MAX_DISCOVERY_TOTAL_BYTES_V06}"
            )

        prefix = _read_prefix(path, min(MAX_INSPECT_BYTES_V06, 65536))
        if _looks_private_key(path, prefix):
            skipped.append({"path": relative_literal, "reason": "key-material-excluded"})
            continue

        digest, observed_size = _stream_sha256(path)
        relative = _safe_rel(root, path)
        inventory.append(
            {
                "artifact_id": _artifact_id(relative, used_ids),
                "path": relative,
                "size": observed_size,
                "sha256": digest,
                "media_type": _media_type(path),
                "role": _role_guess(relative),
            }
        )

    csv_headers: dict[str, list[str]] = {}
    json_objects: dict[str, dict[str, Any]] = {}
    for item in inventory:
        path = root / item["path"]
        if path.suffix.lower() == ".csv":
            header = _csv_header(path)
            if header is not None:
                csv_headers[item["path"]] = header
        elif path.suffix.lower() == ".json":
            obj = _json_object(path)
            if obj is not None:
                json_objects[item["path"]] = obj

    recommendations = (
        _recommend_pkpd(inventory, json_objects, csv_headers)
        + _recommend_csv_splits(inventory, csv_headers)
        + _recommend_structured_checks(inventory, json_objects)
    )
    recommendations = sorted(
        recommendations,
        key=lambda x: (-float(x["confidence"]), x["id"]),
    )

    workflow_map = analyze_static_workflow_v06(root, inventory)
    environment_capture = capture_environment_v06(root, inventory)

    manifest = _selected_manifest(
        root=root,
        subject=subject or root.name,
        inventory=inventory,
        recommendations=recommendations,
        minimum_confidence=minimum_confidence,
        workflow_map=workflow_map,
        minimum_workflow_confidence=minimum_workflow_confidence,
        environment_capture=environment_capture,
    )
    try:
        validate_manifest_shape(manifest)
    except SchemaValidationError as exc:
        raise V06DiscoveryError(
            f"internal discovery generated invalid manifest draft: {exc}"
        ) from exc

    unresolved = list(workflow_map.get("unresolved", []))
    unresolved.extend(environment_capture.get("unresolved", []))
    if not manifest["claims"]:
        unresolved.append(
            {
                "type": "no-supported-checks-detected",
                "message": "PCS did not detect any currently supported v0.6 scientific checks. Add claims/checks manually or install a future domain pack.",
            }
        )
    unsupported = [
        item["path"]
        for item in inventory
        if item["artifact_id"]
        not in {a["id"] for a in manifest["artifacts"]}
    ]
    if unsupported:
        unresolved.append(
            {
                "type": "unselected-artifacts",
                "message": "Some discovered files are not referenced by an auto-selected PCS check.",
                "paths": unsupported[:100],
                "truncated": len(unsupported) > 100,
            }
        )

    inventory_commitment = hashlib.sha256(
        canonicalize_jcs_bytes(
            [
                {
                    "path": item["path"],
                    "sha256": item["sha256"],
                    "size": item["size"],
                }
                for item in inventory
            ]
        )
    ).hexdigest()

    manifest["pcs_intake"]["inventory_commitment_sha256"] = inventory_commitment

    report = {
        "format": DISCOVERY_FORMAT_V06,
        "project_root_name": root.name,
        "subject": manifest["subject"],
        "inventory_commitment_sha256": inventory_commitment,
        "inventory": inventory,
        "skipped": skipped,
        "recommendations": recommendations,
        "selected_recommendations": manifest["pcs_intake"]["selected_recommendations"],
        "workflow_map": workflow_map,
        "selected_workflow_inferences": manifest["pcs_intake"][
            "selected_workflow_inferences"
        ],
        "environment_capture": environment_capture,
        "unresolved": unresolved,
        "summary": {
            "files_inventoried": len(inventory),
            "files_skipped": len(skipped),
            "bytes_inventoried": sum(x["size"] for x in inventory),
            "recommendations": len(recommendations),
            "selected_recommendations": len(manifest["pcs_intake"]["selected_recommendations"]),
            "claims_drafted": len(manifest["claims"]),
            "checks_drafted": len(manifest["checks"]),
            "artifacts_selected": len(manifest["artifacts"]),
            "workflow_sources_analyzed": workflow_map["summary"][
                "source_files_considered"
            ],
            "workflow_nodes_drafted": len(manifest["workflow"]["nodes"]),
            "workflow_edges_inferred": workflow_map["summary"]["workflow_edges"],
            "workflow_unresolved_items": workflow_map["summary"]["unresolved_items"],
            "environment_sources": environment_capture["summary"]["source_files"],
            "environment_dependencies": environment_capture["summary"][
                "dependency_records"
            ],
            "environment_unresolved_items": environment_capture["summary"][
                "unresolved_items"
            ],
            "environment_hermeticity": environment_capture["hermeticity"],
        },
        "manifest_draft": manifest,
    }
    return report


def _write_json(
    value: dict[str, Any],
    path: str | Path,
    *,
    overwrite: bool,
    label: str,
) -> Path:
    output = Path(path).resolve()
    if output.exists() and not overwrite:
        raise V06DiscoveryError(f"refusing to overwrite existing {label}: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return output


def write_discovery_outputs_v06(
    report: dict[str, Any],
    *,
    manifest_output: str | Path,
    report_output: str | Path,
    overwrite: bool = False,
) -> dict[str, str]:
    if report.get("format") != DISCOVERY_FORMAT_V06:
        raise V06DiscoveryError("refusing to write non-v0.6 discovery report")
    manifest_path = _write_json(
        report["manifest_draft"],
        manifest_output,
        overwrite=overwrite,
        label="manifest draft",
    )
    report_path = _write_json(
        report,
        report_output,
        overwrite=overwrite,
        label="discovery report",
    )
    return {
        "manifest_draft": str(manifest_path),
        "discovery_report": str(report_path),
    }


def _verify_snapshot(root: Path, manifest: dict[str, Any]) -> list[dict[str, Any]]:
    verified: list[dict[str, Any]] = []
    for artifact in manifest.get("artifacts", []):
        path = root / artifact["path"]
        if path.is_symlink() or not path.is_file():
            raise V06DiscoveryError(
                f"cannot confirm manifest: artifact missing or unsafe: {artifact['path']}"
            )
        metadata = artifact.get("metadata", {})
        expected_hash = metadata.get("pcs_discovery_sha256")
        expected_size = metadata.get("pcs_discovery_size")
        if not isinstance(expected_hash, str) or not isinstance(expected_size, int):
            raise V06DiscoveryError(
                f"cannot confirm manifest: artifact lacks discovery snapshot metadata: {artifact['id']}"
            )
        actual_hash, actual_size = _stream_sha256(path)
        if actual_hash != expected_hash or actual_size != expected_size:
            raise V06DiscoveryError(
                f"cannot confirm manifest: artifact changed since discovery: {artifact['path']}"
            )
        verified.append(
            {
                "id": artifact["id"],
                "path": artifact["path"],
                "sha256": actual_hash,
                "size": actual_size,
            }
        )
    return verified


def confirm_manifest_draft_v06(
    draft_path: str | Path,
    output_path: str | Path,
    *,
    project_root: str | Path | None = None,
    overwrite: bool = False,
    allow_empty: bool = False,
) -> dict[str, Any]:
    draft = Path(draft_path).resolve()
    try:
        manifest = strict_json_load(draft)
    except (OSError, StrictJSONError) as exc:
        raise V06DiscoveryError(f"cannot load manifest draft: {exc}") from exc
    if not isinstance(manifest, dict):
        raise V06DiscoveryError("manifest draft root must be an object")
    intake = manifest.get("pcs_intake")
    if not isinstance(intake, dict) or intake.get("format") != MANIFEST_DRAFT_FORMAT_V06:
        raise V06DiscoveryError("manifest is not a PCS v0.6 discovery draft")
    if intake.get("status") != "draft":
        raise V06DiscoveryError(
            f"manifest draft has unexpected intake status: {intake.get('status')!r}"
        )
    try:
        validate_manifest_shape(manifest)
    except SchemaValidationError as exc:
        raise V06DiscoveryError(str(exc)) from exc
    if not allow_empty and not manifest.get("claims"):
        raise V06DiscoveryError(
            "refusing to confirm a manifest with no claims; add a supported claim/check or pass --allow-empty explicitly"
        )

    root = Path(project_root).resolve() if project_root is not None else draft.parent.resolve()
    output_candidate = Path(output_path).resolve()
    if output_candidate.parent != root:
        raise V06DiscoveryError(
            "confirmed manifest must be written in the project root so artifact paths remain bound"
        )
    verified = _verify_snapshot(root, manifest)
    confirmed = json.loads(json.dumps(manifest))
    confirmed["pcs_intake"]["status"] = "confirmed"
    confirmed["pcs_intake"]["requires_confirmation"] = False
    confirmed["pcs_intake"]["workflow_inferences_confirmed"] = True

    # The browser Project Mapper intentionally uses lower-assurance heuristics.
    # Confirmation is the authoritative handoff. First rescan the project for
    # environment declarations so a newly added lockfile/container spec cannot
    # be silently omitted from the reviewed artifact set.
    authoritative_rescan = discover_project_v06(
        root,
        subject=manifest.get("subject"),
        minimum_confidence=1.0,
        minimum_workflow_confidence=1.0,
    )
    rescanned_environment_paths = {
        source["path"]
        for source in authoritative_rescan["environment_capture"].get(
            "sources", []
        )
        if isinstance(source, dict) and isinstance(source.get("path"), str)
    }
    reviewed_artifact_paths = {
        artifact["path"]
        for artifact in manifest.get("artifacts", [])
        if isinstance(artifact, dict) and isinstance(artifact.get("path"), str)
    }
    newly_unreviewed_environment_paths = sorted(
        rescanned_environment_paths - reviewed_artifact_paths
    )
    if newly_unreviewed_environment_paths:
        raise V06DiscoveryError(
            "cannot confirm manifest: new or previously unselected environment "
            "source files are present; rerun pcs discover-v06 and review them: "
            f"{newly_unreviewed_environment_paths}"
        )

    # Regenerate the authoritative environment contract from the exact
    # snapshotted, reviewed artifact IDs so certificate cross-references remain
    # stable even when the draft originated in the browser mapper.
    environment_inventory = []
    for artifact in confirmed.get("artifacts", []):
        metadata = artifact.get("metadata", {})
        expected_hash = metadata.get("pcs_discovery_sha256")
        expected_size = metadata.get("pcs_discovery_size")
        if not isinstance(expected_hash, str) or not isinstance(expected_size, int):
            continue
        environment_inventory.append(
            {
                "artifact_id": artifact["id"],
                "path": artifact["path"],
                "size": expected_size,
                "sha256": expected_hash,
                "media_type": artifact.get("media_type", "application/octet-stream"),
                "role": artifact.get("role", "scientific-artifact"),
            }
        )
    fresh_environment = capture_environment_v06(root, environment_inventory)
    fresh_environment["human_confirmed"] = True
    fresh_environment["confirmation_scope"] = (
        "Authoritative PCS environment capture regenerated from the exact "
        "snapshotted environment-source bytes at confirmation. This binds static "
        "dependency, lockfile, interpreter, container/environment declarations and "
        "the reconstruction plan; it does not prove successful installation, ABI "
        "equivalence, dependency availability, or runtime execution."
    )
    confirmed["environment"] = fresh_environment
    confirmed["pcs_intake"]["environment_confirmed"] = True
    confirmed["pcs_intake"]["environment_capture_format"] = fresh_environment[
        "format"
    ]
    confirmed["pcs_intake"]["environment_source_artifacts"] = (
        environment_artifact_ids_v06(fresh_environment)
    )
    confirmed["pcs_intake"]["environment_hermeticity"] = fresh_environment.get(
        "hermeticity"
    )

    for node in confirmed.get("workflow", {}).get("nodes", []):
        contract = node.get("contract")
        if (
            isinstance(contract, dict)
            and contract.get("inference_format") == WORKFLOW_DISCOVERY_FORMAT_V06
        ):
            contract["human_confirmed"] = True
            contract["confirmation_scope"] = (
                "Static dependency inference confirmed; this does not prove "
                "source-code correctness or runtime behavior."
            )
    confirmed["pcs_intake"]["confirmed_artifacts"] = [
        {
            "id": row["id"],
            "sha256": row["sha256"],
            "size": row["size"],
        }
        for row in verified
    ]
    inventory_commitment = confirmed["pcs_intake"].get(
        "inventory_commitment_sha256"
    )
    for artifact in confirmed.get("artifacts", []):
        metadata = artifact.setdefault("metadata", {})
        metadata["pcs_discovery_confirmed"] = True
        if isinstance(inventory_commitment, str):
            metadata["pcs_discovery_inventory_commitment_sha256"] = (
                inventory_commitment
            )
    output = _write_json(
        confirmed,
        output_path,
        overwrite=overwrite,
        label="confirmed manifest",
    )
    return {
        "valid": True,
        "manifest": str(output),
        "claims": len(confirmed["claims"]),
        "checks": len(confirmed["checks"]),
        "artifacts": len(confirmed["artifacts"]),
        "snapshot_verified": len(verified),
    }
