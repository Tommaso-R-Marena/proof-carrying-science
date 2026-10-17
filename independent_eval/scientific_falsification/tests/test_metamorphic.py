"""Task 9 — metamorphic scientific testing vs PCS CLI verify."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from python_harness.hashing import write_json  # noqa: E402
from python_harness.metamorphic import (  # noqa: E402
    DEFAULT_CAMPAIGN_CASE_IDS,
    run_metamorphic_campaign,
    run_metamorphic_suite,
)
from python_harness.paths import CASEBOOK, RESULTS  # noqa: E402


def _assert_suite_ok(report: dict) -> None:
    assert report["valid_total"] >= 3  # baseline + rename + reorder
    assert report["valid_pass"] == report["valid_total"]
    assert report["invalid_total"] >= 1
    assert report["invalid_pass"] == report["invalid_total"]
    assert report["all_oracles_passed"] is True


def test_metamorphic_suite_on_pkpd_case(tmp_path):
    source = CASEBOOK / "cases" / "01_pkpd_one_compartment"
    report = run_metamorphic_suite(source, tmp_path / "meta")
    write_json(RESULTS / "metamorphic_01_pkpd_one_compartment.json", report)
    _assert_suite_ok(report)


def test_metamorphic_suite_on_reaction_case(tmp_path):
    source = CASEBOOK / "cases" / "03_mass_action_reaction_balance"
    report = run_metamorphic_suite(source, tmp_path / "meta")
    write_json(RESULTS / "metamorphic_03_mass_action_reaction_balance.json", report)
    _assert_suite_ok(report)
    assert "reaction_balance" in report["check_types"]
    assert any(c["name"] == "break_model_or_reaction" for c in report["cases"])


def test_metamorphic_suite_on_units_case(tmp_path):
    source = CASEBOOK / "cases" / "04_unit_compatible_concentration"
    report = run_metamorphic_suite(source, tmp_path / "meta")
    write_json(RESULTS / "metamorphic_04_unit_compatible_concentration.json", report)
    _assert_suite_ok(report)
    assert "unit_compatible" in report["check_types"]
    names = {c["name"] for c in report["cases"]}
    assert "incompatible_units" in names
    assert "break_model_or_reaction" not in names  # not applicable


def test_metamorphic_suite_on_composite_case(tmp_path):
    source = CASEBOOK / "cases" / "06_scientific_workflow_composite"
    report = run_metamorphic_suite(source, tmp_path / "meta")
    write_json(RESULTS / "metamorphic_06_scientific_workflow_composite.json", report)
    _assert_suite_ok(report)
    names = {c["name"] for c in report["cases"]}
    assert "break_model_or_reaction" in names
    assert "incompatible_units" in names


def test_metamorphic_campaign_covers_extended_cases(tmp_path):
    campaign = run_metamorphic_campaign(
        CASEBOOK / "cases",
        tmp_path / "work",
        RESULTS,
        case_ids=DEFAULT_CAMPAIGN_CASE_IDS,
    )
    assert campaign["case_count"] == len(DEFAULT_CAMPAIGN_CASE_IDS)
    assert campaign["cases_ok"] == campaign["case_count"]
    assert campaign["oracles_all_passed_count"] == campaign["case_count"]
    for case_id in DEFAULT_CAMPAIGN_CASE_IDS:
        assert (RESULTS / f"metamorphic_{case_id}.json").is_file()
    assert (RESULTS / "metamorphic_campaign.json").is_file()
    assert "03_mass_action_reaction_balance" in campaign["case_ids"]
    assert "04_unit_compatible_concentration" in campaign["case_ids"]
    assert "06_scientific_workflow_composite" in campaign["case_ids"]
