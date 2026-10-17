"""Task 18 — external lab package tests."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent))

from independent_eval.reviewer_adoption.external_lab.burden_tracker import (
    append_log,
    load_steps,
    list_steps,
)

PKG = ROOT / "external_lab" / "package"


def test_checklist_or_defaults_available():
    steps = load_steps(PKG)
    assert len(steps) >= 5
    text = list_steps(PKG)
    assert "checklist" in text.lower() or "configuration" in text.lower()
    # Prefer package docs that refuse completed-validation claims.
    for name in ("README.md", "LIMITATIONS.md", "SUCCESS_FAILURE.md", "checklist.json", "CHECKLIST.json"):
        path = PKG / name
        if path.is_file():
            body = path.read_text(encoding="utf-8").lower()
            if "external" in body and "validation" in body:
                assert "complete" in body or "not" in body or "false" in body
            break
    assert (PKG / "README.md").is_file() or (PKG / "SETUP.md").is_file()


def test_burden_log_never_claims_completed_validation(tmp_path):
    steps = load_steps(PKG)
    step_id = steps[0]["id"]
    log = tmp_path / "burden.jsonl"
    record = append_log(log, step_id=step_id, minutes=12.0, notes="dry run", package_dir=PKG)
    assert record["completed_external_lab_validation"] is False
    lines = log.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    parsed = json.loads(lines[0])
    assert parsed["completed_external_lab_validation"] is False
