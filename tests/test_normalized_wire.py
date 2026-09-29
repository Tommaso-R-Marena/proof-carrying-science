from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from pcs.kernel import build_certificate
from pcs.normalized_wire import (
    NormalizationError,
    _normalize_verified_object,
    normalize_verified_certificate,
    predicate_commitment,
    validate_normalized_wire,
    wire_semantic_hash,
)


def test_verified_pkpd_certificate_normalizes_claim_scope():
    root = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory() as d:
        out = Path(d) / "evidence"
        cert = build_certificate(root / "examples/pkpd_one_compartment/manifest.json", out)
        wire = normalize_verified_certificate(out / "certificate.json", "C_PK_REPLAY")

        assert wire["wire_format"] == "pcs-normalized-decision-v1"
        assert wire["source"]["certificate_semantic_hash"] == cert["semantic_hash"]
        assert wire["claim"]["id"] == "C_PK_REPLAY"
        assert wire["decision"] == "COMPUTATIONALLY_SUPPORTED"
        assert [e["id"] for e in wire["evidence"]] == ["E_PK_REPLAY"]
        assert [a["id"] for a in wire["context"]] == ["A_PK_MODEL"]
        assert wire["invariants"] == {
            "unique_evidence_ids": True,
            "required_ids_unique": True,
            "all_required_evidence_present": True,
            "context_covers": True,
            "required_evidence_bound": True,
        }
        assert wire["wire_semantic_hash"] == wire_semantic_hash(wire)


def test_predicate_commitment_covers_numeric_tolerance_fields():
    a = {
        "type": "pkpd_reference_match",
        "model_artifact": "m",
        "output_artifact": "o",
        "time_column": "time",
        "concentration_column": "concentration",
        "effect_column": "effect",
        "rel_tol": 1e-9,
        "abs_tol": 1e-12,
    }
    b = dict(a)
    b["rel_tol"] = 1e-6
    assert predicate_commitment(a) != predicate_commitment(b)


def test_normalizer_rejects_artifact_tampering_before_wire_export():
    root = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory() as d:
        out = Path(d) / "evidence"
        cert = build_certificate(root / "examples/pkpd_one_compartment/manifest.json", out)
        artifact = next(a for a in cert["artifacts"] if a["id"] == "pk_predictions")
        path = out / artifact["path"]
        path.write_text(path.read_text(encoding="utf-8") + "\n999,999,999\n", encoding="utf-8")
        with pytest.raises(NormalizationError, match="replay-verify"):
            normalize_verified_certificate(out / "certificate.json", "C_PK_REPLAY")


def test_normalizer_rejects_repeated_required_evidence_ids():
    predicate = {"type": "unit_compatible", "left_unit": "mg", "right_unit": "g"}
    cert = {
        "spec_version": "pcs-0.5",
        "checker_version": "pcs-python-kernel/0.5.0",
        "semantic_hash": "0" * 64,
        "assumptions": [],
        "claims": [{
            "id": "C",
            "kind": "computational",
            "predicate": predicate,
            "required_evidence": ["E", "E"],
            "assumptions": [],
            "assessment": {
                "status": "COMPUTATIONALLY_SUPPORTED",
                "reason": "all declared computational checks passed",
            },
        }],
        "evidence": [{
            "id": "E",
            "kind": "computational_test",
            "outcome": "PASS",
            "check_spec": {
                "id": "E",
                "type": "unit_compatible",
                "left_unit": "mg",
                "right_unit": "g",
                "claim_ids": ["C"],
            },
        }],
    }
    with pytest.raises(NormalizationError, match="repeats a required evidence id"):
        _normalize_verified_object(cert, "C")


