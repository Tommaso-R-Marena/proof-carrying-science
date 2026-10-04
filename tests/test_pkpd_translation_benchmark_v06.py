from __future__ import annotations

from pathlib import Path

from pcs.pkpd_translation_benchmark_v06 import (
    PKPD_TRANSLATION_BENCHMARK_FORMAT_V06,
    run_pkpd_translation_benchmark_v06,
)


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "examples" / "pkpd_translation_benchmark"


def test_realistic_pkpd_translation_benchmark_closes_only_supported_frontier(
    tmp_path: Path,
):
    report = run_pkpd_translation_benchmark_v06(
        tmp_path / "run",
        fixture_root=FIXTURE,
    )

    assert report["format"] == PKPD_TRANSLATION_BENCHMARK_FORMAT_V06
    assert report["passed"] is True
    assert all(report["criteria"].values())

    discovery = report["discovery"]
    assert discovery["deterministic_pkpd_contract_recommendations"] == 1
    assert discovery["deterministic_pkpd_replay_recommendations"] == 0

    assert report["initial_search"]["status"] == "AWAITING_REPAIR"
    assert report["initial_search"]["summary"]["repairable_tasks"] == 2
    assert report["initial_search"]["replay_candidate_status"] == (
        "REJECTED_UNGROUNDED"
    )

    final = report["final_search"]
    assert final["status"] == "READY_FOR_HUMAN_CONFIRMATION"
    assert final["summary"]["repairable_tasks"] == 0
    assert final["summary"]["blocking_open_obligations"] == 0
    assert final["summary"]["compiled_selected"] == 4
    assert final["summary"]["trajectory_steps"] == 1

    frontier = report["proof_frontier"]
    assert len(frontier["theorem_backed"]) == 3
    external = frontier["externally_validated_under_trust_contract"][0]
    assert external["status"] == "COMPILED_EXTERNAL_VALIDATOR_BOUND"
    assert external["reported_outcome"] == "PASS"
    assert external["semantic_authority"] == "EXTERNAL_VALIDATOR_TRUST_REQUIRED"
    assert report["design"]["external_validator"]["reference_validation_result"][
        "outcome"
    ] == "PASS"
    assert frontier["certified_checker_missing"] == []
    peak = next(
        item
        for item in frontier["theorem_backed"]
        if item["candidate_id"] == "MODEL_PEAK_THRESHOLD"
    )
    assert peak["proof_level"] == "LEAN_KERNEL"
    assert peak["soundness_theorem"] == "PCS.V2.PKPDCheck.pkpdPeakRun_sound"
    assert "clinical validity" in frontier["not_established"]


def test_realistic_pkpd_translation_benchmark_is_deterministic(tmp_path: Path):
    first = run_pkpd_translation_benchmark_v06(
        tmp_path / "first",
        fixture_root=FIXTURE,
    )
    second = run_pkpd_translation_benchmark_v06(
        tmp_path / "second",
        fixture_root=FIXTURE,
    )

    assert (
        first["inventory_commitment_sha256"]
        == second["inventory_commitment_sha256"]
    )
    assert (
        first["initial_search"]["graph_sha256"]
        == second["initial_search"]["graph_sha256"]
    )
    assert (
        first["final_search"]["graph_sha256"]
        == second["final_search"]["graph_sha256"]
    )
    assert first["criteria"] == second["criteria"]
    assert first["proof_frontier"] == second["proof_frontier"]
