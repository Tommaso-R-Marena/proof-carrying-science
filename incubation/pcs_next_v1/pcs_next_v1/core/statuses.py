"""Explicit assurance classifications — never collapsed to a single Boolean."""

from __future__ import annotations

from enum import Enum
from typing import Any


class AssuranceStatus(str, Enum):
    FORMALLY_VERIFIED = "FORMALLY_VERIFIED"
    COMPUTATIONALLY_TESTED = "COMPUTATIONALLY_TESTED"
    INDEPENDENTLY_REPRODUCED = "INDEPENDENTLY_REPRODUCED"
    SCIENTIFICALLY_SUPPORTED = "SCIENTIFICALLY_SUPPORTED"
    CONDITIONAL = "CONDITIONAL"
    REFUTED = "REFUTED"
    OPEN = "OPEN"
    BLOCKED = "BLOCKED"
    SKIPPED = "SKIPPED"
    UNSUPPORTED = "UNSUPPORTED"


class ClaimClass(str, Enum):
    """Separates technical workflow success from scientific claim strength."""

    TECHNICAL_VERIFICATION = "TECHNICAL_VERIFICATION"
    SCIENTIFIC_CLAIM = "SCIENTIFIC_CLAIM"
    CRYPTOGRAPHIC_AUTH = "CRYPTOGRAPHIC_AUTH"
    FORMAL_THEOREM = "FORMAL_THEOREM"
    OPERATIONAL = "OPERATIONAL"


# Partial order used only for impact / invalidation — not for "better science".
_STRENGTH = {
    AssuranceStatus.REFUTED: 0,
    AssuranceStatus.UNSUPPORTED: 1,
    AssuranceStatus.BLOCKED: 2,
    AssuranceStatus.SKIPPED: 2,
    AssuranceStatus.OPEN: 3,
    AssuranceStatus.CONDITIONAL: 4,
    AssuranceStatus.COMPUTATIONALLY_TESTED: 5,
    AssuranceStatus.INDEPENDENTLY_REPRODUCED: 6,
    AssuranceStatus.SCIENTIFICALLY_SUPPORTED: 6,
    AssuranceStatus.FORMALLY_VERIFIED: 7,
}


def classify_status(value: str | AssuranceStatus) -> AssuranceStatus:
    if isinstance(value, AssuranceStatus):
        return value
    try:
        return AssuranceStatus(value)
    except ValueError as exc:
        raise ValueError(f"unknown assurance status: {value!r}") from exc


def status_record(
    status: AssuranceStatus | str,
    *,
    claim_class: ClaimClass | str,
    reason: str,
    evidence_ids: list[str] | None = None,
    assumptions: list[str] | None = None,
    limitations: list[str] | None = None,
) -> dict[str, Any]:
    st = classify_status(status)
    cc = ClaimClass(claim_class) if isinstance(claim_class, str) else claim_class
    return {
        "status": st.value,
        "claim_class": cc.value,
        "reason": reason,
        "evidence_ids": list(evidence_ids or []),
        "assumptions": list(assumptions or []),
        "limitations": list(limitations or []),
    }


def weaker(a: AssuranceStatus, b: AssuranceStatus) -> AssuranceStatus:
    return a if _STRENGTH[a] <= _STRENGTH[b] else b
