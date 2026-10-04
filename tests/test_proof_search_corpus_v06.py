from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from pcs.artifact_inspection_v06 import (
    ARTIFACT_INSPECTION_QUERY_FORMAT_V06,
    inspect_artifacts_v06,
)
from pcs.decomposition_proposer_v06 import (
    DECOMPOSITION_PROPOSER_RESPONSE_FORMAT_V06,
    build_decomposition_proposer_request_v06,
    compile_decomposition_proposer_response_v06,
)
from pcs.discover_v06 import discover_project_v06
from pcs.proof_repair_v06 import PROOF_REPAIR_RESPONSE_FORMAT_V06
from pcs.proof_search_corpus_v06 import (
    PROOF_SEARCH_CORPUS_FORMAT_V06,
    PROOF_SEARCH_DATA_USE_POLICY_FORMAT_V06,
    PROOF_SEARCH_RECORD_FORMAT_V06,
    V06ProofSearchCorpusError,
    build_proof_search_corpus_v06,
    build_proof_search_record_v06,
    validate_data_use_policy_v06,
    write_proof_search_corpus_v06,
    write_proof_search_record_v06,
)
from pcs.proof_search_v06 import (
    advance_proof_search_v06,
    start_proof_search_v06,
    write_proof_search_session_v06,
)
from pcs.proof_translation_v06 import PROOF_PROPOSALS_FORMAT_V06


ROOT = Path(__file__).resolve().parents[1]


