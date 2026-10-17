"""Task 9 — metamorphic scientific testing vs PCS CLI verify."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from python_harness.metamorphic import run_metamorphic_suite  # noqa: E402
from python_harness.paths import CASEBOOK, RESULTS  # noqa: E402
from python_harness.hashing import write_json  # noqa: E402


def test_metamorphic_suite_on_pkpd_case(tmp_path):
    source = CASEBOOK / "cases" / "01_pkpd_one_compartment"
    report = run_metamorphic_suite(source, tmp_path / "meta")
    write_json(RESULTS / "metamorphic_pkpd_report.json", report)
    assert report["valid_total"] >= 3  # baseline + rename + reorder
    assert report["valid_pass"] == report["valid_total"]
    assert report["invalid_total"] >= 2
    assert report["invalid_pass"] == report["invalid_total"]


def test_metamorphic_suite_on_composite_case(tmp_path):
    source = CASEBOOK / "cases" / "06_scientific_workflow_composite"
    report = run_metamorphic_suite(source, tmp_path / "meta")
    assert report["valid_pass"] == report["valid_total"]
    assert report["invalid_pass"] >= 1
