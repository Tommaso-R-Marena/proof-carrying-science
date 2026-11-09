"""Independent Writ/14 effect FSM, for research cross-checking.

This is a small, pure transition model. The real gateway and detached signed
receipt verifier must independently authenticate the event stream and bind
effect IDs. No statement here proves an external effect really occurred.
"""
from __future__ import annotations

class EffectHistoryError(ValueError):
    pass

NEXT = {
    ("pending", "dispatch_lease"): "working",
    ("working", "delivered"): "delivered",
    ("working", "dispatch_uncertain"): "uncertain",
    ("pending", "cancel_effect"): "canceled",
    ("pending", "dispatch_suppressed"): "suppressed",
    ("pending", "dispatch_expired"): "expired",
}
META = {"revoke_grant", "revoke_delegation", "rotate_epoch"}

def replay(events: tuple[dict,...], expected: dict[int,str]) -> dict[int,str]:
    """Independent one-step projection for all IDs; rejects unknown transitions.

    A lease is the recorded *authorization to attempt an external action*, not
    evidence that the attempt actually happened. Terminal states are sticky.
    """
    state: dict[int,str] = {}
    for event in events:
        if not isinstance(event,dict):
            raise EffectHistoryError("invalid event")
        tag = event.get("event")
        eid = event.get("effect_id")
        if tag == "admit":
            if type(eid) is not int or eid <= 0 or eid in state:
                raise EffectHistoryError("replayed/invalid admission")
            state[eid] = "pending"
        elif tag in META:
            continue
        elif any(kind == tag for _,kind in NEXT):
            if type(eid) is not int or eid not in state:
                raise EffectHistoryError("unknown effect")
            transition = NEXT.get((state[eid],tag))
            if transition is None:
                raise EffectHistoryError("contradictory terminal/lease history")
            state[eid] = transition
        else:
            raise EffectHistoryError("unsupported event")
    if state != expected:
        raise EffectHistoryError("claimed current outbox disagrees with events")
    return state
