from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from pcs.canonical_json import canonicalize_jcs_bytes
from pcs.discover_v06 import discover_project_v06
from pcs.proof_repair_v06 import PROOF_REPAIR_RESPONSE_FORMAT_V06
from pcs.proof_search_v06 import (
    PROOF_SEARCH_SESSION_FORMAT_V06,
    V06ProofSearchError,
    advance_proof_search_v06,
    load_proof_search_session_v06,
    start_proof_search_v06,
    write_proof_search_session_v06,
)
from pcs.proof_translation_v06 import PROOF_PROPOSALS_FORMAT_V06


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


def _csv_proposal(
    ids: dict[str, str],
    *,
    proposal_id: str,
    claim_id: str,
    check_id: str,
    key: str,
    confidence: float = 0.995,
) -> dict:
    return {
        "id": proposal_id,
        "confidence": confidence,
        "finding": (
            "The two cohorts appear intended to represent non-overlapping "
            "populations on their identifier."
        ),
        "artifact_ids": [
            ids["cohort_a.csv"],
            ids["cohort_b.csv"],
        ],
        "claim": {
            "id": claim_id,
            "statement": (
                "The two cohorts are disjoint on their intended identifier."
            ),
            "kind": "computational",
        },
        "check": {
            "id": check_id,
            "type": "csv_disjoint",
            "claim_ids": [claim_id],
            "left_artifact": ids["cohort_a.csv"],
            "right_artifact": ids["cohort_b.csv"],
            "key": key,
        },
    }


def _proposal_file(
    root: Path,
    discovery: dict,
    proposals: list[dict],
) -> Path:
    value = {
        "format": PROOF_PROPOSALS_FORMAT_V06,
        "inventory_commitment_sha256": discovery[
            "inventory_commitment_sha256"
        ],
        "proposer": {
            "kind": "external_model",
            "name": "search-test-model",
            "version": "1",
            "model_family": "fixture",
        },
        "proposals": proposals,
    }
    path = root / "initial-search-proposals.json"
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return path


def _start_blocked_search(
    root: Path,
    *,
    max_iterations: int = 4,
    include_good: bool = False,
) -> tuple[dict, dict, dict[str, str]]:
    _write_csv_pair(root)
    discovery = discover_project_v06(root)
    ids = _inventory_ids(discovery)
    proposals = [
        _csv_proposal(
            ids,
            proposal_id="MODEL_BAD",
            claim_id="C_MODEL_BAD",
            check_id="E_MODEL_BAD",
            key="patient_id",
        )
    ]
    if include_good:
        proposals.append(
            _csv_proposal(
                ids,
                proposal_id="MODEL_GOOD",
                claim_id="C_MODEL_GOOD",
                check_id="E_MODEL_GOOD",
                key="id",
            )
        )
    proposal_path = _proposal_file(root, discovery, proposals)
    session = start_proof_search_v06(
        root,
        proposal_files=[proposal_path],
        max_iterations=max_iterations,
    )
    return discovery, session, ids


def _repair_response(
    session: dict,
    replacement: dict,
    *,
    proposer_version: str = "2",
) -> dict:
    request = session["current_repair_request"]
    task = next(
        task
        for task in request["tasks"]
        if task["proposal_id"] == replacement["id"]
    )
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
            "name": "search-test-repair-model",
            "version": proposer_version,
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


def _root_decomposition_proposal(
    ids: dict[str, str],
    *,
    proposal_id: str = "MODEL_ROOT",
    claim_id: str = "C_ROOT",
    confidence: float = 0.995,
) -> dict:
    return {
        "id": proposal_id,
        "confidence": confidence,
        "finding": "The cohort comparison is methodologically valid.",
        "artifact_ids": [
            ids["cohort_a.csv"],
            ids["cohort_b.csv"],
        ],
        "claim": {
            "id": claim_id,
            "statement": "The cohort comparison is methodologically valid.",
            "kind": "mixed",
        },
        "decomposition": {
            "relation": "root",
            "depends_on_claim_ids": [],
        },
    }


