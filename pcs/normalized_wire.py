from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any
import hashlib
import json

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
from .schema_validation import validate_normalized_decision_shape, SchemaValidationError


WIRE_FORMAT = "pcs-normalized-decision-v1"
NORMALIZED_INDEX_FORMAT = "pcs-normalized-decision-index-v1"
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



def validate_normalized_wire(wire: dict[str, Any]) -> dict[str, Any]:
    """Independently recompute the semantic invariants of a normalized wire object."""
    errors: list[str] = []
    try:
        validate_normalized_decision_shape(wire)
    except SchemaValidationError as exc:
        return {"valid": False, "errors": [str(exc)]}

    supplied_hash = wire.get("wire_semantic_hash")
    expected_hash = wire_semantic_hash(wire)
    if supplied_hash != expected_hash:
        errors.append("wire semantic hash mismatch")

    claim = wire.get("claim", {})
    source = wire.get("source", {})
    if source.get("claim_id") != claim.get("id"):
        errors.append("source claim id does not match normalized claim id")

    required_ids = list(claim.get("required_evidence", []))
    evidence = list(wire.get("evidence", []))
    evidence_ids = [e.get("id") for e in evidence]
    if len(evidence_ids) != len(set(evidence_ids)):
        errors.append("normalized evidence ids are not unique")
    if len(required_ids) != len(set(required_ids)):
        errors.append("normalized required evidence ids are not unique")
    if evidence_ids != required_ids:
        errors.append("normalized evidence scope is not exactly the required evidence list")

    assumption_ids = list(claim.get("assumptions", []))
    context_ids = [a.get("id") for a in wire.get("context", [])]
    if len(context_ids) != len(set(context_ids)):
        errors.append("normalized context assumption ids are not unique")
    if len(assumption_ids) != len(set(assumption_ids)):
        errors.append("normalized claim assumption ids are not unique")
    if context_ids != assumption_ids:
        errors.append("normalized context is not exactly the claim assumption list")

    claim_commitment = claim.get("predicate_commitment")
    for e in evidence:
        if e.get("predicate_commitment") != claim_commitment:
            errors.append(
                f"normalized evidence {e.get('id')} predicate commitment differs from claim"
            )

    evidence_map = {e["id"]: e for e in evidence if isinstance(e.get("id"), str)}
    fresh = assess_claim(claim, evidence_map)
    if fresh.get("status") != wire.get("decision"):
        errors.append(
            f"normalized decision mismatch: recorded={wire.get('decision')} recomputed={fresh.get('status')}"
        )

    expected_invariants = {
        "unique_evidence_ids": len(evidence_ids) == len(set(evidence_ids)),
        "required_ids_unique": len(required_ids) == len(set(required_ids)),
        "all_required_evidence_present": all(eid in evidence_map for eid in required_ids),
        "context_covers": all(aid in set(context_ids) for aid in assumption_ids),
        "required_evidence_bound": all(
            e.get("predicate_commitment") == claim_commitment for e in evidence
        ),
    }
    if wire.get("invariants") != expected_invariants:
        errors.append("recorded invariant summary does not match recomputed invariants")

    return {
        "valid": not errors,
        "errors": errors,
        "wire_semantic_hash": supplied_hash,
        "recomputed_decision": fresh.get("status"),
        "claim_id": claim.get("id"),
    }

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
    validation = validate_normalized_wire(wire)
    if not validation["valid"]:
        raise NormalizationError(
            "internal normalized wire invariant failure: " + "; ".join(validation["errors"])
        )
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



def verify_normalized_against_certificate(
    wire: dict[str, Any],
    certificate_path: str | Path,
) -> dict[str, Any]:
    """Check both internal wire invariants and exact derivation from a verified certificate."""
    internal = validate_normalized_wire(wire)
    errors = list(internal["errors"])
    if not internal["valid"]:
        return {
            **internal,
            "source_certificate_match": False,
        }

    claim_id = wire.get("source", {}).get("claim_id")
    try:
        expected = normalize_verified_certificate(certificate_path, claim_id)
    except (NormalizationError, OSError) as exc:
        errors.append(f"cannot reproduce wire from source certificate: {exc}")
        return {
            **internal,
            "valid": False,
            "errors": errors,
            "source_certificate_match": False,
        }

    source_match = expected == wire
    if not source_match:
        errors.append("normalized wire does not exactly match source certificate normalization")

    return {
        **internal,
        "valid": not errors,
        "errors": errors,
        "source_certificate_match": source_match,
        "source_certificate_semantic_hash": expected["source"]["certificate_semantic_hash"],
    }

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


