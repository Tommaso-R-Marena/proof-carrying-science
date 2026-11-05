"""Task 10 — workflow discovery evaluation vs pcs discover-v06."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from python_harness.discovery_metrics import run_discovery_benchmark, write_report  # noqa: E402
from python_harness.paths import DISCOVERY, RESULTS  # noqa: E402


def test_discovery_benchmark_precision_recall_abstention(tmp_path):
    report = run_discovery_benchmark(
        DISCOVERY / "projects",
        DISCOVERY / "ground_truth.json",
        tmp_path / "disc",
    )
    write_report(report, RESULTS / "discovery_benchmark_report.json")
    assert report["cli_success_count"] == report["project_count"]
    assert report["project_count"] >= 4
    # PKPD and reaction projects should yield high recall/precision.
    by_name = {r["project"]: r for r in report["projects"]}
    assert by_name["pkpd_detectable"]["recall"] == 1.0
    assert by_name["pkpd_detectable"]["precision"] == 1.0
    assert by_name["reaction_detectable"]["recall"] == 1.0
    assert by_name["ambiguous_notes"]["abstention_correct"] is True
    assert by_name["pk_without_pd"]["abstention_correct"] is True
    assert report["macro_precision"] >= 0.75
    assert report["macro_recall"] >= 0.75