def _claim_only_child(
    ids: dict[str, str],
    *,
    proposal_id: str,
    claim_id: str,
    parent_claim_id: str,
    confidence: float = 0.99,
) -> dict:
    return {
        "id": proposal_id,
        "confidence": confidence,
        "finding": "A narrower scientific condition may be required.",
        "artifact_ids": [
            ids["cohort_a.csv"],
            ids["cohort_b.csv"],
        ],
        "claim": {
            "id": claim_id,
            "statement": "The evaluation split is scientifically suitable.",
            "kind": "mixed",
        },
        "decomposition": {
            "parent_claim_id": parent_claim_id,
            "relation": "required_subclaim",
            "depends_on_claim_ids": [],
        },
    }


def _decomposition_response(
    session: dict,
    *,
    parent_proposal_id: str,
    children: list[dict],
    proposer_version: str = "decompose-1",
) -> dict:
    request = session["current_repair_request"]
    task = next(
        task
        for task in request["tasks"]
        if task["proposal_id"] == parent_proposal_id
        and task["allowed_action"] == "decompose_claim"
    )
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
            "name": "search-test-decomposition-model",
            "version": proposer_version,
            "model_family": "fixture",
        },
        "repairs": [
            {
                "obligation_id": task["obligation_id"],
                "proposal_id": task["proposal_id"],
                "action": task["allowed_action"],
                "child_proposals": children,
            }
        ],
    }


def test_search_starts_from_committed_repairable_graph(tmp_path: Path):
    _, session, _ = _start_blocked_search(tmp_path)

    assert session["format"] == PROOF_SEARCH_SESSION_FORMAT_V06
    assert session["status"] == "AWAITING_REPAIR"
    assert session["iteration"] == 0
    assert session["max_iterations"] == 4
    assert session["summary"]["blocking_open_obligations"] == 1
    assert session["summary"]["repairable_tasks"] == 1
    assert len(session["session_sha256"]) == 64
    assert len(session["trajectory"]["trajectory_sha256"]) == 64
    assert session["trajectory"]["steps"] == []
    assert session["authority"]["coordinator_trusted_to_set_authoritative"] is False
    assert session["authority"]["diagnostic_reward_sets_authority"] is False
    assert (
        session["authority"]["scientific_intent_reproposal_requires_human"]
        is True
    )


def test_search_cannot_self_promote_low_confidence_model_proposal(
    tmp_path: Path,
):
    _write_csv_pair(tmp_path)
    discovery = discover_project_v06(tmp_path)
    ids = _inventory_ids(discovery)
    proposal = _csv_proposal(
        ids,
        proposal_id="MODEL_LOW_CONF",
        claim_id="C_MODEL_LOW_CONF",
        check_id="E_MODEL_LOW_CONF",
        key="id",
        confidence=0.97,
    )
    proposal_path = _proposal_file(
        tmp_path,
        discovery,
        [proposal],
    )

    session = start_proof_search_v06(
        tmp_path,
        proposal_files=[proposal_path],
        minimum_model_confidence=0.98,
    )

    assert session["status"] == "BLOCKED_NO_MACHINE_REPAIR"
    assert session["summary"]["blocking_open_obligations"] == 1
    assert session["summary"]["repairable_tasks"] == 0
    candidate = next(
        candidate
        for candidate in session["current_translation"]["candidates"]
        if candidate["id"] == "MODEL_LOW_CONF"
    )
    confidence_obligation = next(
        obligation
        for obligation in candidate["obligations"]
        if obligation["kind"] == "CONFIDENCE_BELOW_SELECTION_THRESHOLD"
    )
    assert confidence_obligation["repair"]["actor"] == "human"
    assert confidence_obligation["repair"]["machine_assisted"] is False


