"""Byte-preserving access to prospectively frozen authentic scientific projects.

Imported scientific source is untrusted data. This module never executes it,
extracts claims, imports reference labels, or permits model training. The final
split requires an explicit evaluation opt-in; this is a workflow guard, not an
access-control or immutable-storage claim.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath

BASE = Path(__file__).resolve().parent
FREEZE = BASE / "prospective-source-freeze.json"
FROZEN_SHA256 = "e0bd653e95027eb51e58907dbfbadd5b613a513bceb828426e84182d5dbfcbae"
MAX_SOURCE_BYTES = 2 * 1024 * 1024
MAX_TOTAL_BYTES = 10 * 1024 * 1024
VERSION = "pcs-prospective-scientific-corpus-v3"


class CorpusError(ValueError):
    """Corpus identity, split, or source-integrity contract was violated."""


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _json(value) -> bytes:
    return (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False,
                       allow_nan=False) + "\n").encode("utf-8")


def source_freeze() -> dict:
    """Read identities and hashes only, independently of scientific extraction."""
    raw = FREEZE.read_bytes()
    if _sha(raw) != FROZEN_SHA256:
        raise CorpusError("prospective source freeze changed")
    data = json.loads(raw)
    if not 0 < data["total_fixture_bytes"] <= MAX_TOTAL_BYTES:
        raise CorpusError("source census exceeds byte bound")
    return data


def projects(split: str = "development") -> tuple[dict, ...]:
    if split not in ("development", "final"):
        raise CorpusError("split must be development or final")
    return tuple(c for c in source_freeze()["cases"] if c["split"] == split)


def _read_source(source: dict, split: str, source_root: Path) -> bytes:
    relative = PurePosixPath(source["path"])
    if (relative.is_absolute() or ".." in relative.parts or
            relative.parts[:2] != ("fixtures", split) or
            len(relative.parts) != 4 or source["split"] != split):
        raise CorpusError("source path violates split boundary")
    path = source_root
    for component in relative.parts:
        path = path / component
        if path.is_symlink():
            raise CorpusError("symlink source component forbidden")
    if not path.is_file():
        raise CorpusError("frozen source missing: " + str(relative))
    count = source["byte_count"]
    if type(count) is not int or not 0 <= count <= MAX_SOURCE_BYTES:
        raise CorpusError("source byte bound")
    if path.stat().st_size != count:
        raise CorpusError("frozen source size changed: " + str(relative))
    with path.open("rb") as stream:
        raw = stream.read(MAX_SOURCE_BYTES + 1)
    if len(raw) != count or _sha(raw) != source["sha256"]:
        raise CorpusError("frozen source bytes changed: " + str(relative))
    return raw


def materialize(output: str | Path, split: str = "development", *,
                allow_final: bool = False,
                source_root: str | Path | None = None) -> tuple[dict, ...]:
    """Copy selected sources, preserving original bytes and exact provenance.

    ``source_root`` permits the coordinating evaluator to unlock separately
    staged final sources after a software freeze. It cannot change admitted
    identities or hashes. The output must be new; no code execution is offered.
    """
    if split == "final" and not allow_final:
        raise CorpusError("final sources require explicit post-freeze evaluation opt-in")
    cases = projects(split)
    frozen = source_freeze()
    root = Path(output).absolute()
    if root.exists() or root.is_symlink():
        raise CorpusError("refuse to overwrite corpus output")
    source_root = BASE if source_root is None else Path(source_root).absolute()
    if source_root.is_symlink():
        raise CorpusError("source root may not be a symlink")
    prepared = []
    for case in cases:
        files = []
        seen = set()
        for key in case["artifact_keys"]:
            source = frozen["sources"][key]
            name = PurePosixPath(source["path"]).name
            if source["project_id"] != case["id"] or name in seen:
                raise CorpusError("ambiguous source project or basename")
            seen.add(name)
            files.append((source, _read_source(source, split, source_root)))
        prepared.append((case, files))
    # Validate every selected source before creating partial output.
    root.mkdir(parents=True, exist_ok=False, mode=0o700)
    records = []
    for case, files in prepared:
        directory = root / case["id"]
        directory.mkdir(mode=0o700)
        artifacts = []
        provenance = []
        for source, raw in files:
            name = PurePosixPath(source["path"]).name
            (directory / name).write_bytes(raw)
            artifacts.append({"path": name, "sha256": _sha(raw),
                              "byte_count": len(raw),
                              "role": source["artifact_role"]})
            provenance.append({**source, "materialized_path": name,
                               "transform": "byte-identical-copy",
                               "imported_code_executed": False})
        manifest = {"format": VERSION, "id": case["id"],
                    "identity": case["identity"], "revision": case["revision"],
                    "scientific_domain": case["scientific_domain"],
                    "paper_doi": case["paper_doi"], "artifacts": artifacts,
                    "authority": "NONE", "training_authorized": False,
                    "imported_code_executed": False}
        (directory / "project.json").write_bytes(_json(manifest))
        (directory / "provenance.json").write_bytes(_json({
            "format": VERSION, "project_id": case["id"],
            "source_freeze_sha256": FROZEN_SHA256, "sources": provenance,
            "authority": "NONE", "training_authorized": False,
            "limitations": frozen["limitations"]}))
        records.append({"id": case["id"], "project_id": case["id"],
                        "split": split, "root": str(directory),
                        "path": str(directory), "artifacts": artifacts})
    (root / "corpus.json").write_bytes(_json({"format": VERSION,
        "split": split, "source_freeze_sha256": FROZEN_SHA256,
        "projects": records, "imported_code_executed": False,
        "training_authorized": False}))
    return tuple(records)
