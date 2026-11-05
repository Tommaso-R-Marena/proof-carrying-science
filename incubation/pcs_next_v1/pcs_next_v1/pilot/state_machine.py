"""Durable pilot state machine with monotonic transitions."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable

from ..core.canonical import canonicalize, canonical_hash
from ..core.errors import ErrorCode, PcsNextError


class PilotState(str, Enum):
    INTAKE = "INTAKE"
    INSPECTION = "INSPECTION"
    CLAIM_IDENTIFICATION = "CLAIM_IDENTIFICATION"
    REVIEWER_CONFIRMATION = "REVIEWER_CONFIRMATION"
    ASSUMPTION_REGISTRATION = "ASSUMPTION_REGISTRATION"
    FROZEN_INPUTS = "FROZEN_INPUTS"
    COMPUTATIONAL_REPLAY = "COMPUTATIONAL_REPLAY"
    EVIDENCE_CAPTURE = "EVIDENCE_CAPTURE"
    FORMAL_VERIFICATION = "FORMAL_VERIFICATION"
    INDEPENDENT_VERIFICATION = "INDEPENDENT_VERIFICATION"
    ASSURANCE_REPORT = "ASSURANCE_REPORT"
    ARCHIVAL_CLOSEOUT = "ARCHIVAL_CLOSEOUT"
    FAILED = "FAILED"
    REJECTED = "REJECTED"


# Allowed forward transitions (plus FAILED/REJECTED from most states).
TRANSITIONS: dict[PilotState, set[PilotState]] = {
    PilotState.INTAKE: {PilotState.INSPECTION, PilotState.FAILED, PilotState.REJECTED},
    PilotState.INSPECTION: {PilotState.CLAIM_IDENTIFICATION, PilotState.FAILED, PilotState.REJECTED},
    PilotState.CLAIM_IDENTIFICATION: {
        PilotState.REVIEWER_CONFIRMATION,
        PilotState.FAILED,
        PilotState.REJECTED,
    },
    PilotState.REVIEWER_CONFIRMATION: {
        PilotState.ASSUMPTION_REGISTRATION,
        PilotState.FAILED,
        PilotState.REJECTED,
    },
    PilotState.ASSUMPTION_REGISTRATION: {
        PilotState.FROZEN_INPUTS,
        PilotState.FAILED,
        PilotState.REJECTED,
    },
    PilotState.FROZEN_INPUTS: {
        PilotState.COMPUTATIONAL_REPLAY,
        PilotState.FAILED,
        PilotState.REJECTED,
    },
    PilotState.COMPUTATIONAL_REPLAY: {
        PilotState.EVIDENCE_CAPTURE,
        PilotState.FAILED,
        PilotState.REJECTED,
    },
    PilotState.EVIDENCE_CAPTURE: {
        PilotState.FORMAL_VERIFICATION,
        PilotState.FAILED,
        PilotState.REJECTED,
    },
    PilotState.FORMAL_VERIFICATION: {
        PilotState.INDEPENDENT_VERIFICATION,
        PilotState.FAILED,
        PilotState.REJECTED,
    },
    PilotState.INDEPENDENT_VERIFICATION: {
        PilotState.ASSURANCE_REPORT,
        PilotState.FAILED,
        PilotState.REJECTED,
    },
    PilotState.ASSURANCE_REPORT: {PilotState.ARCHIVAL_CLOSEOUT, PilotState.FAILED},
    PilotState.ARCHIVAL_CLOSEOUT: set(),
    PilotState.FAILED: set(),
    PilotState.REJECTED: set(),
}


class TransitionError(PcsNextError):
    def __init__(self, message: str, *, details: dict | None = None):
        super().__init__(ErrorCode.STATE_ILLEGAL, message, details=details)


@dataclass
class PilotStateMachine:
    project_id: str
    state: PilotState = PilotState.INTAKE
    generation: int = 0
    history: list[dict[str, Any]] = field(default_factory=list)
    store: dict[str, Any] = field(default_factory=dict)

    def snapshot(self) -> dict[str, Any]:
        body = {
            "format": "pcs-next-pilot-state-v1",
            "project_id": self.project_id,
            "state": self.state.value,
            "generation": self.generation,
            "history": list(self.history),
            "store_keys": sorted(self.store.keys()),
            "store_hashes": {k: canonical_hash(v) for k, v in sorted(self.store.items())},
        }
        return body

    def transition(
        self,
        new_state: PilotState | str,
        *,
        evidence: dict[str, Any] | None = None,
        actor: str = "system",
        expected_generation: int | None = None,
    ) -> dict[str, Any]:
        target = PilotState(new_state) if isinstance(new_state, str) else new_state
        if expected_generation is not None and expected_generation != self.generation:
            raise TransitionError(
                "stale generation (compare-and-swap failed)",
                details={"expected": expected_generation, "actual": self.generation},
            )
        allowed = TRANSITIONS.get(self.state, set())
        if target not in allowed:
            raise TransitionError(
                f"illegal transition {self.state.value} -> {target.value}",
                details={"from": self.state.value, "to": target.value},
            )
        record = {
            "from": self.state.value,
            "to": target.value,
            "at": datetime.now(timezone.utc).isoformat(),
            "actor": actor,
            "generation_before": self.generation,
            "evidence_hash": canonical_hash(evidence) if evidence is not None else None,
        }
        self.history.append(record)
        if evidence is not None:
            key = f"transition-{len(self.history):04d}-{target.value}"
            self.store[key] = evidence
        self.state = target
        self.generation += 1
        return record

    def put(self, key: str, value: Any, *, expected_generation: int | None = None) -> None:
        if expected_generation is not None and expected_generation != self.generation:
            raise TransitionError(
                "stale generation on store put",
                details={"expected": expected_generation, "actual": self.generation},
            )
        self.store[key] = value
        self.generation += 1

    def save(self, path: str | Path) -> None:
        payload = {
            "format": "pcs-next-pilot-state-v1",
            "project_id": self.project_id,
            "state": self.state.value,
            "generation": self.generation,
            "history": self.history,
            "store": self.store,
        }
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_suffix(p.suffix + ".tmp")
        tmp.write_bytes(canonicalize(payload))
        tmp.replace(p)

    @classmethod
    def load(cls, path: str | Path) -> "PilotStateMachine":
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        sm = cls(project_id=raw["project_id"], state=PilotState(raw["state"]), generation=raw["generation"])
        sm.history = list(raw.get("history", []))
        sm.store = dict(raw.get("store", {}))
        return sm


def run_pipeline(
    sm: PilotStateMachine,
    steps: list[tuple[PilotState, Callable[[PilotStateMachine], dict[str, Any]]]],
) -> PilotStateMachine:
    """Execute ordered steps; on exception move to FAILED with evidence."""
    for target, fn in steps:
        try:
            evidence = fn(sm)
            sm.transition(target, evidence=evidence)
        except Exception as exc:  # noqa: BLE001 — boundary: record and fail closed
            sm.transition(
                PilotState.FAILED,
                evidence={"error": str(exc), "error_type": type(exc).__name__},
            )
            break
    return sm
