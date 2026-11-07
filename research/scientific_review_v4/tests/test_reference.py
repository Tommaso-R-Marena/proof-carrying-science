"""Reference integrity/access tests independent of the scientific runtime."""
import importlib.util
import hashlib
import json
from pathlib import Path

import pytest

BASE = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("independent_review_reference", BASE / "reference.py")
REFERENCE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(REFERENCE)


def test_final_labels_require_explicit_evaluation_access():
    with pytest.raises(ValueError, match="evaluation-only"):
        REFERENCE.load_reference("final")


def test_unknown_split_rejected():
    with pytest.raises(ValueError, match="unknown scientific reference split"):
        REFERENCE.load_reference("training")


def test_frozen_development_references_and_workflow():
    rows = REFERENCE.load_reference("development")
    assert len(rows) == 30
    assert sum(row["expected_status"] == "supported" for row in rows) == 25
    assert sum(row["label_provenance"]["reviewer_authored_counterclaim"] for row in rows) == 5
    assert all(not row["label_provenance"]["external_expert_review"] for row in rows)
    assert len(REFERENCE.load_workflow_rubric("development")) == 8
    assert REFERENCE.load_protocol()["source_freeze_sha256"] == REFERENCE.canonical_sha256(BASE / "source-freeze.json")
    REFERENCE.validate_source_bindings(rows, project_root=BASE.parents[1])


def test_source_quote_and_path_tampering_rejected(tmp_path):
    source = tmp_path / "original.txt"
    source.write_text("original scientific statement", encoding="utf-8")
    raw = source.read_bytes()
    row = {"source": {"path": "original.txt", "sha256": hashlib.sha256(raw).hexdigest(),
                      "quote": "original", "byte_start": 0, "byte_end": 8}}
    REFERENCE.validate_source_bindings([row], project_root=tmp_path)
    row["source"]["quote"] = "modified"
    with pytest.raises(ValueError, match="quote mismatch"):
        REFERENCE.validate_source_bindings([row], project_root=tmp_path)
    row["source"]["path"] = "../original.txt"
    with pytest.raises(ValueError, match="project-relative"):
        REFERENCE.validate_source_bindings([row], project_root=tmp_path)


def test_annotation_byte_change_is_rejected(tmp_path):
    path = tmp_path / "development.json"
    path.write_text('{"schema_version":"scientific-reference-v4","annotations":[]}', encoding="utf-8")
    freeze = {"schema_version": "scientific-annotation-freeze-v4", "files": {
        "development.json": hashlib.sha256(path.read_bytes()).hexdigest()}}
    (tmp_path / "annotation-freeze.json").write_text(json.dumps(freeze), encoding="utf-8")
    path.write_text(path.read_text() + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="hash mismatch"):
        REFERENCE.load_reference("development", reference_root=tmp_path)


def test_verification_is_separate_from_source_support():
    rows = REFERENCE.load_reference("development")
    supported = [row for row in rows if row["expected_status"] == "supported"]
    assert any(row["verification_expectation"]["status"] == "unknown" for row in supported)
    assert {row["kind"] for row in supported} == {"scientific_claim", "quantity", "equation"}
    assert all(row.get("caveats") is not None for row in rows)
