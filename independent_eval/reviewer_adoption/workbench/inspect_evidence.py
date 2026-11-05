"""Inspect PCS-style evidence bundles for offline human review.

Never invents ACCEPT/PASS. Status fields are copied and labeled as reported.
Claim-strength labels are inspection_class only — not authority decisions.
"""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

WORKBENCH_DISCLAIMER = (
    "This workbench inspects existing evidence for human review. "
    "It does not replace PCS Lean authority, does not issue ACCEPT/PASS, "
    "and does not certify scientific validity."
)

# Inspection-only claim-strength lattice. Never elevates to ACCEPT/PASS.
INSPECTION_CLASSES = (
    "cryptographic_validity",
    "computationally_supported",
    "empirically_unsupported",
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
)
_COMP_TOKENS = (
    "COMPUTATIONALLY_SUPPORTED",
    "COMPUTATIONAL_SUPPORT",
    "COMPUTATIONALLY_VALID",
    "FORMALLY_SUPPORTED",
)
_EMPIRICAL_UNSUPPORTED_TOKENS = (
    "EMPIRICALLY_UNSUPPORTED",
    "EMPIRICAL_UNSUPPORTED",
    "UNSUPPORTED_INTERPRETATION",
)
_ADEQUACY_OPEN_TOKENS = (
    "OPEN",
    "SCIENTIFIC_ADEQUACY_OPEN",
    "ADEQUACY_OPEN",
    "SCIENTIFICALLY_UNSUPPORTED",
)
_SCIENCE_KINDS = ("scientific", "biology", "clinical", "empirical_adequacy", "adequacy")


@dataclass
class ArtifactIdentity:
    id: str
    path: str | None = None
    role: str | None = None
    media_type: str | None = None
    sha256: str | None = None
    source: str = "unknown"


@dataclass
class ClaimView:
    id: str
    statement: str
    kind: str | None = None
    assumptions: list[str] = field(default_factory=list)
    required_evidence: list[str] = field(default_factory=list)
    reported_status: str | None = None
    status_source: str | None = None
    inspection_class: str = "unknown_or_ambiguous"
    notes: list[str] = field(default_factory=list)


@dataclass
class AssumptionView:
    id: str
    statement: str
    rationale: str | None = None
    scope: list[str] = field(default_factory=list)


@dataclass
class EvidenceInspection:
    subject: str | None
    source_paths: list[str]
    claims: list[ClaimView]
    assumptions: list[AssumptionView]
    artifacts: list[ArtifactIdentity]
    outcomes: list[dict[str, Any]]
    limitations_text: str | None
    limitations_path: str | None
    reported_authority: dict[str, Any]
    warnings: list[str]
    disclaimer: str = WORKBENCH_DISCLAIMER

    def claim_strength_summary(self) -> dict[str, int]:
        counts: Counter[str] = Counter(c.inspection_class for c in self.claims)
        return {cls: int(counts.get(cls, 0)) for cls in INSPECTION_CLASSES}

    def to_dict(self) -> dict[str, Any]:
        return {
            "subject": self.subject,
            "source_paths": self.source_paths,
            "claims": [asdict(c) for c in self.claims],
            "assumptions": [asdict(a) for a in self.assumptions],
            "artifacts": [asdict(a) for a in self.artifacts],
            "outcomes": self.outcomes,
            "limitations_text": self.limitations_text,
            "limitations_path": self.limitations_path,
            "reported_authority": self.reported_authority,
            "warnings": self.warnings,
            "disclaimer": self.disclaimer,
            "claim_strength_summary": self.claim_strength_summary(),
            "workbench_issues_accept": False,
            "inspection_class_note": (
                "inspection_class values are workbench heuristics over reported_* "
                "fields only; they are not PCS authority decisions."
            ),
        }


def _norm_token(value: str | None) -> str:
    if value is None:
        return ""
    return "".join(ch if ch.isalnum() or ch == "_" else "_" for ch in str(value).upper())


def _contains_any(haystack: str, tokens: tuple[str, ...]) -> bool:
    return any(tok in haystack for tok in tokens)