def test_successful_search_step_recompiles_and_stops_before_authority(tmp_path: Path):
    _, session, ids = _start_blocked_search(tmp_path)
    replacement = _csv_proposal(
        ids,
        proposal_id="MODEL_BAD",
        claim_id="C_MODEL_BAD",
        check_id="E_MODEL_BAD",
        key="id",
    )
    response = _repair_response(session, replacement)

    advanced = advance_proof_search_v06(
        tmp_path,
        session,
        response,
    )

    assert advanced["iteration"] == 1
    assert advanced["status"] == "READY_FOR_HUMAN_CONFIRMATION"
    assert advanced["summary"]["blocking_open_obligations"] == 0
    assert advanced["summary"]["compiled_selected"] == 1
    assert advanced["summary"]["diagnostic_reward_total"] > 0
    assert len(advanced["trajectory"]["steps"]) == 1

    step = advanced["trajectory"]["steps"][0]
    assert step["outcome"] == "OBJECTIVE_PROGRESS"
    assert step["diagnostic_reward"] > 0
    assert step["authority"]["sets_authoritative"] is False
    assert step["authority"]["human_confirmation_still_required"] is True
    assert step["authority"]["replay_and_lean_authority_still_required"] is True

    with pytest.raises(V06ProofSearchError, match="cannot advance"):
        advance_proof_search_v06(
            tmp_path,
            advanced,
            response,
        )


def test_search_detects_semantic_cycle_even_when_proposer_metadata_changes(
    tmp_path: Path,
):
    _, session, ids = _start_blocked_search(tmp_path)
    same_bad = _csv_proposal(
        ids,
        proposal_id="MODEL_BAD",
        claim_id="C_MODEL_BAD",
        check_id="E_MODEL_BAD",
        key="patient_id",
    )
    response = _repair_response(
        session,
        same_bad,
        proposer_version="999",
    )

    advanced = advance_proof_search_v06(
        tmp_path,
        session,
        response,
    )

    assert advanced["status"] == "CYCLE_DETECTED"
    assert advanced["trajectory"]["steps"][0]["outcome"] == "CYCLE_DETECTED"
    assert advanced["trajectory"]["steps"][0]["diagnostic_reward"] < 0
    assert (
        advanced["seen_state_sha256"][0]
        == advanced["seen_state_sha256"][1]
    )


def test_search_can_repair_invalid_claim_kind_without_changing_claim_intent(
    tmp_path: Path,
):
    _write_csv_pair(tmp_path)
    discovery = discover_project_v06(tmp_path)
    ids = _inventory_ids(discovery)
    proposal = _csv_proposal(
        ids,
        proposal_id="MODEL_BAD_KIND",
        claim_id="C_MODEL_BAD_KIND",
        check_id="E_MODEL_BAD_KIND",
        key="id",
    )
    proposal["claim"]["kind"] = "not-a-supported-kind"
    proposal_path = _proposal_file(
        tmp_path,
        discovery,
        [proposal],
    )
    session = start_proof_search_v06(
        tmp_path,
        proposal_files=[proposal_path],
    )
    assert session["status"] == "AWAITING_REPAIR"
    task = session["current_repair_request"]["tasks"][0]
    assert task["kind"] == "INVALID_CLAIM_KIND"

    replacement = json.loads(json.dumps(proposal))
    replacement["claim"]["kind"] = "computational"
    response = _repair_response(session, replacement)
    advanced = advance_proof_search_v06(
        tmp_path,
        session,
        response,
    )

    assert advanced["status"] == "READY_FOR_HUMAN_CONFIRMATION"
    assert advanced["summary"]["blocking_open_obligations"] == 0


def test_search_rejects_confidence_inflation_during_other_repair(
    tmp_path: Path,
):
    _, session, ids = _start_blocked_search(tmp_path)
    replacement = _csv_proposal(
        ids,
        proposal_id="MODEL_BAD",
        claim_id="C_MODEL_BAD",
        check_id="E_MODEL_BAD",
        key="id",
        confidence=1.0,
    )
    response = _repair_response(session, replacement)

    with pytest.raises(
        V06ProofSearchError,
        match="changes model confidence",
    ):
        advance_proof_search_v06(
            tmp_path,
            session,
            response,
        )


