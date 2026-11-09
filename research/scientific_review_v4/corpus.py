"""Hash-verified, independently selected paper/code/data corpus for review v4.

Final source files live outside this checkout until the software freeze. This
module never downloads anything or reads extraction/checking output.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
from research.scientific_intake_v1.intake import _regular,safe_name

_BASE = Path(__file__).resolve().parent
_MANIFEST = _BASE / "source-freeze.json"
_DEFAULT_FINAL = Path("/dev/shm/pcs-review-v4-heldout/sources")
FROZEN_SHA256 = "a9bb072cdc5bfd67845418079beedc4ae213cf26c9550627106f5ef6de3f8a2b"


def source_freeze():
    """Return the public source-selection and exact-byte provenance record."""
    raw=_regular(_MANIFEST,2*1024**2)
    if hashlib.sha256(raw).hexdigest()!=FROZEN_SHA256:
        raise ValueError("source freeze changed")
    value=json.loads(raw)
    erratum=json.loads((_BASE/'source-freeze-errata.json').read_text())
    if (erratum.get('frozen_manifest_sha256')!=FROZEN_SHA256 or
        erratum.get('original')!=value.get('frozen_software_baseline') or
        erratum.get('corrected')!='26a8adda12dbb7fd949f14eeddee3d7d870cadd1' or
        erratum.get('source_bytes_changed') is not False):raise ValueError('invalid metadata erratum')
    return value


def projects(split):
    """Return independent source descriptors for development, final, or all."""
    if split not in {"development", "final", "all"}:
        raise ValueError("split must be development, final, or all")
    return [p for p in source_freeze()["projects"]
            if split == "all" or p["split"] == split]


def _verify(path, record):
    if any(p.is_symlink() for p in [path,*path.parents]):raise ValueError('symlink source component')
    data = _regular(path,5*1024**2)
    if len(data) != record["bytes"] or hashlib.sha256(data).hexdigest() != record["sha256"]:
        raise ValueError(f"frozen source changed: {path}")
    return data


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
    out = Path(out).absolute()
    if out.exists() or out.is_symlink():raise ValueError('refuse corpus overwrite')
    result = [];prepared=[]
    for project in selected:
        root = (Path(source_root) if source_root is not None else
                _BASE / "fixtures" / "development" if project["split"] == "development"
                else (_BASE/'fixtures/final' if (_BASE/'fixtures/final').exists() else _DEFAULT_FINAL))
        source = root / project["id"]
        destination = out / project["id"]
        # Verify the entire project before copying any of its files.
        blobs={};seen=set()
        if len(project['files'])>256:raise ValueError('project file bound')
        for record in project["files"]:
            rel = Path(record["path"])
            if rel.is_absolute() or ".." in rel.parts:
                raise ValueError("unsafe source-relative path")
            identity=safe_name(record['path'])
            if identity in seen:raise ValueError('source path collision')
            seen.add(identity);blobs[record['path']]=_verify(source / rel, record)
        if sum(map(len,blobs.values()))>64*1024**2:raise ValueError('project byte bound')
        prepared.append((project,destination,blobs))
    out.mkdir(parents=True,mode=0o700)
    for project,destination,blobs in prepared:
        for name,data in blobs.items():
            target = destination / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        result.append(dict(project, path=str(destination), directory=str(destination)))
    return result
