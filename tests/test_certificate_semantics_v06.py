from __future__ import annotations

from copy import deepcopy

import pytest

from pcs.certificate_semantics_v06 import (
    V06CertificateSemanticsError,
    validate_certificate_semantics_v06,
)
from pcs.certificate_v06 import finalize_certificate_hashes_v06


PREDICATE = {
    "type": "reaction_balance",
    "reactants": [
        {"formula": "H2", "coefficient": 2},
        {"formula": "O2", "coefficient": 1},
    ],
    "products": [{"formula": "H2O", "coefficient": 2}],
}


def certificate_source() -> dict:
    return {
        "spec_version": "pcs-0.6",
        "checker_version": "pcs-python-kernel/0.6.0-dev",
        "canonical_json_profile": "pcs-jcs-rfc8785-v1",
        "semantic_hash_format": "pcs-certificate-semantic-sha256-v2",
        "integrity_hash_format": "pcs-certificate-integrity-sha256-v2",
        "generated_at": "2026-09-29T00:00:00+00:00",
        "subject": "typed semantics fixture",
        "mission_scope": "structural and logical binding test fixture",
        "assumptions": [
            {"id": "A1", "statement": "fixture assumption", "scope": ["C1"]}
        ],
        "claims": [
            {
                "id": "C1",
                "statement": "The fixture reaction is atom-balanced.",
                "kind": "computational",
                "predicate": deepcopy(PREDICATE),
                "required_evidence": ["E1"],
                "assumptions": ["A1"],
                "assessment": {
                    "status": "COMPUTATIONALLY_SUPPORTED",
                    "reason": "all declared computational checks passed",
                },
            }
        ],
        "artifacts": [],
        "evidence": [
            {
                "id": "E1",
                "kind": "computational_test",
                "claim_ids": ["C1"],
                "outcome": "PASS",
                "checker": "pcs-python-kernel/0.6.0-dev",
                "predicate": deepcopy(PREDICATE),
                "artifact_ids": [],
                "check_spec": deepcopy(PREDICATE),
            }
        ],
        "workflow": {"nodes": []},
        "workflow_summary": {"node_count": 0, "topological_order": []},
        "semantic_hash": "",
        "integrity_hash": "",
    }


def finalized() -> dict:
    return finalize_certificate_hashes_v06(certificate_source())


def expect_semantic_rejection(cert: dict, text: str) -> None:
    with pytest.raises(V06CertificateSemanticsError, match=text):
        validate_certificate_semantics_v06(cert)


def test_typed_v06_certificate_semantics_accept():
    validate_certificate_semantics_v06(finalized())


def test_duplicate_claim_id_rejected():
    cert = finalized()
    cert["claims"].append(deepcopy(cert["claims"][0]))
    expect_semantic_rejection(cert, "duplicate claim id")


def test_assumption_scope_must_be_bidirectional():
    cert = finalized()
    cert["assumptions"][0]["scope"] = []
    expect_semantic_rejection(cert, "assumption scope does not include")


def test_evidence_claim_binding_must_be_bidirectional():
    cert = finalized()
    cert["evidence"][0]["claim_ids"] = []
    expect_semantic_rejection(cert, "does not declare support")


def test_required_evidence_predicate_substitution_rejected():
    cert = finalized()
    cert["evidence"][0]["predicate"] = {
        "type": "unit_compatible",
        "left_unit": "mg/L",
        "right_unit": "g/L",
    }
    cert["evidence"][0]["check_spec"] = deepcopy(cert["evidence"][0]["predicate"])
    expect_semantic_rejection(cert, "do not carry the exact same predicate")


def test_evidence_predicate_must_match_check_spec():
    cert = finalized()
    cert["evidence"][0]["predicate"] = {
        "type": "unit_compatible",
        "left_unit": "mg/L",
        "right_unit": "g/L",
    }
    expect_semantic_rejection(cert, "predicate differs from its check specification")


def test_builtin_evidence_artifact_binding_is_exact():
    cert = finalized()
    cert["artifacts"] = [
        {
            "id": "unused",
            "path": "artifacts/unused/payload",
            "role": "fixture",
            "sha256": "0" * 64,
            "media_type": "application/octet-stream",
        }
    ]
    cert["evidence"][0]["artifact_ids"] = ["unused"]
    expect_semantic_rejection(cert, "artifact_ids differ")


def test_unknown_artifact_in_claim_predicate_rejected():
    cert = finalized()
    predicate = {
        "type": "pkpd_contract",
        "model_artifact": "missing_model",
    }
    cert["claims"][0]["predicate"] = deepcopy(predicate)
    cert["evidence"][0]["predicate"] = deepcopy(predicate)
    cert["evidence"][0]["check_spec"] = deepcopy(predicate)
    cert["evidence"][0]["artifact_ids"] = ["missing_model"]
    expect_semantic_rejection(cert, "unknown artifact")


def test_forged_claim_assessment_rejected():
    cert = finalized()
    cert["claims"][0]["assessment"] = {
        "status": "OPEN",
        "reason": "forged",
    }
    expect_semantic_rejection(cert, "assessment mismatch")


def test_artifact_path_traversal_rejected():
    cert = finalized()
    cert["artifacts"] = [
        {
            "id": "A",
            "path": "../escape",
            "role": "fixture",
            "sha256": "0" * 64,
            "media_type": "application/octet-stream",
        }
    ]
    expect_semantic_rejection(cert, "not a canonical relative path")


def test_workflow_summary_is_recomputed():
    cert = finalized()
    cert["workflow_summary"] = {"node_count": 1, "topological_order": []}
    expect_semantic_rejection(cert, "workflow_summary")


def test_workflow_cycle_rejected():
    cert = finalized()
    cert["artifacts"] = [
        {
            "id": "x",
            "path": "artifacts/x/payload",
            "role": "fixture",
            "sha256": "0" * 64,
            "media_type": "application/octet-stream",
        },
        {
            "id": "y",
            "path": "artifacts/y/payload",
            "role": "fixture",
            "sha256": "1" * 64,
            "media_type": "application/octet-stream",
        },
    ]
    cert["workflow"] = {
        "nodes": [
            {
                "id": "N1",
                "operation": "one",
                "inputs": ["y"],
                "outputs": ["x"],
                "contract": {"type": "none"},
            },
            {
                "id": "N2",
                "operation": "two",
                "inputs": ["x"],
                "outputs": ["y"],
                "contract": {"type": "none"},
            },
        ]
    }
    cert["workflow_summary"] = {"node_count": 2, "topological_order": ["N1", "N2"]}
    expect_semantic_rejection(cert, "workflow cycle")


def test_multiple_workflow_producers_rejected():
    cert = finalized()
    cert["artifacts"] = [
        {
            "id": "x",
            "path": "artifacts/x/payload",
            "role": "fixture",
            "sha256": "0" * 64,
            "media_type": "application/octet-stream",
        }
    ]
    cert["workflow"] = {
        "nodes": [
            {
                "id": "N1",
                "operation": "one",
                "inputs": [],
                "outputs": ["x"],
                "contract": {"type": "none"},
            },
            {
                "id": "N2",
                "operation": "two",
                "inputs": [],
                "outputs": ["x"],
                "contract": {"type": "none"},
            },
        ]
    }
    cert["workflow_summary"] = {"node_count": 2, "topological_order": ["N1", "N2"]}
    expect_semantic_rejection(cert, "multiple workflow producers")
