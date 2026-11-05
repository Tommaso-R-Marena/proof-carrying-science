import pytest
from pcs_next_v1.trust.policy import pin_policy, verify_policy_binding, reject_producer_verdict
from pcs_next_v1.core.errors import PcsNextError
from pathlib import Path
import json

FIX = Path(__file__).resolve().parents[2] / "fixtures/synthetic_pilot/acceptance_policy.json"

def test_policy_substitution():
    p = pin_policy(json.loads(FIX.read_text()))
    other = dict(p.raw)
    other["policy_version"] = "9.9.9"
    with pytest.raises(PcsNextError):
        verify_policy_binding(receiver_policy=p, claimed_policy=other, claimed_policy_hash=None)

def test_producer_verdict_ignored():
    r = reject_producer_verdict(True)
    assert r["receiver_action"] == "IGNORED"
