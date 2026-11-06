"""Frozen authentic scientific sources, copied as data without running their code.

Importing this module opens no fixture. ``materialize`` opens only the requested
split and defaults to development. Reference annotations are kept elsewhere and
are never placed in a scientific project. See ``preregistration.json`` for the
source freeze, limitations, identities and collection/evaluation protocol.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

BASE = Path(__file__).resolve().parent
PREREGISTRATION = BASE / "preregistration.json"
SOURCE_MANIFEST = BASE / "fixtures" / "upstream" / "provenance.json"
VERSION = "authentic-scientific-corpus-v2.0"
SPLITS = ("development", "final")
MAX_FIXTURE_BYTES = 10 * 1024 * 1024


class CorpusError(ValueError):
    """Frozen-source provenance or materialization contract was violated."""


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _json(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False,
                       allow_nan=False) + "\n").encode("utf-8")


def preregistration() -> dict:
    """Return frozen protocol metadata; do not open any raw scientific source."""
    return json.loads(PREREGISTRATION.read_text(encoding="utf-8"))


def source_manifest() -> dict:
    """Return source provenance only, checking its preregistered digest."""
    registration = preregistration()
    raw = SOURCE_MANIFEST.read_bytes()
    if _sha(raw) != registration["source_manifest_sha256"]:
        raise CorpusError("source manifest disagrees with preregistration")
    manifest = json.loads(raw)
    if manifest["total_fixture_bytes"] > MAX_FIXTURE_BYTES:
        raise CorpusError("frozen corpus exceeds collection byte bound")
    return manifest


def projects(split: str = "development") -> tuple[dict, ...]:
    """Return fixed identities/revisions without accessing their raw artifacts."""
    if split not in SPLITS:
        raise CorpusError("split must be 'development' or 'final'")
    return tuple(dict(case) for case in preregistration()["cases"]
                 if case["split"] == split)


def _read_source(source: dict, expected: dict, split: str) -> bytes:
    relative = Path(source["path"])
    required_parent = "heldout" if split == "final" else "upstream"
    if (relative.is_absolute() or ".." in relative.parts or
            relative.parts[:2] != ("fixtures", required_parent)):
        raise CorpusError("source path violates frozen split boundary")
    path = BASE / relative
    if path.is_symlink() or not path.is_file():
        raise CorpusError("frozen source is absent or a symlink")
    if path.stat().st_size != expected["byte_count"]:
        raise CorpusError("frozen source byte count changed: " + str(relative))
    raw = path.read_bytes()
    if (_sha(raw) != source["sha256"] or _sha(raw) != expected["sha256"] or
            len(raw) != source["byte_count"]):
        raise CorpusError("frozen source digest changed: " + str(relative))
    return raw


def materialize(output: str | Path, split: str = "development") -> tuple[dict, ...]:
    """Create source projects and return paths, artifacts and provenance records.

    ``output`` must not exist. Each project contains byte-identical external
    artifacts, publication excerpts explicitly marked as derivatives where full
    paper redistribution is not licensed, and generated descriptive manifests.
    No scientific assertion is promoted to truth by this packaging operation.
    """
    selected = projects(split)
    registration = preregistration()
    manifest = source_manifest()
    root = Path(output).absolute()
    if root.exists() or root.is_symlink():
        raise CorpusError("refuse to overwrite materialization output")
    # Check every selected source before making a partial output directory.
    prepared = []
    for case in selected:
        files = []
        for key in case["artifact_keys"]:
            source = manifest["sources"][key]
            expected = registration["pinned_artifacts"][key]
            if source["path"] != expected["path"]:
                raise CorpusError("source path changed after preregistration")
            raw = _read_source(source, expected, split)
            files.append((key, source, raw))
        prepared.append((case, files))
    root.mkdir(parents=True, exist_ok=False, mode=0o700)
    records = []
    for case, files in prepared:
        directory = root / case["id"]
        directory.mkdir(mode=0o700)
        artifacts = []
        provenance = []
        for key, source, raw in files:
            name = Path(source["path"]).name
            (directory / name).write_bytes(raw)
            artifacts.append({"path": name, "sha256": source["sha256"],
                              "byte_count": len(raw), "role": source["artifact_role"],
                              "status": source["status"], "source_key": key})
            provenance.append({**source, "materialized_path": name,
                               "copy_transform": "byte-identical-copy",
                               "copied_sha256": _sha(raw),
                               "imported_code_executed": False})
        description = {
            "format": "pcs-authentic-scientific-project-v2", "id": case["id"],
            "identity": case["identity"], "revision": case["revision"],
            "scientific_domain": case["scientific_domain"],
            "paper_doi": case["paper_doi"], "artifacts": artifacts,
            "packaging": "Source files and short publication excerpts are copied byte for byte; this manifest is generated packaging metadata.",
            "imported_code_executed": False,
        }
        (directory / "project.json").write_bytes(_json(description))
        project_provenance = {
            "format": VERSION, "project_id": case["id"],
            "preregistration_sha256": _sha(PREREGISTRATION.read_bytes()),
            "source_manifest_sha256": registration["source_manifest_sha256"],
            "sources": provenance, "authority": "NONE",
            "imported_code_executed": False,
            "paper_permission_note": "BioModels model encodings have embedded CC0 notices. The original 1991 papers are represented only by limited attributed excerpts. SciPy source is BSD-3-Clause and the SciPy 2020 paper is CC-BY-4.0, as recorded in original notices.",
        }
        (directory / "provenance.json").write_bytes(_json(project_provenance))
        records.append({"id": case["id"], "project_id": case["id"],
                        "split": split, "root": str(directory),
                        "path": str(directory), "artifacts": artifacts,
                        "manifest": str(directory / "project.json"),
                        "provenance": str(directory / "provenance.json")})
    (root / "corpus.json").write_bytes(_json({
        "format": VERSION, "split": split, "projects": records,
        "source_manifest_sha256": registration["source_manifest_sha256"],
        "scientific_case_count": len(records), "imported_code_executed": False,
    }))
    return tuple(records)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--split", choices=SPLITS, default="development")
    args = parser.parse_args(argv)
    for record in materialize(args.output, args.split):
        print(record["project_id"] + "\t" + record["root"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
