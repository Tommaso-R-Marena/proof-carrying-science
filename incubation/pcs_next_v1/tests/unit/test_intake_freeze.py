import json
from pathlib import Path
from pcs_next_v1.pilot.intake import load_intake, freeze_intake, verify_lock_integrity, bind_artifact_hashes

FIX = Path(__file__).resolve().parents[2] / "fixtures/synthetic_pilot"

def test_freeze_and_verify():
    intake = load_intake(FIX / "intake.json")
    bound = bind_artifact_hashes(intake, FIX / "project")
    lock = freeze_intake(bound)
    verify_lock_integrity(lock)
    # mutate intake inside lock
    lock2 = json.loads(json.dumps(lock))
    lock2["intake"]["project_id"] = "tampered"
    import pytest
    from pcs_next_v1.core.errors import PcsNextError
    with pytest.raises(PcsNextError):
        verify_lock_integrity(lock2)