def _write_csv_pair(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
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


def _proposal_file(
    root: Path,
    discovery: dict,
    proposals: list[dict],
    *,
    name: str = "proposals.json",
) -> Path:
    value = {
        "format": PROOF_PROPOSALS_FORMAT_V06,
        "inventory_commitment_sha256": discovery[
            "inventory_commitment_sha256"
        ],
        "proposer": {
            "kind": "external_model",
            "name": "corpus-test-model",
            "version": "1",
            "model_family": "fixture",
        },
        "proposals": proposals,
    }
    path = root / name
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return path


def _csv_proposal(
    ids: dict[str, str],
    *,
    key: str,
    proposal_id: str = "MODEL_DISJOINT",
    claim_id: str = "C_DISJOINT",
) -> dict:
    return {
        "id": proposal_id,
        "confidence": 0.995,
        "finding": "The two cohorts are disjoint on their intended identifier.",
        "artifact_ids": [
            ids["cohort_a.csv"],
            ids["cohort_b.csv"],
        ],
        "claim": {
            "id": claim_id,
            "statement": "The two cohorts are disjoint on their intended identifier.",
            "kind": "computational",
        },
        "check": {
            "id": f"E_{claim_id}",
            "type": "csv_disjoint",
            "claim_ids": [claim_id],
            "left_artifact": ids["cohort_a.csv"],
            "right_artifact": ids["cohort_b.csv"],
            "key": key,
        },
    }


def _replacement_session(root: Path) -> dict:
    _write_csv_pair(root)
    discovery = discover_project_v06(root)
    ids = _inventory_ids(discovery)
    initial = _csv_proposal(ids, key="patient_id")
    proposal_path = _proposal_file(root, discovery, [initial])
    session = start_proof_search_v06(
        root,
        proposal_files=[proposal_path],
        max_iterations=4,
    )
    task = session["current_repair_request"]["tasks"][0]
    repaired = _csv_proposal(ids, key="id")
    response = {
        "format": PROOF_REPAIR_RESPONSE_FORMAT_V06,
        "repair_request_sha256": session["current_repair_request"][
            "repair_request_sha256"
        ],
        "obligation_graph_sha256": session["current_repair_request"][
            "obligation_graph_sha256"
        ],
        "inventory_commitment_sha256": session["current_repair_request"][
            "inventory_commitment_sha256"
        ],
        "proposer": {
            "kind": "external_model",
            "name": "repair-model",
            "version": "1",
            "model_family": "fixture",
        },
        "repairs": [
            {
                "obligation_id": task["obligation_id"],
                "proposal_id": task["proposal_id"],
                "action": task["allowed_action"],
                "replacement_proposal": repaired,
            }
        ],
    }
    return advance_proof_search_v06(root, session, response)


def _root_proposal(ids: dict[str, str]) -> dict:
    return {
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


def _decomposition_run(
    root: Path,
) -> tuple[dict, list[dict], dict]:
    _write_csv_pair(root)
    discovery = discover_project_v06(root)
    ids = _inventory_ids(discovery)
    proposal_path = _proposal_file(
        root,
        discovery,
        [_root_proposal(ids)],
    )
    session = start_proof_search_v06(
        root,
        proposal_files=[proposal_path],
        max_iterations=4,
    )
    request = build_decomposition_proposer_request_v06(
        root,
        session,
    )
    query = {
        "format": ARTIFACT_INSPECTION_QUERY_FORMAT_V06,
        "decomposition_request_sha256": request[
            "decomposition_request_sha256"
        ],
        "search_id": session["search_id"],
        "inventory_commitment_sha256": session[
            "inventory_commitment_sha256"
        ],
        "operations": [
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
    }
    inspection = inspect_artifacts_v06(
        root,
        session,
        request,
        query,
    )
    child = _csv_proposal(
        ids,
        key="id",
        proposal_id="MODEL_CHILD",
        claim_id="C_CHILD",
    )
    child["decomposition"] = {
        "parent_claim_id": "C_ROOT",
        "relation": "required_subclaim",
        "depends_on_claim_ids": [],
    }
    response = {
        "format": DECOMPOSITION_PROPOSER_RESPONSE_FORMAT_V06,
        "decomposition_request_sha256": request[
            "decomposition_request_sha256"
        ],
        "search_id": session["search_id"],
        "inventory_commitment_sha256": session[
            "inventory_commitment_sha256"
        ],
        "inspection_result_sha256": inspection[
            "inspection_result_sha256"
        ],
        "proposer": {
            "kind": "external_model",
            "name": "decomposition-model",
            "version": "1",
            "model_family": "fixture",
        },
        "decision": "decompose",
        "children": [child],
    }
    compilation = compile_decomposition_proposer_response_v06(
        root,
        session,
        request,
        response,
        inspection_result=inspection,
    )
    final = advance_proof_search_v06(
        root,
        session,
        compilation["repair_response"],
    )
    return final, [request, query, inspection, response], session


def _policy(
    *,
    source_class: str = "synthetic",
    content: bool = False,
    evaluation: bool = False,
    training: bool = False,
    authorization_reference: str | None = None,
) -> dict:
    return {
        "format": PROOF_SEARCH_DATA_USE_POLICY_FORMAT_V06,
        "source_class": source_class,
        "purpose": "PCS proof-search model research",
        "content_export_allowed": content,
        "evaluation_allowed": evaluation,
        "training_allowed": training,
        "authorization_reference": authorization_reference,
    }


def test_default_record_is_metadata_only_and_restricted(
    tmp_path: Path,
):
    session = _replacement_session(tmp_path)
    record = build_proof_search_record_v06(
        tmp_path,
        session,
    )

    assert record["format"] == PROOF_SEARCH_RECORD_FORMAT_V06
    assert record["split"] == "restricted"
    assert record["data_use"]["explicit_policy"] is False
    assert record["data_use"]["training_allowed"] is False
    assert record["data_use"]["evaluation_allowed"] is False
    assert record["summary"]["content_included"] is False
    assert "content" not in record
    assert record["summary"]["examples"] == 1

    example = record["examples"][0]
    assert example["content_included"] is False
    assert "content" not in example
    assert example["action"]["action"] == (
        "revise_predicate_from_project_bytes"
    )
    assert example["action"]["mode"] == "replace"
    assert example["labels"]["scientific_truth_label"] is False
    assert example["labels"]["proof_authority_label"] is False
    assert "statement" not in json.dumps(example)


def test_content_export_requires_explicit_permission(
    tmp_path: Path,
):
    session = _replacement_session(tmp_path)

    with pytest.raises(
        V06ProofSearchCorpusError,
        match="content-bearing proof-search export requires",
    ):
        build_proof_search_record_v06(
            tmp_path,
            session,
            include_content=True,
        )

    policy = _policy(content=False, evaluation=True)
    with pytest.raises(
        V06ProofSearchCorpusError,
        match="content-bearing proof-search export requires",
    ):
        build_proof_search_record_v06(
            tmp_path,
            session,
            data_use_policy=policy,
            include_content=True,
        )


def test_partner_training_reuse_requires_authorization_reference():
    with pytest.raises(
        V06ProofSearchCorpusError,
        match="requires authorization_reference",
    ):
        validate_data_use_policy_v06(
            _policy(
                source_class="partner_authorized",
                content=True,
                evaluation=True,
                training=True,
            )
        )

    approved = validate_data_use_policy_v06(
        _policy(
            source_class="partner_authorized",
            content=True,
            evaluation=True,
            training=True,
            authorization_reference="DPA-PCS-PILOT-0001-section-7",
        )
    )
    assert approved["training_allowed"] is True
    assert len(approved["authorization_reference_sha256"]) == 64


def test_training_policy_requires_evaluation_and_content_export():
    with pytest.raises(
        V06ProofSearchCorpusError,
        match="requires evaluation_allowed",
    ):
        validate_data_use_policy_v06(
            _policy(
                content=True,
                evaluation=False,
                training=True,
            )
        )

    with pytest.raises(
        V06ProofSearchCorpusError,
        match="requires content_export_allowed",
    ):
        validate_data_use_policy_v06(
            _policy(
                content=False,
                evaluation=True,
                training=True,
            )
        )


def test_synthetic_training_record_includes_action_content(
    tmp_path: Path,
):
    session = _replacement_session(tmp_path)
    record = build_proof_search_record_v06(
        tmp_path,
        session,
        data_use_policy=_policy(
            content=True,
            evaluation=True,
            training=True,
        ),
        include_content=True,
    )

    assert record["data_use"]["training_allowed"] is True
    assert record["split"] in {"train", "validation", "test"}
    example = record["examples"][0]
    assert example["content_included"] is True
    assert example["content"]["task"]["candidate_snapshot"]
    assert example["content"]["emitted_proposals"][0]["check"]["key"] == "id"


def test_decomposition_inspection_chain_is_verified_and_aligned(
    tmp_path: Path,
):
    session, interactions, historical = _decomposition_run(tmp_path)
    record = build_proof_search_record_v06(
        tmp_path,
        session,
        interaction_documents=interactions,
        historical_sessions=[historical],
        data_use_policy=_policy(
            content=True,
            evaluation=True,
            training=True,
        ),
        include_content=True,
    )

    assert record["summary"]["interactions"] == 4
    example = record["examples"][0]
    assert example["action"]["action"] == "decompose_claim"
    assert example["action"]["mode"] == "decompose"
    assert example["action"]["emitted_proposal_count"] == 1
    assert len(example["interaction_refs"]) == 4
    assert example["content"]["interaction_payloads"]
    kinds = {
        item["kind"]
        for item in record["interaction_summaries"]
    }
    assert kinds == {
        "DECOMPOSITION_REQUEST",
        "INSPECTION_QUERY",
        "INSPECTION_RESULT",
        "DECOMPOSITION_RESPONSE",
    }


def test_wrong_or_tampered_interaction_is_rejected(
    tmp_path: Path,
):
    session, interactions, historical = _decomposition_run(tmp_path)
    tampered = json.loads(json.dumps(interactions))
    inspection = tampered[2]
    inspection["observations"][0]["observation"]["columns"] = ["fake"]

    with pytest.raises(
        V06ProofSearchCorpusError,
        match="invalid artifact inspection result interaction",
    ):
        build_proof_search_record_v06(
            tmp_path,
            session,
            interaction_documents=tampered,
            historical_sessions=[historical],
        )


def test_tampered_session_is_rejected(
    tmp_path: Path,
):
    session = _replacement_session(tmp_path)
    tampered = json.loads(json.dumps(session))
    tampered["summary"]["diagnostic_reward_total"] += 100

    with pytest.raises(
        V06ProofSearchCorpusError,
        match="invalid proof-search session",
    ):
        build_proof_search_record_v06(
            tmp_path,
            tampered,
        )


def test_record_and_policy_files_do_not_change_scientific_inventory(
    tmp_path: Path,
):
    session = _replacement_session(tmp_path)
    before = session["inventory_commitment_sha256"]
    record = build_proof_search_record_v06(
        tmp_path,
        session,
    )
    write_proof_search_record_v06(
        record,
        tmp_path / "search-record.json",
    )
    (tmp_path / "data-use-policy.json").write_text(
        json.dumps(
            _policy(
                content=True,
                evaluation=True,
                training=True,
            ),
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    discovery = discover_project_v06(tmp_path)
    assert discovery["inventory_commitment_sha256"] == before


def test_corpus_is_deterministic_and_preserves_restricted_examples(
    tmp_path: Path,
):
    session = _replacement_session(tmp_path)
    restricted = build_proof_search_record_v06(
        tmp_path,
        session,
    )
    training = build_proof_search_record_v06(
        tmp_path,
        session,
        data_use_policy=_policy(
            content=True,
            evaluation=True,
            training=True,
        ),
        include_content=True,
    )

    first = build_proof_search_corpus_v06(
        [restricted, training]
    )
    second = build_proof_search_corpus_v06(
        [training, restricted]
    )

    assert first == second
    assert first["format"] == PROOF_SEARCH_CORPUS_FORMAT_V06
    assert len(first["corpus_sha256"]) == 64
    assert first["summary"]["records"] == 2
    assert first["summary"]["examples"] == 1
    assert first["summary"]["split_counts"] == {"restricted": 1}
    assert first["summary"]["training_eligible_examples"] == 0
    assert first["summary"]["evaluation_eligible_examples"] == 0
    assert first["summary"]["content_bearing_examples"] == 0
    example = first["examples"][0]
    assert example["data_use"]["training_allowed"] is False
    assert example["data_use"]["evaluation_allowed"] is False
    assert example["data_use"]["content_export_allowed"] is False
    assert example["data_use"]["aggregation_rule"] == "MOST_RESTRICTIVE"
    assert example["content_included"] is False
    assert "content" not in example
    assert len(example["source_record_sha256s"]) == 2
    assert first["trust_model"]["corpus_is_proof_authority"] is False


def test_problem_group_split_is_stable_across_runs(
    tmp_path: Path,
):
    first_session = _replacement_session(tmp_path / "one")
    second_session = _replacement_session(tmp_path / "two")
    policy = _policy(
        content=True,
        evaluation=True,
        training=True,
    )
    first = build_proof_search_record_v06(
        tmp_path / "one",
        first_session,
        data_use_policy=policy,
    )
    second = build_proof_search_record_v06(
        tmp_path / "two",
        second_session,
        data_use_policy=policy,
    )

    assert (
        first["source_session"]["problem_group_sha256"]
        == second["source_session"]["problem_group_sha256"]
    )
    assert first["split"] == second["split"]


def test_record_and_corpus_cli_round_trip(
    tmp_path: Path,
):
    project = tmp_path / "project"
    session = _replacement_session(project)
    session_path = tmp_path / "session.json"
    write_proof_search_session_v06(
        session,
        session_path,
    )

    record_path = tmp_path / "record.json"
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "pcs.cli",
            "export-proof-search-record-v06",
            str(project),
            str(session_path),
            "-o",
            str(record_path),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    record_response = json.loads(proc.stdout)
    assert record_response["format"] == PROOF_SEARCH_RECORD_FORMAT_V06
    assert record_response["data_use"]["training_allowed"] is False

    corpus_path = tmp_path / "corpus.json"
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "pcs.cli",
            "build-proof-search-corpus-v06",
            str(record_path),
            "-o",
            str(corpus_path),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    corpus_response = json.loads(proc.stdout)
    assert corpus_response["format"] == PROOF_SEARCH_CORPUS_FORMAT_V06
    assert corpus_response["summary"]["examples"] == 1
    assert json.loads(
        corpus_path.read_text(encoding="utf-8")
    )["corpus_sha256"] == corpus_response["corpus_sha256"]


def test_corpus_writer_rejects_tampering(
    tmp_path: Path,
):
    session = _replacement_session(tmp_path / "project")
    record = build_proof_search_record_v06(
        tmp_path / "project",
        session,
    )
    corpus = build_proof_search_corpus_v06([record])
    tampered = json.loads(json.dumps(corpus))
    tampered["summary"]["examples"] += 1

    with pytest.raises(
        V06ProofSearchCorpusError,
        match="commitment does not match",
    ):
        write_proof_search_corpus_v06(
            tampered,
            tmp_path / "bad-corpus.json",
        )

def test_corpus_keeps_content_only_when_all_duplicate_sources_allow_it(
    tmp_path: Path,
):
    session = _replacement_session(tmp_path)
    policy = _policy(
        content=True,
        evaluation=True,
        training=True,
    )
    first_record = build_proof_search_record_v06(
        tmp_path,
        session,
        data_use_policy=policy,
        include_content=True,
    )
    second_record = build_proof_search_record_v06(
        tmp_path,
        session,
        data_use_policy=policy,
        include_content=True,
    )

    corpus = build_proof_search_corpus_v06(
        [first_record, second_record]
    )
    assert corpus["summary"]["records"] == 1
    assert corpus["summary"]["examples"] == 1
    example = corpus["examples"][0]
    assert example["data_use"]["training_allowed"] is True
    assert example["content_included"] is True
    assert example["content"]["emitted_proposals"][0]["check"]["key"] == "id"

def test_interaction_export_requires_exact_historical_session_snapshot(
    tmp_path: Path,
):
    session, interactions, historical = _decomposition_run(tmp_path)

    with pytest.raises(
        V06ProofSearchCorpusError,
        match="requires its exact historical proof-search session",
    ):
        build_proof_search_record_v06(
            tmp_path,
            session,
            interaction_documents=interactions,
        )

    record = build_proof_search_record_v06(
        tmp_path,
        session,
        interaction_documents=interactions,
        historical_sessions=[historical],
    )
    assert record["summary"]["interactions"] == 4

