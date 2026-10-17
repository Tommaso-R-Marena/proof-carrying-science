"""Tests for the prioritized proposals catalog."""

from __future__ import annotations

from pathlib import Path

import pytest

from python_harness.proposals_catalog import (
    DEFAULT_PROPOSALS,
    build_catalog,
    write_catalog,
)


def test_default_catalog_all_proposals() -> None:
    catalog = build_catalog()
    assert catalog["proposal_count"] == len(DEFAULT_PROPOSALS)
    assert catalog["proposal_count"] >= 5
    assert "PROPOSALS ONLY" in catalog["disclaimer"]
    for p in catalog["proposals"]:
        assert p["status"] == "proposal"
        assert p["not_claimed_done"] is True


def test_rejects_completion_claim() -> None:
    bad = [
        {
            "id": "X",
            "priority": 1,
            "title": "done?",
            "status": "completed",
            "workstream_affinity": [],
            "summary": "no",
            "rationale": "no",
            "not_claimed_done": True,
        }
    ]
    with pytest.raises(ValueError, match="proposal"):
        build_catalog(bad)


def test_write_catalog_files(tmp_path: Path) -> None:
    jp = tmp_path / "PROPOSALS.json"
    mp = tmp_path / "PROPOSALS.md"
    catalog = write_catalog(json_path=jp, md_path=mp)
    assert jp.is_file()
    assert mp.is_file()
    assert "E-P01" in mp.read_text(encoding="utf-8")
    assert catalog["format"] == "pcs-independent-program-proposals-v1"
