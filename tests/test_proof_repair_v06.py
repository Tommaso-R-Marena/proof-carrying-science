from __future__ import annotations

import json
from pathlib import Path

import pytest

from pcs.discover_v06 import discover_project_v06
from pcs.proof_repair_v06 import (
    PROOF_REPAIR_REQUEST_FORMAT_V06,
    PROOF_REPAIR_RESPONSE_FORMAT_V06,
    V06ProofRepairError,
    build_proof_repair_request_v06,
    compile_proof_repair_response_v06,
    write_compiled_repair_proposals_v06,
)
from pcs.proof_translation_v06 import (
    PROOF_PROPOSALS_FORMAT_V06,
    translate_project_v06,
)


def _write_csv_pair(root: Path) -> None:
    (root / "cohort_a.csv").write_text(
        "id,value\nA,1\nB,2\n",
        encoding="utf-8",
    )
    (root / "cohort_b.csv").write_text(
        "id,value\nC,3\nD,4\n",
        encoding="utf-8",
    )


def _inventory_ids(discovery: dict) -> dict[str, str]:
    return {
        item["path"]: item["artifact_id"]
        for item in discovery["inventory"]
    }


def _bad_model_proposal(root: Path, discovery: dict) -> Path:
    ids = _inventory_ids(discovery)
    value = {
        "format": PROOF_PROPOSALS_FORMAT_V06,
        "inventory_commitment_sha256": discovery[
            "inventory_commitment_sha256"
        ],
        "proposer": {
            "kind": "external_model",
            "name": "repair-test-model",
            "version": "1",
            "model_family": "fixture",
        },
        "proposals": [
            {
                "id": "MODEL_DISJOINT",
                "confidence": 0.995,
                "finding": "The two cohorts should be disjoint.",
                "artifact_ids": [
                    ids["cohort_a.csv"],
                    ids["cohort_b.csv"],
                ],
                "claim": {
                    "id": "C_MODEL_DISJOINT",
                    "statement": "The cohorts are disjoint on their identifier.",
                    "kind": "computational",
                },
                "check": {
                    "id": "E_MODEL_DISJOINT",
                    "type": "csv_disjoint",
                    "claim_ids": ["C_MODEL_DISJOINT"],
                    "left_artifact": ids["cohort_a.csv"],
                    "right_artifact": ids["cohort_b.csv"],
                    "key": "patient_id",
                },
            }
        ],
    }
    path = root / "bad-model-proposals.json"
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return path


def _replacement_proposal(discovery: dict) -> dict:
    ids = _inventory_ids(discovery)
    return {
        "id": "MODEL_DISJOINT",
        "confidence": 0.995,
        "finding": "The two cohorts are disjoint on the shared id column.",
        "artifact_ids": [
            ids["cohort_a.csv"],
            ids["cohort_b.csv"],
        ],
        "claim": {
            "id": "C_MODEL_DISJOINT",
            "statement": "The cohorts are disjoint on their id column.",
            "kind": "computational",
        },
        "check": {
            "id": "E_MODEL_DISJOINT",
            "type": "csv_disjoint",
            "claim_ids": ["C_MODEL_DISJOINT"],
            "left_artifact": ids["cohort_a.csv"],
            "right_artifact": ids["cohort_b.csv"],
            "key": "id",
        },
    }


def _repair_response(request: dict, replacement: dict) -> dict:
    task = request["tasks"][0]
    return {
        "format": PROOF_REPAIR_RESPONSE_FORMAT_V06,
        "repair_request_sha256": request["repair_request_sha256"],
        "obligation_graph_sha256": request[
            "obligation_graph_sha256"
        ],
        "inventory_commitment_sha256": request[
            "inventory_commitment_sha256"
        ],
        "proposer": {
            "kind": "external_model",
            "name": "repair-test-model",
            "version": "2",
            "model_family": "fixture",
        },
        "repairs": [
            {
                "obligation_id": task["obligation_id"],
                "proposal_id": task["proposal_id"],
                "action": task["allowed_action"],
                "replacement_proposal": replacement,
            }
        ],
    }


def _blocked_translation(tmp_path: Path) -> tuple[dict, dict]:
    _write_csv_pair(tmp_path)
    discovery = discover_project_v06(tmp_path)
    proposal = _bad_model_proposal(tmp_path, discovery)
    translation = translate_project_v06(
        tmp_path,
        proposal_files=[proposal],
    )
    return discovery, translation


