from __future__ import annotations

import importlib.metadata
import json
import platform
import sys
from pathlib import Path
from typing import Any

from .hashing import sha256_json

RUNTIME_FORMAT = "pcs-runtime-v1"


def _packages() -> list[dict[str, str]]:
    seen: dict[str, str] = {}
    for dist in importlib.metadata.distributions():
        name = (dist.metadata.get("Name") or "").strip()
        if not name:
            continue
        key = name.casefold()
        version = str(dist.version)
        # If duplicate metadata is present, retain a deterministic representative.
        previous = seen.get(key)
        if previous is None or version < previous:
            seen[key] = version
    return [
        {"name": name, "version": seen[name]}
        for name in sorted(seen)
    ]


def snapshot_environment() -> dict[str, Any]:
    """Return deterministic runtime provenance without environment variables or secrets."""
    snapshot: dict[str, Any] = {
        "format": RUNTIME_FORMAT,
        "python": {
            "implementation": platform.python_implementation(),
            "version": platform.python_version(),
            "version_info": list(sys.version_info[:3]),
        },
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "architecture": platform.architecture()[0],
        },
        "packages": _packages(),
    }
    snapshot["semantic_hash"] = sha256_json(snapshot)
    return snapshot


def write_environment(path: str | Path) -> dict[str, Any]:
    snapshot = snapshot_environment()
    Path(path).write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return snapshot


def _package_map(snapshot: dict[str, Any]) -> dict[str, str]:
    return {
        str(p.get("name")): str(p.get("version"))
        for p in snapshot.get("packages", [])
        if isinstance(p, dict) and p.get("name")
    }


def diff_environments(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    lp, rp = _package_map(left), _package_map(right)
    added = {k: rp[k] for k in sorted(rp.keys() - lp.keys())}
    removed = {k: lp[k] for k in sorted(lp.keys() - rp.keys())}
    changed = {
        k: {"left": lp[k], "right": rp[k]}
        for k in sorted(lp.keys() & rp.keys())
        if lp[k] != rp[k]
    }
    return {
        "same_semantic_hash": left.get("semantic_hash") == right.get("semantic_hash"),
        "python_changed": left.get("python") != right.get("python"),
        "platform_changed": left.get("platform") != right.get("platform"),
        "packages_added": added,
        "packages_removed": removed,
        "packages_changed": changed,
    }


def diff_environment_files(left_path: str | Path, right_path: str | Path) -> dict[str, Any]:
    left = json.loads(Path(left_path).read_text(encoding="utf-8"))
    right = json.loads(Path(right_path).read_text(encoding="utf-8"))
    if left.get("format") != RUNTIME_FORMAT or right.get("format") != RUNTIME_FORMAT:
        raise ValueError("unsupported PCS runtime snapshot format")
    return diff_environments(left, right)
