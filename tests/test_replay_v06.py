from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

from pcs.byte_contract_v06 import parse_certificate_bytes_v06
from pcs.certificate_v06 import finalize_certificate_hashes_v06
from pcs.replay_v06 import verify_certificate_replay_v06


ROOT = Path(__file__).resolve().parents[1]
GOLDEN = ROOT / "tests" / "v06_golden"


def golden_certificate() -> dict:
    return parse_certificate_bytes_v06((GOLDEN / "certificate.json").read_bytes())


def test_golden_typed_certificate_replays_successfully():
    cert = golden_certificate()
    result = verify_certificate_replay_v06(
        cert,
        {
            "certificate.json": (GOLDEN / "certificate.json").read_bytes(),
            "artifacts/fixture.bin": (GOLDEN / "artifacts/fixture.bin").read_bytes(),
        },
    )
    assert result["valid"], result["errors"]
    assert result["claim_statuses"] == {"C1": "COMPUTATIONALLY_SUPPORTED"}
    assert result["evidence"][0]["outcome"] == "PASS"


def test_validly_rehashed_forged_pass_fail_record_is_rejected_by_replay():
    cert = golden_certificate()
    forged = deepcopy(cert)
    forged["evidence"][0]["outcome"] = "FAIL"
    forged["claims"][0]["assessment"] = {
        "status": "FALSIFIED_OR_CHECK_FAILED",
        "reason": "at least one required check failed",
    }
    forged["semantic_hash"] = ""
    forged["integrity_hash"] = ""
    forged = finalize_certificate_hashes_v06(forged)

    result = verify_certificate_replay_v06(forged, {})
    assert not result["valid"]
    assert any("replay outcome mismatch" in error for error in result["errors"])


def test_validly_rehashed_false_pass_is_rejected_by_replay():
    cert = golden_certificate()
    forged = deepcopy(cert)
    bad = {
        "type": "reaction_balance",
        "reactants": [{"formula": "H2", "coefficient": 1}],
        "products": [{"formula": "H2O", "coefficient": 1}],
    }
    forged["claims"][0]["predicate"] = deepcopy(bad)
    forged["evidence"][0]["predicate"] = deepcopy(bad)
    forged["evidence"][0]["check_spec"] = deepcopy(bad)
    forged["semantic_hash"] = ""
    forged["integrity_hash"] = ""
    forged = finalize_certificate_hashes_v06(forged)

    result = verify_certificate_replay_v06(forged, {})
    assert not result["valid"]
    assert any("replay outcome mismatch" in error for error in result["errors"])


def test_builtin_replay_rejects_wrong_checker_identity():
    cert = golden_certificate()
    forged = deepcopy(cert)
    forged["evidence"][0]["checker"] = "other-checker/1"
    forged["semantic_hash"] = ""
    forged["integrity_hash"] = ""
    forged = finalize_certificate_hashes_v06(forged)

    result = verify_certificate_replay_v06(forged, {})
    assert not result["valid"]
    assert any("checker differs" in error for error in result["errors"])


def test_external_formal_pass_collapses_to_unverified():
    predicate = {
        "type": "external",
        "namespace": "lean-example/v1",
        "proposition": "Example proposition",
    }
    source = {
        "spec_version": "pcs-0.6",
        "checker_version": "pcs-python-kernel/0.6.0-dev",
        "canonical_json_profile": "pcs-jcs-rfc8785-v1",
        "semantic_hash_format": "pcs-certificate-semantic-sha256-v2",
        "integrity_hash_format": "pcs-certificate-integrity-sha256-v2",
        "generated_at": "2026-09-29T00:00:00+00:00",
        "subject": "external proof replay boundary",
        "mission_scope": "test that external formal evidence is not trusted",
        "assumptions": [],
        "claims": [
            {
                "id": "C1",
                "statement": "External proposition is formally proved.",
                "kind": "formal",
                "predicate": predicate,
                "required_evidence": ["E1"],
                "assumptions": [],
                "assessment": {
                    "status": "FORMALLY_VERIFIED_UNDER_ASSUMPTIONS",
                    "reason": "all declared formal obligations independently accepted",
                },
            }
        ],
        "artifacts": [],
        "evidence": [
            {
                "id": "E1",
                "kind": "formal_proof",
                "claim_ids": ["C1"],
                "outcome": "PASS",
                "checker": "external-lean/1",
                "predicate": predicate,
                "artifact_ids": [],
                "check_spec": {
                    "type": "external_formal_proof",
                    "validator": "external-lean/1",
                    "predicate": predicate,
                },
            }
        ],
        "workflow": {"nodes": []},
        "workflow_summary": {"node_count": 0, "topological_order": []},
        "semantic_hash": "",
        "integrity_hash": "",
    }
    cert = finalize_certificate_hashes_v06(source)
    result = verify_certificate_replay_v06(cert, {})

    assert not result["valid"]
    assert result["evidence"][0]["outcome"] == "UNVERIFIED"
    assert any("replay outcome mismatch" in error for error in result["errors"])


def test_artifact_hash_is_checked_before_replay():
    predicate = {
        "type": "csv_disjoint",
        "left_artifact": "left",
        "right_artifact": "right",
        "key": "subject_id",
    }
    source = {
        "spec_version": "pcs-0.6",
        "checker_version": "pcs-python-kernel/0.6.0-dev",
        "canonical_json_profile": "pcs-jcs-rfc8785-v1",
        "semantic_hash_format": "pcs-certificate-semantic-sha256-v2",
        "integrity_hash_format": "pcs-certificate-integrity-sha256-v2",
        "generated_at": "2026-09-29T00:00:00+00:00",
        "subject": "artifact replay binding",
        "mission_scope": "test artifact hash binding",
        "assumptions": [],
        "claims": [
            {
                "id": "C1",
                "statement": "CSV keys are disjoint.",
                "kind": "computational",
                "predicate": predicate,
                "required_evidence": ["E1"],
                "assumptions": [],
                "assessment": {
                    "status": "COMPUTATIONALLY_SUPPORTED",
                    "reason": "all declared computational checks passed",
                },
            }
        ],
        "artifacts": [
            {
                "id": "left",
                "path": "artifacts/left.csv",
                "role": "left",
                "sha256": "0" * 64,
                "media_type": "text/csv",
            },
            {
                "id": "right",
                "path": "artifacts/right.csv",
                "role": "right",
                "sha256": "1" * 64,
                "media_type": "text/csv",
            },
        ],
        "evidence": [
            {
                "id": "E1",
                "kind": "computational_test",
                "claim_ids": ["C1"],
                "outcome": "PASS",
                "checker": "pcs-python-kernel/0.6.0-dev",
                "predicate": predicate,
                "artifact_ids": ["left", "right"],
                "check_spec": predicate,
            }
        ],
        "workflow": {"nodes": []},
        "workflow_summary": {"node_count": 0, "topological_order": []},
        "semantic_hash": "",
        "integrity_hash": "",
    }
    cert = finalize_certificate_hashes_v06(source)
    result = verify_certificate_replay_v06(
        cert,
        {
            "artifacts/left.csv": b"subject_id\nA\n",
            "artifacts/right.csv": b"subject_id\nB\n",
        },
    )
    assert not result["valid"]
    assert any("artifact hash mismatch" in error for error in result["errors"])
