from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from .decision import assess_claim
from .hashing import sha256_json
from .jsonio import strict_json_load
from .kernel import (
    CHECKER_VERSION,
    SPEC_VERSION,
    AssuranceError,
    _normalized_predicate_from_check,
    verify_certificate,
)
from .schema_validation import validate_normalized_decision_shape


WIRE_FORMAT = "pcs-normalized-decision-v1"
PREDICATE_COMMITMENT_PREFIX = "pcs-predicate-sha256:"


class NormalizationError(ValueError):
    pass


def predicate_commitment(predicate: dict[str, Any] | None) -> str | None:
    """Bind the complete canonical machine-readable predicate without weakening it.

    Lean's logical kernel only needs exact predicate identity. Rather than project
    away domain-specific fields (for example PK/PD columns and tolerances), the
    wire format commits to the entire normalized Python predicate.
    """
    if predicate is None:
        return None
    if not isinstance(predicate, dict) or not predicate.get("type"):
        raise NormalizationError("predicate must be null or a typed object")
    return PREDICATE_COMMITMENT_PREFIX + sha256_json(predicate)


def _wire_projection(value: dict[str, Any]) -> dict[str, Any]:
    out = deepcopy(value)
    out.pop("wire_semantic_hash", None)
    return out


def wire_semantic_hash(value: dict[str, Any]) -> str:
    return sha256_json(_wire_projection(value))


def _normalize_verified_object(cert: dict[str, Any], claim_id: str) -> dict[str, Any]:
    claims = {c["id"]: c for c in cert.get("claims", [])}
    if claim_id not in claims:
        raise NormalizationError(f"unknown claim id: {claim_id}")
    claim = claims[claim_id]

    required_ids = list(claim.get("required_evidence", []))
    if len(required_ids) != len(set(required_ids)):
        raise NormalizationError(f"claim {claim_id} repeats a required evidence id")

    evidence_map = {e["id"]: e for e in cert.get("evidence", [])}
    missing = [eid for eid in required_ids if eid not in evidence_map]
    if missing:
        raise NormalizationError(
            f"claim {claim_id} is missing required evidence: {', '.join(missing)}"
        )

    assumption_map = {a["id"]: a for a in cert.get("assumptions", [])}
    assumption_ids = list(claim.get("assumptions", []))
    if len(assumption_ids) != len(set(assumption_ids)):
        raise NormalizationError(f"claim {claim_id} repeats an assumption id")
    missing_assumptions = [aid for aid in assumption_ids if aid not in assumption_map]
    if missing_assumptions:
        raise NormalizationError(
            f"claim {claim_id} references missing assumptions: {', '.join(missing_assumptions)}"
        )

    claim_predicate = claim.get("predicate")
    claim_commitment = predicate_commitment(claim_predicate)

    wire_evidence: list[dict[str, Any]] = []
    for eid in required_ids:
        e = evidence_map[eid]
        ep = _normalized_predicate_from_check(e.get("check_spec", {}))
        evidence_commitment = predicate_commitment(ep)
        if evidence_commitment != claim_commitment:
            raise NormalizationError(
                f"required evidence {eid} is not exactly predicate-bound to claim {claim_id}"
            )
        wire_evidence.append(
            {
                "id": e["id"],
                "kind": e["kind"],
                "outcome": e["outcome"],
                "predicate_commitment": evidence_commitment,
            }
        )

    context = [
        {"id": assumption_map[aid]["id"], "statement": assumption_map[aid].get("statement", "")}
        for aid in assumption_ids
    ]

    fresh_assessment = assess_claim(claim, evidence_map)
    if fresh_assessment != claim.get("assessment"):
        raise NormalizationError(
            f"claim {claim_id} recorded assessment differs from pure decision kernel"
        )

    wire: dict[str, Any] = {
        "wire_format": WIRE_FORMAT,
        "source": {
            "spec_version": cert.get("spec_version"),
            "checker_version": cert.get("checker_version"),
            "certificate_semantic_hash": cert.get("semantic_hash"),
            "claim_id": claim_id,
        },
        "context": context,
        "claim": {
            "id": claim["id"],
            "kind": claim["kind"],
            "predicate_commitment": claim_commitment,
            "required_evidence": required_ids,
            "assumptions": assumption_ids,
        },
        "evidence": wire_evidence,
        "decision": fresh_assessment["status"],
        "invariants": {
            "unique_evidence_ids": True,
            "required_ids_unique": True,
            "all_required_evidence_present": True,
            "context_covers": True,
            "required_evidence_bound": True,
        },
        "wire_semantic_hash": "",
    }
    wire["wire_semantic_hash"] = wire_semantic_hash(wire)
    validate_normalized_decision_shape(wire)
    return wire


def normalize_verified_certificate(
    certificate_path: str | Path,
    claim_id: str,
) -> dict[str, Any]:
    """Verify/replay a certificate, then emit one claim-scoped normalized wire state.

    This is the executable side of the serialized -> normalized refinement boundary.
    Invalid or merely self-consistent-but-unreplayed certificates are never normalized.
    """
    path = Path(certificate_path).resolve()
    verification = verify_certificate(path)
    if not verification["valid"]:
        raise NormalizationError(
            "certificate must independently replay-verify before normalization: "
            + "; ".join(verification["errors"])
        )
    cert = strict_json_load(path)
    if cert.get("spec_version") != SPEC_VERSION:
        raise NormalizationError(f"unsupported certificate spec_version: {cert.get('spec_version')!r}")
    if cert.get("checker_version") != CHECKER_VERSION:
        raise NormalizationError(
            f"certificate checker_version differs from normalizer: {cert.get('checker_version')!r}"
        )
    return _normalize_verified_object(cert, claim_id)


def write_normalized_decision(
    certificate_path: str | Path,
    claim_id: str,
    output_path: str | Path,
) -> dict[str, Any]:
    wire = normalize_verified_certificate(certificate_path, claim_id)
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists():
        raise NormalizationError(f"refusing to overwrite normalized decision file: {out}")
    import json

    out.write_text(json.dumps(wire, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return wire
