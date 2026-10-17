from __future__ import annotations

import json
from pathlib import Path

import pytest

from independent_eval.reviewer_adoption.external_lab.burden_tracker import (
    append_log,
    list_steps,
    load_steps,
)

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "external_lab" / "package"


def test_checklist_forbids_external_validation_complete():
    steps = load_steps(PACKAGE)
    assert len(steps) >= 5
    text = list_steps(PACKAGE)
    assert "checklist" in text.lower() or "configuration" in text.lower()

    path = PACKAGE / "CHECKLIST.json"
    assert path.is_file(), "canonical checklist must be CHECKLIST.json only"
    assert not (PACKAGE / "checklist.json").exists(), "lowercase checklist.json collides on case-insensitive FS"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data.get("external_validation_complete_allowed") is False
    assert "EXTERNAL_VALIDATION_COMPLETE" in set(data.get("forbidden_states") or [])

    docs = "\n".join(
        (PACKAGE / name).read_text(encoding="utf-8")
        for name in ("README.md", "LIMITATIONS.md", "SUCCESS_FAILURE.md")
        if (PACKAGE / name).is_file()
    )
    assert "does not claim" in docs.lower() or "not claim" in docs.lower() or "forbidden" in docs.lower()
    assert "EXTERNAL_VALIDATION_COMPLETE" in docs or "completed external" in docs.lower()


def test_burden_tracker_records_minutes_and_never_claims_validation(tmp_path: Path):
    steps = load_steps(PACKAGE)
    step_id = steps[0].get("id") or steps[0].get("step_id")
    log = tmp_path / "burden.jsonl"
    record = append_log(
        log,
        step_id=step_id,
        minutes=12.5,
        notes="out-of-band delay",
        package_dir=PACKAGE,
    )
    assert record["completed_external_lab_validation"] is False
    assert record["minutes"] == 12.5
    parsed = json.loads(log.read_text(encoding="utf-8").strip().splitlines()[0])
    assert parsed["completed_external_lab_validation"] is False

    with pytest.raises(ValueError, match="EXTERNAL_VALIDATION_COMPLETE|completed external"):
        append_log(
            log,
            step_id=step_id,
            minutes=1,
            notes="EXTERNAL_VALIDATION_COMPLETE",
            package_dir=PACKAGE,
            force_completed_validation=True,  # type: ignore[call-arg]
        )
