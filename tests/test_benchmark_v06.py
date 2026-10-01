from __future__ import annotations

import json
from pathlib import Path

import pytest

from pcs.benchmark_v06 import (
    V06BenchmarkError,
    run_benchmark_registry_v06,
    write_benchmark_report_v06,
)


ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "validation" / "real_world" / "registry.json"


def test_real_world_registry_matches_all_five_expected_outcomes():
    report = run_benchmark_registry_v06(REGISTRY)

    assert report["format"] == "pcs-real-world-validation-report-v1"
    assert report["summary"] == {
        "cases": 5,
        "matched_expected": 5,
        "unexpected": 0,
        "expected_pass": 3,
        "expected_fail": 2,
    }

    by_id = {case["id"]: case for case in report["cases"]}
    assert by_id["haber_bosch_balance"]["actual_outcome"] == "PASS"
    assert by_id["iris_clean_split"]["actual_outcome"] == "PASS"
    assert by_id["iris_contaminated_split"]["actual_outcome"] == "FAIL"
    assert by_id["iris_contaminated_split"]["details"]["overlap_sample"] == ["120"]
    assert by_id["indometh_unit_equivalence"]["actual_outcome"] == "PASS"

    pk = by_id["indometh_subject1_single_exponential"]
    assert pk["actual_outcome"] == "FAIL"
    assert pk["details"]["row_count"] == 11
    assert pk["details"]["mismatch_count_reported"] > 0


def test_real_world_report_is_deterministic_and_hash_bound():
    a = run_benchmark_registry_v06(REGISTRY)
    b = run_benchmark_registry_v06(REGISTRY)

    assert a == b
    assert len(a["registry_sha256"]) == 64
    assert len(a["report_semantic_hash"]) == 64
    assert a["report_semantic_hash_format"] == "pcs-real-world-validation-sha256-v1"


def test_fixture_tamper_is_rejected_before_benchmark_execution(tmp_path):
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    case = next(c for c in registry["cases"] if c["id"] == "iris_clean_split")

    train_src = REGISTRY.parent / case["artifacts"]["train"]["path"]
    test_src = REGISTRY.parent / case["artifacts"]["test"]["path"]
    train = tmp_path / train_src.name
    test = tmp_path / test_src.name
    train.write_bytes(train_src.read_bytes() + b"\n# tampered\n")
    test.write_bytes(test_src.read_bytes())

    registry["cases"] = [case]
    path = tmp_path / "registry.json"
    path.write_text(json.dumps(registry), encoding="utf-8")

    with pytest.raises(V06BenchmarkError, match="fixture hash mismatch"):
        run_benchmark_registry_v06(path)


def test_report_writer_refuses_accidental_overwrite(tmp_path):
    report = run_benchmark_registry_v06(REGISTRY)
    out = tmp_path / "report.json"

    write_benchmark_report_v06(report, out)
    original = out.read_bytes()

    with pytest.raises(V06BenchmarkError, match="refusing to overwrite"):
        write_benchmark_report_v06(report, out)

    assert out.read_bytes() == original
