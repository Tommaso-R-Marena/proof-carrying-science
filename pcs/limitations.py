from __future__ import annotations

from pathlib import Path
from typing import Any


NON_CLAIMS = (
    "biological or mechanistic adequacy of the declared model",
    "clinical safety, efficacy, or patient-level predictive validity",
    "regulatory approval, acceptance, certification, or GxP validation",
    "correctness of code or systems outside the explicit PCS assurance boundary",
    "absence of defects beyond the checks and proof obligations represented in the certificate",
)


def render_limitations(certificate: dict[str, Any]) -> str:
    claims = certificate.get("claims", [])
    assumptions = certificate.get("assumptions", [])
    lines = [
        "# PCS Assurance Scope and Limitations",
        "",
        f"**Subject:** {certificate.get('subject', '')}",
        "",
        "This document is generated from the PCS certificate and is delivered with the signed evidence package. "
        "It states the scope of the assurance artifact; it is not a legal or regulatory certification.",
        "",
        "## Claim assessments",
        "",
    ]
    for claim in claims:
        status = claim.get("assessment", {}).get("status", "OPEN")
        lines.append(f"- **{claim.get('id', '')} — {status}:** {claim.get('statement', '')}")
    if not claims:
        lines.append("- No claims are present in this certificate.")

    lines += ["", "## Explicit assumptions", ""]
    for assumption in assumptions:
        lines.append(f"- **{assumption.get('id', '')}:** {assumption.get('statement', '')}")
    if not assumptions:
        lines.append("- No assumptions were declared.")

    lines += [
        "",
        "## This package does not by itself establish",
        "",
    ]
    lines.extend(f"- {item}." for item in NON_CLAIMS)
    lines += [
        "",
        "## Interpretation rule",
        "",
        "A PASS or supported claim means only that the evidence represented by the certificate "
        "satisfied the declared PCS check or proof obligation under its stated assumptions. "
        "Formal/computational assurance and empirical scientific validation remain distinct.",
        "",
        f"Certificate semantic hash: \`{certificate.get('semantic_hash', '')}\`",
        "",
    ]
    return "\n".join(lines)


def write_limitations(certificate: dict[str, Any], path: str | Path) -> Path:
    out = Path(path)
    out.write_text(render_limitations(certificate), encoding="utf-8")
    return out
