"""Read hash-frozen, independently transcribed internal scientific references.

References are evaluation inputs, never interpreter/ranker inputs. Importing this
module performs no I/O. Final labels require an explicit evaluation-only opt-in.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path

_ROOT = Path(__file__).resolve().parent / "reference"


def canonical_sha256(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_protocol() -> dict:
    path = _ROOT / "protocol.json"
    freeze = json.loads((_ROOT / "annotation-freeze.json").read_text(encoding="utf-8"))
    if canonical_sha256(path) != freeze["files"]["protocol.json"]:
        raise ValueError("scientific reference protocol hash mismatch")
    return json.loads(path.read_text(encoding="utf-8"))


def load_reference(split: str, *, allow_final: bool = False, reference_root: str | Path | None = None) -> list[dict]:
    """Load a byte-bound reference split; reject final access without opt-in."""
    if split not in {"development", "final"}:
        raise ValueError("unknown scientific reference split")
    if split == "final" and not allow_final:
        raise ValueError("final references are evaluation-only; explicit opt-in required")
    root = Path(reference_root) if reference_root is not None else _ROOT
    path = root / f"{split}.json"
    freeze_path = root / "annotation-freeze.json"
    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
    expected = freeze["files"][f"{split}.json"]
    if canonical_sha256(path) != expected:
        raise ValueError("scientific reference annotation hash mismatch")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != "scientific-reference-v3":
        raise ValueError("unsupported scientific reference schema")
    rows = payload.get("annotations")
    if not isinstance(rows, list) or any(not isinstance(row, dict) or row.get("split") != split for row in rows):
        raise ValueError("malformed scientific reference annotations")
    ids = [row.get("id") for row in rows]
    if any(not isinstance(item, str) or not item for item in ids) or len(ids) != len(set(ids)):
        raise ValueError("duplicate or invalid scientific reference identifiers")
    return rows
