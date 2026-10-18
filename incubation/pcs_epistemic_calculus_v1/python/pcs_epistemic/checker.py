"""Independent checker for epistemic-calculus certificates."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

from .assures import assure
from .compose import compose_assures
from .dialectic import dialectic_report
from .invalidate import compute_impact, nonimpact
from .lattice import EvidenceClass


class CheckerError(ValueError):
    pass


FORMAT = "pcs-epistemic-certificate-v1"
MAX_BYTES = 2 * 1024 * 1024


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _load(raw: bytes) -> dict[str, Any]:
    if not isinstance(raw, bytes) or len(raw) > MAX_BYTES:
        raise CheckerError("certificate bytes must be within 2 MiB")
    try:
        data = json.loads(raw.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise CheckerError("invalid UTF-8 JSON") from exc
    if not isinstance(data, dict):
        raise CheckerError("certificate must be a JSON object")
    return data


def verify_certificate(raw: bytes) -> dict[str, Any]:
    cert = _load(raw)
    if cert.get("format") != FORMAT:
        raise CheckerError(f"unsupported format: {cert.get('format')}")
    kind = cert.get("kind")
    if kind == "assures":
        claim = cert["claim"]
        evidence = cert["evidence"]
        level = EvidenceClass(cert["level"])
        ok = assure(claim, evidence, level=level)
        return {
            "format": "pcs-epistemic-receipt-v1",
            "kind": kind,
            "accepted": ok,
            "certificate_sha256": _sha(raw),
            "production_authority": False,
        }
    if kind == "compose":
        result = compose_assures(
            cert["upstream_claim"],
            cert["upstream_evidence"],
            cert["downstream_claim"],
            cert["downstream_evidence"],
            level_upstream=cert["upstream_level"],
            level_downstream=cert["downstream_level"],
        )
        return {
            "format": "pcs-epistemic-receipt-v1",
            "kind": kind,
            "accepted": result["composed_assured"],
            "detail": result,
            "certificate_sha256": _sha(raw),
            "production_authority": False,
        }
    if kind == "invalidate":
        report = compute_impact(cert["graph"], cert["changed_artifacts"])
        expected = cert.get("expected_affected_claims")
        accepted = expected is None or sorted(map(str, report["affected_claims"])) == sorted(
            map(str, expected)
        )
        return {
            "format": "pcs-epistemic-receipt-v1",
            "kind": kind,
            "accepted": accepted,
            "impact": report,
            "certificate_sha256": _sha(raw),
            "production_authority": False,
        }
    if kind == "nonimpact":
        result = nonimpact(
            cert["graph"],
            cert["changed_artifacts"],
            cert["claim_id"],
            dependency_complete=bool(cert.get("dependency_complete")),
        )
        return {
            "format": "pcs-epistemic-receipt-v1",
            "kind": kind,
            "accepted": True,
            "detail": result,
            "certificate_sha256": _sha(raw),
            "production_authority": False,
        }
    if kind == "dialectic":
        report = dialectic_report(cert["models"], cert["candidates"])
        expected_core = cert.get("expected_agreement_core")
        expected_dispute = cert.get("expected_dispute_frontier")
        ok = True
        if expected_core is not None:
            ok = ok and report["agreement_core"] == list(expected_core)
        if expected_dispute is not None:
            ok = ok and report["dispute_frontier"] == list(expected_dispute)
        return {
            "format": "pcs-epistemic-receipt-v1",
            "kind": kind,
            "accepted": ok,
            "detail": report,
            "certificate_sha256": _sha(raw),
            "production_authority": False,
        }
    raise CheckerError(f"unsupported certificate kind: {kind}")


def verify_path(path: str) -> dict[str, Any]:
    with open(path, "rb") as fh:
        return verify_certificate(fh.read())
