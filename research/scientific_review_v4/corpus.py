"""Hash-verified, independently selected paper/code/data corpus for review v4.

Final source files live outside this checkout until the software freeze. This
module never downloads anything or reads extraction/checking output.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil

_BASE = Path(__file__).resolve().parent
_MANIFEST = _BASE / "source-freeze.json"
_DEFAULT_FINAL = Path("/dev/shm/pcs-review-v4-heldout/sources")


def source_freeze():
    """Return the public source-selection and exact-byte provenance record."""
    return json.loads(_MANIFEST.read_text(encoding="utf-8"))


def projects(split):
    """Return independent source descriptors for development, final, or all."""
    if split not in {"development", "final", "all"}:
        raise ValueError("split must be development, final, or all")
    return [p for p in source_freeze()["projects"]
            if split == "all" or p["split"] == split]


def _verify(path, record):
    if not path.is_file():
        raise FileNotFoundError(f"frozen source unavailable: {path}")
    data = path.read_bytes()
    if len(data) != record["bytes"] or hashlib.sha256(data).hexdigest() != record["sha256"]:
        raise ValueError(f"frozen source changed: {path}")


def materialize(out, split, allow_final=False, source_root=None):
    """Copy verified original bytes into per-project directories.

    ``source_root`` is an optional root containing project-id directories. The
    default resolves development fixtures here and final files in heldout RAM.
    Explicit final access is required even when a source root is supplied.
    Returns project descriptors including absolute ``path`` and ``directory``.
    """
    selected = projects(split)
    if any(p["split"] == "final" for p in selected) and not allow_final:
        raise PermissionError("final sources remain held out until software freeze")
    out = Path(out).resolve()
    result = []
    for project in selected:
        root = (Path(source_root) if source_root is not None else
                _BASE / "fixtures" / "development" if project["split"] == "development"
                else _DEFAULT_FINAL)
        source = root / project["id"]
        destination = out / project["id"]
        # Verify the entire project before copying any of its files.
        for record in project["files"]:
            rel = Path(record["path"])
            if rel.is_absolute() or ".." in rel.parts:
                raise ValueError("unsafe source-relative path")
            _verify(source / rel, record)
        for record in project["files"]:
            rel = Path(record["path"])
            target = destination / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            if (source / rel).resolve() != target.resolve():
                shutil.copyfile(source / rel, target)
        result.append(dict(project, path=str(destination), directory=str(destination)))
    return result
