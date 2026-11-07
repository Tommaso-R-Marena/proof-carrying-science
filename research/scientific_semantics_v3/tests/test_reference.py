"""Reference integrity checks do not invoke or inspect the interpreter."""
import hashlib
import json
from pathlib import Path
import pytest
from research.scientific_semantics_v3 import reference


def test_development_labels_are_frozen_and_source_grounded():
    rows = reference.load_reference("development")
    assert len(rows) == 28
    assert sum(row["expected_status"] == "supported" for row in rows) == 22
    repository = Path(__file__).resolve().parents[3]
    for row in rows:
        source = row["source"]
        data = (repository / source["path"]).read_bytes()
        assert hashlib.sha256(data).hexdigest() == source["sha256"]
        assert data[source["byte_start"]:source["byte_end"]] == source["quote"].encode()
        assert row["label_provenance"]["pcs_output_used"] is False
        assert row["label_provenance"]["external_expert_review"] is False


def test_final_references_fail_closed_without_explicit_opt_in():
    with pytest.raises(ValueError, match="evaluation-only"):
        reference.load_reference("final")


def test_reference_tampering_is_rejected(tmp_path):
    root = Path(reference.__file__).resolve().parent / "reference"
    (tmp_path / "annotation-freeze.json").write_bytes((root / "annotation-freeze.json").read_bytes())
    (tmp_path / "development.json").write_bytes((root / "development.json").read_bytes() + b" ")
    with pytest.raises(ValueError, match="hash mismatch"):
        reference.load_reference("development", reference_root=tmp_path)


def test_protocol_records_internal_review_and_keeps_evidence_levels_separate():
    protocol = reference.load_protocol()
    assert "not external expert" in protocol["annotation_role"]
    assert "source_declaration" in protocol["evidence_levels"]
    assert "numerical_reproduction" in protocol["evidence_levels"]
    assert "empirical_scientific_conclusion" in protocol["evidence_levels"]
