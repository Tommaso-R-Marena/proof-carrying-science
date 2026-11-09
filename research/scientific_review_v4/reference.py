"""Hash-bound independent review labels; never interpreter or retrieval inputs.

Final labels require an explicit evaluation-only opt-in. This module does not
import the interpreter, checker, extractor, or their outputs.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

_ROOT = Path(__file__).resolve().parent / "reference"
SCHEMA_VERSION = "scientific-reference-v4"


def canonical_sha256(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _read_frozen(name: str, root: Path) -> dict:
    original=root / 'annotation-freeze.json'
    recovered=root / 'annotation-freeze-recovered.json'
    if recovered.exists():
        if canonical_sha256(original)!='0de3e945881de16047584e84720aed388f081f32d8660755304e4ab474a8795b':
            raise ValueError('original annotation freeze changed')
        if canonical_sha256(recovered)!='5dbf52e99976fe656b9423f4fb0b49ad50bf5989a56e0736dec87bad57f5da79':
            raise ValueError('recovered annotation freeze changed')
        freeze=json.loads(recovered.read_text(encoding='utf-8'))
    else:
        freeze=json.loads(original.read_text(encoding='utf-8'))
    path = root / name
    if freeze.get("schema_version") not in {"scientific-annotation-freeze-v4","scientific-annotation-freeze-recovered-v4"}:
        raise ValueError("unsupported scientific annotation freeze")
    if canonical_sha256(path) != freeze["files"].get(name):
        raise ValueError("scientific reference hash mismatch: " + name)
    return json.loads(path.read_text(encoding="utf-8"))


def load_protocol(*, reference_root: str | Path | None = None) -> dict:
    root = Path(reference_root) if reference_root is not None else _ROOT
    return _read_frozen("protocol.json", root)


def load_reference(split: str, *, allow_final: bool = False,
                   reference_root: str | Path | None = None) -> list[dict]:
    if split not in {"development", "final"}:
        raise ValueError("unknown scientific reference split")
    if split == "final" and not allow_final:
        raise ValueError("final references are evaluation-only; explicit opt-in required")
    root = Path(reference_root) if reference_root is not None else _ROOT
    payload = _read_frozen(split + ".json", root)
    if payload.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("unsupported scientific reference schema")
    rows = payload.get("annotations")
    if not isinstance(rows, list) or not rows:
        raise ValueError("missing scientific reference annotations")
    ids = []
    for row in rows:
        if not isinstance(row, dict) or row.get("split") != split:
            raise ValueError("malformed scientific reference annotations")
        identifier = row.get("id")
        if not isinstance(identifier, str) or not identifier:
            raise ValueError("invalid scientific reference identifier")
        ids.append(identifier)
        typed = row.get("typed_expectation", {})
        if any(key not in typed for key in ("kind", "entity", "scope", "relation", "quantity_role", "unit", "conditions")):
            raise ValueError("incomplete typed scientific expectation")
        if not ("value" in typed or "canonical_rhs" in typed):
            raise ValueError("scientific expectation needs value or canonical_rhs")
        if row.get("expected_status") not in {"supported", "contradicted", "insufficient_evidence"}:
            raise ValueError("invalid source-support status")
        if row.get("verification_expectation", {}).get("status") not in {"supported", "unknown"}:
            raise ValueError("invalid verification expectation")
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate scientific reference identifiers")
    return rows


def load_workflow_rubric(split: str, *, allow_final: bool = False,
                         reference_root: str | Path | None = None) -> list[dict]:
    # Exercise exactly the same final-access and hash guards as annotation reads.
    rows = load_reference(split, allow_final=allow_final, reference_root=reference_root)
    root = Path(reference_root) if reference_root is not None else _ROOT
    payload = _read_frozen(split + ".json", root)
    rubric = payload.get("workflow_utility_rubric", [])
    known_ids = {row["id"] for row in rows}
    projects = {row["project_id"] for row in rows}
    for project in projects:
        questions = [question for question in rubric if question.get("project_id") == project]
        if len(questions) != 8:
            raise ValueError("workflow rubric requires eight questions per study")
        for question in questions:
            if not question.get("required_annotation_ids") or not set(question["required_annotation_ids"]).issubset(known_ids):
                raise ValueError("workflow rubric has missing annotation references")
            if not question.get("required_check_scopes"):
                raise ValueError("workflow rubric needs explicit check scopes")
            if question.get("expected_answer") not in {"supported", "unknown"}:
                raise ValueError("invalid workflow expected answer")
    return rubric


def validate_source_bindings(rows: list[dict], *, project_root: str | Path) -> None:
    """Validate original bytes and exact UTF-8 spans, without interpreting claims."""
    root = Path(project_root).resolve()
    for row in rows:
        evidence = [row["source"], *row.get("additional_sources", [])]
        for source in evidence:
            relative = Path(source["path"])
            if relative.is_absolute() or ".." in relative.parts:
                raise ValueError("source paths must be project-relative")
            path = (root / relative).resolve()
            if not path.is_relative_to(root):
                raise ValueError("source path escapes project root")
            raw = path.read_bytes()
            if hashlib.sha256(raw).hexdigest() != source["sha256"]:
                raise ValueError("scientific source hash mismatch")
            start, end = source["byte_start"], source["byte_end"]
            if not isinstance(start, int) or not isinstance(end, int) or not (0 <= start < end <= len(raw)):
                raise ValueError("invalid scientific source span")
            if raw[start:end] != source["quote"].encode("utf-8"):
                raise ValueError("scientific source quote mismatch")
