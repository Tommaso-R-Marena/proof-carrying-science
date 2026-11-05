"""Inspection lane (non-authority): parse certificate / receipt / LIMITATIONS.

Explicit invariants:
  card_issues_accept = false
  inspection_is_not_authority = true
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .claim_lattice import (
    INSPECTION_CLASSES,
    claim_view_from_raw,
    classify_claim,
    summarize_classes,
)
from .hashing import sha256_file
from .paths import find_certificate, find_limitations, find_receipt, resolve_evidence_root

INSPECTION_DISCLAIMER = (
    "Inspection lane is non-authority. It parses certificate/receipt/LIMITATIONS "
    "and classifies reported claims into an inspection_class lattice for human "
    "review. It does not replace pcs verify, does not issue ACCEPT/PASS, and "
    "does not certify scientific or clinical adequacy."
)


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def inspect_evidence(evidence: str | Path) -> dict[str, Any]:
    """Inspect evidence directory or certificate path (non-authority)."""
    root = resolve_evidence_root(evidence)
    warnings: list[str] = []
    source_paths: list[str] = []
    claims: list[dict[str, Any]] = []
    assumptions: list[dict[str, Any]] = []
    artifacts: list[dict[str, Any]] = []
    outcomes: list[dict[str, Any]] = []
    subject: str | None = None
    reported_authority: dict[str, Any] = {
        "lean_authority_accept": None,
        "bundle_valid": None,
        "source": None,
        "note": (
            "Inspection lane never sets authority fields; it only copies "
            "reported values from receipts when present."
        ),
    }

    cert_path = find_certificate(evidence)
    if cert_path is None:
        cert_path = find_certificate(root)

    if cert_path is not None and cert_path.is_file():
        source_paths.append(str(cert_path))
        cert = _read_json(cert_path)
        subject = cert.get("subject") or cert.get("pilot_id")
        for raw in cert.get("claims") or []:
            if isinstance(raw, dict):
                claims.append(claim_view_from_raw(raw, status_source=cert_path.name))
        for raw in cert.get("assumptions") or []:
            if isinstance(raw, dict):
                assumptions.append(
                    {
                        "id": str(raw.get("id") or ""),
                        "statement": str(raw.get("statement") or ""),
                        "rationale": raw.get("rationale"),
                        "scope": list(raw.get("scope") or []),
                    }
                )
        for raw in cert.get("artifacts") or []:
            if not isinstance(raw, dict):
                continue
            art_path = raw.get("path")
            sha = raw.get("sha256")
            if art_path:
                candidate = (cert_path.parent / art_path).resolve()
                if candidate.is_file() and not sha:
                    sha = sha256_file(candidate)
            artifacts.append(
                {
                    "id": str(raw.get("id") or ""),
                    "path": str(art_path) if art_path else None,
                    "role": raw.get("role"),
                    "media_type": raw.get("media_type"),
                    "sha256": sha,
                    "source": cert_path.name,
                }
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
        if "integrity_hash" in cert:
            outcomes.append(
                {
                    "kind": "certificate_integrity_hash",
                    "value": cert.get("integrity_hash"),
                    "reported": True,
                    "source": cert_path.name,
                }
            )
    else:
        warnings.append("No certificate.json / manifest.json found.")

    receipt_path = find_receipt(root)
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
                    "card_decided": False,
                }
            )
            matched = next((c for c in claims if c["id"] == cid), None)
            if matched is not None and decision is not None:
                matched["reported_status"] = str(decision)
                matched["status_source"] = receipt_path.name
                matched["notes"].append(
                    f"Receipt reported decision '{decision}'; inspection did not decide."
                )
                matched["inspection_class"] = classify_claim(
                    reported_status=matched["reported_status"],
                    kind=matched.get("kind"),
                    statement=matched.get("statement"),
                )
                matched["notes"].append(
                    f"inspection_class='{matched['inspection_class']}' recomputed "
                    "after receipt reported_* update; not PCS authority."
                )

    limitations_path = find_limitations(root)
    limitations_text = None
    limitations_rel = None
    if limitations_path is not None:
        source_paths.append(str(limitations_path))
        limitations_text = limitations_path.read_text(encoding="utf-8")
        limitations_rel = str(limitations_path)

    warnings.append(
        "Human reviewers must treat reported statuses and inspection_class labels "
        "as evidence aids only; PCS authority remains the black-box verify lane."
    )

    summary = summarize_classes([c["inspection_class"] for c in claims])
    return {
        "lane": "inspection",
        "card_issues_accept": False,
        "inspection_is_not_authority": True,
        "disclaimer": INSPECTION_DISCLAIMER,
        "subject": subject,
        "evidence_root": str(root),
        "certificate_path": str(cert_path) if cert_path else None,
        "source_paths": source_paths,
        "claims": claims,
        "assumptions": assumptions,
        "artifacts": artifacts,
        "outcomes": outcomes,
        "limitations_text": limitations_text,
        "limitations_path": limitations_rel,
        "reported_authority": reported_authority,
        "claim_strength_summary": summary,
        "inspection_classes": list(INSPECTION_CLASSES),
        "warnings": warnings,
        "inspection_class_note": (
            "inspection_class values are Assurance Card heuristics over reported_* "
            "fields only; they are not PCS authority decisions."
        ),
    }