def test_repair_request_is_graph_bound_and_machine_scoped(tmp_path: Path):
    _, translation = _blocked_translation(tmp_path)

    first = build_proof_repair_request_v06(translation)
    second = build_proof_repair_request_v06(translation)

    assert first["format"] == PROOF_REPAIR_REQUEST_FORMAT_V06
    assert first == second
    assert len(first["repair_request_sha256"]) == 64
    assert first["summary"]["repairable_tasks"] == 1
    task = first["tasks"][0]
    assert task["proposal_id"] == "MODEL_DISJOINT"
    assert task["kind"] == "GROUND_PREDICATE_IN_PROJECT_BYTES"
    assert task["allowed_action"] == "revise_predicate_from_project_bytes"
    assert task["authority"]["can_set_authoritative"] is False
    assert task["authority"]["must_reenter_deterministic_compiler"] is True
    assert all(
        task["kind"] != "HUMAN_CONFIRMATION_REQUIRED"
        for task in first["tasks"]
    )


def test_valid_repair_compiles_to_ordinary_untrusted_proposal_and_reenters_translation(
    tmp_path: Path,
):
    discovery, translation = _blocked_translation(tmp_path)
    request = build_proof_repair_request_v06(translation)
    response = _repair_response(
        request,
        _replacement_proposal(discovery),
    )

    compiled = compile_proof_repair_response_v06(
        translation,
        request,
        response,
    )
    assert compiled["format"] == PROOF_PROPOSALS_FORMAT_V06
    assert len(compiled["compiled_repair_sha256"]) == 64
    assert len(compiled["proposals"]) == 1
    assert compiled["repair_provenance"]["repair_request_sha256"] == (
        request["repair_request_sha256"]
    )

    compiled_path = tmp_path / "pcs-proof-repaired-proposals.json"
    write_compiled_repair_proposals_v06(
        compiled,
        compiled_path,
    )
    repaired = translate_project_v06(
        tmp_path,
        proposal_files=[compiled_path],
    )
    model = next(
        candidate
        for candidate in repaired["candidates"]
        if candidate["source"]["kind"] == "external_model"
    )
    assert model["selected"] is True
    assert model["status"] == "COMPILED_LEAN_BUILTIN"
    assert model["grounding"]["status"] == "GROUNDED"
    assert model["check"]["key"] == "id"
    assert any(
        obligation["kind"] == "HUMAN_CONFIRMATION_REQUIRED"
        for obligation in model["obligations"]
    )


def test_repair_response_cannot_target_stale_graph(tmp_path: Path):
    discovery, translation = _blocked_translation(tmp_path)
    request = build_proof_repair_request_v06(translation)
    response = _repair_response(
        request,
        _replacement_proposal(discovery),
    )
    response["obligation_graph_sha256"] = "0" * 64

    with pytest.raises(
        V06ProofRepairError,
        match="different proof-obligation graph",
    ):
        compile_proof_repair_response_v06(
            translation,
            request,
            response,
        )


def test_repair_response_rejects_authority_smuggling(tmp_path: Path):
    discovery, translation = _blocked_translation(tmp_path)
    request = build_proof_repair_request_v06(translation)
    replacement = _replacement_proposal(discovery)
    replacement["claim"]["authoritative"] = True
    response = _repair_response(request, replacement)

    with pytest.raises(
        V06ProofRepairError,
        match="replacement claim contains forbidden fields",
    ):
        compile_proof_repair_response_v06(
            translation,
            request,
            response,
        )


def test_tampered_repair_request_is_fail_closed(tmp_path: Path):
    _, translation = _blocked_translation(tmp_path)
    request = build_proof_repair_request_v06(translation)
    request["tasks"][0]["allowed_action"] = "declare_pass"

    with pytest.raises(
        V06ProofRepairError,
        match="request commitment",
    ):
        compile_proof_repair_response_v06(
            translation,
            request,
            {
                "format": PROOF_REPAIR_RESPONSE_FORMAT_V06,
                "repair_request_sha256": request["repair_request_sha256"],
                "obligation_graph_sha256": request[
                    "obligation_graph_sha256"
                ],
                "inventory_commitment_sha256": request[
                    "inventory_commitment_sha256"
                ],
                "proposer": {"name": "attacker"},
                "repairs": [],
            },
        )