def test_search_rejects_parent_or_dependency_change_during_repair(
    tmp_path: Path,
):
    _write_csv_pair(tmp_path)
    discovery = discover_project_v06(tmp_path)
    ids = _inventory_ids(discovery)

    root = {
        "id": "MODEL_ROOT",
        "confidence": 0.995,
        "finding": "The cohort comparison is methodologically valid.",
        "artifact_ids": [
            ids["cohort_a.csv"],
            ids["cohort_b.csv"],
        ],
        "claim": {
            "id": "C_ROOT",
            "statement": "The cohort comparison is methodologically valid.",
            "kind": "mixed",
        },
        "decomposition": {
            "relation": "root",
            "depends_on_claim_ids": [],
        },
    }
    child = _csv_proposal(
        ids,
        proposal_id="MODEL_BAD",
        claim_id="C_MODEL_BAD",
        check_id="E_MODEL_BAD",
        key="patient_id",
    )
    child["decomposition"] = {
        "parent_claim_id": "C_ROOT",
        "relation": "required_subclaim",
        "depends_on_claim_ids": [],
    }
    proposal_path = _proposal_file(
        tmp_path,
        discovery,
        [root, child],
    )
    session = start_proof_search_v06(
        tmp_path,
        proposal_files=[proposal_path],
        max_iterations=4,
    )

    replacement = _csv_proposal(
        ids,
        proposal_id="MODEL_BAD",
        claim_id="C_MODEL_BAD",
        check_id="E_MODEL_BAD",
        key="id",
    )
    replacement["decomposition"] = {
        "parent_claim_id": "C_OTHER_PARENT",
        "relation": "required_subclaim",
        "depends_on_claim_ids": [],
    }
    response = _repair_response(session, replacement)

    with pytest.raises(
        V06ProofSearchError,
        match="changes parent/dependency decomposition structure",
    ):
        advance_proof_search_v06(
            tmp_path,
            session,
            response,
        )


def test_search_rejects_checker_family_switch_during_repair(
    tmp_path: Path,
):
    _, session, ids = _start_blocked_search(tmp_path)
    replacement = _csv_proposal(
        ids,
        proposal_id="MODEL_BAD",
        claim_id="C_MODEL_BAD",
        check_id="E_MODEL_BAD",
        key="id",
    )
    replacement["check"] = {
        "id": "E_MODEL_BAD",
        "type": "unit_compatible",
        "claim_ids": ["C_MODEL_BAD"],
        "left_unit": "mg",
        "right_unit": "mg",
    }
    response = _repair_response(session, replacement)

    with pytest.raises(
        V06ProofSearchError,
        match="changes the checker family",
    ):
        advance_proof_search_v06(
            tmp_path,
            session,
            response,
        )


def test_search_rejects_repair_that_changes_scientific_intent(
    tmp_path: Path,
):
    _, session, ids = _start_blocked_search(tmp_path)
    replacement = _csv_proposal(
        ids,
        proposal_id="MODEL_BAD",
        claim_id="C_MODEL_BAD",
        check_id="E_MODEL_BAD",
        key="id",
    )
    replacement["finding"] = "The cohorts have the same number of rows."
    replacement["claim"]["statement"] = (
        "The cohorts contain the same number of records."
    )
    response = _repair_response(session, replacement)

    with pytest.raises(
        V06ProofSearchError,
        match="changes the immutable scientific finding",
    ):
        advance_proof_search_v06(
            tmp_path,
            session,
            response,
        )


def test_search_cycle_detection_ignores_claim_and_check_id_churn(
    tmp_path: Path,
):
    _, session, ids = _start_blocked_search(tmp_path)
    same_bad_new_internal_ids = _csv_proposal(
        ids,
        proposal_id="MODEL_BAD",
        claim_id="C_MODEL_BAD_RENAMED",
        check_id="E_MODEL_BAD_RENAMED",
        key="patient_id",
    )
    response = _repair_response(
        session,
        same_bad_new_internal_ids,
        proposer_version="renamed-ids",
    )

    advanced = advance_proof_search_v06(
        tmp_path,
        session,
        response,
    )

    assert advanced["status"] == "CYCLE_DETECTED"
    assert advanced["trajectory"]["steps"][0]["outcome"] == "CYCLE_DETECTED"


def test_search_hard_stops_at_iteration_budget_without_faking_progress(
    tmp_path: Path,
):
    _, session, ids = _start_blocked_search(
        tmp_path,
        max_iterations=1,
    )
    different_but_still_bad = _csv_proposal(
        ids,
        proposal_id="MODEL_BAD",
        claim_id="C_MODEL_BAD",
        check_id="E_MODEL_BAD",
        key="subject_id",
    )
    response = _repair_response(
        session,
        different_but_still_bad,
    )

    advanced = advance_proof_search_v06(
        tmp_path,
        session,
        response,
    )

    assert advanced["iteration"] == 1
    assert advanced["status"] == "MAX_ITERATIONS_REACHED"
    assert advanced["summary"]["blocking_open_obligations"] == 1
    assert advanced["trajectory"]["steps"][0]["outcome"] == (
        "NOVEL_STATE_NO_OBJECTIVE_PROGRESS"
    )


