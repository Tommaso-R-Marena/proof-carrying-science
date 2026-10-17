"""Inspection-class lattice for Assurance Card claim classification.

This module is NON-AUTHORITY. It classifies reported claim statuses into an
inspection lattice for reviewer display. It never issues ACCEPT/PASS and must
not be treated as PCS computational / cryptographic authority.
"""
from __future__ import annotations

from typing import Any

# Exact lattice required by Workstream F product brief.
INSPECTION_CLASSES = (
    "cryptographic_validity",
    "computationally_supported",
    "scientific_adequacy_open",
    "rejected_or_failed",
    "unknown_or_ambiguous",
)

_REJECT_TOKENS = (
    "REJECT",
    "REJECTED",
    "FAIL",
    "FAILED",
    "FAILURE",
    "INVALID",
    "TAMPERED",
    "HASH_MISMATCH",
    "MISMATCH",
)
_CRYPTO_TOKENS = (
    "CRYPTO",
    "CRYPTOGRAPHIC",
    "SIGNATURE",
    "INTEGRITY",
    "HASH_OK",
    "DIGEST_OK",
    "RECEIPT_VALID",
    "SIGNATURE_OK",
)
_COMP_TOKENS = (
    "COMPUTATIONALLY_SUPPORTED",
    "COMPUTATIONAL_SUPPORT",
    "COMPUTATIONALLY_VALID",
    "FORMALLY_SUPPORTED",
)
_ADEQUACY_OPEN_TOKENS = (
    "OPEN",
    "SCIENTIFIC_ADEQUACY_OPEN",
    "ADEQUACY_OPEN",
    "SCIENTIFICALLY_UNSUPPORTED",
    "EMPIRICALLY_UNSUPPORTED",
    "UNSUPPORTED_INTERPRETATION",
)
_SCIENCE_KINDS = (
    "scientific",
    "biology",
    "clinical",
    "empirical_adequacy",
    "adequacy",
)


def _norm_token(value: str | None) -> str:
    if value is None:
        return ""
    return "".join(ch if ch.isalnum() or ch == "_" else "_" for ch in str(value).upper())


def _contains_any(haystack: str, tokens: tuple[str, ...]) -> bool:
    return any(tok in haystack for tok in tokens)


def classify_claim(
    *,
    reported_status: str | None,
    kind: str | None = None,
    statement: str | None = None,
) -> str:
    """Map reported evidence labels to an inspection_class.

    Offline reviewer aid only. Does not issue ACCEPT/PASS.
    Scientific / adequacy claims with computational labels remain
    ``scientific_adequacy_open`` — computational PASS ≠ empirical adequacy.
    """
    status = _norm_token(reported_status)
    kind_n = _norm_token(kind)
    stmt = _norm_token(statement)
    combined = f"{status} {kind_n} {stmt}"

    if _contains_any(status, _REJECT_TOKENS) or _contains_any(combined, ("HASH_MISMATCH",)):
        return "rejected_or_failed"

    if _contains_any(status, _CRYPTO_TOKENS) or kind_n in (
        "CRYPTO",
        "CRYPTOGRAPHIC",
        "INTEGRITY",
        "SIGNATURE",
    ):
        return "cryptographic_validity"

    science_kinds = {_norm_token(k) for k in _SCIENCE_KINDS}
    science_kind = kind_n in science_kinds or "SCIEN" in kind_n or "CLINIC" in kind_n

    if science_kind:
        # Computational labels do not establish scientific adequacy.
        if _contains_any(status, _REJECT_TOKENS):
            return "rejected_or_failed"
        return "scientific_adequacy_open"

    if _contains_any(status, _ADEQUACY_OPEN_TOKENS) and not _contains_any(status, _COMP_TOKENS):
        return "scientific_adequacy_open"

    if _contains_any(status, _COMP_TOKENS):
        return "computationally_supported"

    if status in ("", "UNREPORTED", "UNKNOWN", "AMBIGUOUS", "N_A", "NA"):
        return "unknown_or_ambiguous"

    return "unknown_or_ambiguous"


def empty_summary() -> dict[str, int]:
    return {cls: 0 for cls in INSPECTION_CLASSES}


def summarize_classes(classes: list[str]) -> dict[str, int]:
    summary = empty_summary()
    for cls in classes:
        if cls in summary:
            summary[cls] += 1
        else:
            summary["unknown_or_ambiguous"] += 1
    return summary


def claim_view_from_raw(
    raw: dict[str, Any],
    *,
    status_source: str | None = None,
) -> dict[str, Any]:
    """Build a normalized claim view dict from a certificate/receipt claim object."""
    assessment = raw.get("assessment") or {}
    reported = (
        assessment.get("status")
        or raw.get("reported_status")
        or raw.get("status")
        or raw.get("decision")
    )
    notes: list[str] = []
    if reported is not None:
        notes.append(
            f"Status '{reported}' is reported by source evidence"
            + (f" ({status_source})" if status_source else "")
            + "; Assurance Card inspection did not decide it."
        )
    else:
        notes.append("No reported status found; left OPEN for human review.")
        reported = "UNREPORTED"

    kind = raw.get("kind")
    statement = str(raw.get("statement") or "")
    inspection_class = classify_claim(
        reported_status=str(reported),
        kind=str(kind) if kind is not None else None,
        statement=statement,
    )
    notes.append(
        f"inspection_class='{inspection_class}' is a non-authority heuristic over "
        "reported_* fields only; not PCS verify authority."
    )
    return {
        "id": str(raw.get("id") or raw.get("claim_id") or ""),
        "statement": statement,
        "kind": kind,
        "assumptions": list(raw.get("assumptions") or []),
        "required_evidence": list(raw.get("required_evidence") or []),
        "reported_status": str(reported),
        "status_source": status_source,
        "inspection_class": inspection_class,
        "notes": notes,
    }
