"""Tests for the program inventory aggregator."""

from __future__ import annotations

from pathlib import Path

from python_harness.inventory_aggregator import (
    aggregate_inventory,
    render_inventory_markdown,
)


REPORTS = (
    "TEST_INVENTORY.md",
    "BUGS_AND_AMBIGUITIES.md",
    "OPEN_TRUST_ASSUMPTIONS.md",
    "TECHNICAL_REPORT.md",
)


def test_missing_prefixes_recorded_as_missing(tmp_path: Path) -> None:
    report = aggregate_inventory(
        repo=tmp_path,
        prefixes=("independent_eval/protocol_adversarial",),
        report_names=REPORTS,
    )
    assert report.workstreams[0].prefix_present is False
    assert all(r.status == "MISSING" for r in report.workstreams[0].reports)
    data = report.to_dict()
    assert data["prefixes_missing"] == 1
    assert "MISSING means absent" in data["disclaimer"]


def test_present_inventory_extracts_collected_tests(tmp_path: Path) -> None:
    prefix = tmp_path / "independent_eval" / "repro_tcb"
    prefix.mkdir(parents=True)
    (prefix / "TEST_INVENTORY.md").write_text(
        "# TEST_INVENTORY\n\n**Collected tests:** 12\n",
        encoding="utf-8",
    )
    (prefix / "TECHNICAL_REPORT.md").write_text("# report\n", encoding="utf-8")
    # BUGS and OPEN_TRUST intentionally absent

    report = aggregate_inventory(
        repo=tmp_path,
        prefixes=("independent_eval/repro_tcb",),
        report_names=REPORTS,
    )
    ws = report.workstreams[0]
    assert ws.prefix_present is True
    by_name = {Path(r.path).name: r for r in ws.reports}
    assert by_name["TEST_INVENTORY.md"].status == "PRESENT"
    assert by_name["TEST_INVENTORY.md"].collected_tests == 12
    assert by_name["TECHNICAL_REPORT.md"].status == "PRESENT"
    assert by_name["BUGS_AND_AMBIGUITIES.md"].status == "MISSING"
    assert by_name["OPEN_TRUST_ASSUMPTIONS.md"].status == "MISSING"
    # Must not invent a zero for missing reports
    assert by_name["BUGS_AND_AMBIGUITIES.md"].collected_tests is None


def test_markdown_render_marks_missing(tmp_path: Path) -> None:
    report = aggregate_inventory(
        repo=tmp_path,
        prefixes=("independent_eval/reviewer_adoption",),
        report_names=("TEST_INVENTORY.md",),
    )
    md = render_inventory_markdown(report)
    assert "MISSING" in md
    assert "independent_eval/reviewer_adoption" in md
