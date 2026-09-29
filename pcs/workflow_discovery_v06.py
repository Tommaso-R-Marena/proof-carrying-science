from __future__ import annotations

import ast
import json
import re
from pathlib import Path, PurePosixPath
from typing import Any


WORKFLOW_DISCOVERY_FORMAT_V06 = "pcs-static-workflow-map-v1"
MAX_SOURCE_INSPECT_BYTES_V06 = 2 * 1024 * 1024
MAX_REFERENCES_PER_SOURCE_V06 = 128
MAX_CONTRACT_REFERENCES_V06 = 48

_READ_FUNCTIONS = {
    "read_csv",
    "read_json",
    "read_parquet",
    "read_excel",
    "read_feather",
    "read_pickle",
    "load",
    "loadtxt",
    "genfromtxt",
}
_WRITE_FUNCTIONS = {
    "save",
    "savetxt",
    "savez",
    "savez_compressed",
}
_READ_METHODS = {
    "read_text",
    "read_bytes",
}
_WRITE_METHODS = {
    "to_csv",
    "to_json",
    "to_parquet",
    "to_excel",
    "to_feather",
    "to_pickle",
    "write_text",
    "write_bytes",
}
_SOURCE_SUFFIXES = {".py", ".ipynb"}


class V06WorkflowDiscoveryError(ValueError):
    pass


def _qualname(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        left = _qualname(node.value)
        return f"{left}.{node.attr}" if left else node.attr
    return None


def _string_expr(node: ast.AST | None, env: dict[str, str]) -> str | None:
    if node is None:
        return None
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.Name):
        return env.get(node.id)
    if isinstance(node, ast.JoinedStr):
        out = []
        for value in node.values:
            if isinstance(value, ast.Constant) and isinstance(value.value, str):
                out.append(value.value)
            elif isinstance(value, ast.FormattedValue):
                inner = _string_expr(value.value, env)
                if inner is None:
                    return None
                out.append(inner)
            else:
                return None
        return "".join(out)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        left = _string_expr(node.left, env)
        right = _string_expr(node.right, env)
        if left is not None and right is not None:
            return left + right
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
        left = _string_expr(node.left, env)
        right = _string_expr(node.right, env)
        if left is not None and right is not None:
            return (PurePosixPath(left) / right).as_posix()
    if isinstance(node, ast.Call):
        name = _qualname(node.func) or ""
        tail = name.rsplit(".", 1)[-1]
        if tail in {"Path", "PurePath", "PurePosixPath", "str"} and node.args:
            return _string_expr(node.args[0], env)
        if name.endswith("os.path.join") or name == "join":
            parts = [_string_expr(arg, env) for arg in node.args]
            if parts and all(part is not None for part in parts):
                result = PurePosixPath(parts[0] or "")
                for part in parts[1:]:
                    result /= part or ""
                return result.as_posix()
    return None


def _static_env(tree: ast.AST) -> dict[str, str]:
    env: dict[str, str] = {}
    body = getattr(tree, "body", [])
    for stmt in body:
        target: ast.AST | None = None
        value: ast.AST | None = None
        if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1:
            target, value = stmt.targets[0], stmt.value
        elif isinstance(stmt, ast.AnnAssign):
            target, value = stmt.target, stmt.value
        if isinstance(target, ast.Name) and value is not None:
            resolved = _string_expr(value, env)
            if resolved is not None:
                env[target.id] = resolved
    return env


def _imports(tree: ast.AST) -> list[str]:
    out: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            out.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            out.add(node.module)
    return sorted(out)


def _mode_from_open(call: ast.Call, env: dict[str, str]) -> str:
    mode = "r"
    if len(call.args) >= 2:
        mode = _string_expr(call.args[1], env) or mode
    for kw in call.keywords:
        if kw.arg == "mode":
            mode = _string_expr(kw.value, env) or mode
    return mode