def test_normalizer_requires_every_required_evidence_to_share_exact_predicate_commitment():
    p1 = {"type": "unit_compatible", "left_unit": "mg", "right_unit": "g"}
    cert = {
        "spec_version": "pcs-0.5",
        "checker_version": "pcs-python-kernel/0.5.0",
        "semantic_hash": "0" * 64,
        "assumptions": [],
        "claims": [{
            "id": "C",
            "kind": "computational",
            "predicate": p1,
            "required_evidence": ["E1", "E2"],
            "assumptions": [],
            "assessment": {
                "status": "COMPUTATIONALLY_SUPPORTED",
                "reason": "all declared computational checks passed",
            },
        }],
        "evidence": [
            {
                "id": "E1",
                "kind": "computational_test",
                "outcome": "PASS",
                "check_spec": {
                    "id": "E1",
                    "type": "unit_compatible",
                    "left_unit": "mg",
                    "right_unit": "g",
                    "claim_ids": ["C"],
                },
            },
            {
                "id": "E2",
                "kind": "computational_test",
                "outcome": "PASS",
                "check_spec": {
                    "id": "E2",
                    "type": "unit_compatible",
                    "left_unit": "mg",
                    "right_unit": "kg",
                    "claim_ids": ["C"],
                },
            },
        ],
    }
    with pytest.raises(NormalizationError, match="not exactly predicate-bound"):
        _normalize_verified_object(cert, "C")


def test_unknown_claim_rejected():
    cert = {
        "spec_version": "pcs-0.5",
        "checker_version": "pcs-python-kernel/0.5.0",
        "semantic_hash": "0" * 64,
        "assumptions": [],
        "claims": [],
        "evidence": [],
    }
    with pytest.raises(NormalizationError, match="unknown claim id"):
        _normalize_verified_object(cert, "C")


def test_frozen_cross_language_wire_vector():
    root = Path(__file__).resolve().parents[1]
    fixture = json.loads((root / "tests/normalized_wire_vectors.json").read_text(encoding="utf-8"))
    assert fixture["format"] == "pcs-normalized-wire-vectors-v1"
    vector = fixture["vectors"][0]
    assert predicate_commitment(vector["full_python_predicate"]) == vector["predicate_commitment"]
    wire = vector["wire"]
    assert wire["claim"]["predicate_commitment"] == vector["predicate_commitment"]
    assert wire["evidence"][0]["predicate_commitment"] == vector["predicate_commitment"]
    assert wire["decision"] == "COMPUTATIONALLY_SUPPORTED"
    assert wire["wire_semantic_hash"] == wire_semantic_hash(wire)


def test_wire_verifier_rejects_rehashed_predicate_binding_tamper():
    root = Path(__file__).resolve().parents[1]
    fixture = json.loads((root / "tests/normalized_wire_vectors.json").read_text(encoding="utf-8"))
    wire = json.loads(json.dumps(fixture["vectors"][0]["wire"]))
    wire["evidence"][0]["predicate_commitment"] = "pcs-predicate-sha256:" + "1" * 64
    wire["invariants"]["required_evidence_bound"] = True
    wire["wire_semantic_hash"] = wire_semantic_hash(wire)
    result = validate_normalized_wire(wire)
    assert not result["valid"]
    assert any("predicate commitment differs" in e for e in result["errors"])


def test_wire_verifier_rejects_rehashed_decision_tamper():
    root = Path(__file__).resolve().parents[1]
    fixture = json.loads((root / "tests/normalized_wire_vectors.json").read_text(encoding="utf-8"))
    wire = json.loads(json.dumps(fixture["vectors"][0]["wire"]))
    wire["decision"] = "OPEN"
    wire["wire_semantic_hash"] = wire_semantic_hash(wire)
    result = validate_normalized_wire(wire)
    assert not result["valid"]
    assert any("normalized decision mismatch" in e for e in result["errors"])


def test_wire_verifier_rejects_hash_tamper():
    root = Path(__file__).resolve().parents[1]
    fixture = json.loads((root / "tests/normalized_wire_vectors.json").read_text(encoding="utf-8"))
    wire = json.loads(json.dumps(fixture["vectors"][0]["wire"]))
    wire["source"]["claim_id"] = "OTHER"
    result = validate_normalized_wire(wire)
    assert not result["valid"]
    assert "wire semantic hash mismatch" in result["errors"]
    assert "source claim id does not match normalized claim id" in result["errors"]
