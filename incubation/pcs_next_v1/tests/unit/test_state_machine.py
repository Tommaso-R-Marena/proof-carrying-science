import pytest
from pcs_next_v1.pilot.state_machine import PilotStateMachine, PilotState, TransitionError

def test_monotonic_and_cas():
    sm = PilotStateMachine("p")
    sm.transition(PilotState.INSPECTION, evidence={"ok": True})
    with pytest.raises(TransitionError):
        sm.transition(PilotState.ASSURANCE_REPORT)
    g = sm.generation
    with pytest.raises(TransitionError):
        sm.transition(PilotState.CLAIM_IDENTIFICATION, expected_generation=g - 1)
