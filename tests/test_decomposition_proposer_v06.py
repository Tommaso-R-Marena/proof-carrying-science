from __future__ import annotations

import json
from pathlib import Path

import pytest

from pcs.check_registry_v06 import CERTIFIED_BUILTIN_CHECK_TYPES_V06
from pcs.decomposition_proposer_v06 import (
    DECOMPOSITION_PROPOSER_REQUEST_FORMAT_V06,
    DECOMPOSITION_PROPOSER_RESPONSE_FORMAT_V06,
    V06DecompositionProposerError,
    build_decomposition_proposer_request_v06,
    compile_decomposition_proposer_response_v06,
    write_decomposition_proposer_request_v06,
)
from pcs.discover_v06 import discover_project_v06
from pcs.external_validator_v06 import EXTERNAL_VALIDATOR_CHECK_TYPES_V06
from pcs.proof_search_v06 import (
    advance_proof_search_v06,
    start_proof_search_v06,
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


def _root_proposal(
    ids: dict[str, str],
    *,
    proposal_id: str = "MODEL_ROOT",
    claim_id: str = "C_ROOT",
) -> dict:
    return {
        "id": proposal_id,
        "confidence": 0.995,
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


def _child_csv_proposal(
    ids: dict[str, str],
    *,
    parent_claim_id: str = "C_ROOT",
) -> dict:
    return {
        "id": "MODEL_DISJOINT",
        "confidence": 0.99,
        "finding": "The cohorts are non-overlapping on the committed identifier.",
        "artifact_ids": [
            ids["cohort_a.csv"],
            ids["cohort_b.csv"],
        ],
        "claim": {
            "id": "C_DISJOINT",
            "statement": "The two cohorts are disjoint on id.",
            "kind": "computational",
        },
        "check": {
            "id": "E_DISJOINT",
            "type": "csv_disjoint",
            "claim_ids": ["C_DISJOINT"],
            "left_artifact": ids["cohort_a.csv"],
            "right_artifact": ids["cohort_b.csv"],
            "key": "id",
        },
        "decomposition": {
            "parent_claim_id": parent_claim_id,
            "relation": "required_subclaim",
            "depends_on_claim_ids": [],
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
            "name": "decomposition-protocol-test-model",
            "version": "1",
            "model_family": "fixture",
        },
        "proposals": proposals,
    }
    path = root / "initial-proposals.json"
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return path


def _start(
    root: Path,
    *,
    roots: int = 1,
) -> tuple[dict, dict, dict[str, str]]:
    _write_csv_pair(root)
    discovery = discover_project_v06(root)
    ids = _inventory_ids(discovery)
    proposals = [
        _root_proposal(
            ids,
            proposal_id=f"MODEL_ROOT_{index}" if roots > 1 else "MODEL_ROOT",
            claim_id=f"C_ROOT_{index}" if roots > 1 else "C_ROOT",
        )
        for index in range(roots)
    ]
    proposal_file = _proposal_file(root, discovery, proposals)
    session = start_proof_search_v06(
        root,
        proposal_files=[proposal_file],
        max_iterations=4,
    )
    return discovery, session, ids


def _response(
    request: dict,
    *,
    decision: str,
    children: list[dict] | None = None,
    reason: str | None = None,
) -> dict:
    value = {
        "format": DECOMPOSITION_PROPOSER_RESPONSE_FORMAT_V06,
        "decomposition_request_sha256": request[
            "decomposition_request_sha256"
        ],
        "search_id": request["search_id"],
        "inventory_commitment_sha256": request[
            "inventory_commitment_sha256"
        ],
        "proposer": {
            "kind": "external_model",
            "name": "decomposer",
            "version": "1",
            "model_family": "fixture",
        },
        "decision": decision,
    }
    if children is not None:
        value["children"] = children
    if reason is not None:
        value["reason"] = reason
    return value


def test_request_is_exactly_bound_and_exposes_metadata_not_bytes(
    tmp_path: Path,
):
    discovery, session, _ = _start(tmp_path)
    request = build_decomposition_proposer_request_v06(
        tmp_path,
        session,
    )

    assert request["format"] == DECOMPOSITION_PROPOSER_REQUEST_FORMAT_V06
    assert request["target"]["proposal_id"] == "MODEL_ROOT"
    assert request["target"]["claim"]["id"] == "C_ROOT"
    assert request["inventory_commitment_sha256"] == discovery[
        "inventory_commitment_sha256"
    ]
    assert len(request["decomposition_request_sha256"]) == 64
    assert request["authority"]["proposer_trusted"] is False
    assert request["authority"]["request_contains_artifact_bytes"] is False
    assert request["authority"]["model_may_set_authoritative"] is False
    assert request["authority"]["model_may_rewrite_parent"] is False
    assert len(request["target"]["candidate_snapshot_sha256"]) == 64

    assert {
        item["type"]
        for item in request["available_authorities"]["certified_checkers"]
    } == set(CERTIFIED_BUILTIN_CHECK_TYPES_V06)
    assert {
        item["type"]
        for item in request["available_authorities"][
            "signed_external_validators"
        ]
    } == set(EXTERNAL_VALIDATOR_CHECK_TYPES_V06)

    allowed_inventory_keys = {
        "artifact_id",
        "path",
        "sha256",
        "size",
        "media_type",
        "role",
    }
    assert request["project_inventory"]
    assert all(
        set(item) == allowed_inventory_keys
        for item in request["project_inventory"]
    )


def test_request_written_inside_project_does_not_change_inventory(
    tmp_path: Path,
):
    _, session, _ = _start(tmp_path)
    request = build_decomposition_proposer_request_v06(
        tmp_path,
        session,
    )
    path = tmp_path / "decomposition-request.json"
    write_decomposition_proposer_request_v06(
        request,
        path,
    )

    rebuilt = build_decomposition_proposer_request_v06(
        tmp_path,
        session,
    )
    assert rebuilt == request


def test_multiple_decomposition_targets_require_explicit_selection(
    tmp_path: Path,
):
    _, session, _ = _start(tmp_path, roots=2)

    with pytest.raises(
        V06DecompositionProposerError,
        match="requires exactly one target",
    ):
        build_decomposition_proposer_request_v06(
            tmp_path,
            session,
        )

    request = build_decomposition_proposer_request_v06(
        tmp_path,
        session,
        proposal_id="MODEL_ROOT_1",
    )
    assert request["target"]["proposal_id"] == "MODEL_ROOT_1"
    assert request["target"]["claim"]["id"] == "C_ROOT_1"


def test_compiled_decomposition_reenters_real_proof_search(
    tmp_path: Path,
):
    _, session, ids = _start(tmp_path)
    request = build_decomposition_proposer_request_v06(
        tmp_path,
        session,
    )
    proposer_response = _response(
        request,
        decision="decompose",
        children=[_child_csv_proposal(ids)],
    )

    compilation = compile_decomposition_proposer_response_v06(
        tmp_path,
        session,
        request,
        proposer_response,
    )
    assert compilation["status"] == "COMPILED_REPAIR_RESPONSE"
    assert compilation["authority"]["sets_authoritative"] is False
    assert compilation["authority"]["changes_search_state"] is False
    assert compilation["introduced_proposal_ids"] == ["MODEL_DISJOINT"]

    advanced = advance_proof_search_v06(
        tmp_path,
        session,
        compilation["repair_response"],
    )
    assert advanced["status"] == "READY_FOR_HUMAN_CONFIRMATION"
    assert advanced["summary"]["blocking_open_obligations"] == 0
    assert advanced["summary"]["compiled_selected"] == 1
    assert advanced["intent_anchors"]["MODEL_DISJOINT"][
        "origin"
    ] == "decomposition"


def test_abstention_is_valid_and_changes_no_search_state(
    tmp_path: Path,
):
    _, session, _ = _start(tmp_path)
    request = build_decomposition_proposer_request_v06(
        tmp_path,
        session,
    )
    compilation = compile_decomposition_proposer_response_v06(
        tmp_path,
        session,
        request,
        _response(
            request,
            decision="abstain",
            reason="The available metadata is insufficient to justify a narrower claim.",
        ),
    )

    assert compilation["status"] == "ABSTAINED_NO_REPAIR"
    assert compilation["repair_response"] is None
    assert compilation["authority"]["sets_authoritative"] is False
    assert compilation["authority"]["changes_search_state"] is False


def test_tampered_request_is_rejected_even_if_rehashed_field_is_unchanged(
    tmp_path: Path,
):
    _, session, ids = _start(tmp_path)
    request = build_decomposition_proposer_request_v06(
        tmp_path,
        session,
    )
    tampered = json.loads(json.dumps(request))
    tampered["target"]["claim"]["statement"] = "A different parent claim."

    with pytest.raises(
        V06DecompositionProposerError,
        match="does not exactly match",
    ):
        compile_decomposition_proposer_response_v06(
            tmp_path,
            session,
            tampered,
            _response(
                request,
                decision="decompose",
                children=[_child_csv_proposal(ids)],
            ),
        )


def test_project_inventory_change_invalidates_request(
    tmp_path: Path,
):
    _, session, _ = _start(tmp_path)
    request = build_decomposition_proposer_request_v06(
        tmp_path,
        session,
    )
    (tmp_path / "new_scientific_data.csv").write_text(
        "id,value\nZ,9\n",
        encoding="utf-8",
    )

    with pytest.raises(
        V06DecompositionProposerError,
        match="project inventory changed",
    ):
        compile_decomposition_proposer_response_v06(
            tmp_path,
            session,
            request,
            _response(
                request,
                decision="abstain",
                reason="No decomposition attempted.",
            ),
        )


def test_wrong_parent_child_fails_deterministic_repair_compiler(
    tmp_path: Path,
):
    _, session, ids = _start(tmp_path)
    request = build_decomposition_proposer_request_v06(
        tmp_path,
        session,
    )
    child = _child_csv_proposal(
        ids,
        parent_claim_id="C_WRONG_PARENT",
    )

    with pytest.raises(
        V06DecompositionProposerError,
        match="failed deterministic repair compilation",
    ):
        compile_decomposition_proposer_response_v06(
            tmp_path,
            session,
            request,
            _response(
                request,
                decision="decompose",
                children=[child],
            ),
        )


def test_response_binding_to_search_and_inventory_is_fail_closed(
    tmp_path: Path,
):
    _, session, ids = _start(tmp_path)
    request = build_decomposition_proposer_request_v06(
        tmp_path,
        session,
    )
    response = _response(
        request,
        decision="decompose",
        children=[_child_csv_proposal(ids)],
    )
    response["search_id"] = "different-search"

    with pytest.raises(
        V06DecompositionProposerError,
        match="different search",
    ):
        compile_decomposition_proposer_response_v06(
            tmp_path,
            session,
            request,
            response,
        )

def test_response_rejects_unsupported_side_channel_fields(
    tmp_path: Path,
):
    _, session, ids = _start(tmp_path)
    request = build_decomposition_proposer_request_v06(
        tmp_path,
        session,
    )
    response = _response(
        request,
        decision="decompose",
        children=[_child_csv_proposal(ids)],
    )
    response["authoritative"] = True

    with pytest.raises(
        V06DecompositionProposerError,
        match="unsupported fields",
    ):
        compile_decomposition_proposer_response_v06(
            tmp_path,
            session,
            request,
            response,
        )


def test_response_requires_explicit_external_model_proposer_kind(
    tmp_path: Path,
):
    _, session, _ = _start(tmp_path)
    request = build_decomposition_proposer_request_v06(
        tmp_path,
        session,
    )
    response = _response(
        request,
        decision="abstain",
        reason="Insufficient evidence.",
    )
    response["proposer"]["kind"] = "trusted_oracle"

    with pytest.raises(
        V06DecompositionProposerError,
        match="must be 'external_model'",
    ):
        compile_decomposition_proposer_response_v06(
            tmp_path,
            session,
            request,
            response,
        )