def classify_claim_strength(
    *,
    reported_status: str | None,
    kind: str | None = None,
    statement: str | None = None,
) -> str:
    """Map reported evidence labels to an inspection_class.

    This is an offline reviewer aid only. It does not issue ACCEPT/PASS and
    must not be treated as PCS Lean or scientific authority.
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

    if _contains_any(status, _EMPIRICAL_UNSUPPORTED_TOKENS):
        return "empirically_unsupported"

    if science_kind and (
        _contains_any(status, _ADEQUACY_OPEN_TOKENS)
        or status in ("", "UNREPORTED")
        or _contains_any(status, _COMP_TOKENS)
    ):
        # Scientific / adequacy claims: computational labels do not establish adequacy.
        if _contains_any(status, _COMP_TOKENS):
            return "empirically_unsupported"
        return "scientific_adequacy_open"

    if _contains_any(status, _ADEQUACY_OPEN_TOKENS) and not _contains_any(status, _COMP_TOKENS):
        return "scientific_adequacy_open"

    if _contains_any(status, _COMP_TOKENS):
        return "computationally_supported"

    if status in ("", "UNREPORTED", "UNKNOWN", "AMBIGUOUS", "N_A", "NA"):
        return "unknown_or_ambiguous"

    return "unknown_or_ambiguous"


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _find_first(root: Path, names: tuple[str, ...]) -> Path | None:
    for name in names:
        candidate = root / name
        if candidate.is_file():
            return candidate
    for name in names:
        matches = sorted(root.rglob(name))
        if matches:
            return matches[0]
    return None


def _claim_from_obj(raw: dict[str, Any], status_source: str | None = None) -> ClaimView:
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
            + "; workbench did not decide it."
        )
    else:
        notes.append("No reported status found; workbench leaves claim OPEN for human review.")
        reported = "UNREPORTED"

    kind = raw.get("kind")
    statement = str(raw.get("statement") or "")
    inspection_class = classify_claim_strength(
        reported_status=str(reported),
        kind=str(kind) if kind is not None else None,
        statement=statement,
    )
    notes.append(
        f"inspection_class='{inspection_class}' is a workbench heuristic over "
        "reported_* fields only; not PCS authority."
    )
    return ClaimView(
        id=str(raw.get("id") or raw.get("claim_id") or ""),
        statement=statement,
        kind=kind,
        assumptions=list(raw.get("assumptions") or []),
        required_evidence=list(raw.get("required_evidence") or []),
        reported_status=str(reported),
        status_source=status_source,
        inspection_class=inspection_class,
        notes=notes,
    )


def _reclassify(claim: ClaimView) -> None:
    claim.inspection_class = classify_claim_strength(
        reported_status=claim.reported_status,
        kind=claim.kind,
        statement=claim.statement,
    )


def inspect_evidence_dir(evidence_dir: str | Path) -> EvidenceInspection:
    root = Path(evidence_dir).resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"evidence directory not found: {root}")
    warnings: list[str] = []
    source_paths: list[str] = []
    claims: list[ClaimView] = []
    assumptions: list[AssumptionView] = []
    artifacts: list[ArtifactIdentity] = []
    outcomes: list[dict[str, Any]] = []
    subject: str | None = None
    reported_authority: dict[str, Any] = {
        "lean_authority_accept": None,
        "bundle_valid": None,
        "source": None,
        "note": "Workbench never sets these fields; it only copies reported values.",
    }
    cert_path = _find_first(root, ("certificate.json", "pcs-certificate.json", "manifest.json"))
    receipt_path = _find_first(
        root, ("verification-receipt.json", "receipt.json", "verification_receipt.json")
    )
    limitations_path = _find_first(root, ("LIMITATIONS.md", "limitations.md"))
    if cert_path is not None:
        source_paths.append(str(cert_path))
        cert = _read_json(cert_path)
        subject = cert.get("subject") or cert.get("pilot_id")
        for raw in cert.get("claims") or []:
            if isinstance(raw, dict):
                claims.append(_claim_from_obj(raw, status_source=cert_path.name))
        for raw in cert.get("assumptions") or []:
            if isinstance(raw, dict):
                assumptions.append(
                    AssumptionView(
                        id=str(raw.get("id") or ""),
                        statement=str(raw.get("statement") or ""),
                        rationale=raw.get("rationale"),
                        scope=list(raw.get("scope") or []),
                    )
                )
        for raw in cert.get("artifacts") or []:
            if isinstance(raw, dict):
                art_path = raw.get("path")
                sha = raw.get("sha256")
                if art_path:
                    candidate = (cert_path.parent / art_path).resolve()
                    if candidate.is_file() and not sha:
                        sha = _sha256_file(candidate)
                artifacts.append(
                    ArtifactIdentity(
                        id=str(raw.get("id") or ""),
                        path=str(art_path) if art_path else None,
                        role=raw.get("role"),
                        media_type=raw.get("media_type"),
                        sha256=sha,
                        source=cert_path.name,
                    )
                )
        if "semantic_hash" in cert:
            outcomes.append(
                {
                    "kind": "certificate_semantic_hash",
                    "value": cert.get("semantic_hash"),
                    "reported": True,
                    "source": cert_path.name,
                }
            )
    else:
        warnings.append("No certificate.json/manifest.json found.")
    if receipt_path is not None:
        source_paths.append(str(receipt_path))
        receipt = _read_json(receipt_path)
        for key in ("valid", "accepted", "lean_authority", "authority_result", "result"):
            if key in receipt:
                reported_authority["source"] = receipt_path.name
                if key in ("valid", "accepted"):
                    reported_authority["bundle_valid"] = receipt.get(key)
                if key in ("lean_authority", "authority_result"):
                    reported_authority["lean_authority_accept"] = receipt.get(key)
        for item in receipt.get("claims") or receipt.get("claim_results") or []:
            if not isinstance(item, dict):
                continue
            cid = str(item.get("claim_id") or item.get("id") or "")
            decision = item.get("decision") or item.get("status")
            outcomes.append(
                {
                    "kind": "receipt_claim_outcome",
                    "claim_id": cid,
                    "reported_decision": decision,
                    "source": receipt_path.name,
                    "workbench_decided": False,
                }
            )
            matched = next((c for c in claims if c.id == cid), None)
            if matched is not None and decision is not None:
                matched.reported_status = str(decision)
                matched.status_source = receipt_path.name
                matched.notes.append(
                    f"Receipt reported decision '{decision}'; workbench did not decide."
                )
                _reclassify(matched)
                matched.notes.append(
                    f"inspection_class='{matched.inspection_class}' recomputed after "
                    "receipt reported_* update; not PCS authority."
                )
    limitations_text = None
    limitations_rel = None
    if limitations_path is not None:
        source_paths.append(str(limitations_path))
        limitations_text = limitations_path.read_text(encoding="utf-8")
        limitations_rel = str(limitations_path)
    warnings.append(
        "Human reviewers must treat reported statuses and inspection_class labels "
        "as evidence aids only; PCS authority remains external to this workbench."
    )
    return EvidenceInspection(
        subject=subject,
        source_paths=source_paths,
        claims=claims,
        assumptions=assumptions,
        artifacts=artifacts,
        outcomes=outcomes,
        limitations_text=limitations_text,
        limitations_path=limitations_rel,
        reported_authority=reported_authority,
        warnings=warnings,
    )
