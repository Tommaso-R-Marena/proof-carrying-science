from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from pcs.discover_v06 import discover_project_v06
from pcs.proof_repair_v06 import PROOF_REPAIR_RESPONSE_FORMAT_V06
from pcs.proof_search_corpus_v06 import (
    PROOF_SEARCH_CORPUS_FORMAT_V06,
    V06ProofSearchCorpusError,
    build_proof_search_corpus_v06,
    write_proof_search_corpus_v06,
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


def _proposal(
    ids: dict[str, str],
    *,
    key: str,
) -> dict:
    return {
        "id": "MODEL_DISJOINT",
        "confidence": 0.995,
        "finding": (
            "The two cohorts appear intended to represent non-overlapping "
            "populations on their identifier."
        ),
        "artifact_ids": [
            ids["cohort_a.csv"],
            ids["cohort_b.csv"],
        ],
        "claim": {
            "id": "C_MODEL_DISJOINT",
            "statement": (
                "The two cohorts are disjoint on their intended identifier."
            ),
            "kind": "computational",
        },
        "check": {
            "id": "E_MODEL_DISJOINT",
            "type": "csv_disjoint",
            "claim_ids": ["C_MODEL_DISJOINT"],
            "left_artifact": ids["cohort_a.csv"],
            "right_artifact": ids["cohort_b.csv"],
            "key": key,
        },
    }


def _proposal_file(
    root: Path,
    discovery: dict,
    proposal: dict,
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
        "proposals": [proposal],
    }
    path = root / "initial-proposals.json"
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return path


def _repair_response(
    session: dict,
    replacement: dict,
    *,
    version: str,
) -> dict:
    task = session["current_repair_request"]["tasks"][0]
    return {
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
            "name": "corpus-test-repair-model",
            "version": version,
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


def _session_after_one_repair(
    root: Path,
    *,
    replacement_key: str,
    version: str,
) -> dict:
    _write_csv_pair(root)
    discovery = discover_project_v06(root)
    ids = _inventory_ids(discovery)
    initial = _proposal(ids, key="patient_id")
    proposal_path = _proposal_file(root, discovery, initial)
    session = start_proof_search_v06(
        root,
        proposal_files=[proposal_path],
    )
    response = _repair_response(
        session,
        _proposal(ids, key=replacement_key),
        version=version,
    )
    return advance_proof_search_v06(
        root,
        session,
        response,
    )


def test_corpus_deduplicates_sources_and_examples_deterministically(
    tmp_path: Path,
):
    progress = _session_after_one_repair(
        tmp_path / "progress",
        replacement_key="id",
        version="progress",
    )
    cycle = _session_after_one_repair(
        tmp_path / "cycle",
        replacement_key="patient_id",
        version="cycle",
    )

    first = build_proof_search_corpus_v06(
        [progress, cycle, progress]
    )
    second = build_proof_search_corpus_v06(
        [cycle, progress]
    )

    assert first == second
    assert first["format"] == PROOF_SEARCH_CORPUS_FORMAT_V06
    assert len(first["corpus_sha256"]) == 64
    assert first["summary"]["source_sessions"] == 2
    assert first["summary"]["examples"] == 2
    assert first["summary"]["outcome_counts"] == {
        "CYCLE_DETECTED": 1,
        "OBJECTIVE_PROGRESS": 1,
    }

    assert {
        example["split"]
        for example in first["examples"]
    } == {first["examples"][0]["split"]}
    for example in first["examples"]:
        assert example["authority"]["training_record_is_authoritative"] is False
        assert example["labels"]["has_scientific_truth_label"] is False
        assert example["labels"]["has_proof_authority_label"] is False
        assert example["state"]["task"]["candidate_snapshot"]
        assert example["target_action"]["replacement_proposal"]["id"] == (
            "MODEL_DISJOINT"
        )
        assert len(
            example["target_action"]["replacement_proposal_sha256"]
        ) == 64


def test_corpus_progress_example_contains_actual_repair_action(
    tmp_path: Path,
):
    session = _session_after_one_repair(
        tmp_path,
        replacement_key="id",
        version="progress",
    )
    corpus = build_proof_search_corpus_v06([session])

    assert corpus["summary"]["examples"] == 1
    example = corpus["examples"][0]
    assert example["labels"]["outcome"] == "OBJECTIVE_PROGRESS"
    assert example["labels"]["diagnostic_reward"] > 0
    assert example["labels"]["label_scope"] == "SEARCH_BEHAVIOR_ONLY"
    assert example["labels"]["blocking_obligations_closed"] == 1
    assert example["allowed_action"] == (
        "revise_predicate_from_project_bytes"
    )
    assert example["target_action"]["replacement_proposal"]["check"]["key"] == (
        "id"
    )
    assert example["observed_transition"]["metrics_after"][
        "blocking_open_obligations"
    ] == 0


def test_corpus_cycle_example_is_negative_search_signal_not_truth_label(
    tmp_path: Path,
):
    session = _session_after_one_repair(
        tmp_path,
        replacement_key="patient_id",
        version="cycle",
    )
    corpus = build_proof_search_corpus_v06([session])

    example = corpus["examples"][0]
    assert example["labels"]["outcome"] == "CYCLE_DETECTED"
    assert example["labels"]["cycle_detected"] is True
    assert example["labels"]["diagnostic_reward"] < 0
    assert example["labels"]["has_scientific_truth_label"] is False
    assert corpus["trust_model"]["diagnostic_reward_is_scientific_truth"] is False


def test_corpus_rejects_tampered_search_session(tmp_path: Path):
    session = _session_after_one_repair(
        tmp_path,
        replacement_key="id",
        version="progress",
    )
    tampered = json.loads(json.dumps(session))
    tampered["summary"]["diagnostic_reward_total"] += 1000

    with pytest.raises(
        V06ProofSearchCorpusError,
        match="invalid proof-search session",
    ):
        build_proof_search_corpus_v06([tampered])


def test_corpus_write_and_cli_export(tmp_path: Path):
    session = _session_after_one_repair(
        tmp_path / "project",
        replacement_key="id",
        version="progress",
    )
    session_path = tmp_path / "search-session.json"
    write_proof_search_session_v06(
        session,
        session_path,
    )

    corpus = build_proof_search_corpus_v06([session])
    direct = tmp_path / "direct-corpus.json"
    written = write_proof_search_corpus_v06(
        corpus,
        direct,
    )
    assert written == str(direct.resolve())

    cli_out = tmp_path / "cli-corpus.json"
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "pcs.cli",
            "export-proof-search-corpus-v06",
            str(session_path),
            "-o",
            str(cli_out),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    response = json.loads(proc.stdout)
    assert response["format"] == PROOF_SEARCH_CORPUS_FORMAT_V06
    assert response["summary"]["examples"] == 1
    loaded = json.loads(cli_out.read_text(encoding="utf-8"))
    assert loaded["corpus_sha256"] == corpus["corpus_sha256"]