def test_repairing_one_proposal_preserves_other_active_model_proposals(
    tmp_path: Path,
):
    _, session, ids = _start_blocked_search(
        tmp_path,
        include_good=True,
    )
    assert session["summary"]["compiled_selected"] == 1

    repaired_bad = _csv_proposal(
        ids,
        proposal_id="MODEL_BAD",
        claim_id="C_MODEL_BAD",
        check_id="E_MODEL_BAD",
        key="id",
    )
    response = _repair_response(session, repaired_bad)
    advanced = advance_proof_search_v06(
        tmp_path,
        session,
        response,
    )

    model_candidates = {
        candidate["id"]: candidate
        for candidate in advanced["current_translation"]["candidates"]
        if candidate["source"]["kind"] == "external_model"
    }
    assert set(model_candidates) == {"MODEL_BAD", "MODEL_GOOD"}
    assert model_candidates["MODEL_BAD"]["selected"] is True
    assert model_candidates["MODEL_GOOD"]["selected"] is True
    assert advanced["summary"]["compiled_selected"] == 2


def test_tampered_search_session_is_fail_closed(tmp_path: Path):
    _, session, ids = _start_blocked_search(tmp_path)
    replacement = _csv_proposal(
        ids,
        proposal_id="MODEL_BAD",
        claim_id="C_MODEL_BAD",
        check_id="E_MODEL_BAD",
        key="id",
    )
    response = _repair_response(session, replacement)

    tampered = json.loads(json.dumps(session))
    tampered["max_iterations"] = 31

    with pytest.raises(V06ProofSearchError, match="session commitment"):
        advance_proof_search_v06(
            tmp_path,
            tampered,
            response,
        )


def test_rehashed_session_still_rejects_tampered_repair_request(tmp_path: Path):
    _, session, ids = _start_blocked_search(tmp_path)
    replacement = _csv_proposal(
        ids,
        proposal_id="MODEL_BAD",
        claim_id="C_MODEL_BAD",
        check_id="E_MODEL_BAD",
        key="id",
    )
    response = _repair_response(session, replacement)

    tampered = json.loads(json.dumps(session))
    tampered["current_repair_request"]["tasks"][0]["allowed_action"] = "declare_pass"
    core = {
        key: value
        for key, value in tampered.items()
        if key != "session_sha256"
    }
    tampered["session_sha256"] = hashlib.sha256(
        canonicalize_jcs_bytes(core)
    ).hexdigest()

    with pytest.raises(
        V06ProofSearchError,
        match="does not exactly match",
    ):
        advance_proof_search_v06(
            tmp_path,
            tampered,
            response,
        )


def test_search_session_round_trip_verifies_commitments(tmp_path: Path):
    _, session, _ = _start_blocked_search(tmp_path)
    path = tmp_path / "pcs-proof-search.json"

    write_proof_search_session_v06(session, path)
    loaded = load_proof_search_session_v06(path)

    assert loaded == session
    assert loaded["session_sha256"] == session["session_sha256"]