def _path_from_call(call: ast.Call, env: dict[str, str]) -> tuple[str | None, str | None]:
    """Return (kind, static path) where kind is read/write or None."""
    name = _qualname(call.func) or ""
    tail = name.rsplit(".", 1)[-1]

    if tail == "open":
        path = _string_expr(call.args[0], env) if call.args else None
        mode = _mode_from_open(call, env)
        kind = "write" if any(flag in mode for flag in ("w", "a", "x", "+")) else "read"
        return kind, path

    if tail in _READ_FUNCTIONS:
        path = _string_expr(call.args[0], env) if call.args else None
        return "read", path

    if tail in _WRITE_FUNCTIONS:
        path = _string_expr(call.args[0], env) if call.args else None
        return "write", path

    if isinstance(call.func, ast.Attribute):
        if tail in _WRITE_METHODS:
            path = _string_expr(call.args[0], env) if call.args else None
            if tail in {"write_text", "write_bytes"}:
                path = _string_expr(call.func.value, env)
            return "write", path
        if tail in _READ_METHODS:
            return "read", _string_expr(call.func.value, env)

    return None, None


def _analyze_python_text(
    source: str,
    *,
    location_prefix: str = "",
) -> dict[str, Any]:
    try:
        tree = ast.parse(source)
    except (SyntaxError, ValueError) as exc:
        return {
            "parse_ok": False,
            "parse_error": f"{type(exc).__name__}: {exc}",
            "imports": [],
            "references": [],
        }

    env = _static_env(tree)
    references: list[dict[str, Any]] = []
    seen: set[tuple[str, str, int]] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        kind, path = _path_from_call(node, env)
        if kind is None:
            continue
        line = int(getattr(node, "lineno", 0))
        api = _qualname(node.func) or "<call>"
        if path is None:
            key = (kind, f"<dynamic:{api}>", line)
            if key in seen:
                continue
            seen.add(key)
            references.append(
                {
                    "kind": kind,
                    "path": None,
                    "api": api,
                    "location": f"{location_prefix}{line}",
                    "resolution": "dynamic",
                }
            )
        else:
            normalized = path.replace("\\", "/")
            key = (kind, normalized, line)
            if key in seen:
                continue
            seen.add(key)
            references.append(
                {
                    "kind": kind,
                    "path": normalized,
                    "api": api,
                    "location": f"{location_prefix}{line}",
                    "resolution": "static_literal",
                }
            )
        if len(references) >= MAX_REFERENCES_PER_SOURCE_V06:
            break

    return {
        "parse_ok": True,
        "parse_error": None,
        "imports": _imports(tree)[:64],
        "references": references,
    }


