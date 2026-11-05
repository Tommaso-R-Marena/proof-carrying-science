from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def collect_file_hashes(root: Path, *, relative_to: Path | None = None) -> dict[str, str]:
    base = relative_to or root
    out: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if path.name == "FIXTURE_HASHES.json":
            continue
        if "__pycache__" in path.parts or path.suffix == ".pyc":
            continue
        rel = path.relative_to(base).as_posix()
        out[rel] = sha256_file(path)
    return out


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def verify_hashes(expected: dict[str, str], root: Path, *, relative_to: Path | None = None) -> list[str]:
    """Return list of mismatch descriptions; empty means all match."""
    base = relative_to or root
    errors: list[str] = []
    for rel, digest in sorted(expected.items()):
        path = base / rel
        if not path.is_file():
            errors.append(f"missing: {rel}")
            continue
        actual = sha256_file(path)
        if actual != digest:
            errors.append(f"hash mismatch: {rel} expected={digest} actual={actual}")
    return errors
