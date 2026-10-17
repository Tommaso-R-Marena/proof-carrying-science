"""Inspect PCS-style evidence bundles for offline human review.

Never invents ACCEPT/PASS. Status fields are copied and labeled as reported.
"""
from __future__ import annotations
import hashlib, json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

WORKBENCH_DISCLAIMER = (
    "This workbench inspects existing evidence for human review. "
    "It does not replace PCS Lean authority, does not issue ACCEPT/PASS, "
    "and does not certify scientific validity."
)

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
            "workbench_issues_accept": False,
        }

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
    reported = assessment.get("status") or raw.get("reported_status") or raw.get("status") or raw.get("decision")
    notes: list[str] = []
    if reported is not None:
        notes.append(f"Status '{reported}' is reported by source evidence"
                     + (f" ({status_source})" if status_source else "")
                     + "; workbench did not decide it.")
    else:
        notes.append("No reported status found; workbench leaves claim OPEN for human review.")
        reported = "UNREPORTED"
    return ClaimView(
        id=str(raw.get("id") or raw.get("claim_id") or ""),
        statement=str(raw.get("statement") or ""),
        kind=raw.get("kind"),
        assumptions=list(raw.get("assumptions") or []),
        required_evidence=list(raw.get("required_evidence") or []),
        reported_status=str(reported),
        status_source=status_source,
        notes=notes,
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
        "lean_authority_accept": None, "bundle_valid": None, "source": None,
        "note": "Workbench never sets these fields; it only copies reported values.",
    }
    cert_path = _find_first(root, ("certificate.json", "pcs-certificate.json", "manifest.json"))
    receipt_path = _find_first(root, ("verification-receipt.json", "receipt.json", "verification_receipt.json"))
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
                assumptions.append(AssumptionView(id=str(raw.get("id") or ""), statement=str(raw.get("statement") or ""), rationale=raw.get("rationale"), scope=list(raw.get("scope") or [])))
        for raw in cert.get("artifacts") or []:
            if isinstance(raw, dict):
                art_path = raw.get("path"); sha = raw.get("sha256")
                if art_path:
                    candidate = (cert_path.parent / art_path).resolve()
                    if candidate.is_file() and not sha:
                        sha = _sha256_file(candidate)
                artifacts.append(ArtifactIdentity(id=str(raw.get("id") or ""), path=str(art_path) if art_path else None, role=raw.get("role"), media_type=raw.get("media_type"), sha256=sha, source=cert_path.name))
        if "semantic_hash" in cert:
            outcomes.append({"kind": "certificate_semantic_hash", "value": cert.get("semantic_hash"), "reported": True, "source": cert_path.name})
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
            outcomes.append({"kind": "receipt_claim_outcome", "claim_id": cid, "reported_decision": decision, "source": receipt_path.name, "workbench_decided": False})
            matched = next((c for c in claims if c.id == cid), None)
            if matched is not None and decision is not None:
                matched.reported_status = str(decision)
                matched.status_source = receipt_path.name
                matched.notes.append(f"Receipt reported decision '{decision}'; workbench did not decide.")
    limitations_text = None; limitations_rel = None
    if limitations_path is not None:
        source_paths.append(str(limitations_path))
        limitations_text = limitations_path.read_text(encoding="utf-8")
        limitations_rel = str(limitations_path)
    warnings.append("Human reviewers must treat reported statuses as evidence labels only; PCS authority remains external to this workbench.")
    return EvidenceInspection(subject=subject, source_paths=source_paths, claims=claims, assumptions=assumptions, artifacts=artifacts, outcomes=outcomes, limitations_text=limitations_text, limitations_path=limitations_rel, reported_authority=reported_authority, warnings=warnings)