def test_search_decompose_claim_adds_child_without_rewriting_parent(
    tmp_path: Path,
):
    _write_csv_pair(tmp_path)
    discovery = discover_project_v06(tmp_path)
    ids = _inventory_ids(discovery)
    root = _root_decomposition_proposal(ids)
    proposal_path = _proposal_file(tmp_path, discovery, [root])
    session = start_proof_search_v06(
        tmp_path,
        proposal_files=[proposal_path],
        max_iterations=4,
    )

    assert session["status"] == "AWAITING_REPAIR"
    task = session["current_repair_request"]["tasks"][0]
    assert task["kind"] == "DECOMPOSITION_LEAF_NEEDS_CHECK_OR_CHILDREN"
    assert task["allowed_action"] == "decompose_claim"
    assert session["authority"]["decomposition_model_trusted"] is False
    assert (
        session["authority"]["decomposition_children_require_human_review"]
        is True
    )

    child = _csv_proposal(
        ids,
        proposal_id="MODEL_DISJOINT",
        claim_id="C_DISJOINT",
        check_id="E_DISJOINT",
        key="id",
        confidence=0.99,
    )
    child["decomposition"] = {
        "parent_claim_id": "C_ROOT",
        "relation": "required_subclaim",
        "depends_on_claim_ids": [],
    }
    response = _decomposition_response(
        session,
        parent_proposal_id="MODEL_ROOT",
        children=[child],
    )
    advanced = advance_proof_search_v06(
        tmp_path,
        session,
        response,
    )

    assert advanced["status"] == "READY_FOR_HUMAN_CONFIRMATION"
    assert advanced["summary"]["blocking_open_obligations"] == 0
    assert advanced["summary"]["compiled_selected"] == 1
    assert advanced["summary"]["decomposed_claims"] == 2
    assert advanced["search_id"] == session["search_id"]

    candidates = {
        item["id"]: item
        for item in advanced["current_translation"]["candidates"]
        if item["source"]["kind"] == "external_model"
    }
    assert set(candidates) == {"MODEL_ROOT", "MODEL_DISJOINT"}
    assert candidates["MODEL_ROOT"]["selected"] is False
    assert candidates["MODEL_ROOT"]["status"] == (
        "DECOMPOSED_CHILDREN_CLOSED_PARENT_REVIEW_REQUIRED"
    )
    assert candidates["MODEL_DISJOINT"]["selected"] is True
    assert candidates["MODEL_DISJOINT"]["formalizable"] is True

    derived = advanced["intent_anchors"]["MODEL_DISJOINT"]
    assert derived["origin"] == "decomposition"
    assert derived["parent_proposal_id"] == "MODEL_ROOT"
    assert derived["parent_claim_id"] == "C_ROOT"
    assert derived["introduced_iteration"] == 1
    assert derived["requires_human_review"] is True
    assert set(advanced["initial_intent_anchors"]) == {"MODEL_ROOT"}

    step = advanced["trajectory"]["steps"][0]
    assert step["introduced_proposal_ids"] == ["MODEL_DISJOINT"]
    assert step["repaired_proposal_ids"] == []
    assert step["outcome"] == "OBJECTIVE_PROGRESS"
    assert step["authority"]["sets_authoritative"] is False


def test_search_can_recursively_decompose_derived_child(
    tmp_path: Path,
):
    _write_csv_pair(tmp_path)
    discovery = discover_project_v06(tmp_path)
    ids = _inventory_ids(discovery)
    root = _root_decomposition_proposal(ids)
    proposal_path = _proposal_file(tmp_path, discovery, [root])
    session = start_proof_search_v06(
        tmp_path,
        proposal_files=[proposal_path],
        max_iterations=4,
    )

    middle = _claim_only_child(
        ids,
        proposal_id="MODEL_METHOD",
        claim_id="C_METHOD",
        parent_claim_id="C_ROOT",
        confidence=0.99,
    )
    first = advance_proof_search_v06(
        tmp_path,
        session,
        _decomposition_response(
            session,
            parent_proposal_id="MODEL_ROOT",
            children=[middle],
        ),
    )
    assert first["status"] == "AWAITING_REPAIR"
    assert first["summary"]["blocking_open_obligations"] >= 1
    assert (
        first["intent_anchors"]["MODEL_METHOD"]["introduced_iteration"]
        == 1
    )

    leaf = _csv_proposal(
        ids,
        proposal_id="MODEL_DISJOINT",
        claim_id="C_DISJOINT",
        check_id="E_DISJOINT",
        key="id",
        confidence=0.985,
    )
    leaf["decomposition"] = {
        "parent_claim_id": "C_METHOD",
        "relation": "required_subclaim",
        "depends_on_claim_ids": [],
    }
    second = advance_proof_search_v06(
        tmp_path,
        first,
        _decomposition_response(
            first,
            parent_proposal_id="MODEL_METHOD",
            children=[leaf],
            proposer_version="decompose-2",
        ),
    )

    assert second["status"] == "READY_FOR_HUMAN_CONFIRMATION"
    assert second["summary"]["blocking_open_obligations"] == 0
    assert second["summary"]["decomposed_claims"] == 3
    assert second["current_translation"]["claim_ir"]["summary"][
        "max_decomposition_depth"
    ] == 2
    assert second["intent_anchors"]["MODEL_DISJOINT"][
        "introduced_iteration"
    ] == 2
    assert second["trajectory"]["steps"][0][
        "introduced_proposal_ids"
    ] == ["MODEL_METHOD"]
    assert second["trajectory"]["steps"][1][
        "introduced_proposal_ids"
    ] == ["MODEL_DISJOINT"]


