"""Graded evidence lattice with explicit non-promotion."""

from __future__ import annotations

from enum import Enum


class EvidenceClass(str, Enum):
    FORMAL = "formal"
    COMPUTATIONAL = "computational"
    EMPIRICAL = "empirical"
    PROVENANCE = "provenance"


def le(left: EvidenceClass, right: EvidenceClass) -> bool:
    """Return True when `left` may discharge an obligation of class `right`."""
    if left == right:
        return True
    if left == EvidenceClass.FORMAL and right == EvidenceClass.COMPUTATIONAL:
        return True
    if right == EvidenceClass.PROVENANCE and left != EvidenceClass.PROVENANCE:
        return True
    return False


def discharges(evidence_cls: EvidenceClass, required: EvidenceClass, *, accepted: bool) -> bool:
    return bool(accepted) and le(evidence_cls, required)


def meet(a: EvidenceClass, b: EvidenceClass) -> EvidenceClass:
    if a == b:
        return a
    if EvidenceClass.PROVENANCE in (a, b):
        return a if b == EvidenceClass.PROVENANCE else b
    if {a, b} == {EvidenceClass.FORMAL, EvidenceClass.COMPUTATIONAL}:
        return EvidenceClass.COMPUTATIONAL
    return EvidenceClass.PROVENANCE