def _analyze_notebook(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return {
            "parse_ok": False,
            "parse_error": f"{type(exc).__name__}: {exc}",
            "imports": [],
            "references": [],
            "code_cells": 0,
        }

    cells = value.get("cells") if isinstance(value, dict) else None
    if not isinstance(cells, list):
        return {
            "parse_ok": False,
            "parse_error": "notebook cells missing",
            "imports": [],
            "references": [],
            "code_cells": 0,
        }

    imports: set[str] = set()
    references: list[dict[str, Any]] = []
    parse_errors: list[str] = []
    code_cells = 0
    for index, cell in enumerate(cells):
        if not isinstance(cell, dict) or cell.get("cell_type") != "code":
            continue
        code_cells += 1
        source = cell.get("source", "")
        if isinstance(source, list):
            source = "".join(str(x) for x in source)
        if not isinstance(source, str):
            continue
        result = _analyze_python_text(
            source,
            location_prefix=f"cell[{index}]:",
        )
        if result["parse_ok"]:
            imports.update(result["imports"])
            references.extend(result["references"])
        else:
            parse_errors.append(f"cell[{index}]: {result['parse_error']}")
        if len(references) >= MAX_REFERENCES_PER_SOURCE_V06:
            references = references[:MAX_REFERENCES_PER_SOURCE_V06]
            break

    return {
        "parse_ok": not parse_errors,
        "parse_error": "; ".join(parse_errors[:8]) if parse_errors else None,
        "imports": sorted(imports)[:64],
        "references": references,
        "code_cells": code_cells,
    }


def _resolve_reference(
    raw_path: str,
    *,
    project_root: Path,
    source_path: Path,
    inventory_by_path: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    if not raw_path or raw_path.startswith(("http://", "https://", "s3://", "gs://")):
        return {"resolution": "external_or_empty", "artifact_id": None, "path": raw_path}

    candidate_paths: list[Path] = []
    raw = Path(raw_path)
    if raw.is_absolute():
        candidate_paths.append(raw)
    else:
        candidate_paths.extend(
            [
                project_root / raw,
                source_path.parent / raw,
            ]
        )

    matches: dict[str, dict[str, Any]] = {}
    for candidate in candidate_paths:
        try:
            resolved = candidate.resolve()
            rel = resolved.relative_to(project_root.resolve()).as_posix()
        except (OSError, ValueError):
            continue
        item = inventory_by_path.get(rel)
        if item is not None:
            matches[rel] = item

    if len(matches) == 1:
        rel, item = next(iter(matches.items()))
        return {
            "resolution": "resolved",
            "artifact_id": item["artifact_id"],
            "path": rel,
        }
    if len(matches) > 1:
        return {
            "resolution": "ambiguous",
            "artifact_id": None,
            "path": raw_path,
            "candidates": sorted(matches),
        }
    return {
        "resolution": "missing",
        "artifact_id": None,
        "path": raw_path,
    }


def analyze_static_workflow_v06(
    project_root: str | Path,
    inventory: list[dict[str, Any]],
) -> dict[str, Any]:
    root = Path(project_root).resolve()
    inventory_by_path = {item["path"]: item for item in inventory}
    source_items = [
        item
        for item in inventory
        if Path(item["path"]).suffix.lower() in _SOURCE_SUFFIXES
    ]

    sources: list[dict[str, Any]] = []
    unresolved: list[dict[str, Any]] = []

    for item in source_items:
        source_path = root / item["path"]
        if item["size"] > MAX_SOURCE_INSPECT_BYTES_V06:
            unresolved.append(
                {
                    "type": "source_too_large_for_static_analysis",
                    "source_path": item["path"],
                    "size": item["size"],
                }
            )
            continue

        suffix = source_path.suffix.lower()
        if suffix == ".py":
            try:
                analysis = _analyze_python_text(
                    source_path.read_text(encoding="utf-8")
                )
            except (OSError, UnicodeDecodeError) as exc:
                analysis = {
                    "parse_ok": False,
                    "parse_error": f"{type(exc).__name__}: {exc}",
                    "imports": [],
                    "references": [],
                }
            source_kind = "python"
        else:
            analysis = _analyze_notebook(source_path)
            source_kind = "jupyter"

        if not analysis["parse_ok"]:
            unresolved.append(
                {
                    "type": "source_parse_incomplete",
                    "source_path": item["path"],
                    "detail": analysis["parse_error"],
                }
            )

        resolved_refs: list[dict[str, Any]] = []
        dynamic_refs: list[dict[str, Any]] = []
        for ref in analysis["references"]:
            if ref["path"] is None:
                dynamic_refs.append(ref)
                continue
            resolution = _resolve_reference(
                ref["path"],
                project_root=root,
                source_path=source_path,
                inventory_by_path=inventory_by_path,
            )
            combined = {**ref, **resolution}
            if resolution["resolution"] == "resolved":
                resolved_refs.append(combined)
            else:
                dynamic_refs.append(combined)

        if dynamic_refs:
            unresolved.append(
                {
                    "type": "unresolved_source_references",
                    "source_path": item["path"],
                    "references": dynamic_refs[:48],
                    "truncated": len(dynamic_refs) > 48,
                }
            )

        reads = sorted(
            {
                ref["artifact_id"]
                for ref in resolved_refs
                if ref["kind"] == "read" and ref.get("artifact_id")
            }
        )
        writes = sorted(
            {
                ref["artifact_id"]
                for ref in resolved_refs
                if ref["kind"] == "write" and ref.get("artifact_id")
            }
        )
        if not reads and not writes:
            continue

        confidence = 0.98 if not dynamic_refs and analysis["parse_ok"] else 0.90
        inference_id = f"W_STATIC_{item['artifact_id']}"
        sources.append(
            {
                "id": inference_id,
                "source_artifact_id": item["artifact_id"],
                "source_path": item["path"],
                "source_kind": source_kind,
                "confidence": confidence,
                "reason": (
                    "Static source analysis resolved literal local artifact paths; "
                    "user code was not executed."
                ),
                "imports": analysis["imports"],
                "resolved_references": resolved_refs,
                "unresolved_reference_count": len(dynamic_refs),
                "reads": reads,
                "writes": writes,
            }
        )

    producers: dict[str, list[str]] = {}
    for source in sources:
        for artifact_id in source["writes"]:
            producers.setdefault(artifact_id, []).append(source["id"])

    ambiguous_outputs = {
        artifact_id: ids
        for artifact_id, ids in producers.items()
        if len(ids) > 1
    }
    for artifact_id, ids in sorted(ambiguous_outputs.items()):
        unresolved.append(
            {
                "type": "multiple_static_producers",
                "artifact_id": artifact_id,
                "source_inference_ids": sorted(ids),
            }
        )

    nodes: list[dict[str, Any]] = []
    node_by_inference: dict[str, str] = {}
    for source in sources:
        outputs = [
            artifact_id
            for artifact_id in source["writes"]
            if artifact_id not in ambiguous_outputs
        ]
        inputs = sorted(
            set([source["source_artifact_id"], *source["reads"]])
        )
        node_id = ("N_STATIC_" + source["source_artifact_id"])[:127]
        node_by_inference[source["id"]] = node_id
        refs = source["resolved_references"][:MAX_CONTRACT_REFERENCES_V06]
        nodes.append(
            {
                "id": node_id,
                "operation": f"static_{source['source_kind']}_workflow",
                "inputs": inputs,
                "outputs": outputs,
                "contract": {
                    "inference_format": WORKFLOW_DISCOVERY_FORMAT_V06,
                    "inference_id": source["id"],
                    "static_only": True,
                    "user_code_executed": False,
                    "source_path": source["source_path"],
                    "source_kind": source["source_kind"],
                    "confidence": source["confidence"],
                    "imports": source["imports"],
                    "resolved_references": [
                        {
                            "kind": ref["kind"],
                            "path": ref["path"],
                            "artifact_id": ref["artifact_id"],
                            "api": ref["api"],
                            "location": ref["location"],
                        }
                        for ref in refs
                    ],
                    "references_truncated": (
                        len(source["resolved_references"]) > len(refs)
                    ),
                },
            }
        )

    producer_node: dict[str, str] = {}
    for node in nodes:
        for artifact_id in node["outputs"]:
            producer_node[artifact_id] = node["id"]

    edges: set[tuple[str, str, str]] = set()
    for node in nodes:
        for artifact_id in node["inputs"]:
            producer = producer_node.get(artifact_id)
            if producer and producer != node["id"]:
                edges.add((producer, node["id"], artifact_id))

    selected_artifact_ids = sorted(
        {
            artifact_id
            for node in nodes
            for artifact_id in node["inputs"] + node["outputs"]
        }
    )

    return {
        "format": WORKFLOW_DISCOVERY_FORMAT_V06,
        "static_only": True,
        "user_code_executed": False,
        "sources": sources,
        "nodes": nodes,
        "edges": [
            {
                "from": source,
                "to": target,
                "artifact_id": artifact_id,
            }
            for source, target, artifact_id in sorted(edges)
        ],
        "selected_artifact_ids": selected_artifact_ids,
        "unresolved": unresolved,
        "summary": {
            "source_files_considered": len(source_items),
            "source_files_with_resolved_dependencies": len(sources),
            "workflow_nodes": len(nodes),
            "workflow_edges": len(edges),
            "resolved_artifact_references": sum(
                len(source["resolved_references"]) for source in sources
            ),
            "unresolved_items": len(unresolved),
        },
    }