def test_decompose_claim_rejects_wrong_parent_binding(
    tmp_path: Path,
):
    _write_csv_pair(tmp_path)
    discovery = discover_project_v06(tmp_path)
    ids = _inventory_ids(discovery)
    root = _root_decomposition_proposal(ids)
    proposal_path = _proposal_file(tmp_path, discovery, [root])
    session = start_proof_search_v06(
        tmp_path,
        proposal_files=[proposal_path],
    )

    child = _csv_proposal(
        ids,
        proposal_id="MODEL_BAD_CHILD",
        claim_id="C_BAD_CHILD",
        check_id="E_BAD_CHILD",
        key="id",
        confidence=0.99,
    )
    child["decomposition"] = {
        "parent_claim_id": "C_NOT_THE_PARENT",
        "relation": "required_subclaim",
        "depends_on_claim_ids": [],
    }
    response = _decomposition_response(
        session,
        parent_proposal_id="MODEL_ROOT",
        children=[child],
    )

    with pytest.raises(
        V06ProofSearchError,
        match="exact target claim as parent",
    ):
        advance_proof_search_v06(
            tmp_path,
            session,
            response,
        )


def test_decompose_claim_rejects_child_confidence_inflation(
    tmp_path: Path,
):
    _write_csv_pair(tmp_path)
    discovery = discover_project_v06(tmp_path)
    ids = _inventory_ids(discovery)
    root = _root_decomposition_proposal(
        ids,
        confidence=0.99,
    )
    proposal_path = _proposal_file(tmp_path, discovery, [root])
    session = start_proof_search_v06(
        tmp_path,
        proposal_files=[proposal_path],
    )

    child = _csv_proposal(
        ids,
        proposal_id="MODEL_OVERCONFIDENT",
        claim_id="C_OVERCONFIDENT",
        check_id="E_OVERCONFIDENT",
        key="id",
        confidence=0.995,
    )
    child["decomposition"] = {
        "parent_claim_id": "C_ROOT",
        "relation": "required_subclaim",
        "depends_on_claim_ids": [],
    }

    with pytest.raises(
        V06ProofSearchError,
        match="may not exceed parent confidence",
    ):
        advance_proof_search_v06(
            tmp_path,
            session,
            _decomposition_response(
                session,
                parent_proposal_id="MODEL_ROOT",
                children=[child],
            ),
        )


def test_decompose_claim_cannot_rewrite_parent_proposal(
    tmp_path: Path,
):
    _write_csv_pair(tmp_path)
    discovery = discover_project_v06(tmp_path)
    ids = _inventory_ids(discovery)
    root = _root_decomposition_proposal(ids)
    proposal_path = _proposal_file(tmp_path, discovery, [root])
    session = start_proof_search_v06(
        tmp_path,
        proposal_files=[proposal_path],
    )
    child = _claim_only_child(
        ids,
        proposal_id="MODEL_CHILD",
        claim_id="C_CHILD",
        parent_claim_id="C_ROOT",
        confidence=0.99,
    )
    response = _decomposition_response(
        session,
        parent_proposal_id="MODEL_ROOT",
        children=[child],
    )
    response["repairs"][0]["replacement_proposal"] = {
        **root,
        "finding": "A different scientific parent.",
    }

    with pytest.raises(
        V06ProofSearchError,
        match="may not replace or rewrite the parent",
    ):
        advance_proof_search_v06(
            tmp_path,
            session,
            response,
        )

