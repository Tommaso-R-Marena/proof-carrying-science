from __future__ import annotations

import json
from pathlib import Path

import pytest

from pcs.artifact_inspection_v06 import (
    ARTIFACT_INSPECTION_QUERY_FORMAT_V06,
    V06ArtifactInspectionError,
    inspect_artifacts_v06,
    verify_artifact_inspection_result_v06,
    write_artifact_inspection_result_v06,
)
from pcs.decomposition_proposer_v06 import (
    DECOMPOSITION_PROPOSER_RESPONSE_FORMAT_V06,
    V06DecompositionProposerError,
    build_decomposition_proposer_request_v06,
    compile_decomposition_proposer_response_v06,
)
from pcs.discover_v06 import discover_project_v06
from pcs.proof_search_v06 import (
    advance_proof_search_v06,
    start_proof_search_v06,
)
from pcs.proof_translation_v06 import PROOF_PROPOSALS_FORMAT_V06


def _write_project(root: Path) -> None:
    (root / "cohort_a.csv").write_text(
        "id,value\nA,1\nB,2\n",
        encoding="utf-8",
    )
    (root / "cohort_b.csv").write_text(
        "id,value\nC,3\nD,4\n",
        encoding="utf-8",
    )
    (root / "model.json").write_text(
        json.dumps(
            {
                "model": "one-compartment",
                "parameters": {
                    "clearance": 2.5,
                    "volume": 10.0,
                },
                "labels": ["A", "B"],
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    (root / "notes.txt").write_text(
        "Study notes\n"
        "Cohorts were assembled independently.\n"
        "Population labels require scientific review.\n",
        encoding="utf-8",
    )
    (root / "unrelated.txt").write_text(
        "This artifact is in the project but not bound to the target claim.\n",
        encoding="utf-8",
    )


def _inventory_ids(discovery: dict) -> dict[str, str]:
    return {
        item["path"]: item["artifact_id"]
        for item in discovery["inventory"]
    }


def _proposal_file(
    root: Path,
    discovery: dict,
    ids: dict[str, str],
) -> Path:
    value = {
        "format": PROOF_PROPOSALS_FORMAT_V06,
        "inventory_commitment_sha256": discovery[
            "inventory_commitment_sha256"
        ],
        "proposer": {
            "kind": "external_model",
            "name": "inspection-test-model",
            "version": "1",
            "model_family": "fixture",
        },
        "proposals": [
            {
                "id": "MODEL_ROOT",
                "confidence": 0.995,
                "finding": "The cohort comparison is methodologically valid.",
                "artifact_ids": [
                    ids["cohort_a.csv"],
                    ids["cohort_b.csv"],
                    ids["model.json"],
                    ids["notes.txt"],
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
        ],
    }
    path = root / "initial-proposals.json"
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return path


def _start(root: Path) -> tuple[dict, dict, dict, dict[str, str]]:
    _write_project(root)
    discovery = discover_project_v06(root)
    ids = _inventory_ids(discovery)
    proposal_file = _proposal_file(root, discovery, ids)
    session = start_proof_search_v06(
        root,
        proposal_files=[proposal_file],
        max_iterations=4,
    )
    request = build_decomposition_proposer_request_v06(
        root,
        session,
    )
    return discovery, session, request, ids


def _query(
    session: dict,
    request: dict,
    operations: list[dict],
) -> dict:
    return {
        "format": ARTIFACT_INSPECTION_QUERY_FORMAT_V06,
        "decomposition_request_sha256": request[
            "decomposition_request_sha256"
        ],
        "search_id": session["search_id"],
        "inventory_commitment_sha256": session[
            "inventory_commitment_sha256"
        ],
        "operations": operations,
    }


def _child_csv(ids: dict[str, str]) -> dict:
    return {
        "id": "MODEL_DISJOINT",
        "confidence": 0.99,
        "finding": "The cohorts are disjoint on id.",
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
            "parent_claim_id": "C_ROOT",
            "relation": "required_subclaim",
            "depends_on_claim_ids": [],
        },
    }


def _decomposition_response(
    session: dict,
    request: dict,
    ids: dict[str, str],
    *,
    inspection_sha256: str | None,
) -> dict:
    value = {
        "format": DECOMPOSITION_PROPOSER_RESPONSE_FORMAT_V06,
        "decomposition_request_sha256": request[
            "decomposition_request_sha256"
        ],
        "search_id": session["search_id"],
        "inventory_commitment_sha256": session[
            "inventory_commitment_sha256"
        ],
        "proposer": {
            "kind": "external_model",
            "name": "inspection-aware-decomposer",
            "version": "1",
            "model_family": "fixture",
        },
        "decision": "decompose",
        "children": [_child_csv(ids)],
    }
    if inspection_sha256 is not None:
        value["inspection_result_sha256"] = inspection_sha256
    return value


def test_decomposition_request_advertises_bounded_inspection_contract(
    tmp_path: Path,
):
    _, _, request, _ = _start(tmp_path)
    contract = request["inspection_contract"]

    assert contract["query_format"] == ARTIFACT_INSPECTION_QUERY_FORMAT_V06
    assert set(contract["allowed_views"]) == {
        "csv_header",
        "json_fields",
        "text_lines",
    }
    assert contract["bounds"]["max_operations"] == 8
    assert contract["authority"]["sets_authoritative"] is False
    assert contract["authority"]["filesystem_paths_supplied_by_model"] is False
    assert contract["authority"]["only_target_bound_artifact_ids_allowed"] is True


def test_bounded_views_are_sha_bound_and_typed(tmp_path: Path):
    _, session, request, ids = _start(tmp_path)
    query = _query(
        session,
        request,
        [
            {
                "id": "csv",
                "artifact_id": ids["cohort_a.csv"],
                "view": "csv_header",
            },
            {
                "id": "json",
                "artifact_id": ids["model.json"],
                "view": "json_fields",
                "fields": [
                    "/model",
                    "/parameters/clearance",
                    "/missing",
                ],
            },
            {
                "id": "text",
                "artifact_id": ids["notes.txt"],
                "view": "text_lines",
                "start_line": 2,
                "max_lines": 2,
            },
        ],
    )

    result = inspect_artifacts_v06(
        tmp_path,
        session,
        request,
        query,
    )
    assert result["authority"]["sets_authoritative"] is False
    assert result["authority"]["changes_search_state"] is False
    assert len(result["inspection_result_sha256"]) == 64

    by_id = {
        item["operation_id"]: item
        for item in result["observations"]
    }
    assert by_id["csv"]["observation"]["columns"] == ["id", "value"]
    assert by_id["csv"]["artifact_sha256"]
    assert len(by_id["csv"]["observation_sha256"]) == 64

    fields = {
        item["pointer"]: item
        for item in by_id["json"]["observation"]["fields"]
    }
    assert fields["/model"]["value"] == "one-compartment"
    assert fields["/parameters/clearance"]["value"] == 2.5
    assert fields["/missing"]["found"] is False

    lines = by_id["text"]["observation"]["returned_lines"]
    assert [item["line"] for item in lines] == [2, 3]
    assert "assembled independently" in lines[0]["text"]


def test_query_cannot_name_filesystem_path_or_unbound_artifact(
    tmp_path: Path,
):
    _, session, request, ids = _start(tmp_path)
    path_query = _query(
        session,
        request,
        [
            {
                "id": "path-attack",
                "artifact_id": ids["cohort_a.csv"],
                "view": "csv_header",
                "path": "../../etc/passwd",
            }
        ],
    )
    with pytest.raises(
        V06ArtifactInspectionError,
        match="unsupported fields",
    ):
        inspect_artifacts_v06(
            tmp_path,
            session,
            request,
            path_query,
        )

    unbound_query = _query(
        session,
        request,
        [
            {
                "id": "unbound",
                "artifact_id": ids["unrelated.txt"],
                "view": "text_lines",
                "start_line": 1,
                "max_lines": 1,
            }
        ],
    )
    with pytest.raises(
        V06ArtifactInspectionError,
        match="outside the unresolved claim's bound artifacts",
    ):
        inspect_artifacts_v06(
            tmp_path,
            session,
            request,
            unbound_query,
        )


def test_inspection_query_and_result_files_do_not_change_inventory(
    tmp_path: Path,
):
    _, session, request, ids = _start(tmp_path)
    query = _query(
        session,
        request,
        [
            {
                "id": "csv",
                "artifact_id": ids["cohort_a.csv"],
                "view": "csv_header",
            }
        ],
    )
    query_path = tmp_path / "inspection-query.json"
    query_path.write_text(
        json.dumps(query, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    result = inspect_artifacts_v06(
        tmp_path,
        session,
        request,
        query,
    )
    write_artifact_inspection_result_v06(
        result,
        tmp_path / "inspection-result.json",
    )

    rebuilt = build_decomposition_proposer_request_v06(
        tmp_path,
        session,
    )
    assert rebuilt == request
    verify_artifact_inspection_result_v06(
        tmp_path,
        session,
        request,
        result,
    )


def test_artifact_mutation_invalidates_inspection(
    tmp_path: Path,
):
    _, session, request, ids = _start(tmp_path)
    query = _query(
        session,
        request,
        [
            {
                "id": "csv",
                "artifact_id": ids["cohort_a.csv"],
                "view": "csv_header",
            }
        ],
    )
    (tmp_path / "cohort_a.csv").write_text(
        "id,value\nMUTATED,9\n",
        encoding="utf-8",
    )

    with pytest.raises(
        V06ArtifactInspectionError,
        match="project inventory changed",
    ):
        inspect_artifacts_v06(
            tmp_path,
            session,
            request,
            query,
        )


def test_tampered_inspection_result_is_rejected(
    tmp_path: Path,
):
    _, session, request, ids = _start(tmp_path)
    result = inspect_artifacts_v06(
        tmp_path,
        session,
        request,
        _query(
            session,
            request,
            [
                {
                    "id": "csv",
                    "artifact_id": ids["cohort_a.csv"],
                    "view": "csv_header",
                }
            ],
        ),
    )
    tampered = json.loads(json.dumps(result))
    tampered["observations"][0]["observation"]["columns"] = ["fake"]

    with pytest.raises(
        V06ArtifactInspectionError,
        match="does not exactly match",
    ):
        verify_artifact_inspection_result_v06(
            tmp_path,
            session,
            request,
            tampered,
        )


def test_decomposition_can_bind_exact_recomputed_inspection_result(
    tmp_path: Path,
):
    _, session, request, ids = _start(tmp_path)
    inspection = inspect_artifacts_v06(
        tmp_path,
        session,
        request,
        _query(
            session,
            request,
            [
                {
                    "id": "left-header",
                    "artifact_id": ids["cohort_a.csv"],
                    "view": "csv_header",
                },
                {
                    "id": "right-header",
                    "artifact_id": ids["cohort_b.csv"],
                    "view": "csv_header",
                },
            ],
        ),
    )
    response = _decomposition_response(
        session,
        request,
        ids,
        inspection_sha256=inspection["inspection_result_sha256"],
    )
    compilation = compile_decomposition_proposer_response_v06(
        tmp_path,
        session,
        request,
        response,
        inspection_result=inspection,
    )
    assert compilation["inspection_result_sha256"] == inspection[
        "inspection_result_sha256"
    ]
    assert compilation["authority"]["sets_authoritative"] is False

    advanced = advance_proof_search_v06(
        tmp_path,
        session,
        compilation["repair_response"],
    )
    assert advanced["status"] == "READY_FOR_HUMAN_CONFIRMATION"
    assert advanced["summary"]["compiled_selected"] == 1


def test_decomposition_rejects_missing_wrong_or_unbound_inspection(
    tmp_path: Path,
):
    _, session, request, ids = _start(tmp_path)
    inspection = inspect_artifacts_v06(
        tmp_path,
        session,
        request,
        _query(
            session,
            request,
            [
                {
                    "id": "left-header",
                    "artifact_id": ids["cohort_a.csv"],
                    "view": "csv_header",
                }
            ],
        ),
    )
    response = _decomposition_response(
        session,
        request,
        ids,
        inspection_sha256=inspection["inspection_result_sha256"],
    )

    with pytest.raises(
        V06DecompositionProposerError,
        match="binds an inspection result but none was supplied",
    ):
        compile_decomposition_proposer_response_v06(
            tmp_path,
            session,
            request,
            response,
        )

    wrong = json.loads(json.dumps(response))
    wrong["inspection_result_sha256"] = "0" * 64
    with pytest.raises(
        V06DecompositionProposerError,
        match="binds a different artifact inspection result",
    ):
        compile_decomposition_proposer_response_v06(
            tmp_path,
            session,
            request,
            wrong,
            inspection_result=inspection,
        )

    unbound = _decomposition_response(
        session,
        request,
        ids,
        inspection_sha256=None,
    )
    with pytest.raises(
        V06DecompositionProposerError,
        match="supplied but the decomposition response does not bind it",
    ):
        compile_decomposition_proposer_response_v06(
            tmp_path,
            session,
            request,
            unbound,
            inspection_result=inspection,
        )


def test_query_operation_count_and_line_bounds_are_fail_closed(
    tmp_path: Path,
):
    _, session, request, ids = _start(tmp_path)
    too_many = _query(
        session,
        request,
        [
            {
                "id": f"op-{index}",
                "artifact_id": ids["cohort_a.csv"],
                "view": "csv_header",
            }
            for index in range(9)
        ],
    )
    with pytest.raises(
        V06ArtifactInspectionError,
        match="requires 1..8 operations",
    ):
        inspect_artifacts_v06(
            tmp_path,
            session,
            request,
            too_many,
        )

    too_many_lines = _query(
        session,
        request,
        [
            {
                "id": "text",
                "artifact_id": ids["notes.txt"],
                "view": "text_lines",
                "start_line": 1,
                "max_lines": 41,
            }
        ],
    )
    with pytest.raises(
        V06ArtifactInspectionError,
        match=r"max_lines must be in \[1,40\]",
    ):
        inspect_artifacts_v06(
            tmp_path,
            session,
            request,
            too_many_lines,
        )
