"""Graded assurance judgment."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from .lattice import EvidenceClass, discharges


def _cls(value: Any) -> EvidenceClass:
    if isinstance(value, EvidenceClass):
        return value
    return EvidenceClass(str(value))


def find_evidence(evidence: Sequence[Mapping[str, Any]], eid: int | str) -> Mapping[str, Any] | None:
    for item in evidence:
        if item.get("id") == eid:
            return item
    return None


def supports_claim(claim: Mapping[str, Any], evidence: Sequence[Mapping[str, Any]]) -> bool:
    required = _cls(claim["required_class"])
    for eid in claim.get("required_evidence", []):
        rec = find_evidence(evidence, eid)
        if rec is None:
            return False
        if not discharges(_cls(rec["class"]), required, accepted=bool(rec.get("accepted"))):
            return False
    return True


def assure(
    claim: Mapping[str, Any],
    evidence: Sequence[Mapping[str, Any]],
    *,
    level: EvidenceClass | str,
) -> bool:
    level_cls = _cls(level)
    if _cls(claim["required_class"]) != level_cls:
        return False
    return supports_claim(claim, evidence)