def write_normalized_set(
    certificate_path: str | Path,
    output_dir: str | Path,
) -> dict[str, Any]:
    """Verify once, then emit one portable normalized wire file per certificate claim."""
    cert_path = Path(certificate_path).resolve()
    verification = verify_certificate(cert_path)
    if not verification["valid"]:
        raise NormalizationError(
            "certificate must independently replay-verify before normalized-set export: "
            + "; ".join(verification["errors"])
        )
    cert = strict_json_load(cert_path)
    out = Path(output_dir).resolve()
    if out.exists():
        if not out.is_dir():
            raise NormalizationError(f"normalized output is not a directory: {out}")
        if any(out.iterdir()):
            raise NormalizationError(f"normalized output directory must be empty: {out}")
    else:
        out.mkdir(parents=True, exist_ok=False)

    entries: list[dict[str, Any]] = []
    for claim in cert.get("claims", []):
        claim_id = claim["id"]
        wire = _normalize_verified_object(cert, claim_id)
        storage_key = hashlib.sha256(claim_id.encode("utf-8")).hexdigest()[:24]
        rel = f"{storage_key}.json"
        path = out / rel
        path.write_text(json.dumps(wire, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        entries.append(
            {
                "claim_id": claim_id,
                "path": rel,
                "decision": wire["decision"],
                "wire_semantic_hash": wire["wire_semantic_hash"],
            }
        )

    index = {
        "index_format": NORMALIZED_INDEX_FORMAT,
        "certificate_semantic_hash": cert.get("semantic_hash"),
        "entries": entries,
    }
    (out / "index.json").write_text(
        json.dumps(index, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return index


def verify_normalized_set(
    normalized_dir: str | Path,
    certificate_path: str | Path,
) -> dict[str, Any]:
    """Verify a delivered normalized index and exact wire derivation from its certificate."""
    root = Path(normalized_dir).resolve()
    cert_path = Path(certificate_path).resolve()
    errors: list[str] = []
    index_path = root / "index.json"
    if not index_path.is_file():
        return {"present": False, "valid": True, "errors": [], "entries": []}

    try:
        index = strict_json_load(index_path)
        cert = strict_json_load(cert_path)
    except Exception as exc:
        return {
            "present": True,
            "valid": False,
            "errors": [f"cannot parse normalized index/certificate: {type(exc).__name__}: {exc}"],
            "entries": [],
        }

    if index.get("index_format") != NORMALIZED_INDEX_FORMAT:
        errors.append("unsupported normalized index format")
    if index.get("certificate_semantic_hash") != cert.get("semantic_hash"):
        errors.append("normalized index certificate semantic hash mismatch")

    entries = index.get("entries")
    if not isinstance(entries, list):
        return {
            "present": True,
            "valid": False,
            "errors": errors + ["normalized index entries must be an array"],
            "entries": [],
        }

    cert_claim_ids = [c.get("id") for c in cert.get("claims", [])]
    entry_claim_ids = [e.get("claim_id") for e in entries if isinstance(e, dict)]
    if entry_claim_ids != cert_claim_ids:
        errors.append("normalized index claim order/scope differs from certificate claims")
    if len(entry_claim_ids) != len(set(entry_claim_ids)):
        errors.append("normalized index contains duplicate claim ids")

    results: list[dict[str, Any]] = []
    seen_paths: set[str] = set()
    for entry in entries:
        if not isinstance(entry, dict):
            errors.append("normalized index entry must be an object")
            continue
        rel = entry.get("path")
        claim_id = entry.get("claim_id")
        if not isinstance(rel, str) or not rel or "/" in rel or "\\" in rel or rel in {".", ".."}:
            errors.append(f"unsafe normalized wire path for claim {claim_id}: {rel!r}")
            continue
        if rel in seen_paths:
            errors.append(f"duplicate normalized wire path: {rel}")
            continue
        seen_paths.add(rel)
        path = (root / rel).resolve()
        try:
            path.relative_to(root)
        except ValueError:
            errors.append(f"normalized wire escapes normalized directory: {rel!r}")
            continue
        if not path.is_file():
            errors.append(f"normalized wire missing for claim {claim_id}: {rel}")
            continue
        try:
            wire = strict_json_load(path)
        except Exception as exc:
            errors.append(f"cannot parse normalized wire {rel}: {type(exc).__name__}: {exc}")
            continue

        result = verify_normalized_against_certificate(wire, cert_path)
        results.append({"claim_id": claim_id, "path": rel, **result})
        if not result["valid"]:
            errors.extend([f"normalized {claim_id}: {e}" for e in result["errors"]])
        if wire.get("source", {}).get("claim_id") != claim_id:
            errors.append(f"normalized index claim id differs from wire source: {claim_id}")
        if wire.get("decision") != entry.get("decision"):
            errors.append(f"normalized index decision mismatch for claim {claim_id}")
        if wire.get("wire_semantic_hash") != entry.get("wire_semantic_hash"):
            errors.append(f"normalized index wire hash mismatch for claim {claim_id}")

    expected_files = {"index.json"} | {
        e.get("path") for e in entries if isinstance(e, dict) and isinstance(e.get("path"), str)
    }
    actual_files = {p.name for p in root.iterdir() if p.is_file()}
    if actual_files != expected_files:
        errors.append(
            f"normalized directory file set mismatch: expected={sorted(expected_files)} actual={sorted(actual_files)}"
        )

    return {
        "present": True,
        "valid": not errors,
        "errors": errors,
        "certificate_semantic_hash": index.get("certificate_semantic_hash"),
        "entries": results,
    }