def test_search_rejects_over_budget_initial_proposal_set(
    tmp_path: Path,
):
    _write_csv_pair(tmp_path)
    discovery = discover_project_v06(tmp_path)
    ids = _inventory_ids(discovery)
    proposals = [
        {
            **_root_decomposition_proposal(
                ids,
                proposal_id=f"MODEL_ROOT_{index}",
                claim_id=f"C_ROOT_{index}",
            ),
            "finding": f"Methodological claim {index}.",
            "claim": {
                "id": f"C_ROOT_{index}",
                "statement": f"Methodological claim {index}.",
                "kind": "mixed",
            },
        }
        for index in range(129)
    ]
    proposal_path = _proposal_file(
        tmp_path,
        discovery,
        proposals,
    )

    with pytest.raises(
        V06ProofSearchError,
        match="initial proof search proposal budget is exceeded",
    ):
        start_proof_search_v06(
            tmp_path,
            proposal_files=[proposal_path],
        )


def test_search_rejects_over_budget_initial_decomposition_depth(
    tmp_path: Path,
):
    _write_csv_pair(tmp_path)
    discovery = discover_project_v06(tmp_path)
    ids = _inventory_ids(discovery)
    proposals = []
    for depth in range(10):
        proposal = {
            "id": f"MODEL_DEPTH_{depth}",
            "confidence": 0.99,
            "finding": f"Nested scientific claim {depth}.",
            "artifact_ids": [
                ids["cohort_a.csv"],
                ids["cohort_b.csv"],
            ],
            "claim": {
                "id": f"C_DEPTH_{depth}",
                "statement": f"Nested scientific claim {depth}.",
                "kind": "mixed",
            },
            "decomposition": (
                {
                    "relation": "root",
                    "depends_on_claim_ids": [],
                }
                if depth == 0
                else {
                    "parent_claim_id": f"C_DEPTH_{depth - 1}",
                    "relation": "required_subclaim",
                    "depends_on_claim_ids": [],
                }
            ),
        }
        proposals.append(proposal)
    proposal_path = _proposal_file(
        tmp_path,
        discovery,
        proposals,
    )

    with pytest.raises(
        V06ProofSearchError,
        match="initial proof search decomposition depth budget is exceeded",
    ):
        start_proof_search_v06(
            tmp_path,
            proposal_files=[proposal_path],
        )


def test_decompose_claim_rejects_more_than_eight_children(
    tmp_path: Path,
):
    _write_csv_pair(tmp_path)
    discovery = discover_project_v06(tmp_path)
    ids = _inventory_ids(discovery)
    root = _root_decomposition_proposal(ids)
    proposal_path = _proposal_file(tmp_path, discovery, [root])
    session = start_proof_search_v06(
        tmp_path,
        proposal_files=[proposal_path],
    )
    children = [
        _claim_only_child(
            ids,
            proposal_id=f"MODEL_CHILD_{index}",
            claim_id=f"C_CHILD_{index}",
            parent_claim_id="C_ROOT",
            confidence=0.99,
        )
        for index in range(9)
    ]

    with pytest.raises(
        V06ProofSearchError,
        match=r"child count must be in \[1,8\]",
    ):
        advance_proof_search_v06(
            tmp_path,
            session,
            _decomposition_response(
                session,
                parent_proposal_id="MODEL_ROOT",
                children=children,
            ),
        )


def test_decompose_claim_rejects_unknown_dependency(
    tmp_path: Path,
):
    _write_csv_pair(tmp_path)
    discovery = discover_project_v06(tmp_path)
    ids = _inventory_ids(discovery)
    root = _root_decomposition_proposal(ids)
    proposal_path = _proposal_file(tmp_path, discovery, [root])
    session = start_proof_search_v06(
        tmp_path,
        proposal_files=[proposal_path],
    )
    child = _claim_only_child(
        ids,
        proposal_id="MODEL_CHILD_DEP",
        claim_id="C_CHILD_DEP",
        parent_claim_id="C_ROOT",
        confidence=0.99,
    )
    child["decomposition"]["depends_on_claim_ids"] = ["C_UNKNOWN"]

    with pytest.raises(
        V06ProofSearchError,
        match="dependencies reference unknown claims",
    ):
        advance_proof_search_v06(
            tmp_path,
            session,
            _decomposition_response(
                session,
                parent_proposal_id="MODEL_ROOT",
                children=[child],
            ),
        )

